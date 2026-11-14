/* Server-only transport. Public browser requests never carry the backend Bearer secret. */
function createProxy({ baseUrl, token, origins = [], allowLocalHttp = false } = {}) {
  return async function handler(req, res) {
    const reply = (status, body) => {
      res.statusCode = status;
      res.setHeader('Content-Type', 'application/json');
      res.setHeader('Cache-Control', 'no-store');
      res.setHeader('X-Content-Type-Options', 'nosniff');
      res.end(JSON.stringify(body));
    };
    let upstream;
    try {
      upstream = new URL(baseUrl);
      if ((upstream.protocol !== 'https:' && !(allowLocalHttp && upstream.hostname === '127.0.0.1')) ||
          upstream.username || upstream.password || upstream.search || upstream.hash || upstream.pathname !== '/') {
        throw new Error('Invalid backend origin');
      }
      if (typeof token !== 'string' || token.length < 32 || !origins.length) throw new Error('Unconfigured');
    } catch {
      return reply(503, { error: 'On-demand processing is unavailable.' });
    }
    const path = req.url.split('?')[0];
    const collection = path === '/api/jobs';
    const individual = /^\/api\/jobs\/aoi_[0-9a-f]{16}(?:\/result)?$/.test(path);
    if (!collection && !individual) return reply(404, { error: 'Not found.' });
    if ((collection && req.method !== 'POST') || (individual && req.method !== 'GET')) {
      return reply(405, { error: 'Unsupported method.' });
    }
    const origin = req.headers.origin;
    if ((origin && !origins.includes(origin)) || req.headers['sec-fetch-site'] === 'cross-site' ||
        (req.method === 'POST' && !origin)) {
      return reply(403, { error: 'Origin is not allowed.' });
    }
    let body;
    if (req.method === 'POST') {
      if (req.headers['content-type']?.split(';')[0].trim() !== 'application/json') {
        return reply(415, { error: 'Use Content-Type: application/json.' });
      }
      try {
        if (Number(req.headers['content-length']) > 8192) return reply(413, { error: 'Body too large.' });
        if (req.body !== undefined) {
          body = typeof req.body === 'string' ? req.body : JSON.stringify(req.body);
        } else {
          const chunks = [];
          let length = 0;
          for await (const chunk of req) {
            length += Buffer.byteLength(chunk);
            if (length > 8192) return reply(413, { error: 'Body too large.' });
            chunks.push(Buffer.from(chunk));
          }
          body = Buffer.concat(chunks).toString('utf8');
        }
        if (Buffer.byteLength(body) > 8192) return reply(413, { error: 'Body too large.' });
        JSON.parse(body);
      } catch {
        return reply(400, { error: 'Invalid JSON body.' });
      }
    }
    try {
      const response = await fetch(new URL(path, upstream), {
        method: req.method,
        headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' },
        body, redirect: 'error', signal: AbortSignal.timeout(10000),
      });
      if (!response.headers.get('content-type')?.toLowerCase().startsWith('application/json')) {
        return reply(502, { error: 'Analysis service returned an invalid response.' });
      }
      const text = await response.text();
      if (text.includes(token)) return reply(502, { error: 'Analysis service returned an invalid response.' });
      if (response.status === 401 || response.status === 403) {
        return reply(503, { error: 'Analysis service authorization is unavailable.' });
      }
      const retry = response.headers.get('retry-after');
      if (response.status === 429 && /^\d{1,5}$/.test(retry || '')) res.setHeader('Retry-After', retry);
      return reply(response.status, JSON.parse(text));
    } catch {
      return reply(502, { error: 'Analysis service is unavailable; retry later.' });
    }
  };
}

module.exports = createProxy({
  baseUrl: process.env.JOB_BACKEND_ORIGIN,
  token: process.env.JOB_API_ACCESS_TOKEN,
  origins: (process.env.JOB_PROXY_ALLOWED_ORIGINS || '').split(',').filter(Boolean),
});
module.exports.createProxy = createProxy;

// Deployment gate for the existing precomputed release. No NASA requests or statistics.
// Operates only on generated build output; source datasets/components are never rewritten.
import assert from 'node:assert/strict';
import { readFileSync, writeFileSync, unlinkSync } from 'node:fs';
import { resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const root = fileURLToPath(new URL('../', import.meta.url));
const directory = resolve(process.argv[2] ?? `${root}/src/web/dist/data`);
const reference = JSON.parse(readFileSync(`${root}/data/processed/nile_delta_ndvi.result.json`));
const index = JSON.parse(readFileSync(`${directory}/index.json`));
assert(Array.isArray(index) && index.length > 0, 'Missing precomputed catalogue');
const selected = [];
const developmentFiles = [];
for (const entry of index) {
  assert(/^results\/[a-z0-9_-]+\.json$/.test(entry.file), 'Unsafe result asset path');
  const path = `${directory}/${entry.file}`;
  const result = JSON.parse(readFileSync(path)); // missing/HTML data fails the deployment
  if (result.metadata?.is_mock === true) {
    developmentFiles.push(path);
    continue;
  }
  assert(entry.region === 'nile_delta' && entry.variable === 'NDVI',
    'Register independent verification before adding another real release dataset');
  assert(result.metadata.is_mock === false, 'A real result must explicitly declare is_mock=false');
  for (const key of ['metadata', 'series']) {
    assert.deepEqual(result[key], reference[key], `Published ${key} differs from the verified export`);
  }
  for (const [key, expected] of Object.entries(reference.trend)) {
    const actual = result.trend[key];
    if (typeof expected === 'number') {
      // Permit floating-point roundoff, not material changes to verified statistics.
      const tolerance = 8 * Number.EPSILON * Math.max(Math.abs(actual), Math.abs(expected));
      assert(Number.isFinite(actual) && Math.abs(actual - expected) <= tolerance,
        `Published trend.${key} differs from the verified export`);
    } else {
      assert.deepEqual(actual, expected, `Published trend.${key} differs from the verified export`);
    }
  }
  for (const key of ['region', 'lat', 'lon', 'variable', 'unit', 'source']) {
    assert.deepEqual(entry[key], result.metadata[key], `Catalogue ${key} mismatch`);
  }
  assert(entry.significant === result.trend.significant, 'Catalogue significance mismatch');
  assert(entry.headline === result.verdict.headline, 'Catalogue verdict mismatch');
  selected.push(entry);
}
assert(selected.length === 1, 'Release requires exactly one verified Nile Delta result');
// All reads/checks finish before modifying generated artifacts.
writeFileSync(`${directory}/index.json`, `${JSON.stringify(selected, null, 2)}\n`);
for (const path of developmentFiles) unlinkSync(path);
console.log('Static release: verified Nile Delta NDVI; development placeholders excluded.');

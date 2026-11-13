import type { AoiJobStatus, AoiSelection, TrendResult } from "../types/trend";

export interface SubmitJobResponse {
  mode: "live" | "unavailable";
  job?: AoiJobStatus;
  message?: string;
}

export function makeBboxAround(lat: number, lon: number, sizeDeg = 0.5): [number, number, number, number] {
  const half = sizeDeg / 2;
  const clampedLat = Math.max(-85, Math.min(85, lat));
  const minLon = Number(Math.max(-180, lon - half).toFixed(4));
  const maxLon = Number(Math.min(180, lon + half).toFixed(4));
  const minLat = Number(Math.max(-90, clampedLat - half).toFixed(4));
  const maxLat = Number(Math.min(90, clampedLat + half).toFixed(4));
  return [minLon, minLat, maxLon, maxLat];
}

export function randomLandSeedAoi(seed: number): AoiSelection {
  // Deterministic PRNG (mulberry32) for reproducible client-side coordinates
  let t = seed >>> 0;
  const rand = () => {
    t += 0x6d2b79f5;
    let r = Math.imul(t ^ (t >>> 15), 1 | t);
    r ^= r + Math.imul(r ^ (r >>> 7), 61 | r);
    return ((r ^ (r >>> 14)) >>> 0) / 4294967296;
  };
  const lat = Number((-45 + rand() * 110).toFixed(4));
  const lon = Number((-130 + rand() * 260).toFixed(4));
  return {
    lat,
    lon,
    bbox: makeBboxAround(lat, lon, 0.5),
    label: `Custom AOI (seed ${seed})`,
    isRandom: true,
  };
}

export async function submitAnalysisJob(payload: {
  bbox: [number, number, number, number];
  product: string;
  start_date: string;
  end_date: string;
}): Promise<SubmitJobResponse> {
  try {
    const resp = await fetch("/api/jobs", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    if (resp.status === 404 || resp.status === 405) {
      return {
        mode: "unavailable",
        message:
          "Live NASA job API (/api/jobs) is not active in this static deployment. Select a pre-computed dataset or dispatch the GitHub Actions NASA AOI workflow.",
      };
    }
    const data = await resp.json();
    if (!resp.ok) {
      return {
        mode: "live",
        message: data?.error || `Job request rejected (HTTP ${resp.status}).`,
      };
    }
    return { mode: "live", job: data as AoiJobStatus };
  } catch {
    return {
      mode: "unavailable",
      message:
        "Could not reach /api/jobs. Showing pre-computed NASA datasets only (no simulated results).",
    };
  }
}

export async function fetchJobStatus(jobId: string): Promise<AoiJobStatus> {
  const resp = await fetch(`/api/jobs/${encodeURIComponent(jobId)}`);
  if (!resp.ok) {
    throw new Error(`Failed to fetch job status (HTTP ${resp.status})`);
  }
  return (await resp.json()) as AoiJobStatus;
}

export async function fetchJobResult(resultFile: string): Promise<TrendResult> {
  const path = resultFile.startsWith("/") ? resultFile : `/data/${resultFile}`;
  const resp = await fetch(path);
  if (!resp.ok) {
    throw new Error(`Failed to load job result ${path} (HTTP ${resp.status})`);
  }
  return (await resp.json()) as TrendResult;
}

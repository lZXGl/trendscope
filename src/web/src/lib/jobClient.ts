import { parseJob, parseResult, readJson } from "./contracts";
import { loadResult } from "./dataLoader";
import { assertJobContinuity, assertJobRequest, assertJobResult, assertResultPath, type AnalysisRequest } from "./jobIdentity";
import type { AoiJobStatus, AoiSelection, TrendResult } from "../types/trend";

// Public same-origin proxy path only. The proxy adds Bearer auth server-side.
// No token or backend credentials belong in a VITE_ environment value.
export const JOB_API_BASE = (import.meta.env?.VITE_JOB_API_BASE_URL ?? "").replace(/\/$/, "");
export const LIVE_JOBS_ENABLED = JOB_API_BASE === "/api";
export const UNAVAILABLE_MESSAGE = "On-demand NASA processing is unavailable in this static release. The precomputed observed dataset remains available.";

export interface SubmitJobResponse {
  mode: "live" | "unavailable";
  job?: AoiJobStatus;
  message?: string;
}

export function makeBboxAround(lat: number, lon: number, sizeDeg = 0.5): [number, number, number, number] {
  if (![lat, lon, sizeDeg].every(Number.isFinite) || Math.abs(lat) > 90 || Math.abs(lon) > 180 || sizeDeg < 0.1 || sizeDeg > 2) {
    throw new Error("Unsupported AOI coordinates or size.");
  }
  const half = sizeDeg / 2;
  const centreLat = Math.max(-90 + half, Math.min(90 - half, lat));
  const centreLon = Math.max(-180 + half, Math.min(180 - half, lon));
  return [centreLon - half, centreLat - half, centreLon + half, centreLat + half]
    .map(v => Number(v.toFixed(4))) as [number, number, number, number];
}

// Candidate continental boxes; these are NOT a land mask. The backend must validate land.
const LAND_BOXES: readonly [number, number, number, number][] = [
  [33, 48, -118, -82],   // North America interior
  [-18, -3, -68, -44],   // South America (Amazon / Cerrado)
  [44, 54, 4, 28],       // Central/Eastern Europe
  [18, 30, 12, 34],      // North Africa / Nile / Sahara
  [-22, 8, 16, 36],      // Sub-Saharan Africa
  [22, 48, 52, 112],     // Central & East Asia
  [-30, -18, 120, 144],  // Australia interior
];

export function randomLandSeedAoi(seed: number): AoiSelection {
  // Deterministic PRNG (mulberry32) for reproducible client-side land coordinates
  let t = seed >>> 0;
  const rand = () => {
    t += 0x6d2b79f5;
    let r = Math.imul(t ^ (t >>> 15), 1 | t);
    r ^= r + Math.imul(r ^ (r >>> 7), 61 | r);
    return ((r ^ (r >>> 14)) >>> 0) / 4294967296;
  };
  const box = LAND_BOXES[Math.floor(rand() * LAND_BOXES.length)];
  const [minLat, maxLat, minLon, maxLon] = box;
  const lat = Number((minLat + rand() * (maxLat - minLat)).toFixed(4));
  const lon = Number((minLon + rand() * (maxLon - minLon)).toFixed(4));
  return {
    lat,
    lon,
    bbox: makeBboxAround(lat, lon, 0.5),
    label: `Candidate AOI (seed ${seed}; land unverified)`,
    isRandom: true,
  };
}

export async function submitAnalysisJob(payload: AnalysisRequest): Promise<SubmitJobResponse> {
  if (!LIVE_JOBS_ENABLED) return { mode: "unavailable", message: UNAVAILABLE_MESSAGE };
  validateRequest(payload);
  let resp: Response;
  try {
    resp = await fetch(`${JOB_API_BASE}/jobs`, {
      signal: AbortSignal.timeout(15000),
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
      cache: "no-store",
      redirect: "error",
    });
  } catch {
    return { mode: "unavailable", message: "Could not reach /api/jobs. Showing pre-computed NASA datasets only (no simulated results)." };
  }
  if (resp.status === 401 || resp.status === 403) throw new Error(API_ACCESS_MESSAGE);
  if (resp.status === 404 || resp.status === 405) {
    return { mode: "unavailable", message: "Live NASA job API (/api/jobs) is not active in this static deployment. Select a pre-computed dataset." };
  }
  if (!resp.headers.get("content-type")?.includes("application/json")) {
    return { mode: "unavailable", message: UNAVAILABLE_MESSAGE };
  }
  const data = await resp.json();
  if (!resp.ok) {
    return { mode: "live", message: typeof data?.error === "string" ? data.error : `Job request rejected (HTTP ${resp.status}).` };
  }
  const job = parseJob(data);
  assertJobRequest(job, payload);
  return { mode: "live", job };
}

export const API_ACCESS_MESSAGE = "Analysis service access was denied. Contact the service operator; no result has been substituted.";
async function apiJson(path: string): Promise<unknown> {
  const response = await fetch(path, { signal: AbortSignal.timeout(15000), cache: "no-store", redirect: "error" });
  if (response.status === 401 || response.status === 403) throw new Error(API_ACCESS_MESSAGE);
  return readJson(response);
}

export async function fetchJobStatus(expected: AoiJobStatus): Promise<AoiJobStatus> {
  if (!/^aoi_[0-9a-f]{16}$/.test(expected.job_id)) throw new Error("Invalid job identifier.");
  const job = parseJob(await apiJson(`${JOB_API_BASE}/jobs/${expected.job_id}`));
  assertJobContinuity(job, expected);
  return job;
}

export async function fetchJobResult(job: AoiJobStatus): Promise<TrendResult> {
  assertResultPath(job);
  const resultFile = job.result_file!;
  const result = resultFile.startsWith("results/")
    ? await loadResult(resultFile)
    : parseResult(await apiJson(resultFile));
  assertJobResult(result, job);
  return result;
}

export function validateRequest(payload: { bbox: number[]; product: string; start_date: string; end_date: string }) {
  const [west, south, east, north] = payload.bbox;
  if (payload.bbox.length !== 4 || !payload.bbox.every(Number.isFinite) ||
      west < -180 || east > 180 || south < -90 || north > 90 ||
      Number((east - west).toFixed(4)) < 0.1 || east - west > 2 ||
      Number((north - south).toFixed(4)) < 0.1 || north - south > 2) {
    throw new Error("AOI must have valid bounds, 0.1–2.0 degrees wide and high.");
  }
  if (payload.product !== "MOD13A3.061") throw new Error("Unsupported NASA product.");
  const parse = (value: string) => {
    if (!/^\d{2}-\d{2}-\d{4}$/.test(value)) throw new Error("Enter both valid dates.");
    const [m, d, y] = value.split("-");
    const iso = `${y}-${m}-${d}`;
    const time = Date.parse(`${iso}T00:00:00Z`);
    if (!Number.isFinite(time) || new Date(time).toISOString().slice(0, 10) !== iso) {
      throw new Error("Enter both valid calendar dates.");
    }
    return time;
  };
  const start = parse(payload.start_date);
  const end = parse(payload.end_date);
  if (start >= end) throw new Error("Start date must precede end date.");
  if (start < Date.UTC(2001, 0, 1) || end > Date.UTC(2024, 11, 31)) {
    throw new Error("Analysis dates must be within 2001–2024.");
  }
}

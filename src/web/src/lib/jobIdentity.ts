import { monthOrdinal } from "./contracts";
import type { AoiJobStatus, TrendResult } from "../types/trend";

export type AnalysisRequest = Pick<AoiJobStatus["request"], "bbox" | "product" | "start_date" | "end_date">;
const requestKeys = ["product", "start_date", "end_date"] as const;
const processingKeys = ["allow_marginal", "min_pixel_presence", "processing_version"] as const;

// The API normalizes coordinates to four decimals. Equal centres do not imply equal AOIs.
export function assertJobRequest(job: AoiJobStatus, expected: AnalysisRequest) {
  if (job.request.bbox.some((v, i) => v !== Number(expected.bbox[i].toFixed(4))) ||
      requestKeys.some(key => job.request[key] !== expected[key]) ||
      job.request.allow_marginal !== false || job.request.min_pixel_presence !== 0.8) {
    throw new Error("The service returned a job for a different request. No result has been substituted.");
  }
  if (job.status === "completed") assertResultPath(job);
}

export function assertJobContinuity(job: AoiJobStatus, expected: AoiJobStatus) {
  assertJobRequest(job, expected.request);
  if (job.job_id !== expected.job_id ||
      processingKeys.some(key => job.request[key] !== expected.request[key])) {
    throw new Error("Status belongs to a different job or processing request. No result has been substituted.");
  }
}

export function assertResultPath(job: AoiJobStatus) {
  if (job.status !== "completed" ||
      ![`/api/jobs/${job.job_id}/result`, `results/${job.job_id}.json`].includes(job.result_file ?? "")) {
    throw new Error("Completed job points to a different or unavailable result. No result has been substituted.");
  }
}

const requestMonth = (date: string) => `${date.slice(6)}-${date.slice(0, 2)}`;

export function assertJobResult(result: TrendResult, job: AoiJobStatus) {
  assertResultPath(job);
  const [w, s, e, n] = job.request.bbox;
  const start = requestMonth(job.request.start_date);
  const end = requestMonth(job.request.end_date);
  const first = monthOrdinal(start);
  const last = monthOrdinal(end);
  if (result.metadata.region !== job.job_id ||
      Math.abs(result.metadata.lat - (s + n) / 2) > 0.0001 ||
      Math.abs(result.metadata.lon - (w + e) / 2) > 0.0001 ||
      job.request.product !== "MOD13A3.061" ||
      result.metadata.variable !== "NDVI" || result.metadata.unit !== "NDVI" ||
      result.metadata.source !== "NASA MODIS MOD13A3.061" ||
      result.trend.slope_unit !== "NDVI/decade" ||
      result.metadata.date_range.start !== start || result.metadata.date_range.end !== end ||
      result.series.length !== last - first + 1 ||
      result.series.some((point, i) => monthOrdinal(point.date) !== first + i)) {
    throw new Error("The returned result does not match the requested area, job, product or date window. No result has been substituted.");
  }
}

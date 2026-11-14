import Ajv2020 from "ajv/dist/2020.js";
import indexSchema from "../../../../schemas/index.schema.json";
import resultSchema from "../../../../schemas/trend_result.schema.json";
import jobSchema from "../../../../schemas/job_status.schema.json";
import type { AoiJobStatus, TrendIndexItem, TrendResult } from "../types/trend";

const ajv = new Ajv2020({ allErrors: true });
const indexValidator = ajv.compile<TrendIndexItem[]>(indexSchema);
const resultValidator = ajv.compile<TrendResult>(resultSchema);
const jobValidator = ajv.compile<AoiJobStatus>(jobSchema);

export function monthOrdinal(value: string): number {
  if (!/^[0-9]{4}-(0[1-9]|1[0-2])$/.test(value) || value.startsWith("0000")) {
    throw new Error("Result contains an invalid calendar month.");
  }
  return Number(value.slice(0, 4)) * 12 + Number(value.slice(5)) - 1;
}

export function parseIndex(data: unknown): TrendIndexItem[] {
  if (!indexValidator(data)) throw new Error("Dataset catalogue does not match the shared contract.");
  if (new Set(data.map(item => item.file)).size !== data.length) {
    throw new Error("Dataset catalogue contains duplicate result files.");
  }
  return data;
}

export function parseResult(data: unknown): TrendResult {
  if (!resultValidator(data)) throw new Error("Result does not match the shared scientific contract.");
  if (data.metadata.is_mock !== false) {
    throw new Error("Development or unclassified results are unavailable in the observed-data release.");
  }
  const ordinals = data.series.map(p => monthOrdinal(p.date));
  if (ordinals.some((v, i) => i > 0 && v <= ordinals[i - 1]) ||
      data.series[0].date !== data.metadata.date_range.start ||
      data.series.at(-1)?.date !== data.metadata.date_range.end) {
    throw new Error("Result calendar is unordered, duplicated or inconsistent with its date range.");
  }
  return data;
}

export function parseJob(data: unknown): AoiJobStatus {
  if (!jobValidator(data)) throw new Error("Job response does not match the shared status contract.");
  if (data.status === "completed" && !data.result_file) {
    throw new Error("Completed job has no available result file.");
  }
  return data;
}

export async function readJson(response: Response): Promise<unknown> {
  if (!response.ok) throw new Error(`Request failed (HTTP ${response.status}).`);
  if (!response.headers.get("content-type")?.includes("application/json")) {
    throw new Error("Expected JSON but received a non-JSON response. Check static/API routing.");
  }
  return response.json();
}

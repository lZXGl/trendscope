import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { assertJobRequest, assertJobContinuity, assertJobResult } from "../src/lib/jobIdentity";
import { fetchJobResult, fetchJobStatus, validateRequest } from "../src/lib/jobClient";
import { parseResult } from "../src/lib/contracts";
import type { AoiJobStatus, TrendResult } from "../src/types/trend";

const id = "aoi_1234567890abcdef";
const job = (): AoiJobStatus => ({
  job_id: id, status: "completed", stage: null,
  request: { bbox: [30.7, 30.7, 31.3, 31.2], product: "MOD13A3.061", start_date: "01-01-2001", end_date: "12-31-2024", allow_marginal: false, min_pixel_presence: 0.8, processing_version: "2" },
  nasa_task_id: null, error: null, retryable: false,
  result_file: `/api/jobs/${id}/result`, created_at: "2026-11-14T00:00:00Z", updated_at: "2026-11-14T00:00:00Z",
});
// Synthetic transport fixtures only; never published or used as scientific results.
const result = (): TrendResult => {
  const value = JSON.parse(readFileSync("public/data/results/nile_delta_ndvi.json", "utf8"));
  value.metadata.region = id;
  return value;
};

test("exact full request and result identity accepts API and same-job static paths", () => {
  const expected = job();
  assertJobRequest(expected, expected.request);
  assertJobResult(parseResult(result()), expected);
  expected.result_file = `results/${id}.json`;
  assertJobResult(parseResult(result()), expected);
});

test("equal centres cannot hide wrong bbox, product or exact daily date window", () => {
  const expected = job();
  for (const request of [
    { ...expected.request, bbox: [30.6, 30.6, 31.4, 31.3] as [number, number, number, number] },
    { ...expected.request, bbox: [30.70005, 30.7, 31.3, 31.2] as [number, number, number, number] },
    { ...expected.request, product: "wrong" },
    { ...expected.request, start_date: "01-02-2001" },
    { ...expected.request, end_date: "12-30-2024" },
    { ...expected.request, allow_marginal: true },
    { ...expected.request, min_pixel_presence: 0.5 },
  ]) assert.throws(() => assertJobRequest({ ...expected, request }, expected.request), /different request/);
});

test("poll continuity pins exact ID and processing settings, not only geography", () => {
  const expected = job();
  assert.throws(() => assertJobContinuity({ ...expected, job_id: "aoi_0000000000000000", result_file: "/api/jobs/aoi_0000000000000000/result" }, expected), /different job/);
  assert.throws(() => assertJobContinuity({ ...expected, request: { ...expected.request, processing_version: "3" } }, expected), /processing request/);
});

test("same centre with wrong result job or monthly period never qualifies", () => {
  const expected = job();
  const wrongId = result(); wrongId.metadata.region = "aoi_0000000000000000";
  assert.throws(() => assertJobResult(parseResult(wrongId), expected), /does not match/);
  const wrongPeriod = result(); wrongPeriod.series.shift(); wrongPeriod.metadata.date_range.start = "2001-02";
  assert.throws(() => assertJobResult(parseResult(wrongPeriod), expected), /date window/);
  const missing = result(); missing.series.splice(10, 1);
  assert.throws(() => assertJobResult(parseResult(missing), expected), /date window/);
  const nulls = result(); nulls.series[10].raw = null; nulls.series[10].anomaly = null;
  assertJobResult(parseResult(nulls), expected);
});

test("source product and slope units are part of the result contract", () => {
  for (const mutate of [
    (v: TrendResult) => { v.metadata.source = "NASA MODIS MOD13A2.061"; },
    (v: TrendResult) => { v.metadata.variable = "temperature"; },
    (v: TrendResult) => { v.metadata.unit = "percent"; },
    (v: TrendResult) => { v.trend.slope_unit = "NDVI/year"; },
  ]) {
    const value = result(); mutate(value);
    assert.throws(() => assertJobResult(parseResult(value), job()), /product/);
  }
});

test("completed job cannot fetch unrelated API/static files or arbitrary URLs", async () => {
  const previous = globalThis.fetch;
  let calls = 0;
  try {
    globalThis.fetch = async () => { calls++; throw new Error("must not fetch"); };
    for (const result_file of ["/api/jobs/aoi_0000000000000000/result", "results/nile_delta_ndvi.json", "https://elsewhere.invalid/result", null]) {
      await assert.rejects(fetchJobResult({ ...job(), result_file }), /different or unavailable/);
    }
    assert.equal(calls, 0);
  } finally { globalThis.fetch = previous; }
});

test("unauthorized status and result are refused before parsing any apparent success", async () => {
  const previous = globalThis.fetch;
  try {
    for (const status of [401, 403]) {
      globalThis.fetch = async () => new Response(JSON.stringify(result()), { status, headers: { "Content-Type": "application/json" } });
      await assert.rejects(fetchJobStatus(job()), /access was denied/);
      await assert.rejects(fetchJobResult(job()), /access was denied/);
    }
  } finally { globalThis.fetch = previous; }
});

test("request dates respect backend supported release range", () => {
  assert.throws(() => validateRequest({ ...job().request, start_date: "12-31-2000" }), /2001–2024/);
  assert.throws(() => validateRequest({ ...job().request, end_date: "01-01-2025" }), /2001–2024/);
});

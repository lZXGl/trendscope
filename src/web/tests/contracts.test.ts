import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { parseIndex, parseJob, parseResult, readJson } from "../src/lib/contracts";
import { chartData, decimalYear, formatProbability } from "../src/lib/chartData";
import { loadIndex, loadResult } from "../src/lib/dataLoader";
import { makeBboxAround, submitAnalysisJob, validateRequest } from "../src/lib/jobClient";

const real = () => JSON.parse(readFileSync("public/data/results/nile_delta_ndvi.json", "utf8"));
const fixture = () => JSON.parse(readFileSync("tests/fixtures/aoi_s101_ndvi.json", "utf8"));

test("observed release accepts full handoff and refuses mock or unknown provenance classification", () => {
  assert.equal(parseResult(real()).series.length, 288);
  assert.throws(() => parseResult(fixture()), /Development/);
  const absent = real(); delete absent.metadata.is_mock;
  assert.throws(() => parseResult(absent), /unclassified/);
});
test("shared schemas reject malformed results, probabilities, status and duplicate catalogue paths", () => {
  const broken = real(); broken.trend.p_value = 1.1;
  assert.throws(() => parseResult(broken), /contract/);
  const duplicate = JSON.parse(readFileSync("public/data/index.json", "utf8"));
  assert.throws(() => parseIndex([...duplicate, ...duplicate]), /duplicate/);
  assert.throws(() => parseJob({ status: "success" }), /contract/);
  assert.throws(() => parseResult({}), /contract/);
});
test("calendar dates, duplicate rows and date range are checked before rendering", () => {
  for (const date of ["2001-13", "2001-00", "0000-01", "2001-1"]) {
    const broken = real(); broken.series[0].date = date;
    assert.throws(() => parseResult(broken));
  }
  const broken = real(); broken.series[1].date = broken.series[0].date;
  assert.throws(() => parseResult(broken), /calendar/);
});
test("chart preserves explicit nulls and inserts absent months without mutation", () => {
  const input = real(); input.series.splice(1, 1); input.series[1].raw = null; input.series[1].anomaly = null;
  const before = JSON.stringify(input);
  const chart = chartData(input, "anomaly");
  assert.equal(chart.dates.length, 288);
  assert.equal(chart.dates[1], "2001-02");
  assert.equal(chart.values[1], null); assert.equal(chart.values[2], null);
  assert.equal(JSON.stringify(input), before);
  const expected = input.trend.sens_slope / 10 * (decimalYear(chart.dates[10]) - decimalYear(chart.dates[0]));
  assert.ok(Math.abs(chart.guide[10] - chart.guide[0] - expected) < 1e-14);
  assert.equal(chartData(input, "raw").guide.length, 0);
});
test("decimal calendar years preserve leap days; tiny positive probabilities remain positive", () => {
  assert.equal(decimalYear("2000-03"), 2000 + 60 / 366);
  assert.equal(decimalYear("1900-03"), 1900 + 59 / 365);
  assert.equal(formatProbability(real().trend.p_value), "5.727e-18");
});
test("request validation follows backend dimensions, product and actual dates", () => {
  const request = { bbox: [30.7, 30.7, 31.2, 31.2], product: "MOD13A3.061", start_date: "01-01-2001", end_date: "12-31-2024" };
  validateRequest(request);
  for (const bad of [{...request, start_date: ""}, {...request, start_date: "02-30-2024"},
    {...request, end_date: "01-01-2000"}, {...request, bbox: [0, 0, 0.01, 1]},
    {...request, bbox: [0, 0, 1, NaN]}, {...request, product: "unsupported"}]) {
    assert.throws(() => validateRequest(bad));
  }
  validateRequest({...request, bbox: makeBboxAround(90, 180)});
  assert.throws(() => makeBboxAround(NaN, 0));
});
test("failed catalogue never falls back to development data; HTML responses are rejected", async () => {
  const previous = globalThis.fetch;
  try {
    globalThis.fetch = async () => new Response("<html>SPA fallback</html>", { headers: {"Content-Type": "text/html"} });
    await assert.rejects(loadIndex(), /Expected JSON/);
    await assert.rejects(loadResult("results/nile_delta_ndvi.json"), /Expected JSON/);
    await assert.rejects(loadResult("../secret.json"), /Invalid result path/);
    await assert.rejects(readJson(new Response("", {status: 404})), /404/);
  } finally { globalThis.fetch = previous; }
});
test("static release does not submit fake or real jobs", async () => {
  const previous = globalThis.fetch;
  try {
    globalThis.fetch = async () => { throw new Error("must not call network"); };
    const response = await submitAnalysisJob({bbox: [0, 0, 1, 1], product: "MOD13A3.061", start_date: "01-01-2001", end_date: "12-31-2024"});
    assert.equal(response.mode, "unavailable"); assert.equal(response.job, undefined);
  } finally { globalThis.fetch = previous; }
});

test("coverage counts absent calendar rows as missing, not 100% completeness", async () => {
  const { createElement } = await import("react");
  const { renderToStaticMarkup } = await import("react-dom/server");
  const { VerdictCard } = await import("../src/components/VerdictCard");
  const input = real(); input.series.splice(10, 2);
  const html = renderToStaticMarkup(createElement(VerdictCard, {result: input}));
  assert.match(html, /286\/288 mo \(2 missing\)/);
});

import { test, expect } from "@playwright/test";
import { readFileSync } from "node:fs";
import { choose } from "./helpers";
import type { AoiJobStatus } from "../../src/types/trend";

test.use({ baseURL: `http://127.0.0.1:${process.env.JOB_PORT}` });
const id = "aoi_1234567890abcdef";
const other = "aoi_0000000000000000";
const job = (status: AoiJobStatus["status"] = "completed"): AoiJobStatus => ({
  job_id: id, status, stage: null,
  request: { bbox: [13.155, 52.27, 13.655, 52.77], product: "MOD13A3.061", start_date: "01-01-2001", end_date: "12-31-2024", allow_marginal: false, min_pixel_presence: 0.8, processing_version: "2" },
  nasa_task_id: null, error: null, retryable: false,
  result_file: status === "completed" ? `/api/jobs/${id}/result` : null,
  created_at: "2026-11-14T00:00:00Z", updated_at: "2026-11-14T00:00:00Z",
});
// Synthetic HTTP fixtures deliberately use the same centre. They are not scientific outputs.
const result = () => {
  const value = JSON.parse(readFileSync("public/data/results/nile_delta_ndvi.json", "utf8"));
  Object.assign(value.metadata, { region: id, lat: 52.52, lon: 13.405 });
  return value;
};
async function noResult(page: import("@playwright/test").Page, message: string) {
  await expect(page.locator(".results-panel [role=alert]")).toContainText(message);
  await expect(page.locator(".chart-canvas")).toHaveCount(0);
  await expect(page.getByText("5.727e-18", { exact: true })).toHaveCount(0);
}

test("A02: same centre and job ID but wrong requested period is rejected visibly", async ({ page }) => {
  await page.route("**/api/jobs**", route => {
    if (route.request().url().endsWith("/result")) return route.fulfill({ json: result() });
    const value = job(); Object.assign(value.request, route.request().postDataJSON());
    return route.fulfill({ json: value });
  });
  await page.goto("/"); await choose(page);
  await page.getByText("Boundary & analysis period", { exact: true }).click();
  const date = page.getByRole("combobox", { name: "Start date", exact: true });
  await date.fill("February 1, 2002"); await date.press("Tab");
  await page.getByRole("button", { name: "Analyze area", exact: true }).click();
  await noResult(page, "date window");
});

for (const mutation of ["bbox", "product", "daily window"] as const) {
  test(`same-centre completed job with wrong ${mutation} is rejected`, async ({ page }) => {
    let resultCalls = 0;
    await page.route("**/api/jobs**", route => {
      if (route.request().url().endsWith("/result")) { resultCalls++; return route.fulfill({ json: result() }); }
      const value = job();
      if (mutation === "bbox") value.request.bbox = [12.905, 52.02, 13.905, 53.02];
      if (mutation === "product") value.request.product = "MOD13A2.061";
      if (mutation === "daily window") value.request.start_date = "01-02-2001";
      return route.fulfill({ json: value });
    });
    await page.goto("/"); await choose(page);
    await page.getByRole("button", { name: "Analyze area", exact: true }).click();
    await noResult(page, "different request"); expect(resultCalls).toBe(0);
  });
}

for (const path of [`/api/jobs/${other}/result`, "results/nile_delta_ndvi.json"]) {
  test(`completed job cannot point at unrelated result ${path}`, async ({ page }) => {
    await page.route("**/api/jobs", route => route.fulfill({ json: { ...job(), result_file: path } }));
    await page.goto("/"); await choose(page);
    await page.getByRole("button", { name: "Analyze area", exact: true }).click();
    await noResult(page, "different or unavailable result");
  });
}

test("same-centre completed result must identify the exact job", async ({ page }) => {
  await page.route("**/api/jobs**", route => {
    const value = result(); value.metadata.region = other;
    return route.fulfill({ json: route.request().method() === "POST" ? job() : value });
  });
  await page.goto("/"); await choose(page);
  await page.getByRole("button", { name: "Analyze area", exact: true }).click();
  await noResult(page, "does not match");
});

for (const boundary of ["submit", "poll", "result"] as const) {
  test(`unauthorized ${boundary} fails visibly without fallback or auto retry`, async ({ page }) => {
    let calls = 0;
    await page.route("**/api/jobs**", route => {
      calls++;
      const post = route.request().method() === "POST";
      if (boundary === "submit" || !post) return route.fulfill({ status: 401, json: { error: "unauthorized" } });
      return route.fulfill({ json: job(boundary === "poll" ? "queued" : "completed") });
    });
    await page.goto("/"); await choose(page);
    await page.getByRole("button", { name: "Analyze area", exact: true }).click();
    await expect(page.locator(".results-panel [role=alert]")).toContainText("access was denied", { timeout: 15000 });
    await noResult(page, "access was denied");
    expect(calls).toBe(boundary === "submit" ? 1 : 2);
    if (boundary === "poll") await expect(page.getByText(/Polling stopped/)).toBeVisible();
  });
}

test("polled completed job cannot change its exact job ID", async ({ page }) => {
  await page.route("**/api/jobs**", route => {
    if (route.request().method() === "POST") return route.fulfill({ json: job("queued") });
    return route.fulfill({ json: { ...job(), job_id: other, result_file: `/api/jobs/${other}/result` } });
  });
  await page.goto("/"); await choose(page);
  await page.getByRole("button", { name: "Analyze area", exact: true }).click();
  await expect(page.locator(".results-panel [role=alert]")).toContainText("different job", { timeout: 15000 });
  await noResult(page, "different job");
});

for (const edit of ["area", "period"] as const) {
  test(`late completed result is ignored after ${edit} changes`, async ({ page }) => {
    let release!: () => void;
    let entered!: () => void;
    const held = new Promise<void>(resolve => { release = resolve; });
    const fetching = new Promise<void>(resolve => { entered = resolve; });
    await page.route("**/api/jobs**", async route => {
      if (route.request().method() === "POST") return route.fulfill({ json: job() });
      entered(); await held; await route.fulfill({ json: result() });
    });
    await page.goto("/"); await choose(page);
    await page.getByRole("button", { name: "Analyze area", exact: true }).click();
    await fetching;
    if (edit === "area") await page.getByLabel("Latitude", { exact: true }).fill("10");
    else {
      await page.getByText("Boundary & analysis period", { exact: true }).click();
      const date = page.getByRole("combobox", { name: "Start date", exact: true });
      await date.fill("February 1, 2002"); await date.press("Tab");
    }
    const response = page.waitForResponse(`**/api/jobs/${id}/result`);
    release(); await response;
    // Let the async consumer run after the held response resolves.
    await page.evaluate(() => new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve))));
    await expect(page.locator(".chart-canvas")).toHaveCount(0);
    await expect(page.getByText("No analysis for this area", { exact: true })).toBeVisible();
    await expect(page.locator(".results-panel [role=alert]")).toHaveCount(0);
  });
}

test("browser sends all operations through same-origin proxy without backend credentials", async ({ page }) => {
  const operations: string[] = [];
  await page.route("**/api/jobs**", route => {
    const request = route.request();
    expect(new URL(request.url()).origin).toBe(`http://127.0.0.1:${process.env.JOB_PORT}`);
    expect(request.headers().authorization).toBeUndefined();
    operations.push(request.method());
    if (request.url().endsWith("/result")) return route.fulfill({ json: result() });
    return route.fulfill({ json: job(request.method() === "POST" ? "queued" : "completed") });
  });
  await page.goto("/"); await choose(page);
  await page.getByRole("button", { name: "Analyze area", exact: true }).click();
  await expect(page.getByText("5.727e-18", { exact: true })).toBeVisible({ timeout: 15000 });
  expect(operations).toEqual(["POST", "GET", "GET"]);
});

import {test, expect} from "@playwright/test";

// Simulated HTTP contract tests ONLY. These never dispatch a NASA task or claim
// backend availability. The production build remains static with jobs disabled.
test.use({baseURL: `http://127.0.0.1:${process.env.JOB_PORT || 4174}`});
const id = "aoi_1234567890abcdef";
const job = (status: string) => ({
  job_id: id, status, stage: status === "processing" ? "waiting_for_nasa" : null,
  request: {bbox: [30.7,30.7,31.2,31.2], product: "MOD13A3.061", start_date: "01-01-2001", end_date: "12-31-2024", allow_marginal: false, min_pixel_presence: 0.8, processing_version: "1"},
  nasa_task_id: null, error: status === "failed" ? "Selected area is not fully on land." : null,
  retryable: false, result_file: status === "completed" ? `/api/jobs/${id}/result` : null,
  created_at: "2026-11-14T00:00:00Z", updated_at: "2026-11-14T00:00:00Z",
});

test("queued → processing → completed uses documented status/result endpoints and dates", async ({page, request}) => {
  const result = await (await request.get(`http://127.0.0.1:${process.env.PREVIEW_PORT || 4173}/data/results/nile_delta_ndvi.json`)).json();
  let polls = 0;
  let submitted: unknown;
  await page.route("**/api/jobs**", async route => {
    if (route.request().method() === "POST") {
      submitted = route.request().postDataJSON();
      return route.fulfill({status: 202, json: job("queued")});
    }
    if (route.request().url().endsWith("/result")) return route.fulfill({json: result});
    polls++;
    return route.fulfill({json: job(polls === 1 ? "processing" : "completed")});
  });
  await page.goto("/");
  await expect(page.getByRole("heading", {name: /Provisional decreasing/})).toBeVisible();
  await page.getByRole("button", {name: "Random Region", exact: true}).click();
  await page.getByLabel("Start date").fill("2002-02-01");
  await page.getByRole("button", {name: "Run NASA Analysis", exact: true}).click();
  await expect(page.getByText(`Job ${id} — QUEUED`)).toBeVisible();
  await expect(page.getByText(/Waiting for NASA AppEEARS/)).toBeVisible({timeout: 10000});
  await expect(page.getByText(`Job ${id} — COMPLETED`)).toBeVisible({timeout: 10000});
  expect(submitted).toMatchObject({start_date: "02-01-2002", end_date: "12-31-2024", product: "MOD13A3.061"});
  expect(polls).toBe(2);
});

test("unsupported land request failure is shown while observed data stays available", async ({page}) => {
  await page.route("**/api/jobs", route => route.fulfill({json: job("failed")}));
  await page.goto("/");
  await page.getByRole("button", {name:"Random Region",exact:true}).click();
  await page.getByRole("button", {name:"Run NASA Analysis",exact:true}).click();
  await expect(page.getByRole("alert")).toContainText("not fully on land");
  await expect(page.getByRole("heading", {name: /Provisional decreasing/})).toBeVisible();
  await expect(page.getByText("DEVELOPMENT FIXTURE (MOCK)")).toHaveCount(0);
});

test("blank dates refuse submission; HTML API fallback reports unavailable", async ({page}) => {
  let calls = 0;
  await page.route("**/api/jobs", route => { calls++; return route.fulfill({contentType: "text/html",body: "<html>SPA</html>"}); });
  await page.goto("/");
  await page.getByRole("button", {name:"Random Region",exact:true}).click();
  await page.getByLabel("Start date").fill("");
  await page.getByRole("button", {name:"Run NASA Analysis",exact:true}).click();
  await expect(page.getByRole("alert")).toContainText("valid dates");
  expect(calls).toBe(0);
  await page.getByLabel("Start date").fill("2001-01-01");
  await page.getByRole("button", {name:"Run NASA Analysis",exact:true}).click();
  await expect(page.getByText(/On-demand NASA processing is unavailable/)).toBeVisible();
  expect(calls).toBe(1);
  await expect(page.getByText(/Job aoi_/)).toHaveCount(0);
});

test("polling failure stops without changing a pending job into a success", async ({page}) => {
  let polls = 0;
  await page.route("**/api/jobs**", route => {
    if (route.request().method() === "POST") return route.fulfill({status:202,json:job("queued")});
    polls++;
    return route.fulfill({status:503,json:{error:"service unavailable"}});
  });
  await page.goto("/");
  await page.getByRole("button", {name:"Random Region",exact:true}).click();
  await page.getByRole("button", {name:"Run NASA Analysis",exact:true}).click();
  await expect(page.getByText(/Polling stopped/)).toBeVisible({timeout:10000});
  await expect(page.getByText(`Job ${id} — QUEUED`)).toBeVisible();
  expect(polls).toBe(1);
});

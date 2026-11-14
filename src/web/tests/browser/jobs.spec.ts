import { test, expect } from "@playwright/test";
import { choose } from "./helpers";

// Intercepted contract responses only: no NASA calls and no claims of live hosting.
test.use({ baseURL: `http://127.0.0.1:${process.env.JOB_PORT}` });
const id = "aoi_1234567890abcdef";
const job = (status: string) => ({
  job_id: id,
  status,
  stage: status === "processing" ? "waiting_for_nasa" : null,
  request: {
    bbox: [13.155, 52.27, 13.655, 52.77],
    product: "MOD13A3.061",
    start_date: "01-01-2001",
    end_date: "12-31-2024",
    allow_marginal: false,
    min_pixel_presence: 0.8,
    processing_version: "1",
  },
  nasa_task_id: null,
  error: status === "failed" ? "Selected area is not fully on land." : null,
  retryable: false,
  result_file: status === "completed" ? `/api/jobs/${id}/result` : null,
  created_at: "2026-11-14T00:00:00Z",
  updated_at: "2026-11-14T00:00:00Z",
});

test("queued → processing → completed uses selected bbox and documented endpoints; rejects unrelated result", async ({
  page,
  request,
}) => {
  // The Nile result must be rejected for Berlin, never relabelled as observations there.
  const result = await (
    await request.get(`http://127.0.0.1:${process.env.PREVIEW_PORT}/data/results/nile_delta_ndvi.json`)
  ).json();
  let polls = 0;
  let submitted: unknown;
  await page.route("**/api/jobs**", (route) => {
    if (route.request().method() === "POST") {
      submitted = route.request().postDataJSON();
      return route.fulfill({ status: 202, json: job("queued") });
    }
    if (route.request().url().endsWith("/result"))
      return route.fulfill({ json: result });
    polls++;
    return route.fulfill({
      json: job(polls === 1 ? "processing" : "completed"),
    });
  });
  await page.goto("/");
  await choose(page);
  await page.getByRole("button", { name: "Analyze area", exact: true }).click();
  await expect(page.getByText("Request queued", { exact: true })).toBeVisible();
  await expect(
    page.getByText("Retrieving NASA observations", { exact: true }),
  ).toBeVisible({ timeout: 15000 });
  await expect(page.getByRole("alert")).toContainText(
    "does not match the requested area",
    { timeout: 15000 },
  );
  expect(submitted).toEqual({
    bbox: [13.155, 52.27, 13.655, 52.77],
    product: "MOD13A3.061",
    start_date: "01-01-2001",
    end_date: "12-31-2024",
  });
  expect(polls).toBe(2);
  await expect(page.locator(".chart-canvas")).toHaveCount(0);
});
test("valid completed request displays its observed result only after explicit submission", async ({
  page,
  request,
}) => {
  const result = await (
    await request.get(`http://127.0.0.1:${process.env.PREVIEW_PORT}/data/results/nile_delta_ndvi.json`)
  ).json();
  // Synthetic API fixture: dynamic results identify their owning job, not the static region.
  result.metadata.region = id;
  const centre = { lat: result.metadata.lat, lon: result.metadata.lon };
  await page.route("**/api/jobs**", (route) => {
    if (route.request().url().endsWith("/result"))
      return route.fulfill({ json: result });
    const value = job("completed");
    value.request.bbox = route.request().postDataJSON().bbox;
    return route.fulfill({ json: value });
  });
  await page.goto("/");
  await choose(page, String(centre.lat), String(centre.lon));
  await expect(page.locator(".chart-canvas")).toHaveCount(0);
  await page.getByRole("button", { name: "Analyze area", exact: true }).click();
  await expect(page.getByText("5.727e-18", { exact: true })).toBeVisible();
});
test("unsupported land request fails clearly without substituting example statistics", async ({
  page,
}) => {
  await page.route("**/api/jobs", (route) =>
    route.fulfill({ json: job("failed") }),
  );
  await page.goto("/");
  await choose(page);
  await page.getByRole("button", { name: "Analyze area", exact: true }).click();
  await expect(page.getByRole("alert")).toContainText("not fully on land");
  await expect(page.locator(".chart-canvas")).toHaveCount(0);
  await page.getByRole("button", { name: "View example", exact: true }).click();
  await expect(page.getByText("5.727e-18", { exact: true })).toBeVisible();
});
test("blank dates refuse submission; HTML API fallback reports unavailable", async ({
  page,
}) => {
  let calls = 0;
  await page.route("**/api/jobs", (route) => {
    calls++;
    return route.fulfill({
      contentType: "text/html",
      body: "<html>SPA</html>",
    });
  });
  await page.goto("/");
  await choose(page);
  await page.getByText("Boundary & analysis period", { exact: true }).click();
  await page
    .getByRole("combobox", { name: "Start date", exact: true })
    .fill("");
  await page
    .getByRole("combobox", { name: "Start date", exact: true })
    .press("Tab");
  await page.getByRole("button", { name: "Analyze area", exact: true }).click();
  await expect(page.locator(".results-panel [role=alert]")).toContainText(
    "valid dates",
  );
  expect(calls).toBe(0);
  await page
    .getByRole("combobox", { name: "Start date", exact: true })
    .fill("February 1, 2002");
  await page
    .getByRole("combobox", { name: "Start date", exact: true })
    .press("Tab");
  await page.getByRole("button", { name: "Analyze area", exact: true }).click();
  await expect(page.locator(".results-panel [role=alert]")).toContainText(
    "On-demand NASA processing is unavailable",
  );
  expect(calls).toBe(1);
});
test("poll failure stops without inventing completion or replacing the result", async ({
  page,
}) => {
  let polls = 0;
  await page.route("**/api/jobs**", (route) => {
    if (route.request().method() === "POST")
      return route.fulfill({ status: 202, json: job("queued") });
    polls++;
    return route.fulfill({
      status: 503,
      json: { error: "service unavailable" },
    });
  });
  await page.goto("/");
  await choose(page);
  await page.getByRole("button", { name: "Analyze area", exact: true }).click();
  await expect(page.getByText(/Polling stopped/)).toBeVisible({
    timeout: 15000,
  });
  await expect(
    page.getByText("Status unavailable", { exact: true }),
  ).toBeVisible();
  expect(polls).toBe(1);
  await expect(page.locator(".chart-canvas")).toHaveCount(0);
});
test("selection changed during submission ignores stale jobs and never fabricates progress", async ({
  page,
}) => {
  let release!: () => void;
  const held = new Promise<void>((resolve) => (release = resolve));
  await page.route("**/api/jobs", async (route) => {
    await held;
    await route.fulfill({ status: 202, json: job("queued") });
  });
  await page.goto("/");
  await choose(page);
  await page.getByRole("button", { name: "Analyze area", exact: true }).click();
  await page.getByLabel("Latitude", { exact: true }).fill("10");
  await expect(
    page.getByText("Submitting request…", { exact: true }),
  ).toHaveCount(0);
  release();
  await expect(
    page.getByText("No analysis for this area", { exact: true }),
  ).toBeVisible();
  await expect(page.getByText("Request queued", { exact: true })).toHaveCount(
    0,
  );
});

test("uncommitted invalid date blocks analysis instead of submitting the previous date", async ({
  page,
}) => {
  let calls = 0;
  await page.route("**/api/jobs", (route) => {
    calls++;
    return route.fulfill({ json: job("queued") });
  });
  await page.goto("/");
  await choose(page);
  await page.getByText("Boundary & analysis period", { exact: true }).click();
  const date = page.getByRole("combobox", { name: "Start date", exact: true });
  await date.fill("February 30, 2020");
  await date.press("Tab");
  await expect(date).toHaveAttribute("aria-invalid", "true");
  await expect(
    page.getByRole("button", { name: "Analyze area", exact: true }),
  ).toBeDisabled();
  expect(calls).toBe(0);
});
test("HTTP unavailable and mismatched job requests never become successful analyses", async ({
  page,
}) => {
  await page.route("**/api/jobs", (route) =>
    route.fulfill({ status: 404, body: "not hosted" }),
  );
  await page.goto("/");
  await choose(page);
  await page.getByRole("button", { name: "Analyze area", exact: true }).click();
  await expect(page.getByRole("alert")).toContainText("not active");
  await expect(page.locator(".chart-canvas")).toHaveCount(0);
  await page.unroute("**/api/jobs");
  await page.route("**/api/jobs", (route) => {
    const bad = job("queued");
    bad.request.bbox = [30.7, 30.7, 31.2, 31.2];
    return route.fulfill({ json: bad });
  });
  await page.getByRole("button", { name: "Analyze area", exact: true }).click();
  await expect(page.getByRole("alert")).toContainText("different request");
  await expect(page.getByText("Request queued", { exact: true })).toHaveCount(
    0,
  );
});

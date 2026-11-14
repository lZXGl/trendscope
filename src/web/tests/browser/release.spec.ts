import { test, expect } from "@playwright/test";

import { choose } from "./helpers";

test("production journey: observed default, chart modes, globe selection, details and static JSON", async ({
  page,
  request,
}) => {
  const errors: string[] = [];
  page.on("pageerror", (e) => errors.push(e.message));
  await page.goto("/");
  await expect(
    page.getByText("Observed example", { exact: true }),
  ).toBeVisible();
  await expect(page.getByText("5.727e-18", { exact: true })).toBeVisible();
  await expect(
    page.getByText("288/288 mo (0 missing)", { exact: true }),
  ).toBeVisible();
  await expect(page.getByText("DEVELOPMENT FIXTURE (MOCK)")).toHaveCount(0);
  await expect(
    page.getByText("No area selected", { exact: true }),
  ).toBeVisible();
  await expect(
    page.getByRole("button", { name: "Compare", exact: true }),
  ).toHaveCount(0);
  await expect(
    page.getByRole("button", { name: "Random Region", exact: true }),
  ).toHaveCount(0);
  await page.getByRole("radio", { name: "Raw values", exact: true }).click();
  await page.getByRole("radio", { name: "Anomaly", exact: true }).click();
  await page.getByText("Source & scientific details", { exact: true }).click();
  await expect(
    page.getByText(/have not been independently authenticated/),
  ).toBeVisible();
  await expect(
    page.getByText(/No slope confidence interval is supplied/),
  ).toBeVisible();
  await expect(page.locator("[data-globe-ready=true]")).toBeVisible({ timeout: 20000 });
  const globe = page.locator(".globe-viewport canvas");
  const box = await globe.boundingBox();
  const position = { x: box!.width * 0.55, y: box!.height * 0.5 };
  await globe.hover({ position });
  await page.evaluate(
    () =>
      new Promise<void>((resolve) =>
        requestAnimationFrame(() => requestAnimationFrame(() => resolve())),
      ),
  );
  await globe.click({ position });
  await expect(page.getByText("Selected area", { exact: true })).toBeVisible();
  await expect(page.locator(".chart-canvas")).toHaveCount(0);
  await expect(page.getByLabel("Latitude", { exact: true })).not.toHaveValue(
    "",
  );
  await page.getByRole("button", { name: "View example", exact: true }).click();
  await expect(page.getByText("5.727e-18", { exact: true })).toBeVisible();
  const index = await request.get("/data/index.json");
  expect(index.headers()["content-type"]).toContain("application/json");
  for (const item of await index.json()) {
    const response = await request.get(`/data/${item.file}`);
    expect(response.status()).toBe(200);
    expect(response.headers()["content-type"]).toContain("application/json");
    expect((await response.json()).metadata.is_mock).toBe(false);
  }
  expect(errors).toEqual([]);
});

test("world map inverse projection, exact editable boundary, clear, persistence and truthful unavailable state", async ({
  page,
}) => {
  let jobs = 0;
  await page.route("**/api/jobs**", (route) => {
    jobs++;
    return route.abort();
  });
  await page.goto("/");
  await page.getByRole("radio", { name: "Map", exact: true }).click();
  const target = await page
    .locator(".world-map svg")
    .evaluate((svg: SVGSVGElement) => {
      const p = new DOMPoint(360 + 13.405 * 2, 180 - 52.52 * 2).matrixTransform(
        svg.getScreenCTM()!,
      );
      return { x: p.x, y: p.y };
    });
  await page.mouse.click(target.x, target.y);
  expect(
    Math.abs(
      Number(await page.getByLabel("Latitude", { exact: true }).inputValue()) -
        52.52,
    ),
  ).toBeLessThan(0.3);
  expect(
    Math.abs(
      Number(await page.getByLabel("Longitude", { exact: true }).inputValue()) -
        13.405,
    ),
  ).toBeLessThan(0.3);
  await choose(page);
  await expect(page.getByTestId("map-selection")).toHaveAttribute(
    "data-bbox",
    "13.155,52.27,13.655,52.77",
  );
  await expect(
    page.getByRole("button", { name: "Analyze area", exact: true }),
  ).toBeDisabled();
  await expect(
    page.getByText(/Live processing is not connected/),
  ).toBeVisible();
  await expect(page.locator(".chart-canvas")).toHaveCount(0);
  await page.getByRole("button", { name: "Zoom to area", exact: true }).click();
  const rect = page.locator("[data-testid=map-selection] rect");
  expect(Number(await rect.getAttribute("width"))).toBeCloseTo(120);
  await page.reload();
  await expect(page.getByLabel("Latitude", { exact: true })).toHaveValue(
    "52.5200",
  );
  await expect(
    page.getByRole("button", { name: "Area confirmed", exact: true }),
  ).toBeVisible();
  await expect(page.locator(".chart-canvas")).toHaveCount(0);
  await page.getByLabel("Width (°)", { exact: true }).fill("0.8");
  await expect(
    page.getByRole("button", { name: "Confirm area", exact: true }),
  ).toBeEnabled();
  await page.getByRole("radio", { name: "Map", exact: true }).click();
  await expect(page.getByTestId("map-selection")).toHaveAttribute(
    "data-bbox",
    "13.005,52.27,13.805,52.77",
  );
  await page.getByRole("button", { name: "Clear", exact: true }).click();
  await expect(page.getByTestId("map-selection")).toHaveCount(0);
  await expect(page.getByLabel("Latitude", { exact: true })).toHaveValue("");
  await expect(
    page.getByText("No area selected", { exact: true }),
  ).toBeVisible();
  expect(jobs).toBe(0);
});

test("invalid and antimeridian coordinates remain visible and refuse confirmation without snapping", async ({
  page,
}) => {
  await page.goto("/");
  await page.getByLabel("Latitude", { exact: true }).fill("12");
  await page.getByLabel("Longitude", { exact: true }).fill("179.9");
  await expect(page.getByRole("alert")).toContainText("antimeridian");
  await expect(page.getByLabel("Longitude", { exact: true })).toHaveValue(
    "179.9",
  );
  await expect(
    page.getByRole("button", { name: "Confirm area", exact: true }),
  ).toBeDisabled();
  await page.getByLabel("Latitude", { exact: true }).fill("100");
  await expect(page.getByRole("alert")).toContainText("Latitude must");
  await expect(page.locator(".chart-canvas")).toHaveCount(0);
});

test("catalogue HTML fallback never substitutes mocks and selection remains usable", async ({
  page,
}) => {
  await page.route("**/data/index.json", (route) =>
    route.fulfill({ contentType: "text/html", body: "<html>SPA</html>" }),
  );
  await page.goto("/");
  await expect(page.getByRole("alert")).toContainText(
    "No mock result has been substituted",
  );
  await expect(page.locator(".chart-canvas")).toHaveCount(0);
  await choose(page);
  await expect(
    page.getByText("No analysis for this area", { exact: true }),
  ).toBeVisible();
});
test("malformed result is a visible error instead of a crash or indefinite loading", async ({
  page,
}) => {
  const errors: string[] = [];
  page.on("pageerror", (e) => errors.push(e.message));
  await page.route("**/data/results/*.json", (route) =>
    route.fulfill({ json: { metadata: { is_mock: false } } }),
  );
  await page.goto("/");
  await expect(page.getByRole("alert")).toContainText(
    "shared scientific contract",
  );
  expect(errors).toEqual([]);
});
test("empty catalogue is explicit", async ({ page }) => {
  await page.route("**/data/index.json", (route) =>
    route.fulfill({ json: [] }),
  );
  await page.goto("/");
  await expect(
    page.getByText(/No observed examples are currently published/),
  ).toBeVisible();
});
test("WebGL failure retains world-map selection and observed example", async ({
  page,
}) => {
  await page.addInitScript(() => {
    const original = HTMLCanvasElement.prototype.getContext;
    HTMLCanvasElement.prototype.getContext = function (
      type: string,
      ...args: unknown[]
    ) {
      if (type.includes("webgl"))
        throw new Error("WebGL unavailable (test fixture)");
      return original.call(this, type as "2d", ...args);
    } as typeof original;
  });
  await page.goto("/");
  await expect(
    page.getByText("3D is unavailable on this device."),
  ).toBeVisible();
  await page
    .getByRole("button", { name: "Use world map", exact: true })
    .click();
  await expect(page.locator(".world-map svg")).toBeVisible();
  await expect(page.getByText("5.727e-18", { exact: true })).toBeVisible();
  await choose(page);
  await expect(page.getByTestId("map-selection")).toBeVisible();
});

test("production HTTP serves bundled JavaScript, CSS, favicon and observed JSON as assets", async ({
  request,
}) => {
  const html = await (await request.get("/")).text();
  const assets = [...html.matchAll(/(?:src|href)="(\/assets\/[^" ]+)"/g)].map(
    (match) => match[1],
  );
  expect(assets.length).toBeGreaterThanOrEqual(2);
  for (const path of [
    ...assets,
    "/favicon.svg",
    "/data/index.json",
    "/data/results/nile_delta_ndvi.json",
  ]) {
    const response = await request.get(path);
    expect(response.status()).toBe(200);
    expect(response.headers()["content-type"]).not.toContain("text/html");
    expect(await response.text()).not.toMatch(/^\s*<!doctype html>/i);
  }
});

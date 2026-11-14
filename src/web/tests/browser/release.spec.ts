import { test, expect } from "@playwright/test";

test("production journey: real default, chart modes, globe/map, compare and refresh", async ({ page, request }) => {
  const errors: string[] = [];
  page.on("pageerror", error => errors.push(error.message));
  await page.goto("/");
  await expect(page.getByRole("heading", { name: /Provisional decreasing NDVI trend/ })).toBeVisible();
  await expect(page.getByText("5.727e-18", { exact: true })).toBeVisible();
  await expect(page.getByText(/288\/288 mo/)).toBeVisible();
  await expect(page.getByText("DEVELOPMENT FIXTURE (MOCK)")).toHaveCount(0);
  await expect(page.locator("canvas")).toHaveCount(2);
  await page.getByRole("button", { name: "Raw Value", exact: true }).click();
  await page.getByRole("button", { name: "Anomaly", exact: true }).click();
  await expect(page.locator("[data-globe-ready=true]")).toBeVisible({timeout: 20000});
  const globe = page.locator("canvas").first();
  const bounds = await globe.boundingBox();
  const position = {x: bounds!.width * 0.6, y: bounds!.height * 0.6};
  await globe.hover({position});
  // Raycasting updates in the render loop. Let the pointer reach a painted
  // frame before pressing, as it does during a real mouse interaction.
  await page.evaluate(() => new Promise<void>(resolve => {
    requestAnimationFrame(() => requestAnimationFrame(() => resolve()));
  }));
  await globe.click({position});
  await expect(page.getByRole("button", {name: "Clear", exact: true})).toBeVisible();
  await page.getByRole("button", {name: "Central Nile Delta study area", exact: true}).last().click();
  await expect(page.getByRole("button", {name: "Clear", exact: true})).toHaveCount(0);

  await page.getByText("All scientific caveats and provenance limits").click();
  await expect(page.getByText(/have not been independently authenticated/)).toBeVisible();
  await page.getByRole("button", { name: "Map", exact: true }).click();
  await page.getByRole("button", { name: "3D Globe", exact: true }).click();
  await page.getByRole("button", { name: "Random Region", exact: true }).click();
  await expect(page.getByRole("button", { name: "On-demand processing unavailable" })).toBeDisabled();
  await expect(page.getByText(/selected candidate area is not the displayed dataset/)).toBeVisible();
  await page.getByRole("button", { name: "Clear", exact: true }).click();
  await page.getByRole("button", { name: "Compare", exact: true }).click();
  await expect(page.getByText(/Only one observed dataset is published/)).toBeVisible();
  await expect(page.getByRole("heading", { name: /Provisional decreasing/ })).toHaveCount(2);
  await page.getByRole("button", { name: "Explorer", exact: true }).click();
  await page.reload();
  await expect(page.getByRole("heading", { name: /Provisional decreasing/ })).toBeVisible();
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

test("mobile layout has no horizontal overflow", async ({ page }) => {
  await page.setViewportSize({width: 320, height: 800});
  await page.goto("/");
  await expect(page.getByRole("heading", {name: /Provisional decreasing/})).toBeVisible();
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
  await page.getByRole("button", {name: "Compare", exact: true}).click();
  await expect(page.getByRole("heading", {name: /Provisional decreasing/})).toHaveCount(2);
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
});

test("catalogue network failure and HTML fallback never display mocks", async ({page}) => {
  await page.route("**/data/index.json", route => route.fulfill({status: 200, contentType: "text/html", body: "<html>SPA fallback</html>"}));
  await page.goto("/");
  await expect(page.getByRole("alert")).toContainText("No mock result has been substituted");
  await expect(page.getByRole("heading", {name: /Time Series/})).toHaveCount(0);
});

test("malformed result is a visible error instead of a crash or indefinite loading", async ({page}) => {
  const errors: string[] = [];
  page.on("pageerror", e => errors.push(e.message));
  await page.route("**/data/results/*.json", route => route.fulfill({json: {metadata: {is_mock: false}}}));
  await page.goto("/");
  await expect(page.getByRole("alert")).toContainText("shared scientific contract");
  expect(errors).toEqual([]);
  await page.getByRole("button", {name: "Compare", exact: true}).click();
  await expect(page.getByRole("alert")).toHaveCount(2);
});

test("empty catalogue is explicit", async ({page}) => {
  await page.route("**/data/index.json", route => route.fulfill({json: []}));
  await page.goto("/");
  await expect(page.getByText("No observed datasets are currently published.")).toBeVisible();
});

test("WebGL initialization failure keeps the map and observed result usable", async ({page}) => {
  await page.addInitScript(() => {
    const original = HTMLCanvasElement.prototype.getContext;
    HTMLCanvasElement.prototype.getContext = function(type: string, ...args: unknown[]) {
      if (type.includes("webgl")) throw new Error("WebGL unavailable (test fixture)");
      return original.call(this, type as "2d", ...args);
    } as typeof original;
  });
  await page.goto("/");
  await expect(page.getByText(/3D rendering is unavailable on this device/)).toBeVisible();
  await page.getByRole("button", {name:"Use regional map"}).click();
  await expect(page.getByText(/Regional map covers Egypt/)).toBeVisible();
  await expect(page.getByRole("heading", {name:/Provisional decreasing/})).toBeVisible();
});

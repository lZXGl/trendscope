import { test, expect } from "@playwright/test";
import { appearance, choose } from "./helpers";
import { mkdir } from "node:fs/promises";
import { resolve } from "node:path";

test("System defaults to OS preference, tracks changes, and explicit choices persist across refresh", async ({
  page,
}) => {
  const errors: string[] = [];
  page.on("pageerror", (e) => errors.push(e.message));
  await page.emulateMedia({ colorScheme: "dark" });
  await page.goto("/");
  await expect(page.locator("html")).toHaveAttribute("data-mode", "dark");
  await expect(
    page.getByRole("combobox", { name: "Appearance" }),
  ).toContainText("System");
  await page.emulateMedia({ colorScheme: "light" });
  await expect(page.locator("html")).toHaveAttribute("data-mode", "light");
  await appearance(page, "Dark");
  await page.reload();
  await expect(page.locator("html")).toHaveAttribute("data-mode", "dark");
  await page.emulateMedia({ colorScheme: "light" });
  await expect(page.locator("html")).toHaveAttribute("data-mode", "dark");
  await appearance(page, "Light");
  await page.reload();
  await expect(page.locator("html")).toHaveAttribute("data-mode", "light");
  await page.emulateMedia({ colorScheme: "dark" });
  await expect(page.locator("html")).toHaveAttribute("data-mode", "light");
  await appearance(page, "System");
  await expect(page.locator("html")).toHaveAttribute("data-mode", "dark");
  await page.reload();
  await expect(
    page.getByRole("combobox", { name: "Appearance" }),
  ).toContainText("System");
  await page.emulateMedia({ colorScheme: "light" });
  await expect(page.locator("html")).toHaveAttribute("data-mode", "light");
  expect(errors).toEqual([]);
});
test("theme bootstrap resolves before the application module loads, including blocked storage", async ({
  page,
}) => {
  await page.emulateMedia({ colorScheme: "dark" });
  await page.route("**/assets/*.js", (route) => route.abort());
  await page.goto("/");
  await expect(page.locator("html")).toHaveAttribute("data-mode", "dark");
  await page.evaluate(() =>
    localStorage.setItem("trendscope.appearance", "light"),
  );
  await page.reload();
  await expect(page.locator("html")).toHaveAttribute("data-mode", "light");
  await page.addInitScript(() =>
    Object.defineProperty(window, "localStorage", {
      get() {
        throw new Error("blocked");
      },
    }),
  );
  await page.reload();
  await expect(page.locator("html")).toHaveAttribute("data-mode", "dark");
});
test("blocked storage keeps controls and geographic selection usable", async ({
  page,
}) => {
  await page.addInitScript(() =>
    Object.defineProperty(window, "localStorage", {
      get() {
        throw new Error("blocked");
      },
    }),
  );
  await page.goto("/");
  await choose(page);
  await appearance(page, "Dark");
  await expect(page.locator("html")).toHaveAttribute("data-mode", "dark");
  await expect(
    page.getByRole("button", { name: "Area confirmed", exact: true }),
  ).toBeVisible();
});
test("Astryx controls support keyboard selection and visible focus", async ({
  page,
}) => {
  await page.goto("/");
  const control = page.getByRole("combobox", { name: "Appearance" });
  await control.focus();
  await control.press("Enter");
  await expect(
    page.getByRole("option", { name: "Dark", exact: true }),
  ).toBeVisible();
  await page.keyboard.press("Home");
  await page.keyboard.press("ArrowDown");
  await page.keyboard.press("Enter");
  await expect(page.locator("html")).toHaveAttribute("data-mode", "dark");
  const latitude = page.getByLabel("Latitude", { exact: true });
  await latitude.focus();
  await page.keyboard.type("52.52");
  await page.keyboard.press("Tab");
  await expect(page.getByLabel("Longitude", { exact: true })).toBeFocused();
  const focus = await page
    .getByLabel("Longitude", { exact: true })
    .evaluate((e) => {
      const c = getComputedStyle(e);
      return {
        outline: c.outlineWidth,
        shadow: c.boxShadow,
        ancestor: getComputedStyle(e.parentElement!).outlineWidth,
      };
    });
  expect(
    focus.outline !== "0px" ||
      focus.shadow !== "none" ||
      focus.ancestor !== "0px",
  ).toBe(true);
});

for (const width of [1920, 1440, 1366, 768, 390, 320])
  for (const theme of ["Light", "Dark"]) {
    test(`rendered ${width}px ${theme}: charts, AOI, tooltips and controls fit`, async ({
      page,
    }, testInfo) => {
      const errors: string[] = [];
      page.on("pageerror", (e) => errors.push(e.message));
      page.on("console", (msg) => {
        if (msg.type() === "error") errors.push(msg.text());
      });
      await page.setViewportSize({ width, height: 1000 });
      await page.goto("/");
      await appearance(page, theme);
      await expect(page.getByText("5.727e-18", { exact: true })).toBeVisible();
      await page.getByRole("radio", { name: "Map", exact: true }).click();
      await choose(page);
      await expect(page.getByTestId("map-selection")).toBeVisible();
      await page
        .getByRole("button", { name: "View example", exact: true })
        .click();
      await expect(page.locator(".chart-canvas canvas")).toBeVisible();
      const chart = page.locator(".chart-canvas canvas");
      await chart.hover({ position: { x: 100, y: 100 } });
      await page
        .getByRole("radio", { name: "Raw values", exact: true })
        .click();
      await page.getByRole("radio", { name: "Anomaly", exact: true }).click();
      expect(
        await page.evaluate(
          () =>
            document.documentElement.scrollWidth <=
            document.documentElement.clientWidth,
        ),
      ).toBe(true);
      for (const selector of [
        ".location-panel",
        ".results-panel",
        ".world-map svg",
        ".chart-canvas",
        ".coordinate-grid",
      ]) {
        const bounds = await page.locator(selector).boundingBox();
        expect(bounds!.width).toBeGreaterThan(200);
        expect(bounds!.x).toBeGreaterThanOrEqual(0);
        expect(bounds!.x + bounds!.width).toBeLessThanOrEqual(
          (await page.evaluate(() => document.documentElement.clientWidth)) + 1,
        );
      }
      await page
        .getByText("Source & scientific details", { exact: true })
        .click();
      await expect(
        page.getByText(/No slope confidence interval/),
      ).toBeVisible();
      expect(
        await page.evaluate(
          () =>
            document.documentElement.scrollWidth <=
            document.documentElement.clientWidth,
        ),
      ).toBe(true);
      await page
        .getByText("Source & scientific details", { exact: true })
        .click();
      await page
        .getByRole("button", { name: "Zoom to area", exact: true })
        .click();
      await page
        .getByRole("button", { name: "World view", exact: true })
        .click();
      await page.locator("header").scrollIntoViewIfNeeded();
      const folder = process.env.UPDATE_UX_SCREENSHOTS
        ? resolve("docs/screenshots")
        : testInfo.outputPath("screenshots");
      await mkdir(folder, { recursive: true });
      await page.screenshot({
        path: resolve(folder, `after-${theme.toLowerCase()}-${width}.png`),
        fullPage: true,
        animations: "disabled",
      });
      expect(errors).toEqual([]);
    });
  }

for (const theme of ["Light", "Dark"])
  test(`320px ${theme} date popover stays on-screen`, async ({
    page,
  }, testInfo) => {
    await page.setViewportSize({ width: 320, height: 900 });
    await page.goto("/");
    await appearance(page, theme);
    await choose(page);
    await page.getByText("Boundary & analysis period", { exact: true }).click();
    await page
      .getByRole("button", { name: "Open calendar", exact: true })
      .first()
      .click();
    const dialog = page.getByRole("dialog");
    await expect(dialog).toBeVisible();
    const box = await dialog.boundingBox();
    expect(box!.x).toBeGreaterThanOrEqual(0);
    expect(box!.x + box!.width).toBeLessThanOrEqual(
      (await page.evaluate(() => document.documentElement.clientWidth)) + 1,
    );
    await page.screenshot({
      path: testInfo.outputPath(`calendar-${theme}.png`),
      fullPage: true,
    });
    await page.keyboard.press("Escape");
    await expect(dialog).not.toBeVisible();
  });

for (const theme of ["Light", "Dark"])
  test(`1440px ${theme} globe and isolated AOI result view`, async ({
    page,
  }, testInfo) => {
    const errors: string[] = [];
    page.on("pageerror", (error) => errors.push(error.message));
    page.on("console", (message) => {
      if (message.type() === "error") errors.push(message.text());
    });
    await page.setViewportSize({ width: 1440, height: 1000 });
    await page.goto("/");
    await appearance(page, theme);
    await expect(page.locator("[data-globe-ready=true]")).toBeVisible();
    await expect(page.getByText("5.727e-18", { exact: true })).toBeVisible();
    const contrast = await page.evaluate(() => {
      const rgb = (color: string) =>
        color
          .match(/[\d.]+/g)!
          .slice(0, 3)
          .map(Number)
          .map((v) => v / 255);
      const luminance = (color: string) =>
        rgb(color)
          .map((c) => (c <= 0.04045 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4))
          .reduce((n, c, i) => n + c * [0.2126, 0.7152, 0.0722][i], 0);
      const background = luminance(
        getComputedStyle(document.querySelector(".results-panel")!)
          .backgroundColor,
      );
      return [".eyebrow", ".stat-grid dt", ".chart-note"].map((selector) => {
        const foreground = luminance(
          getComputedStyle(document.querySelector(selector)!).color,
        );
        return (
          (Math.max(foreground, background) + 0.05) /
          (Math.min(foreground, background) + 0.05)
        );
      });
    });
    for (const ratio of contrast) expect(ratio).toBeGreaterThanOrEqual(4.5);
    const folder = process.env.UPDATE_UX_SCREENSHOTS
      ? resolve("docs/screenshots")
      : testInfo.outputPath("screenshots");
    await mkdir(folder, { recursive: true });
    await page.screenshot({
      path: resolve(folder, `after-default-${theme.toLowerCase()}.png`),
      fullPage: true,
    });
    await choose(page);
    await page.getByRole("radio", { name: "Map", exact: true }).click();
    await page
      .getByRole("button", { name: "Zoom to area", exact: true })
      .click();
    await expect(page.locator(".chart-canvas")).toHaveCount(0);
    await expect(
      page.getByText("No analysis for this area", { exact: true }),
    ).toBeVisible();
    await page.getByText("Boundary & analysis period", { exact: true }).click();
    await expect(page.getByTestId("selected-bounds")).toHaveAttribute(
      "data-bbox",
      "13.155,52.27,13.655,52.77",
    );
    await page.screenshot({
      path: resolve(folder, `after-selection-${theme.toLowerCase()}.png`),
      fullPage: true,
    });
    expect(errors).toEqual([]);
  });

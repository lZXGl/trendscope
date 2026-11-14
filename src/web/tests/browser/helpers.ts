import type { Page } from "@playwright/test";
export async function choose(page: Page, lat = "52.5200", lon = "13.4050") {
  await page.getByLabel("Latitude", { exact: true }).fill(lat);
  await page.getByLabel("Longitude", { exact: true }).fill(lon);
  await page.getByRole("button", { name: "Confirm area", exact: true }).click();
}
export async function appearance(page: Page, name: string) {
  await page.getByRole("combobox", { name: "Appearance" }).click();
  await page.getByRole("option", { name, exact: true }).click();
}

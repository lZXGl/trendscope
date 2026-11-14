import { test } from "node:test";
import assert from "node:assert/strict";
import {
  AOI_STORAGE_KEY,
  EMPTY_AOI,
  coordinateLabel,
  evaluateAoi,
  restoreAoi,
} from "../src/lib/aoi";
import { validateRequest } from "../src/lib/jobClient";

test("AOIs use the selected centre and preserve rectangular dimensions without mutation", () => {
  const draft = { lat: "52.5200", lon: "13.4050", width: "0.8", height: "0.4" };
  const before = JSON.stringify(draft);
  const { area, error } = evaluateAoi(draft);
  assert.equal(error, null);
  assert.deepEqual(area?.bbox, [13.005, 52.32, 13.805, 52.72]);
  assert.equal(area?.lat, 52.52);
  assert.equal(area?.lon, 13.405);
  assert.equal(JSON.stringify(draft), before);
  validateRequest({
    bbox: area!.bbox,
    product: "MOD13A3.061",
    start_date: "01-01-2001",
    end_date: "12-31-2024",
  });
  assert.equal(coordinateLabel(-33.9, -70.7), "33.9000° S, 70.7000° W");
});
test("empty, nonnumeric, out of range and crossing AOIs refuse without snapping", () => {
  assert.equal(evaluateAoi(EMPTY_AOI).area, null);
  for (const patch of [
    { lat: "NaN" },
    { lon: "Infinity" },
    { lat: "91" },
    { lon: "181" },
    { width: "0.09" },
    { height: "2.01" },
    { lat: "90" },
    { lon: "179.9" },
    { lon: "-179.9" },
  ]) {
    const value = evaluateAoi({
      lat: "0",
      lon: "0",
      width: "0.5",
      height: "0.5",
      ...patch,
    });
    assert.equal(value.area, null);
    assert.ok(value.error);
  }
  assert.match(
    evaluateAoi({ lat: "0", lon: "179.9", width: "0.5", height: "0.5" }).error!,
    /antimeridian/,
  );
  assert.deepEqual(
    evaluateAoi({ lat: "89.95", lon: "179.95", width: "0.1", height: "0.1" })
      .area?.bbox,
    [179.9, 89.9, 180, 90],
  );
});
test("saved selections restore only valid confirmation and tolerate missing or blocked storage", () => {
  const original = Object.getOwnPropertyDescriptor(globalThis, "localStorage");
  try {
    for (const text of [
      "bad",
      "null",
      "{}",
      JSON.stringify({ draft: { lat: 52 } }),
    ]) {
      Object.defineProperty(globalThis, "localStorage", {
        configurable: true,
        value: { getItem: () => text },
      });
      assert.deepEqual(restoreAoi(), { draft: EMPTY_AOI, confirmed: false });
    }
    const draft = { lat: "52.52", lon: "13.405", width: "0.5", height: "0.5" };
    Object.defineProperty(globalThis, "localStorage", {
      configurable: true,
      value: {
        getItem: (key: string) => {
          assert.equal(key, AOI_STORAGE_KEY);
          return JSON.stringify({ draft, confirmed: true });
        },
      },
    });
    assert.deepEqual(restoreAoi(), { draft, confirmed: true });
    draft.lat = "100";
    assert.equal(restoreAoi().confirmed, false);
    Object.defineProperty(globalThis, "localStorage", {
      configurable: true,
      get() {
        throw new Error("blocked");
      },
    });
    assert.deepEqual(restoreAoi(), { draft: EMPTY_AOI, confirmed: false });
  } finally {
    if (original) Object.defineProperty(globalThis, "localStorage", original);
    else Reflect.deleteProperty(globalThis, "localStorage");
  }
});

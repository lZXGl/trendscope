import type { AoiSelection } from "../types/trend";

export interface AoiDraft {
  lat: string;
  lon: string;
  width: string;
  height: string;
}
export const EMPTY_AOI: AoiDraft = {
  lat: "",
  lon: "",
  width: "0.5",
  height: "0.5",
};
export const AOI_STORAGE_KEY = "trendscope.aoi.v1";

export function evaluateAoi(draft: AoiDraft): {
  area: AoiSelection | null;
  error: string | null;
} {
  const values = [draft.lat, draft.lon, draft.width, draft.height];
  if (values.some((v) => !v.trim()))
    return {
      area: null,
      error: "Enter latitude, longitude, width and height.",
    };
  const [lat, lon, width, height] = values.map(Number);
  const refuse = (error: string) => ({ area: null, error });
  if (![lat, lon, width, height].every(Number.isFinite))
    return refuse("Use finite numeric coordinates and dimensions.");
  if (lat < -90 || lat > 90 || lon < -180 || lon > 180)
    return refuse("Latitude must be −90 to 90°, and longitude −180 to 180°.");
  if (width < 0.1 || width > 2 || height < 0.1 || height > 2)
    return refuse("Width and height must each be 0.1–2.0°.");
  if (lon - width / 2 < -180 || lon + width / 2 > 180)
    return refuse(
      "This area crosses the antimeridian. Move its centre or reduce its width; crossing areas are not supported.",
    );
  if (lat - height / 2 < -90 || lat + height / 2 > 90)
    return refuse(
      "This area extends beyond a pole. Move its centre or reduce its height.",
    );
  const round = (v: number) => Number(v.toFixed(4));
  const bbox: AoiSelection["bbox"] = [
    round(lon - width / 2),
    round(lat - height / 2),
    round(lon + width / 2),
    round(lat + height / 2),
  ];
  return {
    area: {
      lat: round((bbox[1] + bbox[3]) / 2),
      lon: round((bbox[0] + bbox[2]) / 2),
      bbox,
      label: `${lat.toFixed(4)}°, ${lon.toFixed(4)}°`,
      isRandom: false,
    },
    error: null,
  };
}

export function restoreAoi(): { draft: AoiDraft; confirmed: boolean } {
  try {
    const parsed = JSON.parse(localStorage.getItem(AOI_STORAGE_KEY) ?? "null");
    if (
      parsed &&
      ["lat", "lon", "width", "height"].every(
        (k) => typeof parsed.draft?.[k] === "string",
      )
    ) {
      const draft = parsed.draft as AoiDraft;
      return {
        draft,
        confirmed:
          parsed.confirmed === true && evaluateAoi(draft).area !== null,
      };
    }
  } catch {
    /* Storage can be unavailable; selection still works in memory. */
  }
  return { draft: { ...EMPTY_AOI }, confirmed: false };
}

export function coordinateLabel(lat: number, lon: number): string {
  return `${Math.abs(lat).toFixed(4)}° ${lat < 0 ? "S" : "N"}, ${Math.abs(lon).toFixed(4)}° ${lon < 0 ? "W" : "E"}`;
}

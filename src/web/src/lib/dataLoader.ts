import mockResult from "../data/results.mock.json";
import type { TrendIndexItem, TrendResult } from "../types/trend";

const resultCache = new Map<string, TrendResult>();

const MOCK_INDEX: TrendIndexItem[] = [
  {
    region: mockResult.metadata.region,
    region_name: "Nile Delta",
    lat: mockResult.metadata.lat,
    lon: mockResult.metadata.lon,
    variable: mockResult.metadata.variable,
    variable_name: "Vegetation Index (NDVI)",
    variable_description: "MODIS MOD13A3.061 Monthly 1 km NDVI (Mock Placeholder)",
    unit: mockResult.metadata.unit,
    source: mockResult.metadata.source,
    file: "results/mock_nile_delta_ndvi.json",
    significant: mockResult.trend.significant,
    headline: mockResult.verdict.headline,
  },
];

export async function loadIndex(): Promise<{ items: TrendIndexItem[]; usingFallback: boolean }> {
  try {
    const resp = await fetch("/data/index.json");
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    const data = (await resp.json()) as TrendIndexItem[];
    if (!Array.isArray(data) || data.length === 0) throw new Error("Empty index");
    return { items: data, usingFallback: false };
  } catch {
    return { items: MOCK_INDEX, usingFallback: true };
  }
}

export async function loadResult(file: string): Promise<TrendResult> {
  if (file === "results/mock_nile_delta_ndvi.json") {
    return mockResult as TrendResult;
  }
  const cached = resultCache.get(file);
  if (cached) return cached;

  const resp = await fetch(`/data/${file}`);
  if (!resp.ok) {
    throw new Error(`Failed to load /data/${file} (HTTP ${resp.status})`);
  }
  const parsed = (await resp.json()) as TrendResult;
  resultCache.set(file, parsed);
  return parsed;
}

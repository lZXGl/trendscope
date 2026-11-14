import type { TrendResult } from "../types/trend";
import { monthOrdinal } from "./contracts";

export function decimalYear(month: string): number {
  const year = Number(month.slice(0, 4));
  const start = Date.UTC(year, 0, 1);
  return year + (Date.parse(`${month}-01T00:00:00Z`) - start) /
    (Date.UTC(year + 1, 0, 1) - start);
}

const median = (values: number[]) => {
  const sorted = [...values].sort((a, b) => a - b);
  const mid = Math.floor(sorted.length / 2);
  return sorted.length % 2 ? sorted[mid] : (sorted[mid - 1] + sorted[mid]) / 2;
};

export function chartData(result: TrendResult, mode: "anomaly" | "raw") {
  const lookup = new Map(result.series.map(p => [p.date, p]));
  const first = monthOrdinal(result.metadata.date_range.start);
  const last = monthOrdinal(result.metadata.date_range.end);
  const dates = Array.from({ length: last - first + 1 }, (_, i) => {
    const ordinal = first + i;
    return `${Math.floor(ordinal / 12).toString().padStart(4, "0")}-${(ordinal % 12 + 1).toString().padStart(2, "0")}`;
  });
  const years = dates.map(decimalYear);
  const values = dates.map(date => lookup.get(date)?.[mode === "raw" ? "raw" : "anomaly"] ?? null);
  const valid = values.flatMap((value, i) => value === null ? [] : [{ x: years[i], y: value }]);
  const slope = result.trend.slope_unit === `${result.metadata.unit}/decade`
    ? result.trend.sens_slope / 10
    : result.trend.slope_unit === `${result.metadata.unit}/year` ? result.trend.sens_slope : null;
  const intercept = valid.length >= 2 && slope !== null
    ? median(valid.map(p => p.y)) - slope * median(valid.map(p => p.x)) : null;
  // Descriptive guide only; never interpolate missing measurements or invent a CI.
  const guide = mode === "anomaly" && intercept !== null && slope !== null
    ? years.map(x => intercept + slope * x) : [];
  return { dates, values, guide };
}

export function formatProbability(value: number): string {
  return value === 0 ? "0 (reported)" : value < 0.0001 ? value.toExponential(3) : value.toPrecision(4);
}

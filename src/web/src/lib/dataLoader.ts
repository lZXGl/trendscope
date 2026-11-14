import { parseIndex, parseResult, readJson } from "./contracts";
import type { TrendIndexItem, TrendResult } from "../types/trend";

export async function loadIndex(): Promise<TrendIndexItem[]> {
  return parseIndex(await readJson(await fetch("/data/index.json", { signal: AbortSignal.timeout(15000) })));
}

export async function loadResult(file: string): Promise<TrendResult> {
  if (!/^results\/[a-zA-Z0-9_-]+\.json$/.test(file)) throw new Error("Invalid result path.");
  return parseResult(await readJson(await fetch(`/data/${file}`, { signal: AbortSignal.timeout(15000) })));
}

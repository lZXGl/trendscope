import { readFile, readdir } from "node:fs/promises";
import { parseIndex, parseResult } from "../src/lib/contracts";

const json = async (path: string) => JSON.parse(await readFile(path, "utf8"));
const directory = "public/data";
const items = parseIndex(await json(`${directory}/index.json`));
if (!items.length) throw new Error("Release needs an observed dataset.");
for (const item of items) {
  const result = parseResult(await json(`${directory}/${item.file}`));
  for (const field of ["region", "lat", "lon", "variable", "unit", "source"] as const) {
    if (item[field] !== result.metadata[field]) throw new Error(`Catalogue mismatch: ${item.file} ${field}`);
  }
  if (item.significant !== result.trend.significant || item.headline !== result.verdict.headline) {
    throw new Error(`Catalogue verdict mismatch: ${item.file}`);
  }
}
const published = items.map(item => item.file.slice("results/".length)).sort();
const files = (await readdir(`${directory}/results`)).sort();
if (JSON.stringify(files) !== JSON.stringify(published)) throw new Error("Unlisted public result assets.");
const baseline = await json(`${directory}/results/nile_delta_ndvi.json`);
const handoff = await json("../../data/processed/nile_delta_ndvi.result.json");
if (JSON.stringify(baseline) !== JSON.stringify(handoff)) throw new Error("Baseline differs from reviewed handoff.");
console.log(`Validated ${items.length} observed catalogue entries and reviewed baseline.`);

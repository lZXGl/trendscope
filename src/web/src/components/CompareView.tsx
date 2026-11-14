import { useEffect, useState } from "react";
import { loadResult } from "../lib/dataLoader";
import type { TrendIndexItem, TrendResult } from "../types/trend";
import { TrendChart } from "./TrendChart";
import { VerdictCard } from "./VerdictCard";

function Investigation({ items, label, initialFile }: { items: TrendIndexItem[]; label: string; initialFile: string }) {
  const [file, setFile] = useState(initialFile);
  const [result, setResult] = useState<TrendResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  useEffect(() => {
    let cancelled = false;
    setResult(null);
    setError(null);
    if (file) loadResult(file).then(value => { if (!cancelled) setResult(value); })
      .catch(err => { if (!cancelled) setError(String(err.message)); });
    return () => { cancelled = true; };
  }, [file]);
  return <div className="space-y-4 min-w-0">
    <div className="rounded-xl border border-slate-200 bg-white p-4">
      <label htmlFor={label} className="block text-xs font-semibold uppercase tracking-wider text-slate-500 mb-1.5">{label}</label>
      <select id={label} value={file} onChange={e => setFile(e.target.value)} className="w-full min-w-0 rounded-lg border border-slate-200 bg-slate-50 px-3 py-2 text-sm">
        {items.map(item => <option key={item.file} value={item.file}>{item.region_name} — {item.variable_name} ({item.variable})</option>)}
      </select>
    </div>
    {error ? <div role="alert" className="rounded-xl border border-rose-200 p-4 text-rose-800">{error}</div> : result ? <>
      <TrendChart result={result} compact /><VerdictCard result={result} />
    </> : <div role="status" className="p-8 text-sm text-slate-500">Loading investigation...</div>}
  </div>;
}

export function CompareView({ items }: { items: TrendIndexItem[] }) {
  if (!items.length) return <p>No observed datasets are available for comparison.</p>;
  return <div className="space-y-4">
    {items.length < 2 && <p className="text-sm text-slate-600">Only one observed dataset is published. Both panes show it; independent region comparison is unavailable.</p>}
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
      <Investigation items={items} label="Investigation A" initialFile={items[0].file} />
      <Investigation items={items} label="Investigation B" initialFile={items[1]?.file ?? items[0].file} />
    </div>
  </div>;
}

import { useEffect, useState } from "react";
import { loadResult } from "../lib/dataLoader";
import type { TrendIndexItem, TrendResult } from "../types/trend";
import { TrendChart } from "./TrendChart";
import { VerdictCard } from "./VerdictCard";

interface CompareViewProps {
  items: TrendIndexItem[];
}

export function CompareView({ items }: CompareViewProps) {
  const [leftFile, setLeftFile] = useState(items[0]?.file ?? "");
  const [rightFile, setRightFile] = useState(items[1]?.file ?? items[0]?.file ?? "");
  const [leftResult, setLeftResult] = useState<TrendResult | null>(null);
  const [rightResult, setRightResult] = useState<TrendResult | null>(null);

  useEffect(() => {
    if (!leftFile) return;
    loadResult(leftFile).then(setLeftResult).catch(() => setLeftResult(null));
  }, [leftFile]);

  useEffect(() => {
    if (!rightFile) return;
    loadResult(rightFile).then(setRightResult).catch(() => setRightResult(null));
  }, [rightFile]);

  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
      {[
        { label: "Investigation A", file: leftFile, setFile: setLeftFile, result: leftResult },
        { label: "Investigation B", file: rightFile, setFile: setRightFile, result: rightResult },
      ].map((pane, idx) => (
        <div key={idx} className="space-y-4">
          <div className="rounded-xl border border-slate-200 bg-white p-4">
            <label className="block text-xs font-semibold uppercase tracking-wider text-slate-500 mb-1.5">
              {pane.label}
            </label>
            <select
              value={pane.file}
              onChange={(e) => pane.setFile(e.target.value)}
              className="w-full rounded-lg border border-slate-200 bg-slate-50 px-3 py-2 text-sm text-slate-900 focus:outline-none focus:ring-2 focus:ring-sky-500"
            >
              {items.map((item) => (
                <option key={item.file} value={item.file}>
                  {item.region_name} — {item.variable_name} ({item.variable})
                </option>
              ))}
            </select>
          </div>

          {pane.result ? (
            <>
              <TrendChart result={pane.result} compact />
              <VerdictCard result={pane.result} />
            </>
          ) : (
            <div className="rounded-xl border border-slate-200 bg-white p-8 text-center text-sm text-slate-500">
              Loading investigation...
            </div>
          )}
        </div>
      ))}
    </div>
  );
}

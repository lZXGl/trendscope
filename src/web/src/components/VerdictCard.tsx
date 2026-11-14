import { AlertTriangle, ArrowDownRight, ArrowUpRight, CheckCircle2, Info, Minus, ShieldCheck } from "lucide-react";
import { monthOrdinal } from "../lib/contracts";
import { formatProbability } from "../lib/chartData";
import type { TrendResult } from "../types/trend";

interface VerdictCardProps {
  result: TrendResult;
}

export function VerdictCard({ result }: VerdictCardProps) {
  const { metadata, series, trend, verdict } = result;
  const isMock = Boolean(metadata.is_mock);
  const totalMonths = monthOrdinal(metadata.date_range.end) - monthOrdinal(metadata.date_range.start) + 1;
  const validMonths = series.filter((p) => p.raw !== null && p.anomaly !== null).length;
  const missingMonths = totalMonths - validMonths;
  const coveragePct = totalMonths > 0 ? Math.round((validMonths / totalMonths) * 100) : 0;

  const direction = trend.sens_slope > 0 ? "Increasing" : trend.sens_slope < 0 ? "Decreasing" : "Flat";

  return (
    <div className="rounded-xl border border-slate-200 bg-white p-5 space-y-4">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="space-y-1">
          <div className="flex flex-wrap items-center gap-2">
            <span
              className={`inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-medium ${
                trend.significant
                  ? "bg-emerald-50 text-emerald-800 border border-emerald-200"
                  : "bg-slate-100 text-slate-700 border border-slate-200"
              }`}
            >
              {trend.significant ? <CheckCircle2 className="w-3.5 h-3.5" /> : <Info className="w-3.5 h-3.5" />}
              {trend.significant ? "Nominal p < 0.05 (conditional)" : "No statistically significant trend"}
            </span>

            <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-medium bg-slate-100 text-slate-800 border border-slate-200">
              {direction === "Increasing" ? (
                <ArrowUpRight className="w-3.5 h-3.5 text-emerald-600" />
              ) : direction === "Decreasing" ? (
                <ArrowDownRight className="w-3.5 h-3.5 text-rose-600" />
              ) : (
                <Minus className="w-3.5 h-3.5 text-slate-500" />
              )}
              {direction}
            </span>

            {trend.autocorrected ? (
              <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-medium bg-sky-50 text-sky-800 border border-sky-200">
                <ShieldCheck className="w-3.5 h-3.5" />
                Autocorrelation-Corrected
              </span>
            ) : (
              <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-medium bg-amber-50/70 text-amber-900 border border-amber-200">
                <Info className="w-3.5 h-3.5" />
                Ordinary MK (Uncorrected)
              </span>
            )}

            {isMock && (
              <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-amber-50 text-amber-800 border border-amber-300">
                <AlertTriangle className="w-3.5 h-3.5" />
                DEVELOPMENT FIXTURE (MOCK)
              </span>
            )}
          </div>

          <h3 className="text-base font-semibold text-slate-900 pt-1">{verdict.headline}</h3>
          <p className="text-sm text-slate-600 leading-relaxed">{verdict.summary}</p>
        </div>
      </div>

      <div className="grid grid-cols-2 xl:grid-cols-5 gap-3 pt-1">
        <div className="rounded-lg border border-slate-200 bg-slate-50/70 p-3">
          <div className="text-[11px] uppercase tracking-wider text-slate-500 font-medium">Sen&apos;s Slope</div>
          <div className="text-base break-all font-semibold font-mono tabular-nums text-slate-900 mt-0.5">
            {trend.sens_slope > 0 ? "+" : ""}{trend.sens_slope.toPrecision(5)}
          </div>
          <div className="text-[11px] text-slate-500">{trend.slope_unit}</div>
        </div>

        <div className="rounded-lg border border-slate-200 bg-slate-50/70 p-3">
          <div className="text-[11px] uppercase tracking-wider text-slate-500 font-medium">p-value</div>
          <div className="text-base break-all font-semibold font-mono tabular-nums text-slate-900 mt-0.5">
            {formatProbability(trend.p_value)}
          </div>
          <div className="text-[11px] text-slate-500">{trend.p_value < 0.05 ? "p < 0.05" : "p ≥ 0.05"}</div>
        </div>

        <div className="rounded-lg border border-slate-200 bg-slate-50/70 p-3">
          <div className="text-[11px] uppercase tracking-wider text-slate-500 font-medium">Kendall&apos;s τ</div>
          <div className="text-base break-all font-semibold font-mono tabular-nums text-slate-900 mt-0.5">
            {trend.tau.toFixed(3)}
          </div>
          <div className="text-[11px] text-slate-500">Monotonic rank</div>
        </div>

        <div className="rounded-lg border border-slate-200 bg-slate-50/70 p-3">
          <div className="text-[11px] uppercase tracking-wider text-slate-500 font-medium">Temporal coverage</div>
          <div className="text-base break-all font-semibold font-mono tabular-nums text-slate-900 mt-0.5">
            {coveragePct}%
          </div>
          <div className="text-[11px] text-slate-500">
            {validMonths}/{totalMonths} mo ({missingMonths} missing)
          </div>
        </div>

        <div className="rounded-lg border border-slate-200 bg-slate-50/70 p-3">
          <div className="text-[11px] uppercase tracking-wider text-slate-500 font-medium">Method</div>
          <div className="text-xs font-medium text-slate-800 mt-1 leading-snug">{trend.method}</div>
        </div>
      </div>

      <div className="border-t border-slate-100 pt-3">
        <p className="text-xs text-amber-900 mb-3">Inference is provisional. Temporal completeness does not guarantee spatial coverage, NASA provenance or calibrated significance. Trend does not establish cause.</p>
        <details>
        <summary className="text-xs font-semibold cursor-pointer text-slate-600">All scientific caveats and provenance limits</summary>
        <h4 className="sr-only">
          Scientific Caveats &amp; Limitations
        </h4>
        <ul className="space-y-1.5">
          {verdict.caveats.map((caveat, i) => (
            <li key={i} className="text-xs text-slate-600 flex items-start gap-2">
              <span className="text-slate-400 mt-0.5">•</span>
              <span>{caveat}</span>
            </li>
          ))}
        </ul>
        </details>
      </div>
    </div>
  );
}

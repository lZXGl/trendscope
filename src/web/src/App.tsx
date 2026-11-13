import { useEffect, useMemo, useRef, useState } from "react";
import gsap from "gsap";
import { AlertCircle, Columns2, Compass, Loader2, Play, Shuffle } from "lucide-react";
import { CompareView } from "./components/CompareView";
import { GlobePanel } from "./components/GlobePanel";
import { TrendChart } from "./components/TrendChart";
import { VerdictCard } from "./components/VerdictCard";
import { loadIndex, loadResult } from "./lib/dataLoader";
import {
  fetchJobResult,
  fetchJobStatus,
  makeBboxAround,
  randomLandSeedAoi,
  submitAnalysisJob,
} from "./lib/jobClient";
import type { AoiJobStatus, AoiSelection, TrendIndexItem, TrendResult } from "./types/trend";

const STAGE_LABELS: Record<NonNullable<AoiJobStatus["stage"]>, string> = {
  checking_area: "Validating land AOI bounds...",
  waiting_for_nasa: "Waiting for NASA AppEEARS satellite retrieval...",
  analysing: "Running Mann–Kendall & Sen's slope statistics...",
};

function toMmDdYyyy(isoDate: string): string {
  const [y, m, d] = isoDate.split("-");
  return y && m && d ? `${m}-${d}-${y}` : "01-01-2001";
}

export function App() {
  const mainRef = useRef<HTMLDivElement>(null);
  const [items, setItems] = useState<TrendIndexItem[]>([]);
  const [usingFallback, setUsingFallback] = useState(false);
  const [view, setView] = useState<"explore" | "compare">("explore");
  const [selectedFile, setSelectedFile] = useState<string>("");
  const [activeResult, setActiveResult] = useState<TrendResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [customAoi, setCustomAoi] = useState<AoiSelection | null>(null);
  const [selectedProduct, setSelectedProduct] = useState<string>("MOD13A3.061");
  const [startDate, setStartDate] = useState<string>("2001-01-01");
  const [endDate, setEndDate] = useState<string>("2024-12-31");
  const [jobStatus, setJobStatus] = useState<AoiJobStatus | null>(null);
  const [jobNotice, setJobNotice] = useState<string | null>(null);
  const [submittingJob, setSubmittingJob] = useState<boolean>(false);

  useEffect(() => {
    loadIndex().then(({ items: loaded, usingFallback: fb }) => {
      setItems(loaded);
      setUsingFallback(fb);
      if (loaded[0]) setSelectedFile(loaded[0].file);
    });
  }, []);

  useEffect(() => {
    if (!selectedFile) return;
    setError(null);
    loadResult(selectedFile)
      .then(setActiveResult)
      .catch((err: Error) => setError(err.message));
  }, [selectedFile]);

  useEffect(() => {
    if (!mainRef.current) return;
    const ctx = gsap.context(() => {
      gsap.from(".reveal-card", {
        y: 12,
        opacity: 0,
        duration: 0.35,
        stagger: 0.06,
        ease: "power2.out",
        clearProps: "transform",
      });
    }, mainRef);
    return () => ctx.revert();
  }, [view]);

  const activeItem = useMemo(
    () => items.find((i) => i.file === selectedFile) ?? items[0],
    [items, selectedFile],
  );

  const regions = useMemo(() => {
    const map = new Map<string, string>();
    for (const item of items) map.set(item.region, item.region_name);
    return Array.from(map.entries());
  }, [items]);

  const handleRegionSelect = (region: string) => {
    setCustomAoi(null);
    setJobStatus(null);
    setJobNotice(null);
    const firstMatch = items.find((i) => i.region === region);
    if (firstMatch) setSelectedFile(firstMatch.file);
  };

  const handleSelectCustomAoi = (lat: number, lon: number) => {
    setJobStatus(null);
    setJobNotice(null);
    setError(null);
    setCustomAoi({
      lat: Number(lat.toFixed(4)),
      lon: Number(lon.toFixed(4)),
      bbox: makeBboxAround(lat, lon, 0.5),
      label: `Selected AOI (${lat.toFixed(2)}°, ${lon.toFixed(2)}°)`,
      isRandom: false,
    });
  };

  const handleRandomRegion = () => {
    setJobStatus(null);
    setJobNotice(null);
    setError(null);
    const seed = Math.floor(100 + Math.random() * 9000);
    setCustomAoi(randomLandSeedAoi(seed));
  };

  useEffect(() => {
    if (!jobStatus || (jobStatus.status !== "queued" && jobStatus.status !== "processing")) {
      return;
    }
    const timer = window.setInterval(async () => {
      try {
        const updated = await fetchJobStatus(jobStatus.job_id);
        setJobStatus(updated);
        if (updated.status === "completed" && updated.result_file) {
          const res = await fetchJobResult(updated.result_file);
          setActiveResult(res);
          setJobNotice(null);
        } else if (updated.status === "failed") {
          setError(updated.error || "NASA analysis job failed.");
        }
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to poll job status.");
      }
    }, 4000);
    return () => window.clearInterval(timer);
  }, [jobStatus]);

  const handleSubmitAnalysis = async () => {
    if (!customAoi) return;
    setSubmittingJob(true);
    setError(null);
    setJobNotice(null);
    const res = await submitAnalysisJob({
      bbox: customAoi.bbox,
      product: selectedProduct,
      start_date: toMmDdYyyy(startDate),
      end_date: toMmDdYyyy(endDate),
    });
    setSubmittingJob(false);

    if (res.mode === "unavailable") {
      setJobNotice(res.message ?? "Live job API unavailable.");
      return;
    }
    if (res.message && !res.job) {
      setError(res.message);
      return;
    }
    if (res.job) {
      setJobStatus(res.job);
      if (res.job.status === "completed" && res.job.result_file) {
        try {
          const loaded = await fetchJobResult(res.job.result_file);
          setActiveResult(loaded);
        } catch (err) {
          setError(err instanceof Error ? err.message : "Failed to load cached job result.");
        }
      } else if (res.job.status === "failed") {
        setError(res.job.error || "NASA analysis job failed.");
      }
    }
  };

  return (
    <div ref={mainRef} className="min-h-screen bg-[#FAFAFA] text-slate-900">
      <header className="sticky top-0 z-20 border-b border-slate-200 bg-white/90 backdrop-blur-sm">
        <div className="mx-auto max-w-7xl px-4 sm:px-6 h-14 flex items-center justify-between gap-4">
          <div className="flex items-center gap-2.5">
            <svg
              width="24"
              height="24"
              viewBox="0 0 24 24"
              fill="none"
              aria-hidden="true"
              className="shrink-0"
            >
              <circle cx="12" cy="12" r="9.5" stroke="#0F172A" strokeWidth="1.75" />
              <ellipse cx="12" cy="12" rx="4.5" ry="9.5" stroke="#94A3B8" strokeWidth="1.25" />
              <path
                d="M5.5 14.5L9.5 10.5L13 12.5L18.5 7"
                stroke="#0284C7"
                strokeWidth="2"
                strokeLinecap="round"
                strokeLinejoin="round"
              />
            </svg>
            <div>
              <span className="font-semibold tracking-tight text-slate-900">TrendScope</span>
              <span className="hidden sm:inline text-xs text-slate-500 ml-2">
                Earth System Trend Detective
              </span>
            </div>
          </div>

          <div className="flex items-center gap-2">
            {usingFallback && (
              <span className="hidden md:inline-block text-[11px] font-medium px-2 py-0.5 rounded-md bg-amber-50 text-amber-800 border border-amber-200">
                Previewing Mock Index
              </span>
            )}
            <div className="inline-flex rounded-lg border border-slate-200 bg-slate-50 p-0.5">
              <button
                type="button"
                onClick={() => setView("explore")}
                className={`tactile-btn inline-flex items-center gap-1.5 px-3 py-1 text-xs font-medium rounded-md ${
                  view === "explore"
                    ? "bg-white text-slate-900 shadow-xs"
                    : "text-slate-600 hover:text-slate-900"
                }`}
              >
                <Compass className="w-3.5 h-3.5" />
                Explorer
              </button>
              <button
                type="button"
                onClick={() => setView("compare")}
                className={`tactile-btn inline-flex items-center gap-1.5 px-3 py-1 text-xs font-medium rounded-md ${
                  view === "compare"
                    ? "bg-white text-slate-900 shadow-xs"
                    : "text-slate-600 hover:text-slate-900"
                }`}
              >
                <Columns2 className="w-3.5 h-3.5" />
                Compare
              </button>
            </div>
          </div>
        </div>
      </header>

      <main className="mx-auto max-w-7xl px-4 sm:px-6 py-6">
        {view === "compare" ? (
          <CompareView items={items} />
        ) : (
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
            <div className="lg:col-span-4 space-y-4 reveal-card">
              {items.length > 0 && activeItem && (
                <GlobePanel
                  items={items}
                  selectedRegion={activeItem.region}
                  customAoi={customAoi}
                  onSelectRegion={handleRegionSelect}
                  onSelectCustomAoi={handleSelectCustomAoi}
                />
              )}

              <div className="rounded-xl border border-slate-200 bg-white p-4 space-y-3">
                <div>
                  <div className="flex items-center justify-between gap-2">
                  <label className="block text-xs font-semibold uppercase tracking-wider text-slate-500">
                    Region / AOI
                  </label>
                  <button
                    type="button"
                    onClick={handleRandomRegion}
                    className="tactile-btn inline-flex items-center gap-1 px-2.5 py-1 rounded-md text-[11px] font-medium border border-amber-300 bg-amber-50 text-amber-900 hover:bg-amber-100"
                  >
                    <Shuffle className="w-3 h-3" />
                    Random Region
                  </button>
                </div>
                <p className="text-[11px] text-slate-500">
                  Click anywhere on the 3D globe or pick a pre-computed region below.
                </p>

                {customAoi && (
                  <div className="rounded-lg border border-amber-200 bg-amber-50/70 p-3 space-y-2.5 text-xs">
                    <div className="flex items-center justify-between gap-2">
                      <span className="font-semibold text-amber-950">{customAoi.label}</span>
                      <button
                        type="button"
                        onClick={() => setCustomAoi(null)}
                        className="text-[11px] text-amber-800 underline"
                      >
                        Clear
                      </button>
                    </div>
                    <div className="font-mono text-[11px] text-amber-900">
                      bbox: [{customAoi.bbox.join(", ")}]
                    </div>
                    <div className="grid grid-cols-2 gap-2">
                      <div>
                        <label className="block text-[10px] font-semibold uppercase text-slate-600 mb-0.5">
                          Start Date
                        </label>
                        <input
                          type="date"
                          value={startDate}
                          onChange={(e) => setStartDate(e.target.value)}
                          className="w-full rounded border border-slate-300 bg-white px-2 py-1 text-[11px]"
                        />
                      </div>
                      <div>
                        <label className="block text-[10px] font-semibold uppercase text-slate-600 mb-0.5">
                          End Date
                        </label>
                        <input
                          type="date"
                          value={endDate}
                          onChange={(e) => setEndDate(e.target.value)}
                          className="w-full rounded border border-slate-300 bg-white px-2 py-1 text-[11px]"
                        />
                      </div>
                    </div>
                    <div>
                      <label className="block text-[10px] font-semibold uppercase text-slate-600 mb-0.5">
                        NASA Product
                      </label>
                      <select
                        value={selectedProduct}
                        onChange={(e) => setSelectedProduct(e.target.value)}
                        className="w-full rounded border border-slate-300 bg-white px-2 py-1 text-[11px]"
                      >
                        <option value="MOD13A3.061">MOD13A3.061 (Monthly 1 km NDVI)</option>
                      </select>
                    </div>
                    <button
                      type="button"
                      disabled={submittingJob}
                      onClick={handleSubmitAnalysis}
                      className="tactile-btn w-full inline-flex items-center justify-center gap-1.5 rounded-lg bg-slate-900 text-white px-3 py-2 text-xs font-medium hover:bg-slate-800 disabled:opacity-60"
                    >
                      {submittingJob ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Play className="w-3.5 h-3.5" />}
                      {submittingJob ? "Submitting..." : "Run NASA Analysis"}
                    </button>
                  </div>
                )}
                  <div className="flex flex-wrap gap-1.5">
                    {regions.map(([slug, name]) => (
                      <button
                        key={slug}
                        type="button"
                        onClick={() => handleRegionSelect(slug)}
                        className={`tactile-btn px-3 py-1.5 rounded-lg text-xs font-medium border ${
                          activeItem?.region === slug
                            ? "bg-slate-900 text-white border-slate-900"
                            : "bg-white text-slate-700 border-slate-200 hover:bg-slate-50"
                        }`}
                      >
                        {name}
                      </button>
                    ))}
                  </div>
                </div>

                <div>
                  <label className="block text-xs font-semibold uppercase tracking-wider text-slate-500 mb-1.5">
                    NASA Variable
                  </label>
                  <div className="space-y-1.5">
                    {items
                      .filter((i) => !activeItem || i.region === activeItem.region)
                      .map((item) => (
                        <button
                          key={item.file}
                          type="button"
                          onClick={() => setSelectedFile(item.file)}
                          className={`tactile-btn w-full text-left px-3 py-2 rounded-lg border text-xs ${
                            selectedFile === item.file
                              ? "border-sky-600 bg-sky-50/60 text-slate-900"
                              : "border-slate-200 bg-white text-slate-700 hover:bg-slate-50"
                          }`}
                        >
                          <div className="font-semibold">{item.variable_name}</div>
                          <div className="text-[11px] text-slate-500 mt-0.5">
                            {item.variable} • {item.unit}
                          </div>
                        </button>
                      ))}
                  </div>
                </div>
              </div>
            </div>

            <div className="lg:col-span-8 space-y-4 reveal-card">
              {jobStatus && (
                <div className="rounded-xl border border-sky-200 bg-sky-50/70 p-4 text-xs text-sky-950 space-y-1">
                  <div className="flex items-center justify-between font-semibold">
                    <span>
                      Job {jobStatus.job_id} — {jobStatus.status.toUpperCase()}
                    </span>
                    {jobStatus.nasa_task_id && (
                      <span className="font-mono text-[11px] text-sky-800">
                        NASA Task: {jobStatus.nasa_task_id}
                      </span>
                    )}
                  </div>
                  {jobStatus.stage && (
                    <div className="flex items-center gap-1.5 text-sky-800">
                      <Loader2 className="w-3.5 h-3.5 animate-spin" />
                      <span>{STAGE_LABELS[jobStatus.stage]}</span>
                    </div>
                  )}
                </div>
              )}

              {jobNotice && (
                <div className="rounded-xl border border-amber-200 bg-amber-50 p-4 text-xs text-amber-900 flex items-start gap-2">
                  <AlertCircle className="w-4 h-4 shrink-0 mt-0.5 text-amber-700" />
                  <span>{jobNotice}</span>
                </div>
              )}

              {error && (
                <div className="rounded-xl border border-rose-200 bg-rose-50 p-4 text-sm text-rose-800">
                  {error}
                </div>
              )}

              {activeResult ? (
                <>
                  <TrendChart result={activeResult} />
                  <VerdictCard result={activeResult} />
                </>
              ) : (
                !error && (
                  <div className="rounded-xl border border-slate-200 bg-white p-12 text-center text-sm text-slate-500">
                    Loading NASA Earth trend data...
                  </div>
                )
              )}
            </div>
          </div>
        )}
      </main>
    </div>
  );
}

export default App;

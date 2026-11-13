import { useEffect, useMemo, useRef, useState } from "react";
import gsap from "gsap";
import { Columns2, Compass } from "lucide-react";
import { CompareView } from "./components/CompareView";
import { GlobePanel } from "./components/GlobePanel";
import { TrendChart } from "./components/TrendChart";
import { VerdictCard } from "./components/VerdictCard";
import { loadIndex, loadResult } from "./lib/dataLoader";
import type { TrendIndexItem, TrendResult } from "./types/trend";

export function App() {
  const mainRef = useRef<HTMLDivElement>(null);
  const [items, setItems] = useState<TrendIndexItem[]>([]);
  const [usingFallback, setUsingFallback] = useState(false);
  const [view, setView] = useState<"explore" | "compare">("explore");
  const [selectedFile, setSelectedFile] = useState<string>("");
  const [activeResult, setActiveResult] = useState<TrendResult | null>(null);
  const [error, setError] = useState<string | null>(null);

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
    const firstMatch = items.find((i) => i.region === region);
    if (firstMatch) setSelectedFile(firstMatch.file);
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
              <div className="rounded-xl border border-slate-200 bg-white p-4 space-y-3">
                <div>
                  <label className="block text-xs font-semibold uppercase tracking-wider text-slate-500 mb-1.5">
                    Region
                  </label>
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

              {items.length > 0 && activeItem && (
                <GlobePanel
                  items={items}
                  selectedRegion={activeItem.region}
                  onSelectRegion={handleRegionSelect}
                />
              )}
            </div>

            <div className="lg:col-span-8 space-y-4 reveal-card">
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

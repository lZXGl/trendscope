import { useEffect, useRef, useState } from "react";
import { Button } from "@astryxdesign/core/Button";
import { Selector } from "@astryxdesign/core/Selector";
import { Globe2 } from "lucide-react";
import { GlobePanel } from "./components/GlobePanel";
import { AoiControls } from "./components/AoiControls";
import { TrendChart } from "./components/TrendChart";
import { VerdictCard } from "./components/VerdictCard";
import { loadIndex, loadResult } from "./lib/dataLoader";
import {
  fetchJobResult,
  fetchJobStatus,
  LIVE_JOBS_ENABLED,
  submitAnalysisJob,
  validateRequest,
} from "./lib/jobClient";
import {
  AOI_STORAGE_KEY,
  EMPTY_AOI,
  coordinateLabel,
  evaluateAoi,
  restoreAoi,
  type AoiDraft,
} from "./lib/aoi";
import { useAppearance, type Appearance } from "./lib/appearance";
import type { AoiJobStatus, TrendResult } from "./types/trend";

const stages = {
  checking_area: "Checking the selected area",
  waiting_for_nasa: "Retrieving NASA observations",
  analysing: "Computing the trend",
};
const mmddyyyy = (date: string) => {
  if (!/^\d{4}-\d{2}-\d{2}$/.test(date))
    throw new Error("Enter both valid dates.");
  const [y, m, d] = date.split("-");
  return `${m}-${d}-${y}`;
};

export function App() {
  const [stored] = useState(restoreAoi);
  const [draft, setDraft] = useState(stored.draft);
  const [confirmed, setConfirmed] = useState(stored.confirmed);
  const { area, error: areaError } = evaluateAoi(draft);
  const [example, setExample] = useState<TrendResult | null>(null);
  const [exampleName, setExampleName] = useState("");
  const [catalogueError, setCatalogueError] = useState<string | null>(null);
  const [exampleLoading, setExampleLoading] = useState(true);
  const [display, setDisplay] = useState<"example" | "selection">(
    stored.draft.lat || stored.draft.lon ? "selection" : "example",
  );
  const [analysis, setAnalysis] = useState<TrendResult | null>(null);
  const [job, setJob] = useState<AoiJobStatus | null>(null);
  const [jobError, setJobError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [pollStopped, setPollStopped] = useState(false);
  const [start, setStart] = useState("2001-01-01");
  const [end, setEnd] = useState("2024-12-31");
  const epoch = useRef(0);
  const { appearance, setAppearance } = useAppearance();

  useEffect(() => {
    let cancelled = false;
    loadIndex()
      .then(async (items) => {
        if (!items[0])
          throw new Error("No observed examples are currently published.");
        const value = await loadResult(items[0].file);
        if (!cancelled) {
          setExample(value);
          setExampleName(items[0].region_name);
        }
      })
      .catch((e) => {
        if (!cancelled) setCatalogueError(e.message);
      })
      .finally(() => {
        if (!cancelled) setExampleLoading(false);
      });
    return () => {
      cancelled = true;
      epoch.current++;
    };
  }, []);
  useEffect(() => {
    try {
      localStorage.setItem(
        AOI_STORAGE_KEY,
        JSON.stringify({ draft, confirmed }),
      );
    } catch {
      /* Selection still works in memory. */
    }
  }, [draft, confirmed]);

  const invalidate = () => {
    epoch.current++;
    setConfirmed(false);
    setAnalysis(null);
    setJob(null);
    setJobError(null);
    setPollStopped(false);
    setSubmitting(false);
    setDisplay("selection");
  };
  const edit = (key: keyof AoiDraft, value: string) => {
    invalidate();
    setDraft((previous) => ({ ...previous, [key]: value }));
  };
  const select = (lat: number, lon: number) => {
    invalidate();
    setDraft((previous) => ({
      ...previous,
      lat: lat.toFixed(4),
      lon: lon.toFixed(4),
    }));
  };
  const clear = () => {
    invalidate();
    setDraft({ ...EMPTY_AOI });
  };
  const confirm = () => {
    if (area) {
      setConfirmed(true);
      setDisplay("selection");
    }
  };

  async function completed(value: AoiJobStatus, generation: number) {
    const result = await fetchJobResult(value);
    if (generation === epoch.current) {
      setAnalysis(result);
      setJob(value);
    }
  }
  useEffect(() => {
    if (!job || !["queued", "processing"].includes(job.status) || pollStopped)
      return;
    let cancelled = false;
    let timer: number;
    const generation = epoch.current;
    const poll = async () => {
      try {
        const updated = await fetchJobStatus(job);
        if (cancelled || generation !== epoch.current) return;
        if (updated.status === "completed")
          await completed(updated, generation);
        else if (updated.status === "failed") {
          setJob(updated);
          setJobError(updated.error || "Analysis failed.");
        } else {
          setJob(updated);
          timer = window.setTimeout(poll, 10000);
        }
      } catch (e) {
        if (!cancelled && generation === epoch.current) {
          setPollStopped(true);
          setJobError(
            e instanceof Error ? e.message : "Status is unavailable.",
          );
        }
      }
    };
    timer = window.setTimeout(poll, 10000);
    return () => {
      cancelled = true;
      window.clearTimeout(timer);
    };
  }, [job?.job_id, job?.status, pollStopped]);

  const analyze = async () => {
    if (!area || !confirmed || !LIVE_JOBS_ENABLED) return;
    const generation = ++epoch.current;
    setSubmitting(true);
    setJobError(null);
    setAnalysis(null);
    setJob(null);
    setPollStopped(false);
    setDisplay("selection");
    try {
      const payload = {
        bbox: area.bbox,
        product: "MOD13A3.061",
        start_date: mmddyyyy(start),
        end_date: mmddyyyy(end),
      };
      validateRequest(payload);
      const response = await submitAnalysisJob(payload);
      if (generation !== epoch.current) return;
      if (!response.job) {
        setJobError(response.message || "Live processing is unavailable.");
        return;
      }
      const value = response.job;
      if (value.status === "completed") await completed(value, generation);
      else {
        setJob(value);
        if (value.status === "failed")
          setJobError(value.error || "Analysis failed.");
      }
    } catch (e) {
      if (generation === epoch.current)
        setJobError(
          e instanceof Error ? e.message : "Analysis is unavailable.",
        );
    } finally {
      if (generation === epoch.current) setSubmitting(false);
    }
  };
  const result = display === "example" ? example : analysis;
  const pending =
    submitting ||
    Boolean(
      job && ["queued", "processing"].includes(job.status) && !pollStopped,
    );

  return (
    <div className="app-frame">
      <header className="app-header">
        <a href="/" className="brand" aria-label="TrendScope home">
          <Globe2 aria-hidden size={23} />
          <span>TrendScope</span>
        </a>
        <Selector
          label="Appearance"
          isLabelHidden
          variant="ghost"
          size="sm"
          value={appearance}
          onChange={(value) => setAppearance(value as Appearance)}
          options={[
            { value: "light", label: "Light" },
            { value: "dark", label: "Dark" },
            { value: "system", label: "System" },
          ]}
          width={110}
        />
      </header>
      <main className="workspace">
        <div className="location-panel">
          <GlobePanel area={area} onSelect={select} />
          <AoiControls
            draft={draft}
            area={area}
            error={areaError}
            confirmed={confirmed}
            onEdit={edit}
            onConfirm={confirm}
            onClear={clear}
            start={start}
            end={end}
            onDates={(a, b) => {
              if (a === start && b === end) return;
              epoch.current++;
              setSubmitting(false);
              setStart(a);
              setEnd(b);
              setJob(null);
              setAnalysis(null);
              setJobError(null);
              setPollStopped(false);
            }}
            live={LIVE_JOBS_ENABLED}
            pending={pending}
            onAnalyze={analyze}
          />
        </div>
        <section className="results-panel" aria-label="Trend results">
          <div className="results-heading">
            <div>
              <p className="eyebrow">
                {display === "example" ? "Observed example" : "Selected area"}
              </p>
              <h2>
                {display === "example"
                  ? exampleName || "Loading example…"
                  : area
                    ? coordinateLabel(area.lat, area.lon)
                    : "Select an area to investigate"}
              </h2>
            </div>
            {display === "example" && (draft.lat || draft.lon) ? (
              <Button
                label={analysis ? "View area result" : "Back to selection"}
                size="sm"
                variant="ghost"
                onClick={() => setDisplay("selection")}
              />
            ) : display === "selection" && example ? (
              <Button
                label="View example"
                size="sm"
                variant="ghost"
                onClick={() => setDisplay("example")}
              />
            ) : null}
          </div>
          {display === "example" ? (
            exampleLoading ? (
              <p role="status" className="empty-state">
                Loading observed data…
              </p>
            ) : catalogueError ? (
              <p role="alert" className="notice error">
                {catalogueError} No mock result has been substituted. Refresh to
                retry.
              </p>
            ) : null
          ) : (
            <>
              {jobError && (
                <div role="alert" className="notice error">
                  {jobError}
                  {pollStopped && (
                    <p>
                      Polling stopped. The current status could not be
                      confirmed.
                    </p>
                  )}
                </div>
              )}
              {!result && (
                <div className="empty-state" aria-live="polite">
                  <h3>
                    {pollStopped
                      ? "Status unavailable"
                      : job?.status === "failed"
                        ? "Analysis unavailable"
                        : pending
                          ? job?.status === "processing"
                            ? "Processing your area"
                            : job
                              ? "Request queued"
                              : "Submitting request…"
                          : area
                            ? "No analysis for this area"
                            : "Start with a location"}
                  </h3>
                  <p>
                    {pending
                      ? job?.stage
                        ? stages[job.stage]
                        : "Waiting for the analysis service."
                      : area
                        ? confirmed
                          ? "No result is available for this area."
                          : "Review the boundary, then confirm your area."
                        : "Click anywhere on the globe or map, or enter coordinates."}
                  </p>
                </div>
              )}
              {job && (
                <details className="job-details">
                  <summary>Job details</summary>
                  <p>
                    {job.job_id} · {job.status}
                  </p>
                  {job.nasa_task_id && <p>NASA task: {job.nasa_task_id}</p>}
                </details>
              )}
            </>
          )}
          {result && (
            <>
              <TrendChart result={result} />
              <VerdictCard result={result} />
            </>
          )}
          {catalogueError && display !== "example" && (
            <p className="quiet">
              The observed example is also unavailable: {catalogueError}
            </p>
          )}
        </section>
      </main>
    </div>
  );
}
export default App;

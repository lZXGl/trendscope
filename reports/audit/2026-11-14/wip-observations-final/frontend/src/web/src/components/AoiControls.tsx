import { useState } from "react";
import { Button } from "@astryxdesign/core/Button";
import { TextInput } from "@astryxdesign/core/TextInput";
import { DateInput, type DateInputProps } from "@astryxdesign/core/DateInput";
import type { AoiDraft } from "../lib/aoi";
import { coordinateLabel } from "../lib/aoi";
import type { AoiSelection } from "../types/trend";

interface Props {
  draft: AoiDraft;
  area: AoiSelection | null;
  error: string | null;
  confirmed: boolean;
  onEdit: (key: keyof AoiDraft, value: string) => void;
  onConfirm: () => void;
  onClear: () => void;
  start: string;
  end: string;
  onDates: (start: string, end: string) => void;
  live: boolean;
  pending: boolean;
  onAnalyze: () => void;
}
export function AoiControls(p: Props) {
  const [startError, setStartError] = useState(false);
  const [endError, setEndError] = useState(false);
  const hasInput = Boolean(p.draft.lat || p.draft.lon);
  return (
    <div className="aoi-controls">
      <form
        onSubmit={(event) => {
          event.preventDefault();
          p.onConfirm();
        }}
      >
        <div className="coordinate-grid">
          {(
            [
              ["lat", "Latitude"],
              ["lon", "Longitude"],
              ["width", "Width (°)"],
              ["height", "Height (°)"],
            ] as const
          ).map(([key, label]) => (
            <TextInput
              key={key}
              label={label}
              value={p.draft[key]}
              onChange={(value) => p.onEdit(key, value)}
              inputMode="decimal"
              autoComplete="off"
              size="md"
              width="100%"
              placeholder={
                key === "lat" || key === "lon" ? "Degrees" : undefined
              }
            />
          ))}
        </div>
        {p.error && hasInput && (
          <p role="alert" className="notice error">
            {p.error}
          </p>
        )}
        <div className="selection-actions">
          <div className="selection-summary" aria-live="polite">
            <strong>
              {p.area
                ? coordinateLabel(p.area.lat, p.area.lon)
                : "No area selected"}
            </strong>
            <span>
              {p.area
                ? `${p.draft.width}° × ${p.draft.height}° · ${p.confirmed ? "Confirmed" : "Not confirmed"}`
                : "Rectangular areas, 0.1–2° per side"}
            </span>
          </div>
          <div className="button-row">
            {hasInput && (
              <Button
                label="Clear"
                variant="ghost"
                size="sm"
                onClick={p.onClear}
              />
            )}
            <Button
              label={p.confirmed ? "Area confirmed" : "Confirm area"}
              type="submit"
              size="sm"
              variant="secondary"
              isDisabled={!p.area || p.confirmed}
            />
          </div>
        </div>
      </form>
      {p.area && (
        <div className="analysis-tools">
          <div className="variable-summary">
            <strong>Vegetation · NDVI</strong>
            <span>Monthly · 1 km</span>
          </div>
          <Button
            label="Analyze area"
            variant="primary"
            size="md"
            isDisabled={
              !p.live || !p.confirmed || p.pending || startError || endError
            }
            isLoading={p.pending}
            onClick={() => {
              if (!startError && !endError) p.onAnalyze();
            }}
          />
          {!p.live && (
            <p className="quiet unavailable">
              Live processing is not connected. Your selection stays on this
              device.
            </p>
          )}
          {p.live && !p.confirmed && (
            <p className="quiet">
              Confirm the boundary before requesting analysis.
            </p>
          )}
          <details className="area-details">
            <summary>Boundary &amp; analysis period</summary>
            <dl
              className="bounds-grid"
              data-testid="selected-bounds"
              data-bbox={p.area.bbox.join(",")}
            >
              {[
                ["West", p.area.bbox[0]],
                ["South", p.area.bbox[1]],
                ["East", p.area.bbox[2]],
                ["North", p.area.bbox[3]],
              ].map(([label, value]) => (
                <div key={label}>
                  <dt>{label}</dt>
                  <dd>{Number(value).toFixed(4)}°</dd>
                </div>
              ))}
            </dl>
            <div className="date-grid">
              <DateInput
                label="Start date"
                value={
                  p.start
                    ? (p.start as NonNullable<DateInputProps["value"]>)
                    : undefined
                }
                onChange={(value) => p.onDates(value ?? "", p.end)}
                onEntryErrorChange={(error) => setStartError(Boolean(error))}
                hasClear
                width="100%"
              />
              <DateInput
                label="End date"
                value={
                  p.end
                    ? (p.end as NonNullable<DateInputProps["value"]>)
                    : undefined
                }
                onChange={(value) => p.onDates(p.start, value ?? "")}
                onEntryErrorChange={(error) => setEndError(Boolean(error))}
                hasClear
                width="100%"
              />
            </div>
            <p className="quiet">
              MOD13A3.061 · Monthly NDVI · 1 km. Land and usable coverage are
              checked by the analysis service, not this basemap.
            </p>
          </details>
        </div>
      )}
    </div>
  );
}

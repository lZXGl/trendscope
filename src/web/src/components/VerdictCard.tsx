import { formatProbability } from "../lib/chartData";
import { monthOrdinal } from "../lib/contracts";
import type { TrendResult } from "../types/trend";

export function VerdictCard({ result }: { result: TrendResult }) {
  const { metadata, series, trend, verdict } = result;
  const total =
    monthOrdinal(metadata.date_range.end) -
    monthOrdinal(metadata.date_range.start) +
    1;
  const valid = series.filter(
    (point) => point.raw !== null && point.anomaly !== null,
  ).length;
  const direction =
    trend.sens_slope > 0
      ? "Increasing"
      : trend.sens_slope < 0
        ? "Decreasing"
        : "Flat";
  return (
    <div className="trend-summary">
      <div className="effect-heading">
        <div>
          <p className="eyebrow">{direction} anomalies</p>
          <p className="effect-value">
            {trend.sens_slope > 0 ? "+" : ""}
            {trend.sens_slope.toPrecision(5)} <span>{trend.slope_unit}</span>
          </p>
        </div>
        <span className="quiet">Provisional trend</span>
      </div>
      <dl className="stat-grid">
        <div>
          <dt>Two-sided p-value</dt>
          <dd>{formatProbability(trend.p_value)}</dd>
          <span className="quiet">
            {trend.significant ? "Nominal p < 0.05" : "No significant trend"}
          </span>
        </div>
        <div>
          <dt>Temporal coverage</dt>
          <dd>{Math.round((valid / total) * 100)}%</dd>
          <span className="quiet">
            {valid}/{total} mo ({total - valid} missing)
          </span>
        </div>
      </dl>
      <details className="scientific-details">
        <summary>Source &amp; scientific details</summary>
        <div className="detail-content">
          <dl className="source-grid">
            <div>
              <dt>Source</dt>
              <dd>{metadata.source}</dd>
            </div>
            <div>
              <dt>Study centre</dt>
              <dd>
                {metadata.lat}°, {metadata.lon}°
              </dd>
            </div>
            <div>
              <dt>Method</dt>
              <dd>{trend.method}</dd>
            </div>
            <div>
              <dt>Kendall’s τ</dt>
              <dd>{trend.tau.toFixed(3)}</dd>
            </div>
            <div>
              <dt>Autocorrelation correction</dt>
              <dd>
                {trend.autocorrected
                  ? "Applied"
                  : "Not applied to the primary test"}
              </dd>
            </div>
            <div>
              <dt>Data classification</dt>
              <dd>
                {metadata.is_mock === false
                  ? "Observed input; provenance limitations below"
                  : "Development fixture"}
              </dd>
            </div>
          </dl>
          <p>{verdict.headline}</p>
          <p>{verdict.summary}</p>
          <p>
            No slope confidence interval is supplied. Statistical significance
            is conditional, does not establish cause, and non-significance does
            not prove stability.
          </p>
          <ul>
            {verdict.caveats.map((caveat, i) => (
              <li key={i}>{caveat}</li>
            ))}
          </ul>
        </div>
      </details>
    </div>
  );
}

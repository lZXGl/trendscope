import { useEffect, useRef, useState } from "react";
import * as echarts from "echarts";
import type { TrendResult } from "../types/trend";

interface TrendChartProps {
  result: TrendResult;
  compact?: boolean;
}

export function TrendChart({ result, compact = false }: TrendChartProps) {
  const chartRef = useRef<HTMLDivElement>(null);
  const instanceRef = useRef<echarts.ECharts | null>(null);
  const [mode, setMode] = useState<"anomaly" | "raw">("anomaly");

  useEffect(() => {
    const el = chartRef.current;
    if (!el) return;
    const chart = echarts.init(el);
    instanceRef.current = chart;

    const obs = new ResizeObserver(() => chart.resize());
    obs.observe(el);

    return () => {
      obs.disconnect();
      chart.dispose();
      instanceRef.current = null;
    };
  }, []);

  useEffect(() => {
    const chart = instanceRef.current;
    if (!chart) return;

    const dates = result.series.map((p) => p.date);
    const values = result.series.map((p) => (mode === "anomaly" ? p.anomaly : p.raw));
    const accent = mode === "anomaly" ? "#0284c7" : "#059669";

    chart.setOption({
      animationDuration: 450,
      grid: { top: 28, right: 20, bottom: compact ? 36 : 56, left: 54 },
      tooltip: {
        trigger: "axis",
        backgroundColor: "#ffffff",
        borderColor: "#cbd5e1",
        textStyle: { color: "#0f172a", fontSize: 12 },
        valueFormatter: (v: unknown) =>
          typeof v === "number" ? `${v.toFixed(4)} ${result.metadata.unit}` : "Missing",
      },
      xAxis: {
        type: "category",
        data: dates,
        axisLine: { lineStyle: { color: "#cbd5e1" } },
        axisLabel: { color: "#475569", fontSize: 11 },
      },
      yAxis: {
        type: "value",
        name: mode === "anomaly" ? `Anomaly (${result.metadata.unit})` : result.metadata.unit,
        nameTextStyle: { color: "#64748b", fontSize: 11 },
        splitLine: { lineStyle: { color: "#f1f5f9" } },
        axisLabel: { color: "#475569", fontSize: 11 },
      },
      dataZoom: compact
        ? []
        : [
            { type: "inside", start: 0, end: 100 },
            {
              type: "slider",
              height: 18,
              bottom: 8,
              borderColor: "#e2e8f0",
              fillerColor: "rgba(2, 132, 199, 0.12)",
            },
          ],
      series: [
        {
          name: mode === "anomaly" ? "Monthly Anomaly" : "Raw Observation",
          type: "line",
          data: values,
          connectNulls: false,
          smooth: false,
          showSymbol: dates.length <= 24,
          symbolSize: 6,
          lineStyle: { width: 2, color: accent },
          itemStyle: { color: accent },
          areaStyle: {
            color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
              { offset: 0, color: mode === "anomaly" ? "rgba(2,132,199,0.16)" : "rgba(5,150,105,0.16)" },
              { offset: 1, color: "rgba(255,255,255,0)" },
            ]),
          },
        },
      ],
    });
  }, [result, mode, compact]);

  return (
    <div className="rounded-xl border border-slate-200 bg-white p-4">
      <div className="flex flex-wrap items-center justify-between gap-2 mb-3">
        <div>
          <h2 className="text-sm font-semibold text-slate-900">
            {result.metadata.variable} Time Series ({result.metadata.date_range.start} to{" "}
            {result.metadata.date_range.end})
          </h2>
          <p className="text-xs text-slate-500">{result.metadata.source}</p>
        </div>

        <div className="inline-flex rounded-lg border border-slate-200 bg-slate-50 p-0.5">
          <button
            type="button"
            onClick={() => setMode("anomaly")}
            className={`tactile-btn px-3 py-1 text-xs font-medium rounded-md ${
              mode === "anomaly"
                ? "bg-white text-slate-900 shadow-xs"
                : "text-slate-600 hover:text-slate-900"
            }`}
          >
            Anomaly
          </button>
          <button
            type="button"
            onClick={() => setMode("raw")}
            className={`tactile-btn px-3 py-1 text-xs font-medium rounded-md ${
              mode === "raw"
                ? "bg-white text-slate-900 shadow-xs"
                : "text-slate-600 hover:text-slate-900"
            }`}
          >
            Raw Value
          </button>
        </div>
      </div>

      <div ref={chartRef} className={compact ? "h-[240px] w-full" : "h-[340px] w-full"} />
    </div>
  );
}

import { useEffect, useRef, useState } from "react";
import * as echarts from "echarts";
import "echarts/theme/v5";
import {
  SegmentedControl,
  SegmentedControlItem,
} from "@astryxdesign/core/SegmentedControl";
import { chartData } from "../lib/chartData";
import { useAppearance } from "../lib/appearance";
import type { TrendResult } from "../types/trend";

export function TrendChart({
  result,
  compact = false,
}: {
  result: TrendResult;
  compact?: boolean;
}) {
  const chartRef = useRef<HTMLDivElement>(null);
  const instanceRef = useRef<echarts.ECharts | null>(null);
  const [mode, setMode] = useState<"anomaly" | "raw">("anomaly");
  const { resolved } = useAppearance();
  useEffect(() => {
    if (!chartRef.current) return;
    const chart = echarts.init(chartRef.current, "v5");
    instanceRef.current = chart;
    const observer = new ResizeObserver(() => chart.resize());
    observer.observe(chartRef.current);
    return () => {
      observer.disconnect();
      chart.dispose();
      instanceRef.current = null;
    };
  }, []);
  useEffect(() => {
    const chart = instanceRef.current;
    if (!chart) return;
    const { dates, values, guide } = chartData(result, mode);
    const dark = resolved === "dark";
    const accent =
      mode === "anomaly"
        ? dark
          ? "#7cc9e6"
          : "#176d8d"
        : dark
          ? "#87c7b0"
          : "#247054";
    const text = dark ? "#e7e9eb" : "#26343d";
    const secondary = dark ? "#b6bfc5" : "#52616a";
    const border = dark ? "#454c51" : "#dbe0e3";
    const series: echarts.SeriesOption[] = [
      {
        name: mode === "anomaly" ? "Monthly Anomaly" : "Raw Observation",
        type: "line",
        data: values,
        connectNulls: false,
        smooth: false,
        showSymbol: dates.length <= 24,
        symbolSize: 6,
        lineStyle: { width: 1.7, color: accent },
        itemStyle: { color: accent },
      },
    ];
    if (guide.length)
      series.push({
        name: "Sen slope guide (not observations)",
        type: "line",
        data: guide,
        showSymbol: false,
        lineStyle: { width: 1.5, type: "dashed", color: secondary },
        itemStyle: { color: secondary },
      });
    chart.setOption(
      {
        backgroundColor: "transparent",
        animationDuration: 250,
        grid: { top: 30, right: 12, bottom: compact ? 32 : 56, left: 50 },
        tooltip: {
          trigger: "axis",
          renderMode: "richText",
          confine: true,
          backgroundColor: dark ? "#30383e" : "#ffffff",
          borderColor: border,
          textStyle: { color: text, fontSize: 12 },
          valueFormatter: (value: unknown) =>
            typeof value === "number"
              ? `${value.toFixed(4)} ${result.metadata.unit}`
              : "Missing",
        },
        xAxis: {
          type: "category",
          data: dates,
          axisLine: { lineStyle: { color: border } },
          axisLabel: { color: secondary, fontSize: 11 },
        },
        yAxis: {
          type: "value",
          name:
            mode === "anomaly"
              ? `Anomaly (${result.metadata.unit})`
              : result.metadata.unit,
          nameTextStyle: { color: secondary, fontSize: 11 },
          splitLine: { lineStyle: { color: dark ? "#3b4247" : "#e7ebed" } },
          axisLabel: { color: secondary, fontSize: 11 },
        },
        dataZoom: compact
          ? []
          : [
              { type: "inside", start: 0, end: 100 },
              {
                type: "slider",
                height: 16,
                bottom: 8,
                borderColor: border,
                backgroundColor: "transparent",
                fillerColor: dark
                  ? "rgba(124,201,230,.16)"
                  : "rgba(23,109,141,.12)",
                textStyle: { color: secondary },
                dataBackground: {
                  lineStyle: { color: secondary },
                  areaStyle: { color: dark ? "#30383e" : "#edf1f3" },
                },
                selectedDataBackground: {
                  lineStyle: { color: accent },
                  areaStyle: { color: accent, opacity: 0.12 },
                },
              },
            ],
        series,
      },
      true,
    );
  }, [result, mode, compact, resolved]);
  return (
    <div className="trend-chart">
      <div className="chart-heading">
        <div>
          <h3>Monthly {result.metadata.variable}</h3>
          <p className="quiet">
            {result.metadata.date_range.start} —{" "}
            {result.metadata.date_range.end}
          </p>
        </div>
        <SegmentedControl
          label="Chart values"
          value={mode}
          onChange={(value) => setMode(value as "anomaly" | "raw")}
          size="sm"
        >
          <SegmentedControlItem value="anomaly" label="Anomaly" />
          <SegmentedControlItem value="raw" label="Raw values" />
        </SegmentedControl>
      </div>
      <div
        ref={chartRef}
        role="img"
        aria-label={`Monthly ${result.metadata.variable} ${mode === "raw" ? "observations" : "anomalies"}, ${result.metadata.date_range.start} to ${result.metadata.date_range.end}. Missing months are gaps.`}
        className={compact ? "chart-canvas compact" : "chart-canvas"}
      />
      <p className="chart-note">
        Gaps mark missing months.
        {mode === "anomaly" && " Dashed: descriptive Sen slope."}
      </p>
    </div>
  );
}

import { useEffect, useMemo, useRef, useState } from "react";
import Globe, { type GlobeMethods } from "react-globe.gl";
import type { TrendIndexItem } from "../types/trend";

interface GlobePanelProps {
  items: TrendIndexItem[];
  selectedRegion: string;
  onSelectRegion: (region: string) => void;
}

interface RegionPin {
  region: string;
  name: string;
  lat: number;
  lon: number;
  significant: boolean;
}

const EARTH_DAY_TEXTURE = "https://unpkg.com/three-globe/example/img/earth-day.jpg";

// Map lon [24.5..35.5], lat [22..32.5] (Egypt & Nile Delta) into SVG 360x260
function projectEgypt(lat: number, lon: number) {
  const x = ((lon - 24.5) / (35.5 - 24.5)) * 360;
  const y = ((32.5 - lat) / (32.5 - 22.0)) * 260;
  return { x, y };
}

function toSvgPath(coords: [number, number][], close = false): string {
  const pts = coords.map(([lat, lon]) => {
    const { x, y } = projectEgypt(lat, lon);
    return `${x.toFixed(1)},${y.toFixed(1)}`;
  });
  return `M ${pts.join(" L ")}${close ? " Z" : ""}`;
}

const EGYPT_COAST: [number, number][] = [
  [22.0, 25.0],
  [31.5, 25.1],
  [31.3, 27.2],
  [30.9, 28.9],
  [31.2, 29.9],
  [31.55, 31.1],
  [31.25, 32.3],
  [31.1, 33.8],
  [31.3, 34.2],
  [29.5, 34.9],
  [27.8, 34.3],
  [29.95, 32.55],
  [27.2, 33.85],
  [24.5, 35.2],
  [22.0, 36.8],
];

const NILE_RIVER: [number, number][] = [
  [22.0, 31.3],
  [24.1, 32.9],
  [25.7, 32.6],
  [27.2, 31.2],
  [28.1, 30.75],
  [29.1, 31.1],
  [30.05, 31.23],
  [30.2, 31.15],
];

const NILE_DELTA_FAN: [number, number][] = [
  [30.15, 31.15],
  [31.2, 30.0],
  [31.55, 31.1],
  [31.25, 32.25],
];

export function GlobePanel({ items, selectedRegion, onSelectRegion }: GlobePanelProps) {
  const [mode, setMode] = useState<"map" | "globe">("map");
  const containerRef = useRef<HTMLDivElement>(null);
  const globeRef = useRef<GlobeMethods | undefined>(undefined);
  const [size, setSize] = useState({ width: 380, height: 280 });

  const pins = useMemo<RegionPin[]>(() => {
    const byRegion = new Map<string, RegionPin>();
    for (const item of items) {
      const existing = byRegion.get(item.region);
      if (!existing) {
        byRegion.set(item.region, {
          region: item.region,
          name: item.region_name,
          lat: item.lat,
          lon: item.lon,
          significant: item.significant,
        });
      } else if (item.significant) {
        existing.significant = true;
      }
    }
    return Array.from(byRegion.values());
  }, [items]);

  const activePin = pins.find((p) => p.region === selectedRegion) ?? pins[0];

  useEffect(() => {
    if (mode !== "globe") return;
    const el = containerRef.current;
    if (!el) return;
    const obs = new ResizeObserver((entries) => {
      const rect = entries[0]?.contentRect;
      if (rect && rect.width > 0) {
        setSize({ width: Math.floor(rect.width), height: Math.max(260, Math.floor(rect.height)) });
      }
    });
    obs.observe(el);
    return () => obs.disconnect();
  }, [mode]);

  useEffect(() => {
    if (mode !== "globe" || !globeRef.current || !activePin) return;
    globeRef.current.pointOfView({ lat: activePin.lat, lng: activePin.lon, altitude: 1.85 }, 900);
  }, [mode, activePin]);

  return (
    <div className="rounded-xl border border-slate-200 bg-white overflow-hidden flex flex-col">
      <div className="px-4 py-3 border-b border-slate-100 flex items-center justify-between gap-2">
        <div>
          <h2 className="text-sm font-semibold text-slate-900">Study Region Locator</h2>
          <p className="text-xs text-slate-500">
            {activePin ? `${activePin.name} (${activePin.lat.toFixed(2)}°N, ${activePin.lon.toFixed(2)}°E)` : "Select a region"}
          </p>
        </div>

        <div className="inline-flex rounded-lg border border-slate-200 bg-slate-50 p-0.5">
          <button
            type="button"
            onClick={() => setMode("map")}
            className={`tactile-btn px-2.5 py-1 text-[11px] font-medium rounded-md ${
              mode === "map" ? "bg-white text-slate-900 shadow-xs" : "text-slate-600"
            }`}
          >
            Map
          </button>
          <button
            type="button"
            onClick={() => setMode("globe")}
            className={`tactile-btn px-2.5 py-1 text-[11px] font-medium rounded-md ${
              mode === "globe" ? "bg-white text-slate-900 shadow-xs" : "text-slate-600"
            }`}
          >
            3D Globe
          </button>
        </div>
      </div>

      {mode === "map" ? (
        <div className="relative bg-[#F0F7FF] p-2">
          <svg viewBox="0 0 360 260" className="w-full h-[260px] rounded-lg border border-slate-200/80 bg-[#E0F2FE]">
            {/* Lat/Lon Graticule */}
            {[24, 26, 28, 30, 32].map((lat) => {
              const { y } = projectEgypt(lat, 25);
              return (
                <g key={`lat-${lat}`}>
                  <line x1={0} y1={y} x2={360} y2={y} stroke="#BAE6FD" strokeWidth={0.8} strokeDasharray="3 3" />
                  <text x={6} y={y - 3} fontSize={8} fill="#64748B" fontFamily="monospace">
                    {lat}°N
                  </text>
                </g>
              );
            })}
            {[26, 28, 30, 32, 34].map((lon) => {
              const { x } = projectEgypt(22, lon);
              return (
                <g key={`lon-${lon}`}>
                  <line x1={x} y1={0} x2={x} y2={260} stroke="#BAE6FD" strokeWidth={0.8} strokeDasharray="3 3" />
                  <text x={x + 3} y={253} fontSize={8} fill="#64748B" fontFamily="monospace">
                    {lon}°E
                  </text>
                </g>
              );
            })}

            {/* Geographically projected Egypt landmass, Nile River & Delta */}
            <path
              d={toSvgPath(EGYPT_COAST, true)}
              fill="#F8FAFC"
              stroke="#CBD5E1"
              strokeWidth={1.2}
            />
            <path
              d={toSvgPath(NILE_DELTA_FAN, true)}
              fill="#BBF7D0"
              fillOpacity={0.7}
              stroke="#10B981"
              strokeWidth={1}
            />
            <path
              d={toSvgPath(NILE_RIVER)}
              fill="none"
              stroke="#38BDF8"
              strokeWidth={2}
              strokeLinecap="round"
            />

            {/* Region Pins */}
            {pins.map((pin) => {
              const { x, y } = projectEgypt(pin.lat, pin.lon);
              const isSelected = pin.region === selectedRegion;
              const isLeft = pin.region === "nile_delta";
              const labelWidth = pin.name.length * 6.5 + 12;
              const rectX = isLeft ? x - labelWidth - 10 : x + 10;
              const rectY = isLeft ? y - 16 : y - 4;
              return (
                <g
                  key={pin.region}
                  onClick={() => onSelectRegion(pin.region)}
                  className="cursor-pointer"
                >
                  {isSelected && (
                    <circle cx={x} cy={y} r={14} fill="#0284C7" fillOpacity={0.18} />
                  )}
                  <circle
                    cx={x}
                    cy={y}
                    r={isSelected ? 6.5 : 5}
                    fill={isSelected ? "#0284C7" : "#059669"}
                    stroke="#FFFFFF"
                    strokeWidth={2}
                  />
                  <rect
                    x={rectX}
                    y={rectY}
                    width={labelWidth}
                    height={18}
                    rx={4}
                    fill="#FFFFFF"
                    stroke={isSelected ? "#0284C7" : "#CBD5E1"}
                    strokeWidth={1}
                  />
                  <text
                    x={rectX + 6}
                    y={rectY + 12}
                    fontSize={10}
                    fontWeight={600}
                    fill="#0F172A"
                  >
                    {pin.name}
                  </text>
                </g>
              );
            })}
          </svg>
        </div>
      ) : (
        <div ref={containerRef} className="relative h-[280px] w-full bg-[#E0F2FE] flex items-center justify-center">
          <Globe
            ref={globeRef}
            width={size.width}
            height={size.height}
            backgroundColor="#E0F2FE"
            globeImageUrl={EARTH_DAY_TEXTURE}
            atmosphereColor="#0284c7"
            atmosphereAltitude={0.14}
            pointsData={pins}
            pointLat="lat"
            pointLng="lon"
            pointColor={(d) => ((d as RegionPin).region === selectedRegion ? "#0284c7" : "#059669")}
            pointRadius={(d) => ((d as RegionPin).region === selectedRegion ? 0.85 : 0.55)}
            pointAltitude={0.04}
            ringsData={activePin ? [activePin] : []}
            ringLat="lat"
            ringLng="lon"
            ringColor={() => "#0284c7"}
            ringMaxRadius={3.5}
            ringPropagationSpeed={2}
            ringRepeatPeriod={1200}
            onGlobeReady={() => {
              if (!globeRef.current) return;
              const controls = globeRef.current.controls();
              controls.minDistance = 130;
              controls.maxDistance = 380;
              if (activePin) {
                globeRef.current.pointOfView({ lat: activePin.lat, lng: activePin.lon, altitude: 1.55 }, 0);
              }
            }}
            htmlElementsData={pins}
            htmlLat="lat"
            htmlLng="lon"
            htmlAltitude={0.05}
            htmlElement={(d) => {
              const p = d as RegionPin;
              const isSelected = p.region === selectedRegion;
              const isLeft = p.region === "nile_delta";
              const wrap = document.createElement("div");
              wrap.style.pointerEvents = "none";

              const btn = document.createElement("button");
              btn.type = "button";
              btn.textContent = p.name;
              btn.style.cssText = [
                "padding: 3px 8px",
                "border-radius: 9999px",
                "font-size: 11px",
                "font-weight: 600",
                "white-space: nowrap",
                "cursor: pointer",
                "pointer-events: auto",
                `transform: translate(${isLeft ? "-115%" : "18%"}, ${isLeft ? "-115%" : "18%"})`,
                `background: ${isSelected ? "#0284c7" : "#ffffff"}`,
                `color: ${isSelected ? "#ffffff" : "#0f172a"}`,
                `border: 1px solid ${isSelected ? "#0369a1" : "#cbd5e1"}`,
                "box-shadow: 0 2px 6px rgba(15,23,42,0.18)",
              ].join(";");
              btn.onclick = () => onSelectRegion(p.region);
              wrap.appendChild(btn);
              return wrap;
            }}
            onPointClick={(d) => onSelectRegion((d as RegionPin).region)}
          />
        </div>
      )}
    </div>
  );
}

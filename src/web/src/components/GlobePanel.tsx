import { useEffect, useMemo, useRef, useState } from "react";
import Globe, { type GlobeMethods } from "react-globe.gl";
import * as THREE from "three";
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

const EARTH_DAY_TEXTURE = "https://unpkg.com/three-globe/example/img/earth-blue-marble.jpg";

// Map lon [24..36], lat [22..33] (Egypt & Nile Delta) into SVG 360x260
function projectEgypt(lat: number, lon: number) {
  const x = ((lon - 24.5) / (35.5 - 24.5)) * 360;
  const y = ((32.5 - lat) / (32.5 - 22.0)) * 260;
  return { x, y };
}

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
    globeRef.current.pointOfView({ lat: activePin.lat, lng: activePin.lon, altitude: 1.5 }, 900);
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

            {/* Simplified Egypt landmass & Nile */}
            <path
              d="M 16 260 L 16 55 L 70 46 L 145 48 L 210 34 L 255 44 L 285 68 L 315 115 L 348 195 L 348 260 Z"
              fill="#F8FAFC"
              stroke="#CBD5E1"
              strokeWidth={1.2}
            />
            {/* Nile River & Delta */}
            <path
              d="M 238 260 Q 228 195 215 135 Q 214 95 212 62 M 212 62 L 185 38 M 212 62 L 242 40"
              fill="none"
              stroke="#38BDF8"
              strokeWidth={2}
              strokeLinecap="round"
            />
            {/* Nile Delta agricultural fan */}
            <path
              d="M 212 64 L 184 42 Q 212 33 242 42 Z"
              fill="#BBF7D0"
              fillOpacity={0.65}
              stroke="#10B981"
              strokeWidth={1}
            />

            {/* Region Pins */}
            {pins.map((pin) => {
              const { x, y } = projectEgypt(pin.lat, pin.lon);
              const isSelected = pin.region === selectedRegion;
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
                    x={x + 9}
                    y={y - 10}
                    width={pin.name.length * 6.5 + 12}
                    height={18}
                    rx={4}
                    fill="#FFFFFF"
                    stroke={isSelected ? "#0284C7" : "#CBD5E1"}
                    strokeWidth={1}
                  />
                  <text
                    x={x + 15}
                    y={y + 2}
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
            globeMaterial={new THREE.MeshPhongMaterial({ color: "#93c5fd" })}
            globeImageUrl={EARTH_DAY_TEXTURE}
            atmosphereColor="#0284c7"
            atmosphereAltitude={0.14}
            pointsData={pins}
            pointLat="lat"
            pointLng="lon"
            pointColor={(d) => ((d as RegionPin).region === selectedRegion ? "#0284c7" : "#059669")}
            pointRadius={(d) => ((d as RegionPin).region === selectedRegion ? 0.9 : 0.6)}
            pointAltitude={0.04}
            onGlobeReady={() => {
              if (globeRef.current && activePin) {
                globeRef.current.pointOfView({ lat: activePin.lat, lng: activePin.lon, altitude: 1.5 }, 0);
              }
            }}
            onPointClick={(d) => onSelectRegion((d as RegionPin).region)}
          />
        </div>
      )}
    </div>
  );
}

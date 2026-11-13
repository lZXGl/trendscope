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
  lng: number;
  significant: boolean;
}

const EARTH_DAY_TEXTURE = "https://unpkg.com/three-globe/example/img/earth-blue-marble.jpg";
const EARTH_TOPOLOGY = "https://unpkg.com/three-globe/example/img/earth-topology.png";

export function GlobePanel({ items, selectedRegion, onSelectRegion }: GlobePanelProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const globeRef = useRef<GlobeMethods | undefined>(undefined);
  const [size, setSize] = useState({ width: 380, height: 340 });

  const pins = useMemo<RegionPin[]>(() => {
    const byRegion = new Map<string, RegionPin>();
    for (const item of items) {
      const existing = byRegion.get(item.region);
      if (!existing) {
        byRegion.set(item.region, {
          region: item.region,
          name: item.region_name,
          lat: item.lat,
          lng: item.lon,
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
    const el = containerRef.current;
    if (!el) return;
    const obs = new ResizeObserver((entries) => {
      const rect = entries[0]?.contentRect;
      if (rect && rect.width > 0) {
        setSize({ width: Math.floor(rect.width), height: Math.max(280, Math.floor(rect.height)) });
      }
    });
    obs.observe(el);
    return () => obs.disconnect();
  }, []);

  useEffect(() => {
    if (!globeRef.current || !activePin) return;
    globeRef.current.pointOfView({ lat: activePin.lat, lng: activePin.lng, altitude: 1.55 }, 900);
  }, [activePin]);

  return (
    <div className="rounded-xl border border-slate-200 bg-white overflow-hidden flex flex-col">
      <div className="px-4 py-3 border-b border-slate-100 flex items-center justify-between">
        <div>
          <h2 className="text-sm font-semibold text-slate-900">Study Region Locator</h2>
          <p className="text-xs text-slate-500">Click a pin to inspect satellite trends</p>
        </div>
        {activePin && (
          <span className="text-xs font-mono tabular-nums px-2 py-1 rounded-md bg-slate-100 text-slate-700">
            {activePin.lat.toFixed(2)}°N, {activePin.lng.toFixed(2)}°E
          </span>
        )}
      </div>

      <div ref={containerRef} className="relative h-[320px] w-full bg-[#F1F5F9]">
        <Globe
          ref={globeRef}
          width={size.width}
          height={size.height}
          backgroundColor="rgba(241, 245, 249, 1)"
          globeImageUrl={EARTH_DAY_TEXTURE}
          bumpImageUrl={EARTH_TOPOLOGY}
          atmosphereColor="#0ea5e9"
          atmosphereAltitude={0.14}
          pointsData={pins}
          pointLat="lat"
          pointLng="lng"
          pointColor={(d) => {
            const p = d as RegionPin;
            if (p.region === selectedRegion) return "#0284c7";
            return p.significant ? "#059669" : "#64748b";
          }}
          pointRadius={(d) => ((d as RegionPin).region === selectedRegion ? 0.65 : 0.42)}
          pointAltitude={0.03}
          pointLabel={(d) => {
            const p = d as RegionPin;
            return `<div style="padding:4px 8px;background:#fff;color:#0f172a;border:1px solid #cbd5e1;border-radius:6px;font-size:12px;font-weight:600;">${p.name}</div>`;
          }}
          onPointClick={(d) => onSelectRegion((d as RegionPin).region)}
        />
      </div>
    </div>
  );
}

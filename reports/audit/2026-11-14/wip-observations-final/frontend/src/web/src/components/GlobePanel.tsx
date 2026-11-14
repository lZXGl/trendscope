import {
  Component,
  useEffect,
  useMemo,
  useRef,
  useState,
  type ReactNode,
} from "react";
import Globe, { type GlobeMethods } from "react-globe.gl";
import { Button } from "@astryxdesign/core/Button";
import {
  SegmentedControl,
  SegmentedControlItem,
} from "@astryxdesign/core/SegmentedControl";
import type { AoiSelection } from "../types/trend";
import { useAppearance } from "../lib/appearance";
import { WorldMap } from "./WorldMap";

class GlobeBoundary extends Component<
  { children: ReactNode; fallback: ReactNode },
  { failed: boolean }
> {
  state = { failed: false };
  static getDerivedStateFromError() {
    return { failed: true };
  }
  render() {
    return this.state.failed ? this.props.fallback : this.props.children;
  }
}

export function GlobePanel({
  area,
  onSelect,
}: {
  area: AoiSelection | null;
  onSelect: (lat: number, lon: number) => void;
}) {
  const [mode, setMode] = useState("globe");
  const [ready, setReady] = useState(false);
  const container = useRef<HTMLDivElement>(null);
  const globe = useRef<GlobeMethods | undefined>(undefined);
  const [size, setSize] = useState({ width: 600, height: 440 });
  const { resolved } = useAppearance();
  const color = resolved === "dark" ? "#7edbe2" : "#087c87";
  useEffect(() => {
    if (mode !== "globe" || !container.current) return;
    const observer = new ResizeObserver(([entry]) => {
      if (entry.contentRect.width > 0)
        setSize({
          width: Math.floor(entry.contentRect.width),
          height: Math.floor(entry.contentRect.height),
        });
    });
    observer.observe(container.current);
    return () => observer.disconnect();
  }, [mode]);
  useEffect(() => {
    if (!ready || !globe.current) return;
    globe.current.pointOfView(
      area
        ? { lat: area.lat, lng: area.lon, altitude: 0.24 }
        : { lat: 15, lng: 0, altitude: 2.3 },
      650,
    );
  }, [ready, area?.lat, area?.lon]);
  const polygons = useMemo(() => {
    if (!area) return [];
    const [w, s, e, n] = area.bbox;
    return [
      {
        geometry: {
          type: "Polygon",
          coordinates: [
            [
              [w, s],
              [e, s],
              [e, n],
              [w, n],
              [w, s],
            ],
          ],
        },
      },
    ];
  }, [area]);
  return (
    <section className="geography" aria-label="Geographic selection">
      <div className="panel-heading">
        <h1>Choose an area</h1>
        <SegmentedControl
          label="Geographic view"
          value={mode}
          onChange={(value) => {
            setReady(false);
            setMode(value);
          }}
          size="sm"
        >
          <SegmentedControlItem value="globe" label="Globe" />
          <SegmentedControlItem value="map" label="Map" />
        </SegmentedControl>
      </div>
      {mode === "map" ? (
        <WorldMap area={area} onSelect={onSelect} />
      ) : (
        <div
          ref={container}
          className="globe-viewport"
          data-globe-ready={ready}
        >
          <GlobeBoundary
            fallback={
              <div className="visualization-fallback">
                <p>3D is unavailable on this device.</p>
                <Button label="Use world map" onClick={() => setMode("map")} />
              </div>
            }
          >
            {!ready && (
              <span role="status" className="globe-status">
                Loading globe…
              </span>
            )}
            <Globe
              ref={globe}
              width={size.width}
              height={size.height}
              backgroundColor={resolved === "dark" ? "#202a30" : "#edf3f3"}
              globeImageUrl="https://unpkg.com/three-globe/example/img/earth-day.jpg"
              showAtmosphere={false}
              pointsData={area ? [area] : []}
              pointLat="lat"
              pointLng="lon"
              pointAltitude={0.002}
              pointColor={() => color}
              pointRadius={0.08}
              polygonsData={polygons}
              polygonGeoJsonGeometry="geometry"
              polygonCapColor={() =>
                resolved === "dark"
                  ? "rgba(126,219,226,.28)"
                  : "rgba(8,124,135,.3)"
              }
              polygonSideColor={() => color}
              polygonStrokeColor={() => color}
              polygonAltitude={0.001}
              onGlobeClick={({ lat, lng }) => onSelect(lat, lng)}
              onPolygonClick={(_polygon, _event, coordinates) =>
                onSelect(coordinates.lat, coordinates.lng)
              }
              onPointClick={(point) => {
                const p = point as AoiSelection;
                onSelect(p.lat, p.lon);
              }}
              onGlobeReady={() => {
                setReady(true);
                if (!globe.current) return;
                const controls = globe.current.controls();
                controls.minDistance = 101;
                controls.maxDistance = 500;
                globe.current.pointOfView(
                  area
                    ? { lat: area.lat, lng: area.lon, altitude: 0.24 }
                    : { lat: 15, lng: 0, altitude: 2.3 },
                  0,
                );
              }}
            />
          </GlobeBoundary>
        </div>
      )}
      <div className="map-caption">
        <span>
          {area
            ? "Rectangle = selected analysis boundary"
            : "Click the globe or map to begin"}
        </span>
        <span>WGS84</span>
      </div>
    </section>
  );
}

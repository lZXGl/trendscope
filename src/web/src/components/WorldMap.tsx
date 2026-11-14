import {
  geoEquirectangular,
  geoGraticule,
  geoGraticule10,
  geoPath,
} from "d3-geo";
import { useMemo, useRef, useState } from "react";
import { Button } from "@astryxdesign/core/Button";
import land from "../data/world-land.json";
import type { GeoPermissibleObjects } from "d3-geo";
import type { AoiSelection } from "../types/trend";

export function WorldMap({
  area,
  onSelect,
}: {
  area: AoiSelection | null;
  onSelect: (lat: number, lon: number) => void;
}) {
  const ref = useRef<SVGSVGElement>(null);
  const [close, setClose] = useState(false);
  const projection = useMemo(
    () =>
      geoEquirectangular()
        .translate([360, 180])
        .center(close && area ? [area.lon, area.lat] : [0, 0])
        .scale(
          close && area
            ? 720 /
                ((Math.max(
                  area.bbox[2] - area.bbox[0],
                  area.bbox[3] - area.bbox[1],
                ) *
                  6 *
                  Math.PI) /
                  180)
            : 720 / (2 * Math.PI),
        ),
    [close, area],
  );
  const grid = useMemo(() => {
    if (!close || !area) return geoGraticule10();
    const step = Math.max(
      area.bbox[2] - area.bbox[0],
      area.bbox[3] - area.bbox[1],
    );
    return geoGraticule()
      .extent([
        [
          Math.max(-180, area.lon - step * 4),
          Math.max(-90, area.lat - step * 4),
        ],
        [Math.min(180, area.lon + step * 4), Math.min(90, area.lat + step * 4)],
      ])
      .step([step, step])();
  }, [close, area]);
  const path = geoPath(projection);
  const marker = area ? projection([area.lon, area.lat]) : null;
  const westNorth = area ? projection([area.bbox[0], area.bbox[3]]) : null;
  const eastSouth = area ? projection([area.bbox[2], area.bbox[1]]) : null;
  return (
    <div className="world-map">
      <svg
        ref={ref}
        viewBox="0 0 720 360"
        role="img"
        aria-label="World map. Click a location or use the coordinate fields below."
        onClick={(event) => {
          const svg = ref.current;
          const matrix = svg?.getScreenCTM();
          if (!svg || !matrix) return;
          const point = new DOMPoint(
            event.clientX,
            event.clientY,
          ).matrixTransform(matrix.inverse());
          const location = projection.invert?.([point.x, point.y]);
          if (
            location &&
            Math.abs(location[1]) <= 90 &&
            Math.abs(location[0]) <= 180
          )
            onSelect(location[1], location[0]);
        }}
      >
        <rect width="720" height="360" className="map-water" />
        <path
          d={path(land as GeoPermissibleObjects) ?? ""}
          className="map-land"
        />
        <path d={path(grid) ?? ""} className="map-grid" />
        {area && marker && westNorth && eastSouth && (
          <g data-testid="map-selection" data-bbox={area.bbox.join(",")}>
            <rect
              x={westNorth[0]}
              y={westNorth[1]}
              width={eastSouth[0] - westNorth[0]}
              height={eastSouth[1] - westNorth[1]}
              className="aoi-boundary"
            />
            <circle
              cx={marker[0]}
              cy={marker[1]}
              r="4"
              className="aoi-marker"
            />
          </g>
        )}
      </svg>
      <div className="map-tools">
        <Button
          label={close ? "World view" : "Zoom to area"}
          size="sm"
          onClick={() => setClose(!close)}
          isDisabled={!area}
        />
        <a
          href="https://www.naturalearthdata.com/"
          target="_blank"
          rel="noreferrer"
        >
          Natural Earth
        </a>
      </div>
    </div>
  );
}

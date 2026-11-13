export interface TrendIndexItem {
  region: string;
  region_name: string;
  lat: number;
  lon: number;
  variable: string;
  variable_name: string;
  variable_description: string;
  unit: string;
  source: string;
  file: string;
  significant: boolean;
  headline: string;
}

export interface SeriesPoint {
  date: string;
  raw: number | null;
  anomaly: number | null;
}

export interface TrendResult {
  metadata: {
    region: string;
    lat: number;
    lon: number;
    variable: string;
    unit: string;
    source: string;
    is_mock?: boolean;
    date_range: {
      start: string;
      end: string;
    };
  };
  series: SeriesPoint[];
  trend: {
    method: string;
    sens_slope: number;
    slope_unit: string;
    p_value: number;
    tau: number;
    significant: boolean;
    autocorrected: boolean;
  };
  verdict: {
    headline: string;
    summary: string;
    caveats: string[];
  };
}

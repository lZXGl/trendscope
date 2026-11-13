export interface TrendIndexItem {
  region: string;
  region_name: string;
  is_random?: boolean;
  lat: number;
  lon: number;
  bbox?: [number, number, number, number];
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

export interface AoiSelection {
  lat: number;
  lon: number;
  bbox: [number, number, number, number];
  label: string;
  isRandom: boolean;
}

export interface AoiJobStatus {
  job_id: string;
  status: "queued" | "processing" | "completed" | "failed";
  stage: null | "checking_area" | "waiting_for_nasa" | "analysing";
  request: {
    bbox: [number, number, number, number];
    product: string;
    start_date: string;
    end_date: string;
    allow_marginal: boolean;
    min_pixel_presence: number;
    processing_version: string;
  };
  nasa_task_id: string | null;
  error: string | null;
  retryable: boolean;
  result_file: string | null;
  created_at: string;
  updated_at: string;
}

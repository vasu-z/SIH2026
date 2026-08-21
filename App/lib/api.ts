import Constants from 'expo-constants';

declare const process: { env?: Record<string, string | undefined> };

const expoConfig = Constants.expoConfig as ({ hostUri?: string } | null);
const manifestHost = expoConfig?.hostUri?.split(':')[0];

export const API_BASE_URL =
  process.env?.EXPO_PUBLIC_API_URL ||
  (manifestHost ? `http://${manifestHost}:8000/api` : 'http://127.0.0.1:8000/api');

export type WaterQualityData = {
  id: number;
  station_id: string;
  lat: number;
  lon: number;
  date: string;
  water_level_m: number;
  temperature_c: number | null;
  rainfall_mm: number | null;
  ph: string | null;
  dissolved_oxygen_mg_l: number | null;
  source?: string;
  source_agency?: string;
  is_live_source?: boolean;
  data_quality?: string;
};

export type StationSummary = {
  station_id: string;
  lat: number;
  lon: number;
  record_count: number;
  latest_level: number;
  latest_date: string;
  avg_level: number;
  min_level: number;
  max_level: number;
  trend_7d: number;
};

export type SystemOverview = {
  data_mode: string;
  database: {
    total_records: number;
    live_records: number;
    synthetic_records: number;
    station_count: number;
    date_range: { start: string; end: string };
  };
};

export type PrototypeShowcase = {
  status: string;
  sources: {
    mode: string;
    total_records: number;
    live_records: number;
    synthetic_records: number;
  };
  public_data: {
    record_count: number;
    station_count: number;
    avg_depth_m: number;
    date_range: { start: string | null; end: string | null };
    latest_records: Array<{
      station_id: string;
      lat: number;
      lon: number;
      date: string;
      water_level_m: number;
      data_quality: string;
    }>;
  };
  model_lab: {
    record_count: number;
    station_count: number;
    avg_depth_m: number;
    date_range: { start: string | null; end: string | null };
  };
  selected_station: string;
  models: {
    trust: { trust_score: number; classification: string; factors?: Record<string, number> };
    forecast: { model: string; status: string; p50: number[]; mae: number; rmse: number };
    trend: { trend_direction: string; sen_slope_m_per_year: number; kendall_tau: number };
    incidents: Array<{ incident_id: string; severity: string; station_count: number; confidence: number; explanation?: string }>;
    priority: Array<{ rank: number; region_id: string; region_name: string; priority_score: number; classification: string; evidence_confidence: number }>;
    monitoring: Array<{ rank: number; location_id: string; priority_score: number; estimated_cost: number }>;
    scenario: { engine: string; status: string; difference: { groundwater_change: number; risk_change: number } };
    optimizer: { engine: string; status: string; budget_used: number; selected_interventions: Array<{ id: string; type: string; cost: number; expected_risk_reduction: number }> };
  };
  explainability: string[];
};

export type LiveSources = {
  mode: string;
  total_records: number;
  live_records: number;
  synthetic_records: number;
  latest_live_record?: string | null;
  available_sources?: Array<{ name: string; status: string; endpoint?: string }>;
};

export type DataExplorerResponse = {
  status: string;
  database: string;
  total_records: number;
  matching_records: number;
  page: number;
  page_size: number;
  total_pages: number;
  records: WaterQualityData[];
  all_stations: string[];
};

export type MlRegistry = {
  status: string;
  external_repository: {
    name: string;
    repo_url: string;
    available: boolean;
    notebook: string | null;
    data_file_count: number;
    role: string;
    production_policy: string;
  };
  models: Array<{
    id: string;
    name: string;
    family: string;
    role: string;
    input: string;
    endpoint: string;
    availability: string;
  }>;
};

export type MlRunResponse = {
  status: string;
  requested_model: string;
  selected_station: string;
  horizon: number;
  result: {
    status: string;
    model?: string;
    best_model?: string;
    input_data?: {
      records_used?: number;
      usable_training_rows?: number;
      source?: string;
      live_rows?: number;
      date_range?: { start?: string | null; end?: string | null };
      features?: string[];
    };
    leaderboard?: Array<{ model: string; mae?: number; rmse?: number; r2?: number; status?: string }>;
    ensemble_members?: Array<{ model: string; weight: number }>;
    risk?: {
      label: string;
      max_predicted_depth_m: number;
      change_over_horizon_m: number;
    };
    forecast?: number[];
    p50?: number[];
    trust_score?: number;
    classification?: string;
    fallback_applied?: boolean;
    reason?: string;
  };
};

export type MlBriefing = {
  status: string;
  station_id: string;
  briefing: string;
  ai_result: MlRunResponse['result'];
  sources: LiveSources;
};

export type UnifiedDecision = {
  pipeline: string;
  status: string;
  latency_seconds: number;
  executive_summary: string;
  decision_flow: Record<string, unknown>;
};

export async function apiGet<T>(path: string): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`);
  if (!response.ok) {
    throw new Error(`API ${response.status}: ${await response.text()}`);
  }
  return response.json();
}

export async function apiPost<T>(path: string, body: Record<string, unknown> = {}): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
  if (!response.ok) {
    throw new Error(`API ${response.status}: ${await response.text()}`);
  }
  return response.json();
}

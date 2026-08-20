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

export async function apiGet<T>(path: string): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`);
  if (!response.ok) {
    throw new Error(`API ${response.status}: ${await response.text()}`);
  }
  return response.json();
}

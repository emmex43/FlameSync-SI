export interface Investigation {
  id: string;
  name: string;
  project: string;
  safety_domain: string;
  fuel_type: string;
  oxygen_pct: number | null;
  max_flow_velocity_cm_s: number | null;
  pressure_bar: number | null;
  source_file: string;
  source_row: number;
  raw_data: Record<string, string>;
}

export const MAX_COMPARISON_ITEMS = 4;

export interface PredictionPayload {
  fuel_type: string;
  oxygen_concentration: number;
  chamber_pressure_bar: number;
  mass_flow_rate_mg_s: number;
}

export interface PredictionResponse {
  predicted_burn_time_sec: number;
  feature_importance: Record<string, number>;
}

export interface NumericRange {
  minimum: number;
  maximum: number;
}

export interface BurnTimeValidation {
  validation_method: string;
  samples: number;
  held_out_days: number;
  mae_sec: number;
  rmse_sec: number;
  r2: number;
  mean_baseline_mae_sec: number;
  within_10_sec_fraction: number;
  within_20_sec_fraction: number;
  target_range_sec: NumericRange;
  input_ranges: Record<string, NumericRange>;
}

export interface RankingPayload {
  mission_scenario: string;
  constraints: string;
}

export interface RankedItem {
  investigation_id: string;
  investigation: Investigation;
  relevance_score: number;
  reasoning: string;
}

export interface RankingResponse {
  mission_scenario: string;
  rankings: RankedItem[];
}
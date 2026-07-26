export interface ProcessInput {
  current_grade: string
  target_grade: string
  machine_speed: number
  steam_pressure: number
  dryer_temperature: number
  moisture: number
  basis_weight: number
  caliper: number
  pulp_consistency: number
  stock_flow: number
  refining_energy: number
  headbox_pressure: number
  reel_tension: number
  ambient_temperature: number
  humidity: number
}

export interface FeatureContribution {
  feature: string
  value: string | number
  contribution: number
  importance: number
  direction: string
}

export interface Prediction {
  prediction_id: string
  quality_score: number
  off_spec_probability: number
  expected_stabilization_time: number
  model_version: string
  explanation: {
    summary: string
    top_contributing_features: FeatureContribution[]
    feature_importance: Record<string, number>
  }
  created_at: string
}

export interface Recommendation {
  text: string
  confidence: number
  expected_improvement: number
  affected_variables: string[]
  inference_sources: string[]
}

export interface RecommendationResponse {
  recommendation_id: string
  prediction: Prediction
  recommendations: Recommendation[]
  created_at: string
}

export interface CorrelationPair {
  first_variable: string
  second_variable: string
  correlation: number
}

export interface Correlations {
  record_count: number
  correlation_matrix: Record<string, Record<string, number>>
  strongest_positive_correlations: CorrelationPair[]
  strongest_negative_correlations: CorrelationPair[]
}

export interface DiscoveredRelationship {
  relationship_type: 'lag' | 'nonlinear' | 'interaction'
  variable: string
  interacts_with?: string
  strength: number
  best_lag?: number
  lag_correlation?: number
  rolling_correlation?: number
  grade_pair: string | null
  stage: 'early' | 'middle' | 'late' | null
  transition_count: number
  impact_direction: 'Positive' | 'Negative'
  severity: 'High' | 'Medium' | 'Low'
  summary: string
}

export interface RelationshipDiscovery {
  relationships: DiscoveredRelationship[]
  method: string
  max_lag: number
  record_count: number
}

export interface DemoSeedResult {
  predictions: number
  forecasts: number
  recommendations: number
  decisions: number
  outcomes: number
  audit_records: number
}

export interface DatasetStatistics {
  record_count: number
  generated_at: string
  columns: string[]
  missing_values: Record<string, number>
  numeric_summary: Record<string, Record<string, number>>
  grade_distribution: Record<string, number>
}

export interface ModelInfo {
  model_type: string
  model_version: string
  trained_at: string
  training_records: number
  feature_count: number
  target_metrics: Record<string, number>
  dataset_checksum: string
  supported_outputs: string[]
  artifact_path: string
}

export interface Health {
  status: 'healthy'
  service: string
  version: string
  environment: string
}

export interface Pagination {
  page: number
  page_size: number
  total: number
  total_pages: number
}

export interface PredictionHistoryItem extends Omit<Prediction, 'model_version'> {
  model_version: string
  input_data: ProcessInput
}

export interface RecommendationHistoryItem {
  recommendation_id: string
  prediction_id: string
  recommendations: Recommendation[]
  created_at: string
}

export interface Paginated<T> {
  items: T[]
  pagination: Pagination
}

export interface Alert {
  id: string
  severity: 'info' | 'warning' | 'critical'
  title: string
  description: string
  timestamp: string
  affected_variables: string[]
  suggested_action: string
  acknowledged: boolean
  acknowledged_at?: string
  prediction_id?: string
}

export interface Drift {
  score: number
  severity: 'stable' | 'watch' | 'warning' | 'critical'
  drifting_variables: Record<string, number>
  prediction_drift: number
  recommended_action: string
  calculated_at: string
}

export interface RollingMetric {
  window: string
  average_quality: number
  average_off_spec_probability: number
  average_stabilization_time: number
  recommendation_frequency: number
  alert_frequency: number
  prediction_count: number
}

export interface StreamStatus {
  status: 'starting' | 'running' | 'stopped'
  session_id?: string
  started_at?: string
  sample_count: number
  connected_clients: number
  latest_sample_at?: string
}

export interface LiveMetrics {
  sensor: ProcessInput | null
  prediction: Prediction | null
  recommendations: Recommendation[]
  alerts: Alert[]
  drift: Drift | null
  updated_at: string | null
}

export interface Feedback {
  id: string
  prediction_id: string
  outcome: string
  notes?: string
  created_at: string
}

export interface TrajectoryPoint {
  step: number
  timestamp: string
  basis_weight: number
  lower_bound: number
  upper_bound: number
  deviation_pct: number
  lower_spec_limit: number
  upper_spec_limit: number
}

export interface Forecast {
  forecast_id: string
  transition_id: string
  model_version: string
  history_window: number
  forecast_horizon: number
  confidence: number
  trajectory: TrajectoryPoint[]
  specification: {
    target_basis_weight: number
    lower_spec_limit: number
    upper_spec_limit: number
    current_deviation_pct: number
    maximum_predicted_deviation_pct: number
    crossing_probability: number
    predicted_crossing_step: number | null
    predicted_crossing_time: string | null
    remaining_safe_operating_seconds: number | null
    predicted_stabilization_step: number | null
  }
  top_influencing_variables: [string, number][]
  explanation: string
  created_at: string
}

export interface ForecastSimulation {
  simulation_id: string
  forecast_id: string
  recommendation_id: string
  baseline_trajectory: TrajectoryPoint[]
  intervention_trajectory: TrajectoryPoint[]
  baseline_crossing_probability: number
  intervention_crossing_probability: number
  risk_reduction: number
  expected_deviation_reduction: number
  expected_stabilization_improvement: number
  crossing_delay_steps: number | null
  crossing_avoided: boolean
  confidence: number
  explanation: string
}

export type RecommendationState =
  | 'proposed'
  | 'accepted'
  | 'rejected'
  | 'modified'
  | 'delayed'
  | 'expired'
  | 'applied'
  | 'evaluated'

export interface ForecastRecommendation {
  recommendation_id: string
  forecast_id: string
  state: RecommendationState
  rank: number
  affected_variables: string[]
  current_values: Record<string, number>
  changes: { variable: string; value: number }[]
  baseline_trajectory: TrajectoryPoint[]
  intervention_trajectory: TrajectoryPoint[]
  metrics: {
    crossing_probability_before: number
    crossing_probability_after: number
    predicted_peak_deviation_before: number
    predicted_peak_deviation_after: number
    predicted_stabilization_time_before: number | null
    predicted_stabilization_time_after: number | null
    estimated_improvement: number
    crossing_avoided: boolean
    crossing_delay_steps: number | null
  }
  confidence: number
  constraint_validation: {
    feasible: boolean
    checks: string[]
    violations: string[]
    recipe_rules: string[]
  }
  explanation: {
    selection_reason: string
    forecast_causes: string[]
    trajectory_effect: string
    expected_risks: string[]
    remaining_uncertainty: string
    recipe_attribution: string[]
  }
  inference_sources: string[]
  historical_evidence: {
    similar_transition_count: number
    historical_acceptance_rate: number
    historical_effectiveness: number
  }
  created_at: string
  updated_at: string
  expires_at: string | null
}

export interface Effectiveness {
  evaluated_count: number
  crossing_avoidance_rate: number
  crossing_delay_rate: number
  mean_prediction_error: number
  mean_deviation_improvement: number
  mean_stabilization_improvement: number
}

export interface RecommendationOutcome {
  outcome_id: string
  recommendation_id: string
  metrics: {
    prediction_accuracy: number
    recommendation_accuracy: number
    crossing_avoided: boolean
    crossing_delayed: boolean
    stabilization_improvement: number
    actual_vs_predicted_deviation: number
    deviation_improvement: number
  }
  evaluated_at: string
}

export interface RegisteredModel {
  model_id: string
  version: string
  name: string
  model_kind: 'prediction' | 'forecast'
  algorithm: string
  trained_at: string
  created_at: string
  dataset_checksum: string
  feature_schema_checksum: string
  artifact_checksum: string
  artifact_path: string
  metrics: Record<string, unknown>
  training_parameters: Record<string, unknown>
  description: string
  status: 'active' | 'archived' | 'experimental'
}

export interface RuntimeConfig {
  stream_speed_seconds: number
  alert_thresholds: Record<string, number>
  forecast_horizon: number
  history_window: number
  confidence_threshold: number
  feature_flags: Record<string, boolean>
  relationship_threshold: number
  recommendation_limit: number
}

export interface AuditEntry {
  audit_id: string
  timestamp: string
  actor: string
  action: string
  entity: string
  entity_id: string | null
  details: Record<string, unknown>
  request_id: string | null
}

export interface AdminMetrics {
  uptime_seconds: number
  request_count: number
  response_count: number
  error_count: number
  error_rate: number
  cpu_percent: number
  memory_bytes: number
  memory_percent: number
  disk_total_bytes: number
  disk_used_bytes: number
  disk_free_bytes: number
  active_websocket_connections: number
  throughput: Record<string, number>
  latency: Record<
    string,
    {
      count: number
      average_ms: number
      latest_ms: number
      trend: { timestamp: number; milliseconds: number }[]
    }
  >
}

export interface AdminHealth {
  status: string
  application_version: string
  environment: string
  uptime_seconds: number
  checks: Record<string, Record<string, unknown>>
}

/**
 * EpiSense TypeScript Domain Definitions (Phase 12).
 * Exact type mappings corresponding to Phase 1-12 Pydantic schemas.
 */

export type AlertTier = "informational" | "low" | "medium" | "high";

export type RecommendedReviewAction = "investigate" | "monitor" | "informational" | "discard";

export type PathogenThreatTier =
  | "tier_1_mild"
  | "tier_2_moderate"
  | "tier_3_severe"
  | "tier_4_high_consequence";

export interface RiskScoreBreakdown {
  anomaly_score: number;
  threat_score: number;
  evidence_score: number;
  certainty_score: number;
  spatial_score: number;
  raw_composite_score: number;
  penalty_applied: number;
  final_score: number;
  applied_weights: Record<string, number>;
}

export interface AlertExplanation {
  summary: string;
  driving_factors: string[];
  gating_rationale?: string | null;
  detailed_narrative?: string;
}

export interface EvidenceReference {
  evidence_id: string;
  document_id: string;
  source_id: string;
  start_char: number;
  end_char: number;
  text_span: string;
  attribute_role: string;
  confidence: number;
}

export interface EpidemiologicalAlert {
  alert_id: string;
  signal_id: string;
  disease_key: string;
  geo_key: string;
  pathogen_threat_tier: PathogenThreatTier;
  period_start: string;
  period_end: string;
  composite_score: number;
  event_triage_score?: number;
  decision_category?: string;
  currentness_status?: string;
  source_breakdown?: any[];
  recommended_action?: RecommendedReviewAction;
  indicator_anomaly_result?: Record<string, any> | null;
  alert_tier: AlertTier;
  origin?: OriginClassification;
  is_gated: boolean;
  gating_reason?: string | null;
  score_breakdown: RiskScoreBreakdown;
  explanation: AlertExplanation;
  supporting_fused_event_ids: string[];
  supporting_source_count: number;
  provenance_references: EvidenceReference[];
  created_at: string;
}

export type GeographicLevel =
  | "facility"
  | "settlement"
  | "subdistrict"
  | "district"
  | "state"
  | "country"
  | "supranational"
  | "global";

export interface Location {
  location_id: string;
  original_text: string;
  normalized_name: string;
  resolved_name?: string | null;
  raw_mention?: string | null;
  geographic_level: GeographicLevel;
  latitude?: number | null;
  longitude?: number | null;
  parent_location?: string | null;
  admin1_code?: string | null;
  country_code?: string | null;
}

export interface EpidemiologicalQuantities {
  case_count?: number | null;
  death_count?: number | null;
  hospitalized_count?: number | null;
  recovered_count?: number | null;
  suspected_count?: number | null;
  raw_mentions?: string[];
  resolution_state?: "RESOLVED" | "PARTIALLY_RESOLVED" | "UNRESOLVED";
  semantics_type?: string;
  clinical_case_count?: number | null;
  lab_confirmed_count?: number | null;
  quantity_semantics_note?: string | null;
  max_reported_estimate?: number | null;
  conflict_details?: string | null;
  individual_observations?: any[];
}

export interface SourceGroup {
  source_id: string;
  independence_group: string;
}

export type AssertionStatus =
  | "confirmed"
  | "suspected"
  | "historical"
  | "negated"
  | "hypothetical";

export type CertaintyLevel = "definite" | "probable" | "possible" | "unlikely";

export interface FusedEvent {
  fused_event_id: string;
  canonical_disease: string;
  icd10_code?: string | null;
  canonical_location?: Location | null;
  geographic_hierarchy: {
    country?: string | null;
    region?: string | null;
    district?: string | null;
    subdistrict?: string | null;
    city?: string | null;
  };
  event_window_start: string;
  event_window_end: string;
  is_event_time_estimated: boolean;
  assertion_status: AssertionStatus;
  certainty: CertaintyLevel;
  aggregated_quantities: EpidemiologicalQuantities;
  contributing_observation_ids: string[];
  independent_sources: SourceGroup[];
  independent_source_count: number;
  has_conflicts: boolean;
  conflict_details?: string | null;
  quantity_resolution_status?: "RESOLVED" | "PARTIALLY_RESOLVED" | "UNRESOLVED";
  linkage_classification?: "HIGH_CONFIDENCE_LINKAGE" | "PROVISIONAL_LINKAGE" | "UNLINKED_SINGLETON";
  supporting_observation_count?: number;
  aggregated_case_count?: number;
  aggregated_death_count?: number;
  primary_origin?: string;
  supporting_observations?: any[];
  created_at: string;
  updated_at: string;
}

export type SignalLevel = "noise" | "watch" | "signal" | "strong_signal" | "no_signal";

export type DetectionMethod =
  | "ears_c1"
  | "ears_c2"
  | "ears_c3"
  | "farrington_flexible"
  | "farrington_bounded"
  | "historical_percentile"
  | "multi_detector"
  | "suppressed_insufficient_baseline";

export type BaselineReliability =
  | "stable_baseline"
  | "sparse_data"
  | "sparse_history"
  | "high_variance"
  | "conflicting_data"
  | "insufficient_history"
  | "insufficient_baseline"
  | "incompatible_granularity"
  | "not_evaluable";

export interface SignalObservation {
  signal_id: string;
  disease_key: string;
  geo_key: string;
  target_period_start: string;
  target_period_end: string;
  observed_value: number;
  expected_value: number;
  deviation: number;
  standardized_score?: number | null;
  threshold: number;
  signal_level: SignalLevel;
  origin?: OriginClassification;
  detection_method: DetectionMethod;
  reliability_status: BaselineReliability;
  downgraded_reason?: string | null;
  supporting_fused_event_ids: string[];
  provenance_references: EvidenceReference[];
  generated_at: string;
}

export interface AuditDecisionStep {
  step_number: number;
  step_name: string;
  inputs: Record<string, any>;
  rule_applied: string;
  output_value: any;
  is_gated: boolean;
  gating_detail?: string | null;
}

export interface AlertAuditTrail {
  audit_id: string;
  alert_id: string;
  signal_id: string;
  decision_steps: AuditDecisionStep[];
  applied_weights: Record<string, number>;
  score_breakdown: RiskScoreBreakdown;
  final_score: number;
  final_alert_tier: AlertTier;
  is_gated: boolean;
  gating_reasons: string[];
  audit_checksum: string;
  created_at: string;
}

export interface Epidemiological5W1H {
  who_pathogen: string;
  what_event: string;
  when_period: string;
  where_location: string;
  why_aberration: string;
  how_corroboration: string;
}

export interface ReconstructedEvidenceSpan {
  document_id: string;
  source_id: string;
  start_char: number;
  end_char: number;
  expected_text?: string | null;
  extracted_text: string;
  surrounding_context: string;
  attribute_role: string;
  extraction_method: string;
  is_valid: boolean;
  validation_error?: string | null;
}

export type ProvenanceNodeType =
  | "alert"
  | "signal"
  | "baseline"
  | "time_bin"
  | "fused_event"
  | "document"
  | "evidence_span";

export type ProvenanceEdgeType =
  | "scored_from"
  | "baseline_for"
  | "aggregated_into"
  | "composed_of"
  | "grounded_in"
  | "evidenced_by"
  | "span_of";

export interface ProvenanceNode {
  node_id: string;
  node_type: ProvenanceNodeType;
  entity_id: string;
  label: string;
  metadata: Record<string, any>;
}

export interface ProvenanceEdge {
  source_node_id: string;
  target_node_id: string;
  edge_type: ProvenanceEdgeType;
  description: string;
}

export interface ProvenanceGraph {
  graph_id: string;
  alert_id: string;
  nodes: ProvenanceNode[];
  edges: ProvenanceEdge[];
  is_acyclic: boolean;
  completeness_ratio: number;
  missing_nodes: string[];
}

export interface ExplainabilityDossier {
  dossier_id: string;
  alert_id: string;
  disease_key: string;
  geo_key: string;
  period_start: string;
  period_end: string;
  alert_tier: AlertTier;
  composite_score: number;
  pathogen_threat_tier: PathogenThreatTier;
  briefing: Epidemiological5W1H;
  executive_summary: string;
  driving_risk_factors: string[];
  applied_safety_constraints: string[];
  reconstructed_evidence: ReconstructedEvidenceSpan[];
  audit_trail: AlertAuditTrail;
  provenance_graph: ProvenanceGraph;
  provenance_complete: boolean;
  completeness_notes?: string | null;
  created_at: string;
}

export interface GeoJSONGeometry {
  type: "Point";
  coordinates: [number, number]; // [longitude, latitude]
}

export interface GeoJSONFeature<TProps = Record<string, any>> {
  type: "Feature";
  id?: string;
  geometry: GeoJSONGeometry | null;
  properties: TProps;
}

export interface GeoJSONFeatureCollection<TProps = Record<string, any>> {
  type: "FeatureCollection";
  features: GeoJSONFeature<TProps>[];
  total_features: number;
  features_with_geometry: number;
  unresolved_locations: number;
}

export interface AlertGeoProperties {
  alert_id: string;
  pathogen: string;
  alert_tier: AlertTier;
  composite_score: number;
  pathogen_threat_tier: PathogenThreatTier;
  location_name: string;
  admin_level: string;
  gazetteer_id?: string | null;
  period_start: string;
  period_end: string;
  is_gated: boolean;
  supporting_source_count: number;
  has_geometry: boolean;
}

export interface EventGeoProperties {
  fused_event_id: string;
  canonical_disease: string;
  location_name: string;
  admin_level: string;
  assertion_status: AssertionStatus;
  case_count?: number | null;
  death_count?: number | null;
  independent_source_count: number;
  window_start: string;
  window_end: string;
  has_conflicts: boolean;
  has_geometry: boolean;
}

export interface HeatmapGeoProperties {
  alert_id: string;
  pathogen: string;
  weight: number;
  alert_tier: AlertTier;
  intensity: number;
}

export interface GeoSummaryRegion {
  region: string;
  total_events: number;
  total_alerts: number;
  high_alerts: number;
  medium_alerts: number;
  low_alerts: number;
  informational_alerts: number;
  pathogens: string[];
  max_composite_score: number;
  latest_event_date?: string | null;
}

export interface GeoSummaryResponse {
  total_regions: number;
  regions: GeoSummaryRegion[];
  generated_at: string;
}

export type IngestionStatus =
  | "accepted"
  | "duplicate_skipped"
  | "rejected_malformed"
  | "rejected_error";

export type AlertLifecycleState =
  | "new"
  | "updated"
  | "confirmed_unchanged"
  | "resolved";

export type SourceType =
  | "official_bulletin"
  | "public_syndication"
  | "news_media"
  | "benchmark_corpus";

export interface DocumentIngestionRequest {
  document_id?: string;
  source_id?: string;
  source_name?: string;
  source_type?: SourceType;
  title: string;
  text: string;
  publication_timestamp?: string;
  publication_date?: string;
  url?: string;
  source_url?: string;
  content_hash_sha256?: string;
  language?: string;
  provenance_metadata?: Record<string, string>;
  metadata?: Record<string, any>;
}

export interface DocumentIngestionResponse {
  status: IngestionStatus;
  document_id?: string | null;
  update_id: string;
  fused_events_affected: number;
  bins_affected: number;
  signals_generated: number;
  alerts_generated: number;
  alert_lifecycle_states: Record<string, AlertLifecycleState>;
  message?: string | null;
  timestamp: string;
}

export interface SurveillanceEventUpdate {
  update_id: string;
  document_id?: string | null;
  status: IngestionStatus;
  fused_events_affected: string[];
  bins_affected: string[];
  signals_generated: string[];
  alerts_generated: string[];
  alert_lifecycle_states: Record<string, AlertLifecycleState>;
  message?: string | null;
  timestamp: string;
}

export type HealthStatus = "healthy" | "degraded" | "unhealthy";

export interface ServiceHealthResponse {
  status: HealthStatus;
  version: string;
  service: string;
  pipeline_available: boolean;
  state_store_available: boolean;
  timestamp: string;
}

export interface ReadinessResponse {
  ready: boolean;
  pipeline_ready: boolean;
  state_store_ready: boolean;
  state_documents_count?: number;
  state_alerts_count: number;
  state_events_count: number;
  timestamp: string;
}

export interface LivenessResponse {
  live: boolean;
  status: string;
}

export interface PaginatedResponse<T> {
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
  items: T[];
}

export interface WSSubscriptionFilter {
  pathogen?: string;
  alert_tier?: AlertTier;
  min_score?: number;
  region?: string;
}

export interface WSClientMessage {
  action: "subscribe" | "unsubscribe" | "ping";
  filter?: WSSubscriptionFilter;
}

export interface WSServerMessage {
  type: "connection_ack" | "subscription_ack" | "event_update" | "pong" | "error";
  client_id?: string;
  status?: string;
  filter?: WSSubscriptionFilter;
  data?: SurveillanceEventUpdate;
  message?: string;
  timestamp: string;
}

// -------------------------------------------------------------
// Live Surveillance & Research Extensions (Phase 13)
// -------------------------------------------------------------

export type OriginClassification =
  | "LIVE_EXTERNAL"
  | "MANUAL_SUBMISSION"
  | "HISTORICAL_CORPUS"
  | "BENCHMARK"
  | "SYNTHETIC_TEST";

export type SourceConnectorStatus =
  | "OPERATIONAL"
  | "DEGRADED"
  | "UNAVAILABLE"
  | "AUTHENTICATION_REQUIRED"
  | "NOT_CONFIGURED";

export interface SourceConnectorConfig {
  source_id: string;
  name: string;
  category: string;
  official_source_url: string;
  endpoint_url: string;
  poll_interval_seconds: number;
  is_enabled: boolean;
  is_configured?: boolean;
  status: SourceConnectorStatus;
  last_polled_at?: string | null;
  last_attempted_at?: string | null;
  last_success_at?: string | null;
  last_successful_fetch_at?: string | null;
  http_network_result?: number | null;
  next_scheduled_attempt_at?: string | null;
  last_cursor?: string | null;
  consecutive_failures: number;
  error_message?: string | null;
  operational_status_rationale?: string | null;
  total_retrievals: number;
  total_documents_ingested: number;
  new_documents_ingested?: number;
  last_document_count: number;
  items_discovered?: number;
  items_skipped_duplicates?: number;
  items_deferred?: number;
  parsing_errors?: string[];
}

export interface SourcePollRecord {
  poll_id: string;
  source_id: string;
  polled_at: string;
  status: SourceConnectorStatus;
  http_status?: number | null;
  documents_found: number;
  documents_ingested: number;
  duplicates_skipped: number;
  items_deferred?: number;
  duration_ms: number;
  error_message?: string | null;
  details?: Record<string, any>;
}

export interface PipelineStageExecution {
  stage_number: number;
  stage_name: string;
  status: "PENDING" | "RUNNING" | "COMPLETED" | "SKIPPED" | "FAILED";
  duration_ms: number;
  input_summary: string;
  output_summary: string;
  warnings?: string[];
  error_details?: string | null;
  details?: Record<string, any>;
}

export interface DocumentPipelineTrace {
  trace_id: string;
  document_id: string;
  source_id: string;
  origin: OriginClassification;
  title: string;
  raw_text: string;
  source_url?: string | null;
  publication_timestamp?: string | null;
  retrieval_timestamp: string;
  content_hash_sha256: string;
  overall_status: string;
  total_duration_ms: number;
  stages: PipelineStageExecution[];
  nlp_output?: any;
  candidate_event_ids?: string[];
  fused_event_ids?: string[];
  signal_ids?: string[];
  alert_ids?: string[];
  created_at?: string;
}

export interface MetricScore {
  precision: number;
  recall: number;
  f1: number;
  support: number;
}

export interface NLPEvaluationReport {
  benchmark_version: string;
  evaluated_at: string;
  total_documents_evaluated: number;
  ner_disease_f1: MetricScore;
  geographic_resolution_f1: MetricScore;
  temporal_normalization_f1: MetricScore;
  quantity_extraction_f1: MetricScore;
  assertion_accuracy: number;
  macro_f1: number;
  known_limitations: string[];
}

export interface SurveillanceAccounting {
  documents_ingested_total: number;
  documents_ingested_live: number;
  documents_ingested_historical: number;
  documents_ingested_manual: number;
  documents_parsed_successfully: number;
  documents_without_events: number;
  candidate_events_extracted: number;
  fused_events_active: number;
  fused_events_superseded: number;
  independently_corroborated_events: number;
  unverified_single_source_claims: number;
  indicator_time_bins_total: number;
  verified_numerical_indicator_bins: number;
  signals_evaluated: number;
  signals_blocked_insufficient_baseline: number;
  signals_eligible_stable_baseline: number;
  definitions?: Record<string, string>;
}

export interface LiveSurveillanceMetrics {
  timestamp: string;
  live_surveillance: {
    documents_ingested_live: number;
    alerts_generated_live: number;
    fused_events_live: number;
    alert_tiers: Record<string, number>;
  };
  connector_health: {
    total_connectors: number;
    operational_connectors: number;
    degraded_connectors: number;
    unavailable_connectors: number;
    auth_required_connectors: number;
  };
  segregated_corpus_breakdown: {
    total_documents: number;
    live_external_documents: number;
    historical_baseline_documents: number;
    total_alerts: number;
    live_alerts: number;
    historical_baseline_alerts: number;
  };
  surveillance_accounting?: SurveillanceAccounting;
  system_telemetry: {
    state_checksum_sha256: string;
    sequence_number: number;
    dead_letter_count: number;
    system_status: string;
  };
}

export interface SummaryFigureItem {
  label: string;
  value: string | number;
  description?: string;
  status?: string;
  operational_count?: number;
  total_connectors?: number;
  raw_ingested_count?: number;
  unique_ingested_count?: number;
  duplicates_filtered_count?: number;
  out_of_scope_count?: number;
  administrative_count?: number;
  priority_relevant_count?: number;
  actionable_positive_count?: number;
  negative_ruleout_count?: number;
}

export interface OperationalDocumentAudit {
  date_window_start: string;
  date_window_end: string;
  raw_ingested_count: number;
  unique_ingested_count: number;
  duplicates_filtered_count: number;
  out_of_scope_count: number;
  out_of_scope_documents: Array<{
    document_id: string;
    title: string;
    source_id: string;
    publication_timestamp: string;
    pathogen: string;
    reason: string;
    duplicate_count: number;
  }>;
  administrative_count: number;
  administrative_documents: Array<{
    document_id: string;
    title: string;
    source_id: string;
    publication_timestamp: string;
    reason: string;
    duplicate_count: number;
  }>;
  priority_disease_documents_count: number;
  priority_disease_documents: Array<{
    document_id: string;
    title: string;
    source_id: string;
    publication_timestamp: string;
    disease: string;
    assertion_status: string;
    clinical_summary: string;
    duplicate_count: number;
  }>;
  actionable_positive_outbreak_reports: number;
  negative_ruleout_reports: number;
  negative_ruleout_documents: Array<any>;
  positive_outbreak_documents: Array<any>;
}

export interface SourcePollingAuditItem {
  source_id: string;
  name: string;
  category: string;
  status: string;
  http_status: number | null;
  polling_state: "EMPTY_OR_UNCHANGED" | "AUTHENTICATION_REQUIRED" | "DEGRADED" | "UNAVAILABLE" | string;
  finding_summary: string;
  official_url: string;
}

export interface OverviewFinding {
  event_id: string;
  disease: string;
  location: string;
  period: string;
  headline: string;
  decision_category: string;
  origin: string;
  sources_count: number;
}

export interface ConnectorSummaryItem {
  source_id: string;
  name: string;
  category: string;
  status: string;
  official_url: string;
  error_message: string | null;
  last_polled_at: string | null;
}

export interface OperationalOverview {
  timestamp: string;
  summary_figures: {
    overall_source_status: SummaryFigureItem;
    new_operational_reports: SummaryFigureItem;
    priority_events_requiring_review: SummaryFigureItem;
    eligible_numerical_series: SummaryFigureItem;
    current_supported_anomalies?: SummaryFigureItem;
    current_eligible_forecasts?: SummaryFigureItem;
    supported_forecasts_or_anomalies: SummaryFigureItem;
    suppressed_analyses_insufficient_baseline: SummaryFigureItem;
  };
  operational_audit?: OperationalDocumentAudit;
  separated_counters?: Record<string, any>;
  source_polling_audit?: SourcePollingAuditItem[];
  most_important_new_findings: OverviewFinding[];
  empty_findings_message?: string;
  what_we_know: string[];
  what_is_uncertain: string[];
  recommended_next_steps: string[];
  connectors_summary: ConnectorSummaryItem[];
}

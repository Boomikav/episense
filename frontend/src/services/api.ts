/**
 * Centralized EpiSense API HTTP Client (Phase 12).
 * Strictly typed against Phase 12 REST API endpoints.
 */

import type {
  AlertGeoProperties,
  AlertAuditTrail,
  DocumentIngestionRequest,
  DocumentIngestionResponse,
  EpidemiologicalAlert,
  EventGeoProperties,
  ExplainabilityDossier,
  FusedEvent,
  GeoJSONFeatureCollection,
  GeoSummaryResponse,
  HeatmapGeoProperties,
  LivenessResponse,
  PaginatedResponse,
  ProvenanceGraph,
  ReadinessResponse,
  ServiceHealthResponse,
  SignalObservation,
} from "../types/api";

const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL || "http://localhost:8008";

export class ApiError extends Error {
  code: string;
  status: number;
  details?: any;

  constructor(message: string, code = "API_ERROR", status = 500, details?: any) {
    super(message);
    this.name = "ApiError";
    this.code = code;
    this.status = status;
    this.details = details;
  }
}

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const url = `${API_BASE_URL}${path}`;
  const headers = new Headers(options?.headers || {});
  if (!headers.has("Content-Type") && options?.body) {
    headers.set("Content-Type", "application/json");
  }
  if (!headers.has("Accept")) {
    headers.set("Accept", "application/json");
  }

  const response = await fetch(url, {
    ...options,
    headers,
  });

  if (!response.ok) {
    let errorData: any = null;
    try {
      errorData = await response.json();
    } catch {
      // Non-JSON error
    }

    const message =
      errorData?.error?.message ||
      errorData?.detail ||
      `Request failed with status ${response.status}: ${response.statusText}`;
    const code = errorData?.error?.code || "HTTP_ERROR";

    throw new ApiError(message, code, response.status, errorData?.error?.details);
  }

  return response.json() as Promise<T>;
}

export const api = {
  baseUrl: API_BASE_URL,

  // Health
  getHealth: () => request<ServiceHealthResponse>("/health"),
  getReadiness: () => request<ReadinessResponse>("/health/ready"),
  getLiveness: () => request<LivenessResponse>("/health/live"),

  // Alerts
  getAlerts: (params?: {
    pathogen?: string;
    location?: string;
    alert_tier?: string;
    threat_tier?: string;
    min_score?: number;
    max_score?: number;
    origin?: string;
    priority_only?: boolean;
    current_only?: boolean;
    page?: number;
    page_size?: number;
  }) => {
    const q = new URLSearchParams();
    if (params?.pathogen) q.set("pathogen", params.pathogen);
    if (params?.location) q.set("location", params.location);
    if (params?.alert_tier) q.set("alert_tier", params.alert_tier);
    if (params?.threat_tier) q.set("threat_tier", params.threat_tier);
    if (params?.min_score !== undefined) q.set("min_score", String(params.min_score));
    if (params?.max_score !== undefined) q.set("max_score", String(params.max_score));
    if (params?.origin) q.set("origin", params.origin);
    if (params?.priority_only !== undefined) q.set("priority_only", String(params.priority_only));
    if (params?.current_only !== undefined) q.set("current_only", String(params.current_only));
    if (params?.page) q.set("page", String(params.page));
    if (params?.page_size) q.set("page_size", String(params.page_size));
    const qs = q.toString();
    return request<PaginatedResponse<EpidemiologicalAlert>>(`/api/v1/alerts${qs ? `?${qs}` : ""}`);
  },

  getAlertById: (alertId: string) =>
    request<EpidemiologicalAlert>(`/api/v1/alerts/${alertId}`),

  getAlertDossier: (alertId: string) =>
    request<ExplainabilityDossier>(`/api/v1/alerts/${alertId}/dossier`),

  getAlertAudit: (alertId: string) =>
    request<AlertAuditTrail>(`/api/v1/alerts/${alertId}/audit`),

  getAlertProvenance: (alertId: string) =>
    request<ProvenanceGraph>(`/api/v1/alerts/${alertId}/provenance`),

  // Events
  getEvents: (params?: {
    pathogen?: string;
    location?: string;
    assertion_status?: string;
    origin?: string;
    priority_only?: boolean;
    current_only?: boolean;
    page?: number;
    page_size?: number;
  }) => {
    const q = new URLSearchParams();
    if (params?.pathogen) q.set("pathogen", params.pathogen);
    if (params?.location) q.set("location", params.location);
    if (params?.assertion_status) q.set("assertion_status", params.assertion_status);
    if (params?.origin) q.set("origin", params.origin);
    if (params?.priority_only !== undefined) q.set("priority_only", String(params.priority_only));
    if (params?.current_only !== undefined) q.set("current_only", String(params.current_only));
    if (params?.page) q.set("page", String(params.page));
    if (params?.page_size) q.set("page_size", String(params.page_size));
    const qs = q.toString();
    return request<PaginatedResponse<FusedEvent>>(`/api/v1/events${qs ? `?${qs}` : ""}`);
  },

  getEventById: (eventId: string) =>
    request<FusedEvent>(`/api/v1/events/${eventId}`),

  // Signals
  getSignals: (params?: {
    pathogen?: string;
    location?: string;
    signal_level?: string;
    origin?: string;
    priority_only?: boolean;
    current_only?: boolean;
    page?: number;
    page_size?: number;
  }) => {
    const q = new URLSearchParams();
    if (params?.pathogen) q.set("pathogen", params.pathogen);
    if (params?.location) q.set("location", params.location);
    if (params?.signal_level) q.set("signal_level", params.signal_level);
    if (params?.origin) q.set("origin", params.origin);
    if (params?.priority_only !== undefined) q.set("priority_only", String(params.priority_only));
    if (params?.current_only !== undefined) q.set("current_only", String(params.current_only));
    if (params?.page) q.set("page", String(params.page));
    if (params?.page_size) q.set("page_size", String(params.page_size));
    const qs = q.toString();
    return request<PaginatedResponse<SignalObservation>>(`/api/v1/signals${qs ? `?${qs}` : ""}`);
  },

  getSignalById: (signalId: string) =>
    request<SignalObservation>(`/api/v1/signals/${signalId}`),

  // Geospatial
  getGeoAlerts: (params?: {
    pathogen?: string;
    alert_tier?: string;
    min_score?: number;
    current_only?: boolean;
    priority_only?: boolean;
  }) => {
    const q = new URLSearchParams();
    if (params?.pathogen) q.set("pathogen", params.pathogen);
    if (params?.alert_tier) q.set("alert_tier", params.alert_tier);
    if (params?.min_score !== undefined) q.set("min_score", String(params.min_score));
    if (params?.current_only !== undefined) q.set("current_only", String(params.current_only));
    if (params?.priority_only !== undefined) q.set("priority_only", String(params.priority_only));
    const qs = q.toString();
    return request<GeoJSONFeatureCollection<AlertGeoProperties>>(`/api/v1/geo/alerts${qs ? `?${qs}` : ""}`);
  },

  getGeoEvents: (params?: {
    pathogen?: string;
    assertion_status?: string;
    current_only?: boolean;
    priority_only?: boolean;
  }) => {
    const q = new URLSearchParams();
    if (params?.pathogen) q.set("pathogen", params.pathogen);
    if (params?.assertion_status) q.set("assertion_status", params.assertion_status);
    if (params?.current_only !== undefined) q.set("current_only", String(params.current_only));
    if (params?.priority_only !== undefined) q.set("priority_only", String(params.priority_only));
    const qs = q.toString();
    return request<GeoJSONFeatureCollection<EventGeoProperties>>(`/api/v1/geo/events${qs ? `?${qs}` : ""}`);
  },

  getGeoHeatmap: () =>
    request<GeoJSONFeatureCollection<HeatmapGeoProperties>>("/api/v1/geo/heatmap"),

  getGeoSummary: () =>
    request<GeoSummaryResponse>("/api/v1/geo/summary"),

  // Document Ingestion
  submitDocument: (payload: DocumentIngestionRequest) =>
    request<DocumentIngestionResponse>("/api/v1/documents", {
      method: "POST",
      body: JSON.stringify(payload),
    }),

  // Operational Live Metrics (Segregated from baseline)
  getLiveMetrics: () =>
    request<import("../types/api").LiveSurveillanceMetrics>("/api/v1/metrics/live"),

  // Operational Overview (6 Top Figures & Synthesis Briefings)
  getOperationalOverview: () =>
    request<import("../types/api").OperationalOverview>("/api/v1/metrics/overview"),

  // Public Health Sources & Connectors
  listSources: () =>
    request<import("../types/api").SourceConnectorConfig[]>("/api/v1/sources"),

  pollSource: (sourceId: string) =>
    request<import("../types/api").SourcePollRecord>(`/api/v1/sources/${sourceId}/poll`, {
      method: "POST",
    }),

  pollAllSources: () =>
    request<import("../types/api").SourcePollRecord[]>("/api/v1/sources/poll-all", {
      method: "POST",
    }),

  getSourceHistory: (sourceId: string, limit = 20) =>
    request<import("../types/api").SourcePollRecord[]>(`/api/v1/sources/${sourceId}/history?limit=${limit}`),

  // NLP Workbench & 17-Stage Traces
  listWorkbenchDocuments: (params?: {
    origin?: string;
    source_id?: string;
    freshness?: string;
    currentness_status?: string;
    disease?: string;
    limit?: number;
    offset?: number;
  }) => {
    const q = new URLSearchParams();
    if (params?.origin && params.origin !== "ALL") q.set("origin", params.origin);
    if (params?.source_id) q.set("source_id", params.source_id);
    if (params?.freshness && params.freshness !== "ALL") q.set("freshness", params.freshness);
    if (params?.currentness_status && params.currentness_status !== "ALL") q.set("currentness_status", params.currentness_status);
    if (params?.disease) q.set("disease", params.disease);
    if (params?.limit) q.set("limit", String(params.limit));
    if (params?.offset) q.set("offset", String(params.offset));
    const qs = q.toString();
    return request<any[]>(`/api/v1/workbench/documents${qs ? `?${qs}` : ""}`);
  },

  getDocumentTrace: (documentId: string) =>
    request<import("../types/api").DocumentPipelineTrace>(`/api/v1/workbench/traces/${documentId}`),

  analyzeDocument: (documentId: string) =>
    request<{
      document_id: string;
      status: string;
      candidates_extracted: number;
      fused_events_produced: number;
      fused_event_ids: string[];
    }>(`/api/v1/workbench/analyze/${documentId}`, {
      method: "POST",
    }),

  // Event Fusion & Anti-Inflation Inspector
  listFusionClusters: (params?: {
    disease?: string;
    location?: string;
    priority_only?: boolean;
    current_only?: boolean;
    filter_mode?: string;
    origin?: string;
    limit?: number;
  }) => {
    const q = new URLSearchParams();
    if (params?.disease) q.set("disease", params.disease);
    if (params?.location) q.set("location", params.location);
    if (params?.priority_only !== undefined) q.set("priority_only", String(params.priority_only));
    if (params?.current_only !== undefined) q.set("current_only", String(params.current_only));
    if (params?.filter_mode) q.set("filter_mode", params.filter_mode);
    if (params?.origin) q.set("origin", params.origin);
    if (params?.limit) q.set("limit", String(params.limit));
    const qs = q.toString();
    return request<FusedEvent[]>(`/api/v1/fusion/clusters${qs ? `?${qs}` : ""}`);
  },

  getFusionCardinality: (origin: string = "LIVE_EXTERNAL") =>
    request<{
      origin: string;
      total_source_observations: number;
      total_event_groups: number;
      high_confidence_groups: number;
      provisional_groups: number;
      unlinked_singletons: number;
      priority_event_groups: number;
      non_priority_event_groups: number;
      priority_observations: number;
      non_priority_observations: number;
      unaccounted_observations: number;
      priority_disease_breakdown: Record<string, { event_groups: number; observations: number }>;
    }>(`/api/v1/fusion/cardinality?origin=${encodeURIComponent(origin)}`),

  getClusterDetails: (fusedEventId: string) =>
    request<{
      fused_event: FusedEvent;
      formula: string;
      threshold: number;
      weights: Record<string, number>;
      anti_inflation_rationale: string;
      supporting_observations: any[];
      distinct_sources_count: number;
      is_multi_source_corroborated: boolean;
    }>(`/api/v1/fusion/clusters/${fusedEventId}`),

  // Empirical Benchmark Evaluation Runner
  runEvaluation: () =>
    request<import("../types/api").NLPEvaluationReport>("/api/v1/evaluation/run", {
      method: "POST",
    }),

  // Epidemiological Forecasting & Data Sufficiency
  getSufficiencyAudit: () =>
    request<Record<string, any>>("/api/v1/forecasting/sufficiency"),

  listForecastingSeries: (params?: { disease?: string; geo?: string }) => {
    const q = new URLSearchParams();
    if (params?.disease) q.set("disease", params.disease);
    if (params?.geo) q.set("geo", params.geo);
    const qs = q.toString();
    return request<any[]>(`/api/v1/forecasting/series${qs ? `?${qs}` : ""}`);
  },

  generateForecast: (payload: {
    series_key?: string;
    disease_key?: string;
    geo_key?: string;
    model_type?: string;
    horizon_weeks?: number;
    persist?: boolean;
  }) =>
    request<any>("/api/v1/forecasting/predict", {
      method: "POST",
      body: JSON.stringify(payload),
    }),

  listForecastHistory: (params?: { disease?: string; geo?: string; limit?: number }) => {
    const q = new URLSearchParams();
    if (params?.disease) q.set("disease", params.disease);
    if (params?.geo) q.set("geo", params.geo);
    if (params?.limit) q.set("limit", String(params.limit));
    const qs = q.toString();
    return request<any[]>(`/api/v1/forecasting/history${qs ? `?${qs}` : ""}`);
  },

  getSpatiotemporalPanel: (params?: { disease?: string; frequency?: string; geography?: string; limit?: number }) => {
    const q = new URLSearchParams();
    if (params?.disease) q.set("disease", params.disease);
    if (params?.frequency) q.set("frequency", params.frequency);
    if (params?.geography) q.set("geography", params.geography);
    if (params?.limit) q.set("limit", String(params.limit));
    const qs = q.toString();
    return request<{ total_count: number; returned_count: number; records: any[] }>(`/api/v1/forecasting/panel${qs ? `?${qs}` : ""}`);
  },

  getEvaluationBenchmarks: () =>
    request<{ evaluations: any[]; ablations: any[]; outbreak_metrics: any }>(`/api/v1/forecasting/evaluations`),

  compareLiveObservation: (payload: {
    disease: string;
    location: string;
    observation_period: string;
    observed_cases: number;
    case_definition?: string;
  }) =>
    request<{
      disease: string;
      location: string;
      observation_period: string;
      observed_cases: number;
      expected_baseline_median: number;
      expected_range_lower: number;
      expected_range_upper: number;
      residual: number;
      percentage_deviation: number;
      z_score: number;
      status: string;
      epidemiological_interpretation: string;
      recommended_action: string;
      source_provenance: string;
    }>(`/api/v1/forecasting/compare-live`, {
      method: "POST",
      body: JSON.stringify(payload),
    }),
};

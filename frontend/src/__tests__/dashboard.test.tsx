import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { MetricCards } from "../components/dashboard/MetricCards";
import { RiskDistributionChart } from "../components/dashboard/RiskDistributionChart";
import { RegionalSummaryTable } from "../components/dashboard/RegionalSummaryTable";
import type { EpidemiologicalAlert, FusedEvent, GeoSummaryRegion, SignalObservation } from "../types/api";

describe("Dashboard Components", () => {
  const mockAlerts: EpidemiologicalAlert[] = [
    {
      alert_id: "a-1",
      signal_id: "sig-1",
      disease_key: "nipah virus",
      geo_key: "kerala",
      pathogen_threat_tier: "tier_4_high_consequence",
      period_start: "2026-09-01",
      period_end: "2026-09-07",
      composite_score: 0.88,
      alert_tier: "high",
      is_gated: false,
      gating_reason: null,
      score_breakdown: {
        anomaly_score: 0.9,
        threat_score: 1.0,
        evidence_score: 0.8,
        certainty_score: 0.85,
        spatial_score: 0.5,
        composite_score: 0.88,
        raw_composite_score: 0.88,
        threat_tier: "tier_4_high_consequence",
        alert_tier: "high",
        safety_ceiling_applied: false,
        reliability_ceiling_applied: false,
        is_gated: false,
      },
      explanation: {
        summary: "Severe cluster of Nipah virus",
        driving_factors: ["Fatality risk", "Rapid aberration"],
        safety_gating_applied: false,
        safety_gating_reason: null,
        reliability_status: "RELIABLE",
        supporting_events_count: 1,
        supporting_sources_count: 2,
      },
      supporting_fused_event_ids: ["fe-1"],
      supporting_source_count: 2,
      provenance_references: [],
      created_at: "2026-09-07T12:00:00Z",
    },
    {
      alert_id: "a-2",
      signal_id: "sig-2",
      disease_key: "cholera",
      geo_key: "maharashtra",
      pathogen_threat_tier: "tier_3_severe",
      period_start: "2026-09-01",
      period_end: "2026-09-07",
      composite_score: 0.72,
      alert_tier: "medium",
      is_gated: false,
      gating_reason: null,
      score_breakdown: {
        anomaly_score: 0.7,
        threat_score: 0.6,
        evidence_score: 0.7,
        certainty_score: 0.8,
        spatial_score: 0.4,
        composite_score: 0.72,
        raw_composite_score: 0.72,
        threat_tier: "tier_3_severe",
        alert_tier: "medium",
        safety_ceiling_applied: false,
        reliability_ceiling_applied: false,
        is_gated: false,
      },
      explanation: {
        summary: "Waterborne outbreak in urban sector",
        driving_factors: ["Case spike"],
        safety_gating_applied: false,
        safety_gating_reason: null,
        reliability_status: "RELIABLE",
        supporting_events_count: 1,
        supporting_sources_count: 2,
      },
      supporting_fused_event_ids: ["fe-2"],
      supporting_source_count: 2,
      provenance_references: [],
      created_at: "2026-09-07T12:00:00Z",
    },
  ];

  const mockEvents: FusedEvent[] = [
    {
      fused_id: "fe-1",
      canonical_disease: "nipah virus",
      canonical_location: {
        raw_text: "Kerala",
        resolved_name: "Kerala",
        geonames_id: null,
        country_code: "IN",
        admin1_code: "KL",
        admin2_code: null,
        feature_class: "A",
        feature_code: "ADM1",
        latitude: 10.8505,
        longitude: 76.2711,
        resolution_method: "exact",
        confidence: 1.0,
      },
      temporal_window: {
        earliest_start: "2026-09-01",
        latest_end: "2026-09-07",
        calendar_year: 2026,
        iso_week: 36,
        resolution_type: "exact_day",
        date_inferred: false,
      },
      quantities: {
        cases: 4,
        deaths: 2,
        hospitalizations: 4,
        cumulative_cases: 4,
        case_interval: null,
        death_interval: null,
        aggregation_source_count: 1,
      },
      source_count: 2,
      independent_source_group_count: 2,
      assertion_status: "CONFIRMED",
      candidate_ids: ["c-1", "c-2"],
      provenance_summary: {
        total_sources: 2,
        source_types: ["official_bulletin", "lab_report"],
        source_ids: ["who", "lab_kerala"],
        source_groups: ["g1", "g2"],
        min_publication_date: "2026-09-01",
        max_publication_date: "2026-09-07",
        evidence_span_count: 4,
      },
      deterministic_hash: "hash123",
      created_at: "2026-09-07T12:00:00Z",
      updated_at: "2026-09-07T12:00:00Z",
    },
  ];

  const mockSignals: SignalObservation[] = [
    {
      signal_id: "sig-1",
      time_bin_id: "bin-1",
      pathogen: "nipah virus",
      location: "Kerala",
      target_period_start: "2026-09-01",
      target_period_end: "2026-09-07",
      observed_value: 4,
      expected_value: 0.2,
      deviation: 3.8,
      threshold: 2.0,
      signal_level: "STRONG_SIGNAL",
      detection_method: "EARS_C3",
      reliability_status: "RELIABLE",
      supporting_fused_event_ids: ["fe-1"],
      provenance_references: [],
      generated_at: "2026-09-07T12:00:00Z",
    },
  ];

  it("renders metric cards with correct alert counts", () => {
    render(
      <MetricCards
        alerts={mockAlerts}
        events={mockEvents}
        signals={mockSignals}
        documentsCount={110}
      />
    );

    expect(screen.getByText("Narrative Event Reviews")).toBeInTheDocument();
    expect(screen.getAllByText("2").length).toBeGreaterThanOrEqual(1);
    expect(screen.getByText("Canonical Fused Events")).toBeInTheDocument();
    expect(screen.getByText("Statistical Anomalies")).toBeInTheDocument();
    expect(screen.getByText("Operational Feeds")).toBeInTheDocument();
    expect(screen.getByText("/ 6")).toBeInTheDocument();
  });

  it("renders risk distribution stratification", () => {
    render(<RiskDistributionChart alerts={mockAlerts} />);
    expect(screen.getByText("Epidemiological Risk Distribution")).toBeInTheDocument();
    expect(screen.getByText("Pathogen Threat Stratification")).toBeInTheDocument();
  });

  it("renders regional summary table accurately", () => {
    const mockRegions: GeoSummaryRegion[] = [
      {
        region: "Kerala",
        total_events: 5,
        total_alerts: 3,
        high_alerts: 2,
        medium_alerts: 1,
        low_alerts: 0,
        informational_alerts: 0,
        pathogens: ["nipah virus"],
        max_composite_score: 0.92,
      },
    ];

    render(<RegionalSummaryTable regions={mockRegions} onSelectRegion={() => {}} />);
    expect(screen.getByText("Geographic Surveillance Summary")).toBeInTheDocument();
    expect(screen.getByText("Kerala")).toBeInTheDocument();
    expect(screen.getByText("nipah virus")).toBeInTheDocument();
  });
});

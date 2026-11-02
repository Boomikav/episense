import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { AlertDetailModal } from "../components/alerts/AlertDetailModal";
import { EventTable } from "../components/events/EventTable";
import { SignalTable } from "../components/signals/SignalTable";
import { SystemHealthCard } from "../components/status/SystemHealthCard";
import { api } from "../services/api";
import type { EpidemiologicalAlert, FusedEvent, SignalObservation } from "../types/api";

describe("AlertDetailModal Component", () => {
  const mockAlert: EpidemiologicalAlert = {
    alert_id: "alert-xyz",
    signal_id: "sig-xyz",
    disease_key: "nipah virus",
    geo_key: "Kozhikode",
    pathogen_threat_tier: "tier_4_high_consequence",
    period_start: "2026-09-01",
    period_end: "2026-09-07",
    composite_score: 0.895,
    alert_tier: "high",
    is_gated: false,
    gating_reason: null,
    score_breakdown: {
      anomaly_score: 0.92,
      threat_score: 1.0,
      evidence_score: 0.85,
      certainty_score: 0.9,
      spatial_score: 0.8,
      composite_score: 0.895,
      raw_composite_score: 0.895,
      threat_tier: "tier_4_high_consequence",
      alert_tier: "high",
      safety_ceiling_applied: false,
      reliability_ceiling_applied: false,
      is_gated: false,
    },
    explanation: {
      summary: "Severe Nipah cluster detected in Kozhikode district with acute encephalitis",
      driving_factors: ["Extreme pathogen threat", "Z-score anomaly"],
      safety_gating_applied: false,
      safety_gating_reason: null,
      reliability_status: "RELIABLE",
      supporting_events_count: 2,
      supporting_sources_count: 3,
    },
    supporting_fused_event_ids: ["fe-1", "fe-2"],
    supporting_source_count: 3,
    provenance_references: [],
    created_at: "2026-09-07T12:00:00Z",
  };

  it("renders 5W1H briefing, score breakdown, and allows tab switching", async () => {
    vi.spyOn(api, "getAlertById").mockResolvedValue(mockAlert);
    vi.spyOn(api, "getAlertDossier").mockResolvedValue({
      alert_id: "alert-xyz",
      briefing: {
        who_pathogen: "Nipah Virus (tier_4_high_consequence)",
        where_location: "Kozhikode",
        when_time_window: "2026-09-01 to 2026-09-07",
        what_clinical_events: "Acute encephalitis",
        why_aberration: "EARS C1 detected anomaly",
        how_credible: "High evidence credibility",
      },
      driving_factors: [],
      score_breakdown: mockAlert.score_breakdown,
      gating_status: { is_gated: false, reason: null },
      reconstructed_evidence: [],
      generated_at: new Date().toISOString(),
    });
    vi.spyOn(api, "getAlertAudit").mockResolvedValue({
      audit_id: "aud-1",
      alert_id: "alert-xyz",
      signal_id: "sig-xyz",
      decision_steps: [],
      applied_weights: {},
      score_breakdown: mockAlert.score_breakdown,
      audit_checksum: "sha-hash-12345",
      recorded_at: new Date().toISOString(),
    });
    vi.spyOn(api, "getAlertProvenance").mockResolvedValue({
      alert_id: "alert-xyz",
      nodes: [],
      edges: [],
      root_document_ids: [],
    });

    const onClose = vi.fn();
    render(<AlertDetailModal alertId="alert-xyz" onClose={onClose} />);

    await waitFor(() => {
      expect(screen.getAllByText(/nipah virus/i)[0]).toBeInTheDocument();
    });

    expect(screen.getAllByText(/Kozhikode/i)[0]).toBeInTheDocument();
    expect(screen.getByText("0.895")).toBeInTheDocument();

    // Tab buttons exist
    const riskTab = screen.getByRole("button", { name: /Risk Breakdown/i });
    const dossierTab = screen.getByRole("button", { name: /Explainability Dossier/i });
    const auditTab = screen.getByRole("button", { name: /Decision Audit Trail/i });
    const lineageTab = screen.getByRole("button", { name: /Provenance DAG/i });

    expect(riskTab).toBeInTheDocument();
    expect(dossierTab).toBeInTheDocument();
    expect(auditTab).toBeInTheDocument();
    expect(lineageTab).toBeInTheDocument();

    // Switch tabs
    fireEvent.click(dossierTab);
    fireEvent.click(auditTab);
    fireEvent.click(lineageTab);
    fireEvent.click(riskTab);
  });
});

describe("EventTable Component", () => {
  const mockEvents: FusedEvent[] = [
    {
      fused_event_id: "fe-001",
      canonical_disease: "Dengue Fever",
      canonical_location: {
        resolved_name: "Pune",
        level: "district",
        country: "India",
        latitude: 18.5204,
        longitude: 73.8567,
      },
      event_window_start: "2026-09-01T00:00:00Z",
      event_window_end: "2026-09-07T00:00:00Z",
      is_event_time_estimated: false,
      assertion_status: "confirmed",
      certainty: "high",
      aggregated_quantities: {
        case_count: 15,
        hospitalized_count: 4,
        death_count: 0,
      },
      contributing_observation_ids: ["obs-1", "obs-2"],
      independent_sources: ["source_a", "source_b"],
      independent_source_count: 2,
      has_conflicts: false,
      created_at: "2026-09-07T12:00:00Z",
      updated_at: "2026-09-07T12:00:00Z",
    },
  ];

  it("renders canonical fused events table correctly", () => {
    render(<EventTable events={mockEvents} />);

    expect(screen.getByText("Dengue Fever")).toBeInTheDocument();
    expect(screen.getByText("Pune")).toBeInTheDocument();
    expect(screen.getByText("15")).toBeInTheDocument();
    expect(screen.getByText("2")).toBeInTheDocument();
  });
});

describe("SignalTable Component", () => {
  const mockSignals: SignalObservation[] = [
    {
      signal_id: "sig-001",
      disease_key: "cholera",
      geo_key: "puri",
      target_period_start: "2026-09-01T00:00:00Z",
      target_period_end: "2026-09-07T00:00:00Z",
      observed_value: 22,
      expected_value: 2.5,
      deviation: 3.5,
      threshold: 4.8,
      detection_method: "farrington_flexible",
      signal_level: "strong_signal",
      reliability_status: "stable_baseline",
      supporting_fused_event_ids: ["fe-1"],
      provenance_references: [],
      generated_at: "2026-09-07T12:00:00Z",
    },
  ];

  it("renders early warning signals table with metrics", () => {
    render(<SignalTable signals={mockSignals} />);

    expect(screen.getByText("cholera")).toBeInTheDocument();
    expect(screen.getByText("puri")).toBeInTheDocument();
    expect(screen.getByText("22")).toBeInTheDocument();
    expect(screen.getByText("+3.50σ")).toBeInTheDocument();
  });
});

describe("SystemHealthCard Component", () => {
  it("renders system health container and monitoring cards", async () => {
    vi.spyOn(api, "getHealth").mockResolvedValue({
      status: "healthy",
      version: "1.0.0",
      environment: "production",
      pipeline_available: true,
      state_store_available: true,
      timestamp: new Date().toISOString(),
    });

    vi.spyOn(api, "getReadiness").mockResolvedValue({
      status: "ready",
      ready: true,
      state_documents_count: 110,
      state_alerts_count: 170,
    });

    vi.spyOn(api, "getLiveness").mockResolvedValue({
      status: "live",
      live: true,
    });

    render(<SystemHealthCard />);
    await waitFor(() => {
      expect(screen.getByText(/Pipeline & Surveillance State Diagnostics/i)).toBeInTheDocument();
    });
    expect(screen.getByText(/Ready for Traffic/i)).toBeInTheDocument();
    expect(screen.getByText(/FastAPI In-Process Daemon/i)).toBeInTheDocument();
  });
});

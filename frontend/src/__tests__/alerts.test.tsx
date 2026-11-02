import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { AlertTable } from "../components/alerts/AlertTable";
import { AlertFilters } from "../components/alerts/AlertFilters";
import type { EpidemiologicalAlert } from "../types/api";

describe("Alerts Components", () => {
  const mockAlerts: EpidemiologicalAlert[] = [
    {
      alert_id: "alert-001",
      signal_id: "sig-001",
      disease_key: "avian influenza",
      geo_key: "West Bengal",
      pathogen_threat_tier: "tier_1",
      period_start: "2026-09-01",
      period_end: "2026-09-07",
      composite_score: 0.842,
      alert_tier: "high",
      is_gated: false,
      gating_reason: null,
      score_breakdown: {
        anomaly_score: 0.88,
        threat_score: 1.0,
        evidence_score: 0.75,
        certainty_score: 0.8,
        spatial_score: 0.4,
        composite_score: 0.842,
        raw_composite_score: 0.842,
        threat_tier: "tier_1",
        alert_tier: "high",
        safety_ceiling_applied: false,
        reliability_ceiling_applied: false,
        is_gated: false,
      },
      explanation: {
        summary: "Avian influenza cluster with abnormal transmission dynamics",
        driving_factors: ["High case rate", "Pathogen threat level"],
        safety_gating_applied: false,
        safety_gating_reason: null,
        reliability_status: "RELIABLE",
        supporting_events_count: 2,
        supporting_sources_count: 3,
      },
      supporting_fused_event_ids: ["fe-1"],
      supporting_source_count: 3,
      provenance_references: [],
      created_at: "2026-09-07T12:00:00Z",
    },
  ];

  it("renders alert table rows and handles select callback", () => {
    const onSelect = vi.fn();
    render(<AlertTable alerts={mockAlerts} onSelectAlert={onSelect} />);

    expect(screen.getByText("avian influenza")).toBeInTheDocument();
    expect(screen.getByText("West Bengal")).toBeInTheDocument();
    expect(screen.getByText("INFORMATIONAL")).toBeInTheDocument();

    const row = screen.getByText("avian influenza").closest("tr");
    expect(row).not.toBeNull();
    if (row) fireEvent.click(row);

    expect(onSelect).toHaveBeenCalledWith("alert-001");
  });

  it("updates filter criteria and triggers callbacks", () => {
    const onPathogenChange = vi.fn();
    const onLocationChange = vi.fn();
    const onTierChange = vi.fn();
    const onMinScoreChange = vi.fn();
    const onReset = vi.fn();

    render(
      <AlertFilters
        pathogen=""
        location=""
        alertTier=""
        minScore={0}
        onPathogenChange={onPathogenChange}
        onLocationChange={onLocationChange}
        onAlertTierChange={onTierChange}
        onMinScoreChange={onMinScoreChange}
        onResetFilters={onReset}
      />
    );

    const pathogenInput = screen.getByPlaceholderText("Filter by pathogen (e.g. Dengue, Cholera)...");
    fireEvent.change(pathogenInput, { target: { value: "cholera" } });
    expect(onPathogenChange).toHaveBeenCalledWith("cholera");

    const resetButton = screen.getByText("Reset");
    fireEvent.click(resetButton);
    expect(onReset).toHaveBeenCalled();
  });
});

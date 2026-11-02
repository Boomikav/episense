import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import { ForecastingView } from "../views/ForecastingView";
import { api } from "../services/api";

describe("ForecastingView Component", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  const mockSufficiency = {
    Dengue: {
      disease: "Dengue",
      total_fused_events: 36,
      total_time_bins: 28,
      unique_locations_count: 12,
      max_consecutive_weeks: 2,
      data_structure_classification: "Cross-sectional snapshots (outbreak reports at single points in time)",
      event_cases: 72643,
    },
    Cholera: {
      disease: "Cholera",
      total_fused_events: 27,
      total_time_bins: 15,
      unique_locations_count: 7,
      max_consecutive_weeks: 1,
      data_structure_classification: "Cross-sectional snapshots",
      event_cases: 146937,
    },
  };

  const mockSeries = [
    {
      series_key: "dengue:delhi",
      disease_key: "dengue",
      geo_key: "delhi",
      total_bins: 10,
      positive_case_bins: 4,
      max_consecutive_weeks: 2,
      data_structure: "Cross-sectional snapshot",
      forecasting_eligible: false,
      rationale: "Suppressed: 2 consecutive weeks < 12 required.",
    },
  ];

  it("renders data sufficiency feasibility table and scientific gating safeguards", async () => {
    vi.spyOn(api, "getSufficiencyAudit").mockResolvedValue(mockSufficiency);
    vi.spyOn(api, "listForecastingSeries").mockResolvedValue(mockSeries);
    vi.spyOn(api, "listForecastHistory").mockResolvedValue([]);

    render(<ForecastingView />);

    await waitFor(() => {
      expect(screen.getByText(/Epidemiological Forecasting & Baseline Data-Sufficiency Audit/i)).toBeInTheDocument();
      expect(screen.getByText("Dengue")).toBeInTheDocument();
      expect(screen.getByText("Cholera")).toBeInTheDocument();
      const suppressedBadges = screen.getAllByText(/SUPPRESSED \(N < 12\)/i);
      expect(suppressedBadges.length).toBeGreaterThanOrEqual(1);
    });
  });
});

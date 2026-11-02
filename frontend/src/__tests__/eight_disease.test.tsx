import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import { EightDiseaseIntelligenceView } from "../views/EightDiseaseIntelligenceView";
import { api } from "../services/api";

describe("EightDiseaseIntelligenceView Component", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  const mockSufficiency = {
    Dengue: {
      disease: "Dengue",
      modelling_status: "FORECAST_READY",
      forecast_eligibility: "FORECAST_READY",
      operational_data_freshness: "FRESH (Lag: 0d)",
      historical_trend: "Seasonal Post-Monsoon Surge",
      best_candidate_model: "Spatiotemporal Panel Poisson GLM (7 Focal States)",
      target_variable: "Reported case incidence",
      target_unit: "cases",
      geographic_level: "7 Endemic States / National",
      expected_seasonal_range: [1500, 2840, 5600],
      latest_observation_date: "2026-W44",
      source_provenance: "NVBDCP / NCDC Annual Series & Weekly IDSP",
    },
    Malaria: {
      disease: "Malaria",
      modelling_status: "FORECAST_READY",
      forecast_eligibility: "FORECAST_READY",
      operational_data_freshness: "FRESH (Lag: 62d)",
      historical_trend: "Decreasing (-10.4% vis-a-vis 2025)",
      best_candidate_model: "Negative Binomial GLM / Autoregressive (h=1..6)",
      target_variable: "Reported case incidence",
      target_unit: "cases",
      geographic_level: "National (NCVBDC) / District (IDSP)",
      expected_seasonal_range: [5000, 15000, 39000],
      latest_observation_date: "August 2026",
      source_provenance: "NCVBDC MMIS National Monthly Reports",
    },
    Chikungunya: {
      disease: "Chikungunya",
      modelling_status: "BASELINE_ONLY",
      forecast_eligibility: "BASELINE_ONLY",
      operational_data_freshness: "FRESH (Lag: 0d)",
      historical_trend: "Endemic Baseline with Seasonal Spikes",
      best_candidate_model: "Seasonal Median & 3-Year Persistence Baseline",
      expected_seasonal_range: [400, 1100, 3200],
      latest_observation_date: "2026-W44",
      source_provenance: "NCVBDC / NVBDCP Annual",
    },
    Leptospirosis: {
      disease: "Leptospirosis",
      modelling_status: "INSUFFICIENT_HISTORICAL_DATA",
      forecast_eligibility: "INSUFFICIENT_HISTORICAL_DATA",
      operational_data_freshness: "STALE",
      historical_trend: "Post-Monsoon Clustered Outbreaks",
      best_candidate_model: "Historical Reference Baseline (Annual N=7)",
      expected_seasonal_range: [100, 450, 1200],
      latest_observation_date: "2024",
      source_provenance: "NCDC Zoonosis Division",
    },
    Cholera: {
      disease: "Cholera",
      modelling_status: "BASELINE_ONLY",
      forecast_eligibility: "BASELINE_ONLY",
      operational_data_freshness: "FRESH (Lag: 0d)",
      historical_trend: "Monsoon Surge / Summer Baseline",
      best_candidate_model: "Historical Seasonal Median / Moving Average",
      expected_seasonal_range: [200, 600, 1800],
      latest_observation_date: "2026-W44",
      source_provenance: "IDSP Weekly & Annual Surveillance",
    },
    "Acute Diarrhoeal Disease": {
      disease: "Acute Diarrhoeal Disease",
      modelling_status: "BASELINE_ONLY",
      forecast_eligibility: "BASELINE_ONLY",
      operational_data_freshness: "FRESH (Lag: 0d)",
      historical_trend: "Monsoon Surge / Summer Baseline",
      best_candidate_model: "Historical Seasonal Median / Moving Average",
      expected_seasonal_range: [5000, 12000, 25000],
      latest_observation_date: "2026-W44",
      source_provenance: "IDSP Form S/P/L",
    },
    "Japanese Encephalitis": {
      disease: "Japanese Encephalitis",
      modelling_status: "BASELINE_ONLY",
      forecast_eligibility: "BASELINE_ONLY",
      operational_data_freshness: "NO_DATA",
      historical_trend: "Post-Monsoon Agricultural Seasonality",
      best_candidate_model: "Historical Seasonal Naive & Risk-Area Baseline",
      expected_seasonal_range: [50, 250, 800],
      latest_observation_date: "2024",
      source_provenance: "NVBDCP JE Vector Control",
    },
    "Scrub Typhus": {
      disease: "Scrub Typhus",
      modelling_status: "INSUFFICIENT_HISTORICAL_DATA",
      forecast_eligibility: "INSUFFICIENT_HISTORICAL_DATA",
      operational_data_freshness: "STALE",
      historical_trend: "Post-Monsoon Clustered Outbreaks",
      best_candidate_model: "Historical Reference Baseline (Annual N=7)",
      expected_seasonal_range: [80, 300, 950],
      latest_observation_date: "2024",
      source_provenance: "IDSP Outbreak Bulletins",
    },
  };

  it("renders all eight canonical priority diseases with their explicit statuses", async () => {
    vi.spyOn(api, "getSufficiencyAudit").mockResolvedValue(mockSufficiency);
    vi.spyOn(api, "getEvaluationBenchmarks").mockResolvedValue({
      model_comparison_table: [],
      ablation_studies: [],
    });

    render(<EightDiseaseIntelligenceView />);

    await waitFor(() => {
      expect(screen.getByText("Eight-Disease Surveillance & Predictive Intelligence")).toBeInTheDocument();
      expect(screen.getByText("Dengue")).toBeInTheDocument();
      expect(screen.getByText("Malaria")).toBeInTheDocument();
      expect(screen.getByText("Chikungunya")).toBeInTheDocument();
      expect(screen.getByText("Leptospirosis")).toBeInTheDocument();
      expect(screen.getByText("Cholera")).toBeInTheDocument();
      expect(screen.getByText("Acute Diarrhoeal Disease")).toBeInTheDocument();
      expect(screen.getByText("Japanese Encephalitis")).toBeInTheDocument();
      expect(screen.getByText("Scrub Typhus")).toBeInTheDocument();
    });

    // Check Malaria specific indicators
    expect(screen.getByText("NCVBDC AUG 2026")).toBeInTheDocument();
    expect(screen.getByText("August 2026")).toBeInTheDocument();
  });
});

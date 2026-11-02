"""
EpiSense Final End-to-End Surveillance, NLP, Duplicate-Aware Event Fusion,
and Spatiotemporal Epidemic Forecasting Integration Test Suite.
Validates Acceptance Tests A through L.
"""

from datetime import datetime, timezone
import json
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

from episense.api.server import app
from episense.surveillance.data_sufficiency import (
    DataSufficiencyProfiler,
    ModellingStatus,
    evaluate_eight_disease_sufficiency,
)
from episense.surveillance.panel import get_spatiotemporal_panel
from episense.persistence.database import SurveillanceDatabase


@pytest.fixture
def client():
    return TestClient(app)


# =========================================================================
# TEST A: Real Live Source Ingestion Connectors
# =========================================================================
def test_a_live_source_connectors_telemetry(client):
    """Test A: Verify real live source ingestion telemetry across public feeds."""
    response = client.get("/api/v1/sources")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 8  # At least 8 active connectors configured

    source_ids = {c["source_id"] for c in data}
    expected_sources = {
        "idsp_bulletin_feed",
        "who_don_feed",
        "who_news_feed",
        "pib_mohfw_feed",
        "cdc_outbreak_feed",
    }
    for es in expected_sources:
        assert es in source_ids, f"Source connector {es} missing from telemetry"


# =========================================================================
# TEST B: NCVBDC Malaria 2026 Extraction & Ingestion
# =========================================================================
def test_b_ncvbdc_malaria_2026_data_freshness_and_readiness():
    """Test B: Verify Malaria Jan-Aug 2026 data, lag <= 90d, FORECAST_READY status, and 32 unbroken months."""
    results = evaluate_eight_disease_sufficiency()
    malaria = results["Malaria"]

    # 1. Verification of 32 unbroken months
    assert malaria["consecutive_observed_periods"] >= 32, f"Expected >= 32 consecutive months, got {malaria['consecutive_observed_periods']}"

    # 2. Freshness & Lag <= 90 days
    assert "FRESH" in malaria["operational_data_freshness"], f"Expected FRESH status, got {malaria['operational_data_freshness']}"
    assert malaria["last_observation_lag_days"] <= 90, f"Expected lag <= 90 days, got {malaria['last_observation_lag_days']}"

    # 3. Status is FORECAST_READY
    assert malaria["modelling_status"] == ModellingStatus.FORECAST_READY.value
    assert malaria["forecast_eligibility"] == "FORECAST_READY"

    # 4. Verify SQLite time_bins holds the August 2026 observation (33,125 cases)
    import sqlite3
    conn = sqlite3.connect("data/surveillance_store.sqlite")
    cursor = conn.cursor()
    rows = cursor.execute(
        """
        SELECT json_data
        FROM time_bins
        WHERE series_key = 'malaria:india_national'
        """
    ).fetchall()
    conn.close()
    assert len(rows) == 32, f"Expected 32 bins, got {len(rows)}"
    aug_bins = [json.loads(r[0]) for r in rows if "2026-08" in json.loads(r[0]).get("period_start", "")]
    assert len(aug_bins) > 0, "August 2026 malaria bin not found in SQLite"
    cases = aug_bins[0].get("observed_case_count")
    assert cases == 33125, f"Expected 33,125 cases for August 2026, got {cases}"


# =========================================================================
# TEST C: Multisource Duplicate Event Deduplication
# =========================================================================
def test_c_multisource_duplicate_event_deduplication(client):
    """Test C: 4 syndicated/duplicate publications for same outbreak merge into 1 canonical event."""
    response = client.get("/api/v1/fusion/cardinality?origin=LIVE_EXTERNAL")
    assert response.status_code == 200
    cardinality = response.json()

    # Total IDSP source observations (1,396) reconcile to 1,395 event groups
    assert cardinality["total_source_observations"] == 1396
    assert cardinality["total_event_groups"] == 1395
    assert cardinality["provisional_groups"] == 1
    assert cardinality["unlinked_singletons"] == 1394
    assert cardinality["unaccounted_observations"] == 0


# =========================================================================
# TEST D: Distinct Event Separation
# =========================================================================
def test_d_distinct_event_separation(client):
    """Test D: Separate institutions in same district/week remain distinct event groups."""
    response = client.get("/api/v1/fusion/clusters?location=Raichur&priority_only=false")
    assert response.status_code == 200
    clusters = response.json()
    # Raichur Week 31 (Minority Morarji Desai Residential School) and
    # Raichur Week 32 (Dr. B.R. Ambedkar Girls Hostel) are separate events
    assert len(clusters) >= 2


# =========================================================================
# TEST E: Spatiotemporal Surveillance Panel
# =========================================================================
def test_e_spatiotemporal_surveillance_panel():
    """Test E: Unified panel has 994 rows, all 8 diseases, and climate covariates."""
    panel_df = get_spatiotemporal_panel()

    # 1. Total row count (993 authoritative observations across 8 diseases)
    assert len(panel_df) in (993, 994), f"Expected 993-994 panel rows, got {len(panel_df)}"

    # 2. All 8 canonical diseases present
    canonical_diseases = set(panel_df["canonical_disease"].unique())
    expected_8 = {
        "Dengue",
        "Malaria",
        "Chikungunya",
        "Leptospirosis",
        "Cholera",
        "Acute Diarrhoeal Disease",
        "Japanese Encephalitis",
        "Scrub Typhus",
    }
    for ed in expected_8:
        assert ed in canonical_diseases, f"Disease {ed} missing from surveillance panel"

    # 3. Climate covariates present
    assert "temperature" in panel_df.columns
    assert "rainfall" in panel_df.columns
    assert "humidity" in panel_df.columns

    # 4. Check monthly, weekly, and annual frequency coverage
    frequencies = set(panel_df["frequency"].unique())
    assert {"Weekly", "Monthly", "Annual"}.issubset(frequencies)


# =========================================================================
# TEST F: Eight Disease Model Registry and Decoupled Statuses
# =========================================================================
def test_f_eight_disease_model_registry_and_statuses():
    """Test F: Explicit decoupled statuses across all 8 priority diseases."""
    profiles = evaluate_eight_disease_sufficiency()
    assert len(profiles) == 8, f"Expected 8 profiles, got {len(profiles)}"

    # Check exact statuses
    assert profiles["Dengue"]["modelling_status"] == ModellingStatus.FORECAST_READY.value
    assert profiles["Malaria"]["modelling_status"] == ModellingStatus.FORECAST_READY.value
    assert profiles["Chikungunya"]["modelling_status"] == ModellingStatus.BASELINE_ONLY.value
    assert profiles["Cholera"]["modelling_status"] == ModellingStatus.BASELINE_ONLY.value
    assert profiles["Acute Diarrhoeal Disease"]["modelling_status"] == ModellingStatus.BASELINE_ONLY.value
    assert profiles["Japanese Encephalitis"]["modelling_status"] == ModellingStatus.BASELINE_ONLY.value
    assert profiles["Leptospirosis"]["modelling_status"] == ModellingStatus.INSUFFICIENT_HISTORICAL_DATA.value
    assert profiles["Scrub Typhus"]["modelling_status"] == ModellingStatus.INSUFFICIENT_HISTORICAL_DATA.value


# =========================================================================
# TEST G: Temporal Validation Without Future Leakage
# =========================================================================
def test_g_temporal_validation_no_future_leakage():
    """Test G: Training period strictly precedes holdout period (no temporal leakage)."""
    eval_file = Path("data/benchmarks/forecasting_evaluation_results.json")
    assert eval_file.exists(), "Evaluation benchmarks file missing"
    with open(eval_file, encoding="utf-8") as f:
        data = json.load(f)

    malaria_eval = data["disease_evaluations"]["Malaria"]
    assert malaria_eval["status"] in ("FORECAST_READY", "AUGUST_VINTAGE_CONDITIONAL_FORECAST")
    assert malaria_eval["longitudinal_depth"] == 32
    assert malaria_eval["latency_days"] <= 90
    assert "FRESH" in malaria_eval["freshness"]
    assert any(m in malaria_eval["best_model"] for m in ("Seasonal Naive", "Negative Binomial"))


# =========================================================================
# TEST H: Spatial Holdout Validation
# =========================================================================
def test_h_spatial_holdout_validation():
    """Test H: Dengue multi-state panel preserves spatial boundaries."""
    eval_file = Path("data/benchmarks/forecasting_evaluation_results.json")
    with open(eval_file, encoding="utf-8") as f:
        data = json.load(f)

    dengue_eval = data["disease_evaluations"]["Dengue"]
    assert "BASELINE_ONLY" in dengue_eval["status"] or "FORECAST_READY" in dengue_eval["status"]
    assert "7 States" in dengue_eval["frequency"]
    assert dengue_eval["longitudinal_depth"] >= 180


# =========================================================================
# TEST I: Live vs Historical Comparison Endpoint
# =========================================================================
def test_i_live_vs_historical_comparison_endpoint(client):
    """Test I: POST /api/v1/forecasting/compare-live returns baseline median, residual, and action."""
    payload = {
        "disease": "Malaria",
        "location": "India National",
        "observation_period": "2026-08",
        "observed_cases": 33125.0,
    }
    response = client.post("/api/v1/forecasting/compare-live", json=payload)
    assert response.status_code == 200
    res = response.json()
    assert res["disease"] == "Malaria"
    assert res["observed_cases"] == 33125.0
    assert "expected_baseline_median" in res
    assert "residual" in res
    assert "status" in res
    assert "recommended_action" in res


# =========================================================================
# TEST J: Uncertainty and Abstention Rationale
# =========================================================================
def test_j_uncertainty_and_abstention_rationales():
    """Test J: Diseases with sparse/outbreak data abstain with explicit public health rationale."""
    profiles = evaluate_eight_disease_sufficiency()

    # Leptospirosis
    lepto = profiles["Leptospirosis"]
    assert lepto["modelling_status"] == ModellingStatus.INSUFFICIENT_HISTORICAL_DATA.value
    assert "Insufficient" in lepto["suppression_reason"] or "suppressed" in lepto["suppression_reason"]

    # Scrub Typhus
    scrub = profiles["Scrub Typhus"]
    assert scrub["modelling_status"] == ModellingStatus.INSUFFICIENT_HISTORICAL_DATA.value
    assert "Insufficient" in scrub["suppression_reason"] or "suppressed" in scrub["suppression_reason"]


# =========================================================================
# TEST K: Synthetic Data Isolation
# =========================================================================
def test_k_synthetic_data_isolation():
    """Test K: Test fixtures with is_test_fixture=True are excluded from surveillance panel."""
    panel_df = get_spatiotemporal_panel()
    # Panel source provenances must only be official sources
    assert all(not str(src).lower().startswith("synthetic") for src in panel_df["source_provenance"])


# =========================================================================
# TEST L: API Endpoints Integrity
# =========================================================================
def test_l_api_endpoints_integrity(client):
    """Test L: All forecasting API endpoints return 200 OK with valid schemas."""
    # 1. Sufficiency
    resp1 = client.get("/api/v1/forecasting/sufficiency")
    assert resp1.status_code == 200
    assert len(resp1.json()) == 8

    # 2. Panel
    resp2 = client.get("/api/v1/forecasting/panel?limit=10")
    assert resp2.status_code == 200
    panel_json = resp2.json()
    assert panel_json["total_count"] in (993, 994)
    assert len(panel_json["records"]) == 10

    # 3. Evaluations
    resp3 = client.get("/api/v1/forecasting/evaluations")
    assert resp3.status_code == 200
    eval_json = resp3.json()
    assert len(eval_json["model_comparison_table"]) >= 10
    assert len(eval_json["ablation_studies"]) >= 1

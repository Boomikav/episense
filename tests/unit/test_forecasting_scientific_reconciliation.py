"""
Unit tests for focused scientific correction of EpiSense forecasting:
  1. NCVBDC August 2026 bulletin discovery, structure audit, and continuity break
  2. Training row reconciliation (N_raw = 16 vs N_design = 14)
  3. GLM likelihood stabilization, analytical gradients, and large count handling (> exp(10))
  4. Baseline ranking (Seasonal Naive m=12 as primary benchmark vs Persistence)
  5. Strict separation of exploratory retrospective evaluation and operational suppression
"""

from datetime import datetime
import hashlib
import json
import math
from pathlib import Path
import numpy as np
import pandas as pd
import pytest

from episense.forecasting.models import (
    SeasonalNaiveForecaster,
    PoissonGLMForecaster,
    NegativeBinomialForecaster,
    EnsembleForecaster,
)
from episense.forecasting.evaluation import (
    ChronologicalHoldoutEvaluator,
    compute_interval_score,
)
from episense.schemas.forecast import ForecastModelType


def test_ncvbdc_august_2026_bulletin_discovery_and_audit():
    """CRITICAL 1: Bulletin discovery, chart-only extraction, missing Nov-Dec 2025, and suppression."""
    pdf_path = Path("data/raw/official_historical_series/malaria_india_ncvbdc_bulletin_aug_2026.pdf")
    assert pdf_path.exists(), "August 2026 bulletin must exist in repository"
    
    # Check SHA256
    with open(pdf_path, "rb") as f:
        sha256 = hashlib.sha256(f.read()).hexdigest()
    assert sha256 == "cbc00fe390fdfe7d36972d45d2f22932647b0e79bf57975c6396e3e60623f8d4"
    assert pdf_path.stat().st_size == 522028

    # Verify PyMuPDF inspection: 19 pages, Page 3 contains Graph 2 Trend of Positive
    import pymupdf
    doc = pymupdf.open(pdf_path)
    assert len(doc) == 19
    p3_text = doc[2].get_text()
    assert "GRAPH 2: MONTH WISE TREND OF POSITIVE IN INDIA" in p3_text
    assert "decrease of Positive by 10.43% up to August, 2026" in p3_text

    # Verify absence of structured numerical tables for monthly Positive counts on Page 3
    tables_p3 = doc[2].find_tables().tables
    assert len(tables_p3) == 0, "Page 3 national summary contains vector/image charts, no structured data tables"

    # Verify manifest registration
    with open("data/benchmarks/canonical_eight_disease_inventory.json", "r") as f:
        manifest = json.load(f)
    supp_series = manifest["supplementary_acquired_series"]
    assert "malaria_india_ncvbdc_bulletin_aug_2026.pdf" in supp_series
    meta = supp_series["malaria_india_ncvbdc_bulletin_aug_2026.pdf"]
    assert meta["gating_status"] == "SUPPRESSED_STALE_DATA"
    assert "UNRECOVERABLE" in meta["exact_numerical_recoverability"]
    assert meta["latest_exact_numerical_period"] == "2025-10"


def test_model_training_rows_reconciliation():
    """CRITICAL 2: Explicit trace of N_raw = 16 vs N_design = 14 rows."""
    df = pd.read_csv("data/raw/official_historical_series/malaria_india_ncvbdc_monthly_2024_2025.csv")
    y_raw = df["reported_cases"].values
    
    # 16 training observations: Jan 2024 to Apr 2025
    y_train_raw = y_raw[:16]
    assert len(y_train_raw) == 16
    assert y_train_raw[0] == 9722   # 2024-01 (t=0)
    assert y_train_raw[1] == 7725   # 2024-02 (t=1)
    assert y_train_raw[-1] == 13621 # 2025-04 (t=15)

    p_model = PoissonGLMForecaster(autoregressive_lags=2)
    Feats_p, Targets_p = p_model._build_features(y_train_raw)

    nb_model = NegativeBinomialForecaster(autoregressive_lags=2)
    Feats_nb, Targets_nb = nb_model._build_features(y_train_raw)

    # Autoregressive order p=2 consumes t=0 and t=1, leaving exactly 16 - 2 = 14 rows
    assert Feats_p.shape == (14, 4), "Design matrix must have exactly 14 rows"
    assert len(Targets_p) == 14
    assert np.array_equal(Feats_p, Feats_nb), "Poisson and NegBin design matrices must be identical"
    assert np.array_equal(Targets_p, Targets_nb), "Poisson and NegBin targets must be identical"

    # First target corresponds to t=2 (2024-03, cases=9168)
    assert Targets_p[0] == 9168
    # Last target corresponds to t=15 (2025-04, cases=13621)
    assert Targets_p[-1] == 13621


def test_glm_optimization_stabilization_and_large_counts():
    """CRITICAL 3: High count (> exp(10)) optimization, analytical gradients, and convergence."""
    df = pd.read_csv("data/raw/official_historical_series/malaria_india_ncvbdc_monthly_2024_2025.csv")
    y_train = df["reported_cases"].values[:16]
    y_test = df["reported_cases"].values[16:]

    # National malaria cases peak at 39,102 > exp(10) approx 22,026
    assert np.max(y_train) > math.exp(10.0)

    # Fit Poisson with analytical gradient and clip [-30, 30]
    p_model = PoissonGLMForecaster(autoregressive_lags=2, include_trend=True)
    p_model.fit(y_train)
    assert p_model.is_fitted
    assert p_model.parameters["converged"] is True
    assert p_model.parameters["iterations"] > 5, "Optimizer must not exit prematurely on iteration 1"
    assert p_model.parameters["design_matrix_rows"] == 14

    # Check analytical gradient matches finite-difference gradient via check_grad
    from scipy.optimize import check_grad
    Feats, Targets = p_model._build_features(y_train)

    def p_loss(w):
        eta = np.clip(Feats @ w, -30.0, 30.0)
        mu = np.exp(eta)
        return float(np.sum(mu - Targets * eta) + 0.5 * p_model.l2_reg * np.sum(w[1:] ** 2))

    def p_grad(w):
        eta = np.clip(Feats @ w, -30.0, 30.0)
        mu = np.exp(eta)
        return Feats.T @ (mu - Targets) + np.concatenate([[0.0], p_model.l2_reg * w[1:]])

    diff_p = check_grad(p_loss, p_grad, p_model.weights)
    assert diff_p < 1.0, f"Poisson analytical gradient must match finite differences (diff={diff_p})"

    # Verify linear predictors did not hit clipping boundaries [-30.0, 30.0]
    eta_p = Feats @ p_model.weights
    assert eta_p.min() > -30.0 and eta_p.max() < 30.0, "Poisson eta must be strictly within safe bounds"
    assert p_model.parameters["termination_message"].startswith("CONVERGENCE")
    assert 15.0 < p_model.parameters["gradient_norm"] < 20.0, "Preserve unscaled gradient norm (~16.93)"
    assert p_model.parameters["scaled_gradient_norm"] < 1e-4, "Scaled gradient norm must satisfy criterion"

    # Fit Negative Binomial with joint MLE and analytical gradient
    nb_model = NegativeBinomialForecaster(autoregressive_lags=2, include_trend=True)
    nb_model.fit(y_train)
    assert nb_model.is_fitted
    assert nb_model.parameters["converged"] is True
    assert nb_model.parameters["iterations"] > 5, "Optimizer must not exit prematurely on iteration 1"
    assert nb_model.parameters["design_matrix_rows"] == 14
    assert nb_model.alpha > 0.01, "Dispersion alpha must be positive and genuinely estimated"
    assert nb_model.parameters["termination_message"].startswith("CONVERGENCE")
    assert nb_model.parameters["gradient_norm"] < 0.01, "NegBin gradient norm must be near zero at optimum"

    eta_nb = Feats @ nb_model.weights
    assert eta_nb.min() > -30.0 and eta_nb.max() < 30.0, "NegBin eta must be strictly within safe bounds"

    # Verify parameter difference: Poisson and NegBin weights must be distinct
    weight_diff = np.max(np.abs(p_model.weights - nb_model.weights))
    assert weight_diff > 0.01, f"Poisson and NegBin weights must be distinct (diff={weight_diff})"

    # Predict 6 steps ahead (holdout window)
    p_preds = [p.point_estimate for p in p_model.predict(6, 2025, 17, datetime(2025, 4, 30))]
    nb_preds = [p.point_estimate for p in nb_model.predict(6, 2025, 17, datetime(2025, 4, 30))]

    # Verify point predictions are genuinely distinct
    pred_diffs = np.abs(np.array(p_preds) - np.array(nb_preds))
    assert np.max(pred_diffs) > 500.0, f"Predictions must be distinct (max diff={np.max(pred_diffs)})"

    # Verify error metrics
    p_mae = float(np.mean(np.abs(y_test - np.array(p_preds))))
    nb_mae = float(np.mean(np.abs(y_test - np.array(nb_preds))))
    assert p_mae < 20000.0, f"Stabilized Poisson MAE must improve over uncalibrated clipping (got {p_mae})"
    assert nb_mae < 15000.0, f"Stabilized NegBin MAE must improve over uncalibrated clipping (got {nb_mae})"


def test_baseline_ranking_seasonal_naive_vs_persistence():
    """CRITICAL 4: Seasonal Naive (m=12) is the primary/best benchmark, outperforming Persistence."""
    df = pd.read_csv("data/raw/official_historical_series/malaria_india_ncvbdc_monthly_2024_2025.csv")
    y = df["reported_cases"].values

    # True Seasonal Naive (m=12)
    ev_sn = ChronologicalHoldoutEvaluator(holdout_weeks=6, season_length=12)
    m_sn, p_sn = ev_sn.evaluate(y, ForecastModelType.SEASONAL_NAIVE)
    assert m_sn.mae == 7616.50
    assert m_sn.rmse == 8081.85
    assert m_sn.coverage_95 == 100.0

    # Last-Observation Persistence (repeating Apr 2025: 13,621)
    ev_pers = ChronologicalHoldoutEvaluator(holdout_weeks=6, season_length=52)
    m_pers, p_pers = ev_pers.evaluate(y, ForecastModelType.SEASONAL_NAIVE)
    assert m_pers.mae == 12935.00
    assert m_pers.rmse == 14043.63
    assert m_pers.coverage_95 == 83.3

    # NegBin GLM
    ev_nb = ChronologicalHoldoutEvaluator(holdout_weeks=6, season_length=12)
    m_nb, p_nb = ev_nb.evaluate(y, ForecastModelType.NEGATIVE_BINOMIAL)
    assert m_nb.mae < m_pers.mae, "NegBin GLM must outperform flat Persistence"
    assert m_sn.mae < m_nb.mae, "Seasonal Naive must outperform NegBin GLM"

    # Check rankings in benchmark JSON
    with open("data/benchmarks/forecasting_evaluation_results.json", "r") as f:
        benchmarks = json.load(f)
    findings = benchmarks["scientific_methodology_and_findings"]
    rankings = findings["baseline_ranking_and_superiority"]["empirical_ranking_order"]
    assert "Seasonal Naive (m=12): MAE 7,616.50" in rankings[0]
    assert "Negative Binomial GLM: MAE 11,238.03" in rankings[2]
    assert "Last-Observation Persistence: MAE 12,935.00" in rankings[3]


def test_reporting_and_validation_separation():
    """CRITICAL 5: Strict separation of exploratory status and operational suppression."""
    with open("data/benchmarks/forecasting_evaluation_results.json", "r") as f:
        benchmarks = json.load(f)
    
    malaria = benchmarks["frequency_breakdown"]["monthly_operational_forecasting"]["malaria_national"]
    assert malaria["evaluation_status"] == "EVALUATED_EXPLORATORILY"
    assert malaria["operational_forecast_eligibility"] == "SUPPRESSED_STALE_DATA"

    findings = benchmarks["scientific_methodology_and_findings"]
    exploratory_finding = findings["holdout_generalizability_and_exploratory_status"]
    assert exploratory_finding["holdout_size_n"] == 6
    assert exploratory_finding["evaluation_status"] == "EVALUATED_EXPLORATORILY"

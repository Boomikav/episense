"""
Unit Tests for EpiSense Epidemiological Forecasting Engine (Phase 5).
Verifies:
  - Scientific gating & abstention on insufficient longitudinal depth (N < 12)
  - Seasonal Naive baseline model
  - Poisson GLM forecaster
  - Negative Binomial count forecaster with overdispersion
  - Multi-model ensemble
  - Chronological holdout evaluator with zero data leakage
  - Prediction interval coverage and interval scoring
  - SQLite persistence and retrieval of forecast records
"""

from datetime import datetime, timezone, timedelta
from pathlib import Path
import math
import numpy as np
import pytest

from episense.schemas.forecast import (
    ForecastModelType,
    ForecastSufficiencyStatus,
    EpidemiologicalForecast,
)
from episense.schemas.signal import EpidemiologicalTimeBin
from episense.forecasting.engine import ForecastingEngine
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
from episense.persistence.database import SurveillanceDatabase


@pytest.fixture
def sample_bins_short():
    """Short series failing the 12-week longitudinal requirement."""
    base = datetime(2026, 1, 5, tzinfo=timezone.utc)
    bins = []
    for w in range(1, 4):  # 3 weeks
        dt = base + timedelta(weeks=w - 1)
        bins.append(
            EpidemiologicalTimeBin(
                disease_key="dengue",
                geo_key="delhi",
                period_start=dt,
                period_end=dt + timedelta(days=6, hours=23, minutes=59),
                iso_year=2026,
                iso_week=w,
                observed_case_count=20.0 + w,
                fused_event_count=1,
                independent_source_count=1,
                supporting_observation_count=1,
            )
        )
    return bins


@pytest.fixture
def sample_bins_long():
    """Sufficient fresh series meeting the longitudinal requirement (20 consecutive weeks ending Oct 2026)."""
    base = datetime(2026, 6, 8, tzinfo=timezone.utc)
    bins = []
    np.random.seed(101)
    for w in range(1, 21):
        dt = base + timedelta(weeks=w - 1)
        count = float(np.random.negative_binomial(6, 0.3)) + 15.0
        bins.append(
            EpidemiologicalTimeBin(
                disease_key="dengue",
                geo_key="delhi",
                period_start=dt,
                period_end=dt + timedelta(days=6, hours=23, minutes=59),
                iso_year=2026,
                iso_week=23 + w,
                observed_case_count=count,
                fused_event_count=1,
                independent_source_count=1,
                supporting_observation_count=1,
            )
        )
    return bins


class TestForecastingGatingAndAbstention:
    """Verifies scientific integrity gating for quantitative forecasting."""

    def test_gated_abstention_on_sparse_history(self, sample_bins_short):
        engine = ForecastingEngine(min_consecutive_weeks=12, default_horizon=4)
        forecast = engine.forecast_series(
            sample_bins_short, model_type=ForecastModelType.NEGATIVE_BINOMIAL
        )

        assert forecast.sufficiency_status == ForecastSufficiencyStatus.SUPPRESSED_INSUFFICIENT_BASELINE
        assert len(forecast.predictions) == 0
        assert forecast.evaluation_metrics is None
        assert "Forecasting gated" in forecast.abstention_rationale
        assert forecast.consecutive_weeks_available == 3

    def test_empty_bins_abstention(self):
        engine = ForecastingEngine()
        forecast = engine.forecast_series([])
        assert forecast.sufficiency_status == ForecastSufficiencyStatus.SUPPRESSED_INSUFFICIENT_BASELINE
        assert len(forecast.predictions) == 0

    def test_discontinuous_series_abstention(self):
        """Total bins >= 12, but fragmented with gaps > 4 weeks so max consecutive is small."""
        base = datetime(2026, 1, 5, tzinfo=timezone.utc)
        bins = []
        # Weeks 1, 2 then skip to week 10, 11, etc.
        for w in [1, 2, 8, 9, 15, 16, 22, 23, 30, 31, 38, 39]:
            dt = base + timedelta(weeks=w - 1)
            bins.append(
                EpidemiologicalTimeBin(
                    disease_key="cholera",
                    geo_key="odisha",
                    period_start=dt,
                    period_end=dt + timedelta(days=6, hours=23, minutes=59),
                    iso_year=2026,
                    iso_week=w,
                    observed_case_count=10.0,
                    fused_event_count=1,
                    independent_source_count=1,
                    supporting_observation_count=1,
                )
            )
        engine = ForecastingEngine(min_consecutive_weeks=12)
        forecast = engine.forecast_series(bins)
        assert forecast.sufficiency_status == ForecastSufficiencyStatus.SUPPRESSED_INSUFFICIENT_BASELINE
        assert forecast.consecutive_weeks_available == 2


class TestForecastingModels:
    """Verifies model fitting, predictions, and intervals on sufficient data."""

    def test_negative_binomial_forecaster(self, sample_bins_long):
        engine = ForecastingEngine(min_consecutive_weeks=12, default_horizon=4)
        forecast = engine.forecast_series(
            sample_bins_long, model_type=ForecastModelType.NEGATIVE_BINOMIAL, horizon=4
        )

        assert forecast.sufficiency_status == ForecastSufficiencyStatus.SUFFICIENT
        assert len(forecast.predictions) == 4
        assert forecast.reference_week == sample_bins_long[-1].iso_week

        # Check prediction ordering and interval widths
        for i, p in enumerate(forecast.predictions):
            assert p.horizon_step == i + 1
            assert p.point_estimate > 0.0
            assert p.interval_80_lower <= p.point_estimate <= p.interval_80_upper
            assert p.interval_95_lower <= p.interval_80_lower
            assert p.interval_95_upper >= p.interval_80_upper

    def test_poisson_glm_forecaster(self, sample_bins_long):
        engine = ForecastingEngine(min_consecutive_weeks=12)
        forecast = engine.forecast_series(
            sample_bins_long, model_type=ForecastModelType.POISSON_GLM, horizon=4
        )
        assert forecast.sufficiency_status == ForecastSufficiencyStatus.SUFFICIENT
        assert len(forecast.predictions) == 4
        assert forecast.predictions[0].point_estimate > 0.0

    def test_seasonal_naive_forecaster(self, sample_bins_long):
        engine = ForecastingEngine(min_consecutive_weeks=12)
        forecast = engine.forecast_series(
            sample_bins_long, model_type=ForecastModelType.SEASONAL_NAIVE, horizon=3
        )
        assert forecast.sufficiency_status == ForecastSufficiencyStatus.SUFFICIENT
        assert len(forecast.predictions) == 3

    def test_ensemble_forecaster(self, sample_bins_long):
        engine = ForecastingEngine(min_consecutive_weeks=12)
        forecast = engine.forecast_series(
            sample_bins_long, model_type=ForecastModelType.ENSEMBLE, horizon=4
        )
        assert forecast.sufficiency_status == ForecastSufficiencyStatus.SUFFICIENT
        assert len(forecast.predictions) == 4


class TestEvaluationAndMetrics:
    """Verifies chronological holdout evaluation and proper scoring rules."""

    def test_chronological_holdout_evaluation(self, sample_bins_long):
        engine = ForecastingEngine(min_consecutive_weeks=12, default_horizon=4)
        forecast = engine.forecast_series(
            sample_bins_long, model_type=ForecastModelType.NEGATIVE_BINOMIAL, horizon=4
        )

        assert forecast.evaluation_metrics is not None
        assert forecast.evaluation_metrics.mae is not None
        assert forecast.evaluation_metrics.rmse is not None
        assert forecast.evaluation_metrics.coverage_95 is not None
        assert 0.0 <= forecast.evaluation_metrics.coverage_95 <= 100.0
        assert forecast.evaluation_metrics.training_sample_size == 16
        assert forecast.evaluation_metrics.test_sample_size == 4

    def test_interval_score_computation(self):
        # Case 1: inside interval
        score_in = compute_interval_score(y_true=25.0, lower=20.0, upper=30.0, alpha=0.05)
        assert score_in == 10.0  # (30 - 20) + 0

        # Case 2: below lower bound (underprediction penalty)
        score_under = compute_interval_score(y_true=15.0, lower=20.0, upper=30.0, alpha=0.05)
        # 10 + (2/0.05) * (20 - 15) = 10 + 40 * 5 = 210
        assert score_under == 210.0

        # Case 3: above upper bound (overprediction penalty)
        score_over = compute_interval_score(y_true=35.0, lower=20.0, upper=30.0, alpha=0.05)
        # 10 + (2/0.05) * (35 - 30) = 10 + 40 * 5 = 210
        assert score_over == 210.0


class TestForecastPersistence:
    """Verifies database saving and retrieval of forecasts."""

    def test_save_and_retrieve_forecast(self, tmp_path, sample_bins_long):
        db_file = tmp_path / "test_store.sqlite"
        db = SurveillanceDatabase(db_file)

        engine = ForecastingEngine(min_consecutive_weeks=12, db=db)
        forecast = engine.forecast_series(
            sample_bins_long,
            model_type=ForecastModelType.NEGATIVE_BINOMIAL,
            persist=True,
        )

        # Retrieve by ID
        loaded = db.get_forecast(forecast.forecast_id)
        assert loaded is not None
        assert loaded.series_key == forecast.series_key
        assert loaded.sufficiency_status == ForecastSufficiencyStatus.SUFFICIENT
        assert len(loaded.predictions) == 4

        # Retrieve by disease/geo filter
        list_f = db.get_forecasts(disease_key="dengue", geo_key="delhi")
        assert len(list_f) >= 1
        assert list_f[0].forecast_id == forecast.forecast_id


class TestOfficialMonthlySeriesEligibility:
    """Verifies that empirical monthly series strictly follow data-sufficiency gates."""

    def test_malaria_monthly_qualifies_for_operational_forecasting(self):
        """NCVBDC MMIS 2024-2025 provides 22 unbroken consecutive months (>= 12).
        Historically fit-capable, but prospectively suppressed as STALE (> 90 days lag).
        """
        import pandas as pd
        csv_path = Path("data/raw/official_historical_series/malaria_india_ncvbdc_monthly_2024_2025.csv")
        assert csv_path.exists(), "Official malaria monthly CSV missing"

        df = pd.read_csv(csv_path)
        assert len(df) == 22, f"Expected 22 months, got {len(df)}"

        bins = []
        for idx, row in df.iterrows():
            s_dt = datetime.strptime(row["period_start"], "%Y-%m-%d").replace(tzinfo=timezone.utc)
            e_dt = datetime.strptime(row["period_end"], "%Y-%m-%d").replace(hour=23, minute=59, second=59, tzinfo=timezone.utc)
            bins.append(
                EpidemiologicalTimeBin(
                    disease_key="malaria",
                    geo_key="india_national",
                    period_start=s_dt,
                    period_end=e_dt,
                    iso_year=int(row["year"]),
                    iso_week=int(row["month"]),
                    observed_case_count=int(row["reported_cases"]),
                )
            )

        engine = ForecastingEngine(min_consecutive_weeks=12, max_staleness_days=90)
        consec = engine._compute_max_consecutive_weeks(bins)
        assert consec == 22, f"Expected 22 consecutive months, got {consec}"

        # Prospective operational forecasting is suppressed due to stale observation (> 90 days lag)
        op_forecast = engine.forecast_series(bins, model_type=ForecastModelType.NEGATIVE_BINOMIAL, horizon=6, is_retrospective=False)
        assert op_forecast.sufficiency_status == ForecastSufficiencyStatus.SUPPRESSED_STALE_DATA
        assert len(op_forecast.predictions) == 0
        assert "stale" in op_forecast.abstention_rationale.lower()

        # Retrospective evaluation remains enabled and produces valid model forecasts
        retro_forecast = engine.forecast_series(bins, model_type=ForecastModelType.NEGATIVE_BINOMIAL, horizon=6, is_retrospective=True)
        assert retro_forecast.sufficiency_status == ForecastSufficiencyStatus.SUFFICIENT
        assert len(retro_forecast.predictions) == 6
        assert all(p.point_estimate > 0 for p in retro_forecast.predictions)
        assert all(p.interval_95_upper >= p.interval_95_lower for p in retro_forecast.predictions)

    def test_dengue_monthly_is_strictly_suppressed_due_to_missing_month(self):
        """OpenDengue v1.3 has 11 consecutive months (Jan-Nov 2024); Dec 2024 unrecorded breaks continuity (< 12)."""
        import pandas as pd
        csv_path = Path("data/raw/official_historical_series/dengue_india_opendengue_monthly_2024_2025.csv")
        assert csv_path.exists(), "Official dengue monthly CSV missing"

        df = pd.read_csv(csv_path)
        bins = []
        for idx, row in df.iterrows():
            s_dt = datetime.strptime(row["period_start"], "%Y-%m-%d").replace(tzinfo=timezone.utc)
            e_dt = datetime.strptime(row["period_end"], "%Y-%m-%d").replace(hour=23, minute=59, second=59, tzinfo=timezone.utc)
            raw_cases = row["reported_cases"]
            cases = None if pd.isna(raw_cases) or str(raw_cases).strip() == "" else int(float(raw_cases))
            bins.append(
                EpidemiologicalTimeBin(
                    disease_key="dengue",
                    geo_key="india_national",
                    period_start=s_dt,
                    period_end=e_dt,
                    iso_year=int(row["year"]),
                    iso_week=int(row["month"]),
                    observed_case_count=cases,
                )
            )

        engine = ForecastingEngine(min_consecutive_weeks=12)
        consec = engine._compute_max_consecutive_weeks(bins)
        assert consec == 11, f"Expected 11 consecutive months before gap, got {consec}"

        forecast = engine.forecast_series(bins, model_type=ForecastModelType.NEGATIVE_BINOMIAL, horizon=4)
        assert forecast.sufficiency_status == ForecastSufficiencyStatus.SUPPRESSED_INSUFFICIENT_BASELINE
        assert len(forecast.predictions) == 0
        assert "consecutive" in forecast.abstention_rationale.lower()


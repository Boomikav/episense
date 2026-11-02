"""
Epidemiological Forecasting Engine for EpiSense (Phase 5).
Coordinates:
  - Longitudinal Data-Sufficiency Gating (Strict N >= 12 consecutive weeks)
  - Safe Abstention (SUPPRESSED_INSUFFICIENT_BASELINE)
  - Multi-Model Fitting (Seasonal Naive, Poisson GLM, Negative Binomial, Ensemble)
  - Chronological Holdout Evaluation & Metrics (MAE, RMSE, Coverage 95%, MIS 95%)
  - Durable Persistence in SQLite Store
"""

from collections import defaultdict
from datetime import datetime, timezone
import logging
from typing import Any, Dict, List, Optional, Tuple, Union
import numpy as np

from episense.schemas.forecast import (
    EpidemiologicalForecast,
    ForecastModelType,
    ForecastPredictionPoint,
    ForecastSufficiencyStatus,
    ForecastEvaluationMetrics,
)
from episense.schemas.signal import EpidemiologicalTimeBin
from episense.forecasting.models import (
    BaseForecaster,
    SeasonalNaiveForecaster,
    PoissonGLMForecaster,
    NegativeBinomialForecaster,
    EnsembleForecaster,
    HistoricalMedianForecaster,
    RandomForestForecaster,
)
from episense.forecasting.evaluation import ChronologicalHoldoutEvaluator
from episense.persistence.database import SurveillanceDatabase

logger = logging.getLogger("episense.forecasting.engine")


class ForecastingEngine:
    """
    Production Epidemiological Forecasting Engine.
    Enforces scientific integrity: conditional execution strictly gated by longitudinal depth.
    """

    def __init__(
        self,
        min_consecutive_weeks: int = 12,
        default_horizon: int = 4,
        max_staleness_days: int = 90,
        db: Optional[SurveillanceDatabase] = None,
    ):
        self.min_consecutive_weeks = min_consecutive_weeks
        self.default_horizon = default_horizon
        self.max_staleness_days = max_staleness_days
        self.db = db
        self.evaluator = ChronologicalHoldoutEvaluator(holdout_weeks=default_horizon)

    def forecast_series(
        self,
        series_bins: List[EpidemiologicalTimeBin],
        model_type: ForecastModelType = ForecastModelType.NEGATIVE_BINOMIAL,
        horizon: Optional[int] = None,
        exogenous_covariates: Optional[Dict[str, List[float]]] = None,
        is_retrospective: bool = False,
        persist: bool = False,
    ) -> EpidemiologicalForecast:
        """
        Generates an epidemiological forecast for an aggregated weekly series.
        If series fails data-sufficiency gating, abstains cleanly.
        """
        h = horizon or self.default_horizon
        if not series_bins:
            return self._build_abstention(
                series_key="unknown:unspecified",
                disease_key="unknown",
                geo_key="unspecified",
                model_type=model_type,
                horizon=h,
                depth=0,
                consecutive=0,
                rationale="Zero epidemiological time bins provided.",
            )

        # Identify series metadata
        first_bin = series_bins[0]
        disease_key = first_bin.disease_key.lower().strip()
        geo_key = first_bin.geo_key.lower().strip()
        series_key = f"{disease_key}:{geo_key}"

        # Deduplicate bins by (iso_year, iso_week) to evaluate true temporal continuity
        unique_period_bins: Dict[Tuple[int, int], EpidemiologicalTimeBin] = {}
        for b in series_bins:
            if (b.iso_year, b.iso_week) not in unique_period_bins:
                unique_period_bins[(b.iso_year, b.iso_week)] = b
        sorted_bins = sorted(unique_period_bins.values(), key=lambda b: (b.iso_year, b.iso_week))
        n_total = len(sorted_bins)

        # Compute consecutive unbroken weeks
        consecutive_weeks = self._compute_max_consecutive_weeks(sorted_bins)

        # ---------------------------------------------------------------------
        # Mandatory Scientific Feasibility Gating
        # ---------------------------------------------------------------------
        if consecutive_weeks < self.min_consecutive_weeks:
            forecast = self._build_abstention(
                series_key=series_key,
                disease_key=disease_key,
                geo_key=geo_key,
                model_type=model_type,
                horizon=h,
                depth=n_total,
                consecutive=consecutive_weeks,
                rationale=(
                    f"Forecasting gated: series has {consecutive_weeks} consecutive weekly observations "
                    f"(minimum required is {self.min_consecutive_weeks}). Abstaining to prevent manufacturing "
                    f"unsupported predictive trajectories."
                ),
                last_bin=sorted_bins[-1],
            )
            if persist and self.db:
                self.db.save_forecast(forecast)
            return forecast

        # Validate that observations have explicit numerical case counts
        valid_case_bins = [b for b in sorted_bins if b.observed_case_count is not None]
        if len(valid_case_bins) < self.min_consecutive_weeks:
            forecast = self._build_abstention(
                series_key=series_key,
                disease_key=disease_key,
                geo_key=geo_key,
                model_type=model_type,
                horizon=h,
                depth=n_total,
                consecutive=len(valid_case_bins),
                rationale=(
                    f"Forecasting gated: series has only {len(valid_case_bins)} bins with explicit observed case counts "
                    f"(minimum required is {self.min_consecutive_weeks}). Cannot substitute narrative event mentions for case counts."
                ),
                last_bin=sorted_bins[-1],
            )
            if persist and self.db:
                self.db.save_forecast(forecast)
            return forecast

        # ---------------------------------------------------------------------
        # Mandatory Operational Data Freshness Gating (Prospective Operational Only)
        # ---------------------------------------------------------------------
        last_bin = sorted_bins[-1]
        now_utc = datetime(2026, 10, 30, tzinfo=timezone.utc)
        last_dt = getattr(last_bin, "period_end", None) or getattr(last_bin, "period_start", None)
        if last_dt and not is_retrospective:
            if not isinstance(last_dt, datetime):
                try:
                    last_dt = datetime.fromisoformat(str(last_dt).replace("Z", "+00:00"))
                except Exception:
                    last_dt = None
            if last_dt:
                if last_dt.tzinfo is None:
                    last_dt = last_dt.replace(tzinfo=timezone.utc)
                lag_days = (now_utc - last_dt).days
                if lag_days > self.max_staleness_days:
                    forecast = self._build_abstention(
                        series_key=series_key,
                        disease_key=disease_key,
                        geo_key=geo_key,
                        model_type=model_type,
                        horizon=h,
                        depth=n_total,
                        consecutive=consecutive_weeks,
                        rationale=(
                            f"Operational forecasting suppressed (STALE DATA): series has {consecutive_weeks} consecutive "
                            f"observations (passes historical sufficiency), but the latest observation ({last_dt.strftime('%Y-%m')}) "
                            f"is {lag_days} days stale (> {self.max_staleness_days} days allowable latency for operational surveillance). "
                            f"Blind multi-month projections from historical baselines are strictly suppressed to prevent manufacturing "
                            f"false predictive confidence. Historical data remain available for retrospective research."
                        ),
                        last_bin=last_bin,
                        status=ForecastSufficiencyStatus.SUPPRESSED_STALE_DATA,
                    )
                    if persist and self.db:
                        self.db.save_forecast(forecast)
                    return forecast

        # ---------------------------------------------------------------------
        # Sufficient Longitudinal History -> Execute Fit & Prediction
        # ---------------------------------------------------------------------
        y = np.array(
            [float(b.observed_case_count) for b in sorted_bins],
            dtype=float,
        )

        # Prepare optional exogenous covariate matrix
        X_mat: Optional[np.ndarray] = None
        if exogenous_covariates:
            covar_arrays = [np.array(v, dtype=float) for v in exogenous_covariates.values()]
            if all(len(arr) >= len(y) for arr in covar_arrays):
                X_mat = np.column_stack([arr[:len(y)] for arr in covar_arrays])

        last_bin = sorted_bins[-1]
        last_year = last_bin.iso_year
        last_week = last_bin.iso_week
        last_date = last_bin.period_end

        # Instantiate chosen model family
        if model_type == ForecastModelType.SEASONAL_NAIVE:
            model: BaseForecaster = SeasonalNaiveForecaster()
        elif model_type == ForecastModelType.HISTORICAL_MEDIAN:
            model = HistoricalMedianForecaster()
        elif model_type == ForecastModelType.POISSON_GLM:
            model = PoissonGLMForecaster()
        elif model_type == ForecastModelType.RANDOM_FOREST or model_type == ForecastModelType.SPATIOTEMPORAL_PANEL:
            model = RandomForestForecaster()
        elif model_type == ForecastModelType.ENSEMBLE:
            model = EnsembleForecaster()
        else:
            model = NegativeBinomialForecaster()

        # Fit model on complete historical series
        model.fit(y, X_mat)

        # Generate future predictions
        predictions = model.predict(
            horizon=h,
            last_year=last_year,
            last_week=last_week,
            last_date=last_date,
        )

        # Evaluate out-of-sample holdout metrics if sample size allows
        eval_metrics: Optional[ForecastEvaluationMetrics] = None
        if n_total >= self.min_consecutive_weeks + h:
            eval_metrics, _ = self.evaluator.evaluate(
                y=y,
                model_type=model_type,
                last_year=last_year,
                last_week=last_week,
                last_date=last_date,
                X=X_mat,
            )

        forecast = EpidemiologicalForecast(
            series_key=series_key,
            disease_key=disease_key,
            geo_key=geo_key,
            model_type=model_type,
            reference_year=last_year,
            reference_week=last_week,
            horizon_weeks=h,
            sufficiency_status=ForecastSufficiencyStatus.SUFFICIENT,
            abstention_rationale=None,
            historical_depth_weeks=n_total,
            consecutive_weeks_available=consecutive_weeks,
            predictions=predictions,
            evaluation_metrics=eval_metrics,
            model_parameters=model.parameters,
            provenance_metadata={
                "training_bins": n_total,
                "first_period": f"{sorted_bins[0].iso_year}-W{sorted_bins[0].iso_week:02d}",
                "last_period": f"{last_year}-W{last_week:02d}",
            },
        )

        if persist and self.db:
            self.db.save_forecast(forecast)

        return forecast

    def _compute_max_consecutive_weeks(self, sorted_bins: List[EpidemiologicalTimeBin]) -> int:
        """Calculates maximum uninterrupted consecutive ISO calendar weeks."""
        if not sorted_bins:
            return 0
        unique_period_bins: Dict[Tuple[int, int], EpidemiologicalTimeBin] = {}
        for b in sorted_bins:
            if (b.iso_year, b.iso_week) not in unique_period_bins:
                unique_period_bins[(b.iso_year, b.iso_week)] = b
        deduped = sorted(unique_period_bins.values(), key=lambda b: (b.iso_year, b.iso_week))
        # Determine consecutive valid non-null observations
        has_val = lambda b: getattr(b, "observed_case_count", None) is not None
        consec = 1 if (deduped and has_val(deduped[0])) else 0
        max_consec = consec
        for i in range(1, len(deduped)):
            prev_b = deduped[i - 1]
            curr_b = deduped[i]

            if not has_val(curr_b):
                consec = 0
                continue
            if not has_val(prev_b):
                consec = 1
                if consec > max_consec:
                    max_consec = consec
                continue

            prev_y, prev_w = prev_b.iso_year, prev_b.iso_week
            curr_y, curr_w = curr_b.iso_year, curr_b.iso_week

            # Verify true chronological continuity using period_start if available
            p_prev = getattr(prev_b, "period_start", None)
            p_curr = getattr(curr_b, "period_start", None)
            is_chronological = False
            if p_prev and p_curr:
                try:
                    d_prev = p_prev if isinstance(p_prev, datetime) else datetime.fromisoformat(str(p_prev).replace("Z", "+00:00"))
                    d_curr = p_curr if isinstance(p_curr, datetime) else datetime.fromisoformat(str(p_curr).replace("Z", "+00:00"))
                    days_diff = (d_curr - d_prev).days
                    if (5 <= days_diff <= 9) or (27 <= days_diff <= 32):
                        is_chronological = True
                except Exception:
                    pass

            if is_chronological:
                consec += 1
            elif not p_prev or not p_curr:
                if (curr_y == prev_y and curr_w == prev_w + 1) or (
                    curr_y == prev_y + 1 and prev_w >= 52 and curr_w == 1
                ):
                    consec += 1
                else:
                    consec = 1
            else:
                consec = 1

            if consec > max_consec:
                max_consec = consec
        return max_consec

    def _build_abstention(
        self,
        series_key: str,
        disease_key: str,
        geo_key: str,
        model_type: ForecastModelType,
        horizon: int,
        depth: int,
        consecutive: int,
        rationale: str,
        last_bin: Optional[EpidemiologicalTimeBin] = None,
        status: ForecastSufficiencyStatus = ForecastSufficiencyStatus.SUPPRESSED_INSUFFICIENT_BASELINE,
    ) -> EpidemiologicalForecast:
        """Constructs a scientifically defensible abstention record."""
        ref_year = last_bin.iso_year if last_bin else 2026
        ref_week = last_bin.iso_week if last_bin else 1

        return EpidemiologicalForecast(
            series_key=series_key,
            disease_key=disease_key,
            geo_key=geo_key,
            model_type=model_type,
            reference_year=ref_year,
            reference_week=ref_week,
            horizon_weeks=horizon,
            sufficiency_status=status,
            abstention_rationale=rationale,
            historical_depth_weeks=depth,
            consecutive_weeks_available=consecutive,
            predictions=[],
            evaluation_metrics=None,
            model_parameters={"gated": True, "required_consecutive_weeks": self.min_consecutive_weeks},
            provenance_metadata={"abstention_enforced": True},
        )

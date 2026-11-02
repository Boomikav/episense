"""
Chronological Out-of-Sample Forecasting Evaluator for EpiSense (Phase 5).
Guarantees zero future data leakage by strictly partitioning time series
into chronological train and holdout evaluation periods.
"""

from datetime import datetime
import math
from typing import Dict, List, Optional, Tuple, Type
import numpy as np

from episense.schemas.forecast import (
    ForecastEvaluationMetrics,
    ForecastModelType,
    ForecastPredictionPoint,
)
from episense.forecasting.models import (
    BaseForecaster,
    SeasonalNaiveForecaster,
    PoissonGLMForecaster,
    NegativeBinomialForecaster,
    EnsembleForecaster,
    HistoricalMedianForecaster,
    RandomForestForecaster,
    PersistenceForecaster,
)


def compute_interval_score(y_true: float, lower: float, upper: float, alpha: float = 0.05) -> float:
    """
    Computes the proper scoring rule: Interval Score (Gneiting & Raftery, 2007).
    MIS_alpha = (U - L) + (2/alpha)*(L - y)*I(y < L) + (2/alpha)*(y - U)*I(y > U)
    Penalizes wider intervals and observations falling outside bounds.
    """
    width = upper - lower
    under = (2.0 / alpha) * (lower - y_true) if y_true < lower else 0.0
    over = (2.0 / alpha) * (y_true - upper) if y_true > upper else 0.0
    return float(width + under + over)


class ChronologicalHoldoutEvaluator:
    """
    Executes chronological holdout evaluation of count forecasting models.
    """

    def __init__(self, holdout_weeks: int = 4, season_length: int = 52):
        self.holdout_weeks = holdout_weeks
        self.season_length = season_length

    def evaluate(
        self,
        y: np.ndarray,
        model_type: ForecastModelType = ForecastModelType.NEGATIVE_BINOMIAL,
        last_year: int = 2026,
        last_week: int = 40,
        last_date: Optional[datetime] = None,
        X: Optional[np.ndarray] = None,
    ) -> Tuple[ForecastEvaluationMetrics, List[ForecastPredictionPoint]]:
        """
        Splits y into train [0 : N - holdout_weeks] and test [N - holdout_weeks : N].
        Fits model exclusively on train and evaluates against test.
        """
        y_arr = np.asarray(y, dtype=float)
        n = len(y_arr)

        if n <= self.holdout_weeks:
            return (
                ForecastEvaluationMetrics(
                    mae=None,
                    rmse=None,
                    mape=None,
                    coverage_80=None,
                    coverage_95=None,
                    mean_interval_score_95=None,
                    training_sample_size=n,
                    test_sample_size=0,
                ),
                [],
            )

        n_train = n - self.holdout_weeks
        y_train = y_arr[:n_train]
        y_test = y_arr[n_train:]

        X_train = X[:n_train] if X is not None else None
        X_test = X[n_train:] if X is not None else None

        # Instantiate model
        if model_type == ForecastModelType.SEASONAL_NAIVE:
            model: BaseForecaster = SeasonalNaiveForecaster(season_length=self.season_length)
        elif model_type == ForecastModelType.HISTORICAL_MEDIAN:
            model = HistoricalMedianForecaster(season_length=self.season_length)
        elif model_type == ForecastModelType.POISSON_GLM:
            model = PoissonGLMForecaster()
        elif model_type == ForecastModelType.RANDOM_FOREST or model_type == ForecastModelType.SPATIOTEMPORAL_PANEL:
            model = RandomForestForecaster(season_length=self.season_length)
        elif model_type == ForecastModelType.ENSEMBLE:
            model = EnsembleForecaster(season_length=self.season_length)
        elif model_type == ForecastModelType.PERSISTENCE:
            model = PersistenceForecaster()
        else:
            model = NegativeBinomialForecaster()

        # Fit exclusively on train
        model.fit(y_train, X_train)

        # Predict for holdout horizon
        base_date = last_date or datetime.now()
        preds = model.predict(
            horizon=self.holdout_weeks,
            last_year=last_year,
            last_week=last_week - self.holdout_weeks,
            last_date=base_date,
            X_future=X_test,
        )

        # Compute error metrics
        y_hat = np.array([p.point_estimate for p in preds])
        errors = y_test - y_hat
        abs_errors = np.abs(errors)
        sq_errors = errors ** 2

        mae = float(np.mean(abs_errors))
        rmse = float(math.sqrt(float(np.mean(sq_errors))))

        # MASE: scale by mean absolute error of in-sample naive 1-step persistence
        if len(y_train) > 1:
            scale_denom = float(np.mean(np.abs(np.diff(y_train))))
            mase = float(mae / max(1.0, scale_denom))
        else:
            mase = 1.0

        # Poisson deviance: 2 * sum( y * log(y / mu) - (y - mu) )
        dev_terms = []
        for yt, yh in zip(y_test, y_hat):
            yt_safe = max(0.0, float(yt))
            yh_safe = max(0.01, float(yh))
            if yt_safe > 0:
                dev = 2.0 * (yt_safe * math.log(yt_safe / yh_safe) - (yt_safe - yh_safe))
            else:
                dev = 2.0 * yh_safe
            dev_terms.append(dev)
        poisson_dev = float(np.mean(dev_terms))

        # Percentage errors
        mape_vals = [abs_err / max(1.0, float(yt)) for abs_err, yt in zip(abs_errors, y_test)]
        mape = float(np.mean(mape_vals) * 100.0)

        # Interval coverages
        c80_count = sum(
            1 for yt, p in zip(y_test, preds) if p.interval_80_lower <= yt <= p.interval_80_upper
        )
        c95_count = sum(
            1 for yt, p in zip(y_test, preds) if p.interval_95_lower <= yt <= p.interval_95_upper
        )

        cov_80 = float((c80_count / self.holdout_weeks) * 100.0)
        cov_95 = float((c95_count / self.holdout_weeks) * 100.0)

        # Mean Interval Score (alpha=0.05 for 95% interval)
        interval_scores = [
            compute_interval_score(yt, p.interval_95_lower, p.interval_95_upper, alpha=0.05)
            for yt, p in zip(y_test, preds)
        ]
        mis_95 = float(np.mean(interval_scores))

        metrics = ForecastEvaluationMetrics(
            mae=round(mae, 2),
            rmse=round(rmse, 2),
            mase=round(mase, 3),
            poisson_deviance=round(poisson_dev, 2),
            mape=round(mape, 2),
            coverage_80=round(cov_80, 1),
            coverage_95=round(cov_95, 1),
            mean_interval_score_95=round(mis_95, 2),
            training_sample_size=n_train,
            test_sample_size=self.holdout_weeks,
        )

        return metrics, preds

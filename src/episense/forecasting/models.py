"""
Epidemiological Forecasting Model Implementations for EpiSense (Phase 5).
Includes:
  - BaseForecaster (abstract contract)
  - SeasonalNaiveForecaster (calendar-cycle benchmark)
  - PoissonGLMForecaster (count generalized linear model)
  - NegativeBinomialForecaster (overdispersed count regression with dispersion parameter)
  - EnsembleForecaster (variance-weighted ensemble)
"""

from abc import ABC, abstractmethod
from datetime import datetime, timedelta, timezone
import math
from typing import Any, Dict, List, Optional, Tuple
import numpy as np
from scipy import stats
from scipy.optimize import minimize
from scipy.special import gammaln, psi

from episense.schemas.forecast import (
    ForecastModelType,
    ForecastPredictionPoint,
    ForecastEvaluationMetrics,
)


class BaseForecaster(ABC):
    """
    Abstract Base Class for epidemiological count forecasters.
    """

    def __init__(self, model_type: ForecastModelType):
        self.model_type = model_type
        self.is_fitted: bool = False
        self.parameters: Dict[str, Any] = {}

    @abstractmethod
    def fit(self, y: np.ndarray, X: Optional[np.ndarray] = None) -> "BaseForecaster":
        """
        Fits the model to historical time-series counts y of shape (N,)
        and optional exogenous covariate matrix X of shape (N, K).
        """
        pass

    @abstractmethod
    def predict(
        self,
        horizon: int,
        last_year: int,
        last_week: int,
        last_date: datetime,
        X_future: Optional[np.ndarray] = None,
    ) -> List[ForecastPredictionPoint]:
        """
        Generates predictions and prediction intervals for `horizon` weeks ahead.
        """
        pass


def _advance_iso_week(year: int, week: int, steps: int) -> Tuple[int, int]:
    """Advances an ISO calendar week by a given number of steps, handling year boundaries."""
    dt = datetime.fromisocalendar(year, week, 1) + timedelta(weeks=steps)
    iso_y, iso_w, _ = dt.isocalendar()
    return iso_y, iso_w


def _week_date_bounds(year: int, week: int) -> Tuple[datetime, datetime]:
    """Returns Monday 00:00:00 to Sunday 23:59:59 UTC for a given ISO week."""
    mon = datetime.fromisocalendar(year, week, 1).replace(
        hour=0, minute=0, second=0, microsecond=0, tzinfo=timezone.utc
    )
    sun = mon + timedelta(days=6, hours=23, minutes=59, seconds=59)
    return mon, sun


class SeasonalNaiveForecaster(BaseForecaster):
    """
    Seasonal Naive Forecaster.
    Projects future counts based on previous seasonal cycles (default 52 weeks).
    When series length is less than 52, uses the most recent observed value
    or cyclical periodicity.
    """

    def __init__(self, season_length: int = 52):
        super().__init__(ForecastModelType.SEASONAL_NAIVE)
        self.season_length = season_length
        self.history: np.ndarray = np.array([])
        self.residual_sigma: float = 1.0

    def fit(self, y: np.ndarray, X: Optional[np.ndarray] = None) -> "SeasonalNaiveForecaster":
        y_clean = np.asarray(y, dtype=float)
        self.history = y_clean
        n = len(y_clean)

        if n >= 2:
            # Estimate residual variance from successive differences
            diffs = np.diff(y_clean)
            self.residual_sigma = max(1.0, float(np.std(diffs)))
        else:
            self.residual_sigma = max(1.0, float(np.mean(y_clean) * 0.5) if n > 0 else 1.0)

        self.parameters = {
            "season_length": self.season_length,
            "training_samples": n,
            "residual_sigma": self.residual_sigma,
            "last_observed_value": float(y_clean[-1]) if n > 0 else 0.0,
        }
        self.is_fitted = True
        return self

    def predict(
        self,
        horizon: int,
        last_year: int,
        last_week: int,
        last_date: datetime,
        X_future: Optional[np.ndarray] = None,
    ) -> List[ForecastPredictionPoint]:
        if not self.is_fitted or len(self.history) == 0:
            raise RuntimeError("Model must be fitted before predict() is called.")

        n = len(self.history)
        points: List[ForecastPredictionPoint] = []

        for h in range(1, horizon + 1):
            target_year, target_week = _advance_iso_week(last_year, last_week, h)
            period_start, period_end = _week_date_bounds(target_year, target_week)

            # Seasonal lookup if available, otherwise last observed value
            if n >= self.season_length:
                point_est = float(self.history[-self.season_length + ((h - 1) % self.season_length)])
            else:
                point_est = float(self.history[-1])

            point_est = max(0.0, point_est)

            # Uncertainty expands with horizon sqrt(h)
            sigma_h = self.residual_sigma * math.sqrt(h)
            z_80 = 1.282
            z_95 = 1.960

            points.append(
                ForecastPredictionPoint(
                    horizon_step=h,
                    target_year=target_year,
                    target_week=target_week,
                    period_start=period_start,
                    period_end=period_end,
                    point_estimate=round(point_est, 2),
                    interval_80_lower=round(max(0.0, point_est - z_80 * sigma_h), 2),
                    interval_80_upper=round(point_est + z_80 * sigma_h, 2),
                    interval_95_lower=round(max(0.0, point_est - z_95 * sigma_h), 2),
                    interval_95_upper=round(point_est + z_95 * sigma_h, 2),
                )
            )

        return points


class PoissonGLMForecaster(BaseForecaster):
    """
    Poisson Generalized Linear Model (GLM) for epidemiological count series.
    y_t ~ Poisson(lambda_t), ln(lambda_t) = beta_0 + sum(beta_k * ln(y_{t-k} + 1)) + trend * t + X * theta.
    Estimated via penalized maximum likelihood.
    """

    def __init__(self, autoregressive_lags: int = 2, include_trend: bool = True, l2_reg: float = 1e-3):
        super().__init__(ForecastModelType.POISSON_GLM)
        self.p_lags = autoregressive_lags
        self.include_trend = include_trend
        self.l2_reg = l2_reg
        self.weights: np.ndarray = np.array([])
        self.history: np.ndarray = np.array([])

    def _build_features(self, y: np.ndarray, X: Optional[np.ndarray] = None) -> Tuple[np.ndarray, np.ndarray]:
        n = len(y)
        rows = []
        targets = []
        for t in range(self.p_lags, n):
            feats = [1.0]  # Intercept
            # Lags in log1p space
            for k in range(1, self.p_lags + 1):
                feats.append(math.log1p(float(y[t - k])))
            if self.include_trend:
                feats.append(float(t) / float(n))
            if X is not None and len(X) > t:
                feats.extend(X[t].tolist())
            rows.append(feats)
            targets.append(float(y[t]))
        return np.array(rows), np.array(targets)

    def fit(self, y: np.ndarray, X: Optional[np.ndarray] = None) -> "PoissonGLMForecaster":
        y_clean = np.asarray(y, dtype=float)
        self.history = y_clean
        n = len(y_clean)

        if n <= self.p_lags:
            # Fallback to sample mean if series is too short for lags
            self.weights = np.array([math.log(max(0.1, float(np.mean(y_clean))))])
            self.is_fitted = True
            self.parameters = {"mean_fallback": True, "lambda": float(np.mean(y_clean))}
            return self

        Feats, Targets = self._build_features(y_clean, X)
        num_feats = Feats.shape[1]

        # Numerically stable negative log-likelihood objective with analytical gradient
        def loss_and_grad(w: np.ndarray) -> Tuple[float, np.ndarray]:
            eta = np.clip(Feats @ w, -30.0, 30.0)
            mu = np.exp(eta)
            loss = np.sum(mu - Targets * eta) + 0.5 * self.l2_reg * np.sum(w[1:] ** 2)
            grad = Feats.T @ (mu - Targets) + np.concatenate([[0.0], self.l2_reg * w[1:]])
            return float(loss), grad

        w0 = np.zeros(num_feats)
        w0[0] = math.log(max(0.1, float(np.mean(Targets))))

        res = minimize(loss_and_grad, w0, jac=True, method="L-BFGS-B")
        self.weights = res.x if res.success else w0
        grad_norm = float(np.linalg.norm(res.jac)) if hasattr(res, "jac") and res.jac is not None else 0.0
        sum_targets = float(np.sum(Targets))
        scaled_grad_norm = float(grad_norm / sum_targets) if sum_targets > 0 else grad_norm
        self.parameters = {
            "converged": bool(res.success),
            "iterations": int(res.nit),
            "termination_message": str(res.message),
            "gradient_norm": grad_norm,
            "scaled_gradient_norm": scaled_grad_norm,
            "weights": self.weights.tolist(),
            "lags": self.p_lags,
            "training_samples": n,
            "design_matrix_rows": len(Targets),
        }
        self.is_fitted = True
        return self

    def predict(
        self,
        horizon: int,
        last_year: int,
        last_week: int,
        last_date: datetime,
        X_future: Optional[np.ndarray] = None,
    ) -> List[ForecastPredictionPoint]:
        if not self.is_fitted:
            raise RuntimeError("Model must be fitted before predict() is called.")

        points: List[ForecastPredictionPoint] = []
        sim_history = list(self.history)
        n_orig = len(self.history)

        for h in range(1, horizon + 1):
            target_year, target_week = _advance_iso_week(last_year, last_week, h)
            period_start, period_end = _week_date_bounds(target_year, target_week)

            if len(self.weights) == 1:
                lam = math.exp(self.weights[0])
            else:
                feats = [1.0]
                for k in range(1, self.p_lags + 1):
                    feats.append(math.log1p(float(sim_history[-k])))
                if self.include_trend:
                    feats.append(float(n_orig + h - 1) / float(n_orig))
                if X_future is not None and len(X_future) >= h:
                    feats.extend(X_future[h - 1].tolist())

                lin = float(np.clip(np.dot(feats[:len(self.weights)], self.weights), -30.0, 30.0))
                lam = math.exp(lin)

            lam = max(0.01, lam)
            sim_history.append(lam)

            # Poisson quantiles for prediction intervals
            q80_low = float(stats.poisson.ppf(0.10, lam))
            q80_high = float(stats.poisson.ppf(0.90, lam))
            q95_low = float(stats.poisson.ppf(0.025, lam))
            q95_high = float(stats.poisson.ppf(0.975, lam))

            points.append(
                ForecastPredictionPoint(
                    horizon_step=h,
                    target_year=target_year,
                    target_week=target_week,
                    period_start=period_start,
                    period_end=period_end,
                    point_estimate=round(lam, 2),
                    interval_80_lower=round(max(0.0, q80_low), 2),
                    interval_80_upper=round(q80_high, 2),
                    interval_95_lower=round(max(0.0, q95_low), 2),
                    interval_95_upper=round(q95_high, 2),
                )
            )

        return points


class NegativeBinomialForecaster(BaseForecaster):
    """
    Negative Binomial Regression Forecaster.
    Accounts for overdispersion (variance > mean) in epidemiological outbreak counts.
    Var(y) = mu + alpha * mu^2, where alpha is the dispersion parameter.
    """

    def __init__(self, autoregressive_lags: int = 2, include_trend: bool = True, l2_reg: float = 1e-3):
        super().__init__(ForecastModelType.NEGATIVE_BINOMIAL)
        self.p_lags = autoregressive_lags
        self.include_trend = include_trend
        self.l2_reg = l2_reg
        self.weights: np.ndarray = np.array([])
        self.alpha: float = 0.2  # Dispersion parameter
        self.history: np.ndarray = np.array([])

    def _build_features(self, y: np.ndarray, X: Optional[np.ndarray] = None) -> Tuple[np.ndarray, np.ndarray]:
        return PoissonGLMForecaster(self.p_lags, self.include_trend, self.l2_reg)._build_features(y, X)

    def fit(self, y: np.ndarray, X: Optional[np.ndarray] = None) -> "NegativeBinomialForecaster":
        y_clean = np.asarray(y, dtype=float)
        self.history = y_clean
        n = len(y_clean)

        if n <= self.p_lags:
            mean_y = max(0.1, float(np.mean(y_clean)))
            var_y = max(mean_y, float(np.var(y_clean)) if n > 1 else mean_y * 1.5)
            self.alpha = max(0.05, (var_y - mean_y) / (mean_y ** 2)) if var_y > mean_y else 0.1
            self.weights = np.array([math.log(mean_y)])
            self.is_fitted = True
            self.parameters = {"mean_fallback": True, "mu": mean_y, "alpha": self.alpha}
            return self

        # First fit Poisson to initialize weights
        poisson_fit = PoissonGLMForecaster(self.p_lags, self.include_trend, self.l2_reg)
        poisson_fit.fit(y_clean, X)
        w_init = poisson_fit.weights

        # Estimate dispersion alpha using Pearson residual method of moments
        Feats, Targets = poisson_fit._build_features(y_clean, X)
        lin_init = np.clip(Feats @ w_init, -30.0, 30.0)
        mu_pred = np.exp(lin_init)

        residuals = Targets - mu_pred
        deg_freedom = max(1, len(Targets) - len(w_init))
        pearson_chi2 = np.sum((residuals ** 2) / np.maximum(mu_pred, 1e-3))
        dispersion_ratio = float(pearson_chi2 / deg_freedom)

        if dispersion_ratio > 1.0:
            alpha_init = float(np.clip((dispersion_ratio - 1.0) / np.mean(mu_pred), 0.01, 5.0))
        else:
            alpha_init = 0.05

        # Joint Negative Binomial MLE over (w, theta = ln(alpha)) with analytical gradients
        def nb_loss_and_grad(params: np.ndarray) -> Tuple[float, np.ndarray]:
            w = params[:-1]
            theta = float(params[-1])
            alpha = math.exp(float(np.clip(theta, -10.0, 5.0)))
            r = 1.0 / alpha

            eta = np.clip(Feats @ w, -30.0, 30.0)
            mu = np.exp(eta)

            ll = (
                gammaln(Targets + r)
                - gammaln(r)
                - gammaln(Targets + 1.0)
                + Targets * np.log(np.maximum(alpha * mu, 1e-12))
                - (Targets + r) * np.log1p(alpha * mu)
            )
            loss = -np.sum(ll) + 0.5 * self.l2_reg * np.sum(w[1:] ** 2)

            g_beta = Feats.T @ ((mu - Targets) / (1.0 + alpha * mu)) + np.concatenate([[0.0], self.l2_reg * w[1:]])
            term_psi = psi(Targets + r) - psi(r) - np.log1p(alpha * mu)
            g_theta = float(np.sum(r * term_psi - (Targets - mu) / (1.0 + alpha * mu)))

            grad = np.concatenate([g_beta, [g_theta]])
            return float(loss), grad

        p0 = np.concatenate([w_init, [math.log(alpha_init)]])
        res = minimize(nb_loss_and_grad, p0, jac=True, method="L-BFGS-B")

        if res.success:
            self.weights = res.x[:-1]
            self.alpha = float(np.exp(np.clip(res.x[-1], -10.0, 5.0)))
        else:
            self.weights = w_init
            self.alpha = alpha_init

        # Re-evaluate dispersion with optimized NB weights
        lin_opt = np.clip(Feats @ self.weights, -30.0, 30.0)
        mu_opt = np.exp(lin_opt)
        residuals_opt = Targets - mu_opt
        pearson_chi2_opt = np.sum((residuals_opt ** 2) / np.maximum(mu_opt, 1e-3))
        dispersion_ratio_opt = float(pearson_chi2_opt / deg_freedom)

        grad_norm_nb = float(np.linalg.norm(res.jac)) if hasattr(res, "jac") and res.jac is not None else 0.0
        sum_targets_nb = float(np.sum(Targets))
        scaled_grad_norm_nb = float(grad_norm_nb / sum_targets_nb) if sum_targets_nb > 0 else grad_norm_nb

        self.parameters = {
            "converged": bool(res.success),
            "iterations": int(res.nit),
            "termination_message": str(res.message),
            "gradient_norm": grad_norm_nb,
            "scaled_gradient_norm": scaled_grad_norm_nb,
            "weights": self.weights.tolist(),
            "alpha": self.alpha,
            "dispersion_ratio": dispersion_ratio_opt,
            "training_samples": n,
            "design_matrix_rows": len(Targets),
        }
        self.is_fitted = True
        return self

    def predict(
        self,
        horizon: int,
        last_year: int,
        last_week: int,
        last_date: datetime,
        X_future: Optional[np.ndarray] = None,
    ) -> List[ForecastPredictionPoint]:
        if not self.is_fitted:
            raise RuntimeError("Model must be fitted before predict() is called.")

        points: List[ForecastPredictionPoint] = []
        sim_history = list(self.history)
        n_orig = len(self.history)

        for h in range(1, horizon + 1):
            target_year, target_week = _advance_iso_week(last_year, last_week, h)
            period_start, period_end = _week_date_bounds(target_year, target_week)

            if len(self.weights) == 1:
                mu = math.exp(self.weights[0])
            else:
                feats = [1.0]
                for k in range(1, self.p_lags + 1):
                    feats.append(math.log1p(float(sim_history[-k])))
                if self.include_trend:
                    feats.append(float(n_orig + h - 1) / float(n_orig))
                if X_future is not None and len(X_future) >= h:
                    feats.extend(X_future[h - 1].tolist())

                lin = float(np.clip(np.dot(feats[:len(self.weights)], self.weights), -30.0, 30.0))
                mu = math.exp(lin)

            mu = max(0.01, mu)
            sim_history.append(mu)

            # Scipy Negative Binomial parameterization:
            # Var = mu + alpha * mu^2
            # n = 1/alpha, p = 1 / (1 + alpha * mu)
            n_param = 1.0 / self.alpha
            p_param = 1.0 / (1.0 + self.alpha * mu)

            q80_low = float(stats.nbinom.ppf(0.10, n_param, p_param))
            q80_high = float(stats.nbinom.ppf(0.90, n_param, p_param))
            q95_low = float(stats.nbinom.ppf(0.025, n_param, p_param))
            q95_high = float(stats.nbinom.ppf(0.975, n_param, p_param))

            points.append(
                ForecastPredictionPoint(
                    horizon_step=h,
                    target_year=target_year,
                    target_week=target_week,
                    period_start=period_start,
                    period_end=period_end,
                    point_estimate=round(mu, 2),
                    interval_80_lower=round(max(0.0, q80_low), 2),
                    interval_80_upper=round(q80_high, 2),
                    interval_95_lower=round(max(0.0, q95_low), 2),
                    interval_95_upper=round(q95_high, 2),
                )
            )

        return points


class EnsembleForecaster(BaseForecaster):
    """
    Weighted combination ensemble of Negative Binomial, Poisson, and Seasonal Naive models.
    """

    def __init__(self, weights: Optional[Dict[str, float]] = None, season_length: int = 52):
        super().__init__(ForecastModelType.ENSEMBLE)
        self.sub_weights = weights or {"nb": 0.50, "poisson": 0.30, "naive": 0.20}
        self.season_length = season_length
        self.nb = NegativeBinomialForecaster()
        self.poisson = PoissonGLMForecaster()
        self.naive = SeasonalNaiveForecaster(season_length=season_length)

    def fit(self, y: np.ndarray, X: Optional[np.ndarray] = None) -> "EnsembleForecaster":
        self.nb.fit(y, X)
        self.poisson.fit(y, X)
        self.naive.season_length = self.season_length
        self.naive.fit(y, X)
        self.is_fitted = True
        self.parameters = {
            "sub_weights": self.sub_weights,
            "nb_params": self.nb.parameters,
            "poisson_params": self.poisson.parameters,
        }
        return self

    def predict(
        self,
        horizon: int,
        last_year: int,
        last_week: int,
        last_date: datetime,
        X_future: Optional[np.ndarray] = None,
    ) -> List[ForecastPredictionPoint]:
        pts_nb = self.nb.predict(horizon, last_year, last_week, last_date, X_future)
        pts_poi = self.poisson.predict(horizon, last_year, last_week, last_date, X_future)
        pts_nai = self.naive.predict(horizon, last_year, last_week, last_date, X_future)

        w_nb = self.sub_weights.get("nb", 0.5)
        w_poi = self.sub_weights.get("poisson", 0.3)
        w_nai = self.sub_weights.get("naive", 0.2)
        total_w = w_nb + w_poi + w_nai

        ensemble_pts: List[ForecastPredictionPoint] = []
        for i in range(horizon):
            nb_p, poi_p, nai_p = pts_nb[i], pts_poi[i], pts_nai[i]

            pt_est = (w_nb * nb_p.point_estimate + w_poi * poi_p.point_estimate + w_nai * nai_p.point_estimate) / total_w
            i80_l = (w_nb * nb_p.interval_80_lower + w_poi * poi_p.interval_80_lower + w_nai * nai_p.interval_80_lower) / total_w
            i80_u = (w_nb * nb_p.interval_80_upper + w_poi * poi_p.interval_80_upper + w_nai * nai_p.interval_80_upper) / total_w
            i95_l = (w_nb * nb_p.interval_95_lower + w_poi * poi_p.interval_95_lower + w_nai * nai_p.interval_95_lower) / total_w
            i95_u = (w_nb * nb_p.interval_95_upper + w_poi * poi_p.interval_95_upper + w_nai * nai_p.interval_95_upper) / total_w

            ensemble_pts.append(
                ForecastPredictionPoint(
                    horizon_step=nb_p.horizon_step,
                    target_year=nb_p.target_year,
                    target_week=nb_p.target_week,
                    period_start=nb_p.period_start,
                    period_end=nb_p.period_end,
                    point_estimate=round(pt_est, 2),
                    interval_80_lower=round(max(0.0, i80_l), 2),
                    interval_80_upper=round(i80_u, 2),
                    interval_95_lower=round(max(0.0, i95_l), 2),
                    interval_95_upper=round(i95_u, 2),
                )
            )

        return ensemble_pts


class HistoricalMedianForecaster(BaseForecaster):
    """
    Historical Seasonal Median Baseline Forecaster.
    Computes empirical median and quantiles for baseline comparison.
    Ideal for diseases where full parametric autoregression is not supported
    or where baseline expectations serve as comparative context.
    """

    def __init__(self, season_length: int = 12):
        super().__init__(ForecastModelType.HISTORICAL_MEDIAN)
        self.season_length = season_length
        self.median_val: float = 0.0
        self.q80_low: float = 0.0
        self.q80_high: float = 0.0
        self.q95_low: float = 0.0
        self.q95_high: float = 0.0
        self.history: np.ndarray = np.array([])

    def fit(self, y: np.ndarray, X: Optional[np.ndarray] = None) -> "HistoricalMedianForecaster":
        y_clean = np.asarray(y, dtype=float)
        self.history = y_clean
        n = len(y_clean)
        if n > 0:
            self.median_val = float(np.median(y_clean))
            self.q80_low = float(np.percentile(y_clean, 10.0))
            self.q80_high = float(np.percentile(y_clean, 90.0))
            self.q95_low = float(np.percentile(y_clean, 2.5))
            self.q95_high = float(np.percentile(y_clean, 97.5))
        self.is_fitted = True
        self.parameters = {
            "median": self.median_val,
            "q80_lower": self.q80_low,
            "q80_upper": self.q80_high,
            "q95_lower": self.q95_low,
            "q95_upper": self.q95_high,
            "sample_size": n,
        }
        return self

    def predict(
        self,
        horizon: int,
        last_year: int,
        last_week: int,
        last_date: datetime,
        X_future: Optional[np.ndarray] = None,
    ) -> List[ForecastPredictionPoint]:
        if not self.is_fitted:
            raise RuntimeError("Model must be fitted before predict() is called.")

        points: List[ForecastPredictionPoint] = []
        for h in range(1, horizon + 1):
            target_year, target_week = _advance_iso_week(last_year, last_week, h)
            period_start, period_end = _week_date_bounds(target_year, target_week)
            points.append(
                ForecastPredictionPoint(
                    horizon_step=h,
                    target_year=target_year,
                    target_week=target_week,
                    period_start=period_start,
                    period_end=period_end,
                    point_estimate=round(self.median_val, 2),
                    interval_80_lower=round(max(0.0, self.q80_low), 2),
                    interval_80_upper=round(self.q80_high, 2),
                    interval_95_lower=round(max(0.0, self.q95_low), 2),
                    interval_95_upper=round(self.q95_high, 2),
                )
            )
        return points


class RandomForestForecaster(BaseForecaster):
    """
    Supervised Machine Learning Forecaster using Random Forest Regression.
    Incorporates:
      - Autoregressive lags (t-1, t-2)
      - Rolling statistics (mean, variance)
      - Seasonal harmonics (sin/cos of calendar period)
      - Environmental and climate covariates (temperature, rainfall, humidity)
    Computes ensemble tree distribution percentiles for empirical prediction intervals.
    """

    def __init__(self, n_estimators: int = 100, p_lags: int = 2, season_length: int = 12):
        super().__init__(ForecastModelType.RANDOM_FOREST)
        self.n_estimators = n_estimators
        self.p_lags = p_lags
        self.season_length = season_length
        self.model = None
        self.history: np.ndarray = np.array([])
        self.feature_names: List[str] = []
        self.feature_importances_: Dict[str, float] = {}

    def _build_features(self, history: List[float], t_idx: int, X_row: Optional[np.ndarray] = None) -> List[float]:
        feats = []
        for lag in range(1, self.p_lags + 1):
            val = history[-lag] if len(history) >= lag else history[-1]
            feats.append(math.log1p(max(0.0, float(val))))

        # Rolling mean (window 3)
        window = history[-min(3, len(history)):]
        feats.append(math.log1p(max(0.0, float(np.mean(window)))))

        # Seasonal harmonics
        period_pos = (t_idx % self.season_length) / float(self.season_length)
        feats.append(math.sin(2.0 * math.pi * period_pos))
        feats.append(math.cos(2.0 * math.pi * period_pos))

        # Exogenous covariates
        if X_row is not None:
            feats.extend(float(v) for v in X_row)

        return feats

    def fit(self, y: np.ndarray, X: Optional[np.ndarray] = None) -> "RandomForestForecaster":
        from sklearn.ensemble import RandomForestRegressor

        y_clean = np.asarray(y, dtype=float)
        self.history = y_clean
        n = len(y_clean)

        if n <= self.p_lags:
            self.model = None
            self.is_fitted = True
            return self

        X_rows = []
        y_targets = []
        for i in range(self.p_lags, n):
            hist_sub = list(y_clean[:i])
            x_cov = X[i] if X is not None and len(X) > i else None
            feat = self._build_features(hist_sub, i, x_cov)
            X_rows.append(feat)
            y_targets.append(y_clean[i])

        X_mat = np.array(X_rows, dtype=float)
        y_vec = np.array(y_targets, dtype=float)

        rf = RandomForestRegressor(n_estimators=self.n_estimators, random_state=42, max_depth=6)
        rf.fit(X_mat, y_vec)
        self.model = rf
        self.is_fitted = True

        self.feature_names = [f"lag_{k}" for k in range(1, self.p_lags + 1)] + ["roll_mean_3", "sin_season", "cos_season"]
        if X is not None and X.shape[1] > 0:
            for k in range(X.shape[1]):
                self.feature_names.append(f"covar_{k}")

        self.feature_importances_ = {
            name: round(float(imp), 4)
            for name, imp in zip(self.feature_names, rf.feature_importances_)
        }
        self.parameters = {
            "n_estimators": self.n_estimators,
            "feature_importances": self.feature_importances_,
            "training_samples": len(y_targets),
        }
        return self

    def predict(
        self,
        horizon: int,
        last_year: int,
        last_week: int,
        last_date: datetime,
        X_future: Optional[np.ndarray] = None,
    ) -> List[ForecastPredictionPoint]:
        if not self.is_fitted:
            raise RuntimeError("Model must be fitted before predict() is called.")

        points: List[ForecastPredictionPoint] = []
        sim_history = list(self.history)
        n_orig = len(self.history)

        for h in range(1, horizon + 1):
            target_year, target_week = _advance_iso_week(last_year, last_week, h)
            period_start, period_end = _week_date_bounds(target_year, target_week)

            if self.model is None or len(sim_history) < self.p_lags:
                mu = float(np.mean(sim_history)) if sim_history else 1.0
                q80_l, q80_u = mu * 0.7, mu * 1.3
                q95_l, q95_u = mu * 0.5, mu * 1.6
            else:
                x_cov = X_future[h - 1] if X_future is not None and len(X_future) >= h else None
                feats = np.array([self._build_features(sim_history, n_orig + h - 1, x_cov)], dtype=float)

                # Individual tree predictions for empirical intervals
                tree_preds = np.array([float(tree.predict(feats)[0]) for tree in self.model.estimators_])
                mu = float(np.mean(tree_preds))
                q80_l = float(np.percentile(tree_preds, 10.0))
                q80_u = float(np.percentile(tree_preds, 90.0))
                q95_l = float(np.percentile(tree_preds, 2.5))
                q95_u = float(np.percentile(tree_preds, 97.5))

            mu = max(0.0, mu)
            sim_history.append(mu)

            points.append(
                ForecastPredictionPoint(
                    horizon_step=h,
                    target_year=target_year,
                    target_week=target_week,
                    period_start=period_start,
                    period_end=period_end,
                    point_estimate=round(mu, 2),
                    interval_80_lower=round(max(0.0, q80_l), 2),
                    interval_80_upper=round(q80_u, 2),
                    interval_95_lower=round(max(0.0, q95_l), 2),
                    interval_95_upper=round(q95_u, 2),
                )
            )

        return points


class PersistenceForecaster(BaseForecaster):
    """
    Random-walk / Last-observation persistence forecaster.
    Forecasts hat{y}_{t+h} = y_t for all horizons h=1..H.
    Uncertainty expands with sqrt(h) based on sample difference standard deviation.
    """

    def __init__(self):
        super().__init__(ForecastModelType.PERSISTENCE)
        self.last_observed_value: float = 0.0
        self.residual_sigma: float = 1.0

    def fit(self, y: np.ndarray, X: Optional[np.ndarray] = None) -> "PersistenceForecaster":
        y_clean = np.asarray(y, dtype=float)
        n = len(y_clean)
        if n == 0:
            raise ValueError("Training data cannot be empty.")
        self.last_observed_value = float(y_clean[-1])
        if n >= 2:
            diffs = np.diff(y_clean)
            self.residual_sigma = max(1.0, float(np.std(diffs)))
        else:
            self.residual_sigma = max(1.0, self.last_observed_value * 0.5)

        self.parameters = {
            "last_observed_value": self.last_observed_value,
            "residual_sigma": self.residual_sigma,
            "training_samples": n,
        }
        self.is_fitted = True
        return self

    def predict(
        self,
        horizon: int,
        last_year: int,
        last_week: int,
        last_date: datetime,
        X_future: Optional[np.ndarray] = None,
    ) -> List[ForecastPredictionPoint]:
        if not self.is_fitted:
            raise RuntimeError("Model must be fitted before predict() is called.")

        points: List[ForecastPredictionPoint] = []
        z_80 = 1.282
        z_95 = 1.960

        for h in range(1, horizon + 1):
            target_year, target_week = _advance_iso_week(last_year, last_week, h)
            period_start, period_end = _week_date_bounds(target_year, target_week)
            sigma_h = self.residual_sigma * math.sqrt(h)

            points.append(
                ForecastPredictionPoint(
                    horizon_step=h,
                    target_year=target_year,
                    target_week=target_week,
                    period_start=period_start,
                    period_end=period_end,
                    point_estimate=round(self.last_observed_value, 2),
                    interval_80_lower=round(max(0.0, self.last_observed_value - z_80 * sigma_h), 2),
                    interval_80_upper=round(self.last_observed_value + z_80 * sigma_h, 2),
                    interval_95_lower=round(max(0.0, self.last_observed_value - z_95 * sigma_h), 2),
                    interval_95_upper=round(self.last_observed_value + z_95 * sigma_h, 2),
                )
            )

        return points

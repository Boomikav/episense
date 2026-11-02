"""
Bounded Farrington-Style Anomaly Detector for EpiSense (Phase 8).
Implements a defensible, bounded quasi-Poisson overdispersion estimator with
Anscombe 2/3 power skewness correction for surveillance counts.
NOTE: This is a bounded approximation designed for moderate historical series,
distinguished from a full multi-year polynomial seasonal Farrington GLM.
"""

import math
from typing import List, Optional
from pydantic import BaseModel, Field

from episense.schemas.signal import DetectionMethod


class FarringtonResult(BaseModel):
    """
    Structured outcome of a bounded Farrington-style aberration test.
    """
    method: DetectionMethod = DetectionMethod.FARRINGTON_BOUNDED
    observed: float = 0.0
    expected_mean: float = 0.0
    overdispersion_factor: float = 1.0
    threshold: float = 0.0
    z_alpha: float = 1.96
    is_alert: bool = False
    reference_count: int = 0
    is_valid: bool = True
    rationale: str = ""


class BoundedFarringtonDetector:
    """
    Computes a bounded Farrington-style threshold on historical surveillance counts.
    Refuses to manufacture false confidence when historical data is insufficient.
    """

    def __init__(
        self,
        min_reference_periods: int = 3,
        z_alpha: float = 1.96,  # 95% one-sided upper prediction bound (alpha = 0.05 ~ 1.96 / 1.645)
        smoothing_epsilon: float = 0.001,
    ):
        self.min_reference_periods = min_reference_periods
        self.z_alpha = z_alpha
        self.smoothing_epsilon = smoothing_epsilon

    def evaluate(
        self,
        reference_values: List[float],
        observed_value: float,
    ) -> FarringtonResult:
        """
        Evaluates an observed value against reference historical periods.
        """
        n = len(reference_values)
        if n < self.min_reference_periods:
            return FarringtonResult(
                observed=observed_value,
                expected_mean=0.0,
                overdispersion_factor=1.0,
                threshold=float("inf"),
                z_alpha=self.z_alpha,
                is_alert=False,
                reference_count=n,
                is_valid=False,
                rationale=(
                    f"Insufficient historical data for bounded Farrington estimation: "
                    f"{n} reference periods available (minimum required is {self.min_reference_periods})"
                ),
            )

        mu = sum(reference_values) / n

        # Check for all-zero history
        if mu <= self.smoothing_epsilon:
            # Baseline expected is 0; any positive observation above 0 is noteworthy,
            # but threshold cannot be computed via log-link without smoothing
            threshold = max(1.0, self.z_alpha)
            is_alert = observed_value >= threshold
            return FarringtonResult(
                observed=observed_value,
                expected_mean=0.0,
                overdispersion_factor=1.0,
                threshold=round(threshold, 3),
                z_alpha=self.z_alpha,
                is_alert=is_alert,
                reference_count=n,
                is_valid=True,
                rationale=(
                    f"All-zero historical baseline (mu=0.0); observed {observed_value:.1f} "
                    f"(minimum alerting threshold {threshold:.1f})"
                ),
            )

        # Estimate overdispersion factor phi:
        # phi = max(1.0, (1 / (n - 1)) * sum((y - mu)^2 / (mu + epsilon)))
        quasi_variance = sum((y - mu) ** 2 for y in reference_values) / max(1, n - 1)
        phi = max(1.0, quasi_variance / max(mu, self.smoothing_epsilon))

        # Anscombe / Farrington-Stroup 2/3 power skewness transformation:
        # Transformed upper bound:
        # U = (mu^(2/3) + (2/3) * z_alpha * sqrt(phi * mu^(1/3)))^(3/2)
        try:
            mu_23 = mu ** (2.0 / 3.0)
            mu_13 = mu ** (1.0 / 3.0)
            inner = mu_23 + (2.0 / 3.0) * self.z_alpha * math.sqrt(phi * mu_13)
            if inner > 0.0:
                threshold = inner ** (3.0 / 2.0)
            else:
                threshold = mu + self.z_alpha * math.sqrt(phi * mu)
        except Exception:
            # Fallback to standard Poisson/overdispersed normal approximation
            threshold = mu + self.z_alpha * math.sqrt(phi * mu)

        is_alert = observed_value > threshold

        return FarringtonResult(
            observed=round(observed_value, 3),
            expected_mean=round(mu, 3),
            overdispersion_factor=round(phi, 3),
            threshold=round(threshold, 3),
            z_alpha=self.z_alpha,
            is_alert=is_alert,
            reference_count=n,
            is_valid=True,
            rationale=(
                f"Bounded Farrington-style threshold {threshold:.2f} (expected {mu:.2f}, "
                f"overdispersion phi={phi:.2f}, z={self.z_alpha}); observed {observed_value:.1f}"
            ),
        )

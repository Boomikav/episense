"""
Historical Epidemiological Baseline Engine for EpiSense (Phase 8).
Calculates rolling historical mean, median, sample variance, standard deviation,
and dispersion metrics with strict sparse-data handling.
"""

import math
from typing import List, Optional
from uuid import NAMESPACE_DNS, uuid5
from episense.schemas.signal import (
    BaselineEstimate,
    BaselineReliability,
    EpidemiologicalTimeBin,
)
from episense.baseline.reliability import BaselineReliabilityTracker


class BaselineEngine:
    """
    Computes statistical baseline expectations for epidemiological time-series.
    """

    def __init__(
        self,
        min_sample_size: int = 3,
        cv_threshold: float = 1.5,
        smoothing_epsilon: float = 0.001,
    ):
        self.min_sample_size = min_sample_size
        self.smoothing_epsilon = smoothing_epsilon
        self.reliability_tracker = BaselineReliabilityTracker(
            min_sample_size=min_sample_size, cv_threshold=cv_threshold
        )

    def compute_baseline(
        self,
        historical_bins: List[EpidemiologicalTimeBin],
        target_bin: EpidemiologicalTimeBin,
        value_type: str = "cases",
    ) -> BaselineEstimate:
        """
        Computes rolling baseline estimates from historical periods preceding target_bin.
        """
        d_key = target_bin.disease_key
        g_key = target_bin.geo_key
        w_weeks = len(historical_bins)

        # Deterministic UUID5 baseline_id
        seed = f"{d_key}:{g_key}:{target_bin.period_start.isoformat()}:baseline"
        deterministic_baseline_id = uuid5(NAMESPACE_DNS, seed)

        # Assess data reliability first
        reliability, rationale = self.reliability_tracker.evaluate_reliability(
            historical_bins, target_bin, value_type=value_type
        )

        if not historical_bins:
            return BaselineEstimate(
                baseline_id=deterministic_baseline_id,
                disease_key=d_key,
                geo_key=g_key,
                target_period_start=target_bin.period_start,
                target_period_end=target_bin.period_end,
                baseline_window_weeks=max(1, w_weeks),
                baseline_count=0.0,
                baseline_mean=0.0,
                baseline_median=0.0,
                baseline_std=0.0,
                baseline_variance=0.0,
                dispersion_metric=0.0,
                lower_bound=0.0,
                upper_bound=0.0,
                number_of_historical_bins=0,
                number_of_nonzero_bins=0,
                method="historical_rolling",
                reliability_status=reliability,
                rationale=rationale,
            )

        # Extract values according to explicit surveillance stream metric
        values: List[float] = []
        for b in historical_bins:
            if value_type == "cases":
                # Invariant: Document / fused event count must NOT substitute for true case count
                val = b.observed_case_count if b.observed_case_count is not None else 0.0
            elif value_type == "deaths":
                val = b.observed_death_count if b.observed_death_count is not None else 0.0
            elif value_type in ("events", "fused_events", "mentions"):
                val = float(b.fused_event_count)
            else:
                val = b.observed_case_count if b.observed_case_count is not None else 0.0
            values.append(float(val))

        n = len(values)
        nonzero_n = sum(1 for v in values if v > 0.0)
        mean_val = sum(values) / n

        # Median calculation
        sorted_vals = sorted(values)
        if n % 2 == 1:
            median_val = sorted_vals[n // 2]
        else:
            median_val = (sorted_vals[n // 2 - 1] + sorted_vals[n // 2]) / 2.0

        # Sample variance with Bessel's correction (N-1)
        if n > 1:
            variance_val = sum((v - mean_val) ** 2 for v in values) / (n - 1)
        else:
            variance_val = 0.0
        std_val = math.sqrt(variance_val)

        # Dispersion metric (Variance-to-mean ratio for Poisson overdispersion)
        dispersion = variance_val / max(mean_val, self.smoothing_epsilon)

        # Bounds (2 standard deviations)
        lower_b = max(0.0, mean_val - 2.0 * std_val)
        upper_b = mean_val + 2.0 * std_val

        return BaselineEstimate(
            baseline_id=deterministic_baseline_id,
            disease_key=d_key,
            geo_key=g_key,
            target_period_start=target_bin.period_start,
            target_period_end=target_bin.period_end,
            baseline_window_weeks=n,
            baseline_count=float(sum(values)),
            baseline_mean=round(mean_val, 3),
            baseline_median=round(median_val, 3),
            baseline_std=round(std_val, 3),
            baseline_variance=round(variance_val, 3),
            dispersion_metric=round(dispersion, 3),
            lower_bound=round(lower_b, 3),
            upper_bound=round(upper_b, 3),
            number_of_historical_bins=n,
            number_of_nonzero_bins=nonzero_n,
            method="historical_rolling",
            reliability_status=reliability,
            rationale=rationale,
        )

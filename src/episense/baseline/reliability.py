"""
Data Quality and Baseline Reliability Tracker for EpiSense (Phase 8).
Prevents manufacturing false statistical confidence from sparse or unobserved historical series.
"""

from typing import List, Tuple
from episense.schemas.signal import BaselineReliability, EpidemiologicalTimeBin


class BaselineReliabilityTracker:
    """
    Assesses whether a historical series contains sufficient statistical power
    to support an early-warning anomaly baseline.
    """

    def __init__(self, min_sample_size: int = 3, cv_threshold: float = 1.5):
        self.min_sample_size = min_sample_size
        self.cv_threshold = cv_threshold

    def evaluate_reliability(
        self,
        historical_bins: List[EpidemiologicalTimeBin],
        target_bin: EpidemiologicalTimeBin,
        value_type: str = "cases",
    ) -> Tuple[BaselineReliability, str]:
        """
        Evaluates the reliability state of the baseline given historical bins and the target bin.
        Returns:
            (reliability_status, rationale)
        """
        # Check target bin conflicts
        if target_bin.has_conflicts:
            return (
                BaselineReliability.CONFLICTING_DATA,
                f"Target period {target_bin.iso_year}-W{target_bin.iso_week:02d} contains conflicting quantities: {target_bin.conflicting_quantities}",
            )

        # Check geographic, disease & temporal granularity compatibility
        for b in historical_bins:
            if b.disease_key.lower().strip() != target_bin.disease_key.lower().strip():
                return (
                    BaselineReliability.INCOMPATIBLE_GRANULARITY,
                    f"Incompatible disease key: historical bin has disease '{b.disease_key}' vs target '{target_bin.disease_key}'",
                )
            if b.geo_key.lower().strip() != target_bin.geo_key.lower().strip():
                return (
                    BaselineReliability.INCOMPATIBLE_GRANULARITY,
                    f"Incompatible spatial granularity: historical bin has geo '{b.geo_key}' vs target '{target_bin.geo_key}'",
                )

        n_bins = len(historical_bins)
        if n_bins < self.min_sample_size:
            return (
                BaselineReliability.INSUFFICIENT_HISTORY,
                f"Insufficient historical data: {n_bins} historical bins available (minimum required is {self.min_sample_size})",
            )

        # Extract values according to explicit metric stream
        if value_type == "cases":
            values = [b.observed_case_count if b.observed_case_count is not None else 0.0 for b in historical_bins]
        elif value_type == "deaths":
            values = [b.observed_death_count if b.observed_death_count is not None else 0.0 for b in historical_bins]
        else:
            values = [float(b.fused_event_count) for b in historical_bins]

        nonzero_count = sum(1 for v in values if v > 0)

        if nonzero_count < 2:
            return (
                BaselineReliability.SPARSE_HISTORY,
                f"Sparse historical data: only {nonzero_count} non-zero periods observed across {n_bins} historical weeks",
            )

        # Check for extreme variance / volatility
        mean_val = sum(values) / n_bins
        if mean_val > 0.0:
            var_val = sum((v - mean_val) ** 2 for v in values) / max(1, n_bins - 1)
            std_val = var_val ** 0.5
            cv = std_val / mean_val
            if cv > self.cv_threshold:
                return (
                    BaselineReliability.HIGH_VARIANCE,
                    f"High historical variance (coefficient of variation {cv:.2f} > threshold {self.cv_threshold})",
                )

        return (
            BaselineReliability.STABLE_BASELINE,
            f"Stable statistical baseline established over {n_bins} historical weeks ({nonzero_count} non-zero periods)",
        )

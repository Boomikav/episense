"""
CDC Early Aberration Reporting System (EARS) Detectors for EpiSense (Phase 8).
Implements deterministic C1 (mild sensitivity), C2 (standard with 2-week guard band),
and C3 (accumulated persistent aberration over 3 weeks).
"""

import math
from typing import List, Optional
from pydantic import BaseModel, Field

from episense.schemas.signal import DetectionMethod


class EARSResult(BaseModel):
    """
    Structured outcome of an EARS aberration evaluation.
    """
    method: DetectionMethod
    statistic: float = 0.0
    threshold: float = 2.0
    is_alert: bool = False
    baseline_mean: float = 0.0
    baseline_std: float = 0.0
    reference_count: int = 0
    guard_band_weeks: int = 0
    is_valid: bool = True
    rationale: str = ""


class EARSDetector:
    """
    Computes EARS C1, C2, and C3 statistics on epidemiological count sequences.
    """

    def __init__(
        self,
        baseline_weeks: int = 7,
        threshold: float = 2.0,
        smoothing_epsilon: float = 1.0,
    ):
        self.baseline_weeks = baseline_weeks
        self.threshold = threshold
        self.smoothing_epsilon = smoothing_epsilon

    def evaluate_c1(
        self,
        series: List[float],
        target_idx: Optional[int] = None,
    ) -> EARSResult:
        """
        EARS C1: Uses the 7 historical periods immediately preceding the target (no guard band).
        Formula:
            C1(t) = (Y(t) - mean(Y(t-1 ... t-7))) / max(std(Y(t-1 ... t-7)), epsilon)
        """
        idx = target_idx if target_idx is not None else len(series) - 1
        if idx < 0 or idx >= len(series):
            return EARSResult(
                method=DetectionMethod.EARS_C1,
                is_valid=False,
                threshold=self.threshold,
                rationale=f"Invalid target index {idx} for series of length {len(series)}",
            )

        y_t = series[idx]
        start_idx = max(0, idx - self.baseline_weeks)
        ref_values = series[start_idx:idx]

        if len(ref_values) < self.baseline_weeks:
            return EARSResult(
                method=DetectionMethod.EARS_C1,
                is_valid=False,
                reference_count=len(ref_values),
                threshold=self.threshold,
                rationale=f"EARS C1 requires {self.baseline_weeks} historical periods; found {len(ref_values)}",
            )

        mean_ref, std_ref = self._compute_mean_std(ref_values)
        denom = max(std_ref, self.smoothing_epsilon)
        c1_stat = (y_t - mean_ref) / denom
        is_alert = c1_stat >= self.threshold

        return EARSResult(
            method=DetectionMethod.EARS_C1,
            statistic=round(c1_stat, 3),
            threshold=self.threshold,
            is_alert=is_alert,
            baseline_mean=round(mean_ref, 3),
            baseline_std=round(std_ref, 3),
            reference_count=len(ref_values),
            guard_band_weeks=0,
            is_valid=True,
            rationale=(
                f"EARS C1 score {c1_stat:.2f} (threshold {self.threshold:.2f}) based on "
                f"observed {y_t:.1f} vs baseline mean {mean_ref:.2f} +/- {std_ref:.2f}"
            ),
        )

    def evaluate_c2(
        self,
        series: List[float],
        target_idx: Optional[int] = None,
        guard_band_weeks: int = 2,
    ) -> EARSResult:
        """
        EARS C2: Uses 7 historical periods with a 2-week guard band (t-9 to t-2)
        to prevent contamination from the immediate outbreak onset.
        Formula:
            C2(t) = (Y(t) - mean(Y(t-guard ... t-guard-7))) / max(std, epsilon)
        """
        idx = target_idx if target_idx is not None else len(series) - 1
        if idx < 0 or idx >= len(series):
            return EARSResult(
                method=DetectionMethod.EARS_C2,
                is_valid=False,
                threshold=self.threshold,
                rationale=f"Invalid target index {idx} for series of length {len(series)}",
            )

        y_t = series[idx]
        end_ref = idx - guard_band_weeks
        start_ref = end_ref - self.baseline_weeks

        if start_ref < 0:
            ref_count = max(0, end_ref)
            return EARSResult(
                method=DetectionMethod.EARS_C2,
                is_valid=False,
                reference_count=ref_count,
                guard_band_weeks=guard_band_weeks,
                threshold=self.threshold,
                rationale=(
                    f"EARS C2 requires {self.baseline_weeks + guard_band_weeks} historical periods "
                    f"({self.baseline_weeks} baseline + {guard_band_weeks} guard band); found {idx}"
                ),
            )

        ref_values = series[start_ref:end_ref]
        mean_ref, std_ref = self._compute_mean_std(ref_values)
        denom = max(std_ref, self.smoothing_epsilon)
        c2_stat = (y_t - mean_ref) / denom
        is_alert = c2_stat >= self.threshold

        return EARSResult(
            method=DetectionMethod.EARS_C2,
            statistic=round(c2_stat, 3),
            threshold=self.threshold,
            is_alert=is_alert,
            baseline_mean=round(mean_ref, 3),
            baseline_std=round(std_ref, 3),
            reference_count=len(ref_values),
            guard_band_weeks=guard_band_weeks,
            is_valid=True,
            rationale=(
                f"EARS C2 score {c2_stat:.2f} (threshold {self.threshold:.2f}) with {guard_band_weeks}-week "
                f"guard band; observed {y_t:.1f} vs baseline mean {mean_ref:.2f} +/- {std_ref:.2f}"
            ),
        )

    def evaluate_c3(
        self,
        series: List[float],
        target_idx: Optional[int] = None,
        persistence_window: int = 3,
        guard_band_weeks: int = 2,
    ) -> EARSResult:
        """
        EARS C3: Measures accumulated persistent aberration across 3 consecutive weeks
        using C2 standardized deviations.
        Formula:
            C3(t) = sum_{k=0}^{persistence_window-1} max(0, C2(t-k) - 1.0)
        """
        idx = target_idx if target_idx is not None else len(series) - 1
        if idx < persistence_window - 1:
            return EARSResult(
                method=DetectionMethod.EARS_C3,
                is_valid=False,
                threshold=self.threshold,
                rationale=f"EARS C3 requires at least {persistence_window} points for persistence accumulation",
            )

        c2_scores: List[float] = []
        for k in range(persistence_window):
            curr_idx = idx - k
            c2_res = self.evaluate_c2(series, target_idx=curr_idx, guard_band_weeks=guard_band_weeks)
            if not c2_res.is_valid:
                return EARSResult(
                    method=DetectionMethod.EARS_C3,
                    is_valid=False,
                    threshold=self.threshold,
                    rationale=f"EARS C3 persistence could not evaluate C2 at t-{k}: {c2_res.rationale}",
                )
            c2_scores.append(c2_res.statistic)

        # Accumulate excess over 1.0
        c3_stat = sum(max(0.0, score - 1.0) for score in c2_scores)
        is_alert = c3_stat >= self.threshold

        return EARSResult(
            method=DetectionMethod.EARS_C3,
            statistic=round(c3_stat, 3),
            threshold=self.threshold,
            is_alert=is_alert,
            baseline_mean=round(c2_scores[0], 3),
            baseline_std=0.0,
            reference_count=len(c2_scores),
            guard_band_weeks=guard_band_weeks,
            is_valid=True,
            rationale=(
                f"EARS C3 accumulated score {c3_stat:.2f} (threshold {self.threshold:.2f}) "
                f"over {persistence_window} weeks (C2 scores: {[round(s, 2) for s in c2_scores]})"
            ),
        )

    def _compute_mean_std(self, values: List[float]) -> tuple[float, float]:
        n = len(values)
        if n == 0:
            return 0.0, 0.0
        mean_v = sum(values) / n
        if n == 1:
            return mean_v, 0.0
        var_v = sum((x - mean_v) ** 2 for x in values) / (n - 1)
        return mean_v, math.sqrt(var_v)

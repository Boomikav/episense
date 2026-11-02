"""
Deterministic Early Warning Signal Detector for EpiSense (Phase 8).
Coordinates EARS and bounded Farrington detectors, enforces data reliability gates,
and produces explainable SignalObservation records with complete provenance.
"""

import math
from typing import List, Optional
from uuid import NAMESPACE_DNS, uuid5

from episense.schemas.document import OriginClassification
from episense.schemas.signal import (
    BaselineEstimate,
    BaselineReliability,
    DetectionMethod,
    EpidemiologicalTimeBin,
    SignalLevel,
    SignalObservation,
)
from episense.anomaly.ears import EARSDetector, EARSResult
from episense.anomaly.farrington import BoundedFarringtonDetector, FarringtonResult


class SignalDetector:
    """
    Coordinates statistical anomaly detectors to emit explainable early-warning signals.
    """

    def __init__(
        self,
        ears_threshold: float = 2.0,
        farrington_z: float = 1.96,
        smoothing_epsilon: float = 0.001,
    ):
        self.ears_detector = EARSDetector(
            threshold=ears_threshold,
            smoothing_epsilon=smoothing_epsilon,
        )
        self.farrington_detector = BoundedFarringtonDetector(
            z_alpha=farrington_z,
            smoothing_epsilon=smoothing_epsilon,
        )

    def detect_signal(
        self,
        historical_bins: List[EpidemiologicalTimeBin],
        target_bin: EpidemiologicalTimeBin,
        baseline: BaselineEstimate,
        value_type: str = "cases",
    ) -> SignalObservation:
        """
        Evaluates a target bin against historical bins and its baseline estimate.
        Returns a structured, explainable SignalObservation.
        """
        # Determine observed value according to explicit surveillance stream metric
        obs_val: Optional[float] = None
        if value_type == "cases":
            # Invariant: Fused event mentions must NOT substitute for true case counts
            if target_bin.observed_case_count is not None:
                obs_val = float(target_bin.observed_case_count)
        elif value_type == "deaths":
            if target_bin.observed_death_count is not None:
                obs_val = float(target_bin.observed_death_count)
        elif value_type in ("events", "fused_events", "mentions"):
            obs_val = float(target_bin.fused_event_count)
        else:
            if target_bin.observed_case_count is not None:
                obs_val = float(target_bin.observed_case_count)

        calc_val = obs_val if obs_val is not None else 0.0
        exp_val = baseline.baseline_mean
        dev = calc_val - exp_val

        # Standardized deviation statistic (Z-score)
        # Suppress artificial Z-score if baseline history is absent or insufficient
        reliability = baseline.reliability_status
        is_baseline_insufficient = reliability in (
            BaselineReliability.INSUFFICIENT_HISTORY,
            BaselineReliability.INSUFFICIENT_BASELINE,
            BaselineReliability.INCOMPATIBLE_GRANULARITY,
            BaselineReliability.NOT_EVALUABLE,
        )

        std = baseline.baseline_std
        if is_baseline_insufficient:
            z_score = None
        elif std > 0.0:
            z_score = round(dev / std, 3)
        else:
            denom = max(1.0, math.sqrt(exp_val) if exp_val > 0 else 1.0)
            z_score = 0.0 if dev == 0.0 else round(dev / denom, 3)

        # Build combined series for EARS (historical bins + target bin)
        series_values: List[float] = []
        for b in historical_bins:
            if value_type == "cases":
                v = b.observed_case_count if b.observed_case_count is not None else 0.0
            elif value_type == "deaths":
                v = b.observed_death_count if b.observed_death_count is not None else 0.0
            elif value_type in ("events", "fused_events", "mentions"):
                v = float(b.fused_event_count)
            else:
                v = b.observed_case_count if b.observed_case_count is not None else 0.0
            series_values.append(float(v))
        series_values.append(calc_val)
        target_idx = len(series_values) - 1

        # Run EARS detectors
        c1_res = self.ears_detector.evaluate_c1(series_values, target_idx=target_idx)
        c2_res = self.ears_detector.evaluate_c2(series_values, target_idx=target_idx)
        c3_res = self.ears_detector.evaluate_c3(series_values, target_idx=target_idx)

        # Run bounded Farrington detector
        historical_values = series_values[:-1]
        farrington_res = self.farrington_detector.evaluate(historical_values, calc_val)

        # Signal Classification Logic
        reliability = baseline.reliability_status
        independent_sources = target_bin.independent_source_count

        alert_methods: List[DetectionMethod] = []
        if c1_res.is_alert:
            alert_methods.append(DetectionMethod.EARS_C1)
        if c2_res.is_alert:
            alert_methods.append(DetectionMethod.EARS_C2)
        if c3_res.is_alert:
            alert_methods.append(DetectionMethod.EARS_C3)
        if farrington_res.is_alert:
            alert_methods.append(DetectionMethod.FARRINGTON_BOUNDED)

        # Default classification
        signal_level = SignalLevel.NO_SIGNAL
        is_downgraded = False
        downgrade_reason = None

        if is_baseline_insufficient:
            primary_method = DetectionMethod.SUPPRESSED_INSUFFICIENT_BASELINE
            primary_threshold = self.ears_detector.threshold
            is_downgraded = True
            downgrade_reason = "Signal suppressed: Insufficient historical baseline data, incompatible in granularity, or not evaluable."
        else:
            primary_method = DetectionMethod.EARS_C1
            primary_threshold = self.ears_detector.threshold

            if c2_res.is_alert:
                primary_method = DetectionMethod.EARS_C2
                primary_threshold = c2_res.threshold
            elif farrington_res.is_alert:
                primary_method = DetectionMethod.FARRINGTON_BOUNDED
                primary_threshold = farrington_res.threshold
            elif c1_res.is_alert:
                primary_method = DetectionMethod.EARS_C1
                primary_threshold = c1_res.threshold
            elif c3_res.is_alert:
                primary_method = DetectionMethod.EARS_C3
                primary_threshold = c3_res.threshold

        has_any_alert = len(alert_methods) > 0 and not is_baseline_insufficient

        # Multi-detector consensus check
        has_multi_detector = len(alert_methods) >= 2 and not is_baseline_insufficient

        if is_baseline_insufficient:
            signal_level = SignalLevel.NO_SIGNAL
        elif has_multi_detector and reliability == BaselineReliability.STABLE_BASELINE and independent_sources >= 2:
            signal_level = SignalLevel.STRONG_SIGNAL
            primary_method = DetectionMethod.MULTI_DETECTOR
        elif has_any_alert or (z_score and z_score >= 2.0):
            # Candidate for SIGNAL
            if reliability in (
                BaselineReliability.INSUFFICIENT_HISTORY,
                BaselineReliability.INCOMPATIBLE_GRANULARITY,
                BaselineReliability.NOT_EVALUABLE,
            ):
                signal_level = SignalLevel.NO_SIGNAL
                is_downgraded = True
                downgrade_reason = "Signal suppressed: Insufficient historical baseline data, incompatible in granularity, or not evaluable."
            elif reliability == BaselineReliability.CONFLICTING_DATA:
                signal_level = SignalLevel.WATCH
                is_downgraded = True
                downgrade_reason = "Downgraded from SIGNAL to WATCH due to conflicting quantity reports in target period"
            elif independent_sources < 2 and reliability == BaselineReliability.HIGH_VARIANCE:
                signal_level = SignalLevel.WATCH
                is_downgraded = True
                downgrade_reason = "Downgraded from SIGNAL to WATCH: single reporting source under high historical variance"
            elif reliability == BaselineReliability.SPARSE_HISTORY and exp_val == 0.0:
                signal_level = SignalLevel.NO_SIGNAL
                is_downgraded = True
                downgrade_reason = "Signal suppressed: Historical baseline has zero variation (sparse history); statistical deviation cannot be inferred."
            else:
                signal_level = SignalLevel.SIGNAL
        elif (z_score and z_score >= 1.5):
            if reliability in (
                BaselineReliability.INSUFFICIENT_HISTORY,
                BaselineReliability.SPARSE_HISTORY,
                BaselineReliability.INCOMPATIBLE_GRANULARITY,
                BaselineReliability.NOT_EVALUABLE,
            ):
                signal_level = SignalLevel.NO_SIGNAL
                is_downgraded = True
                downgrade_reason = "Signal suppressed: Insufficient or incompatible baseline observations."
            else:
                signal_level = SignalLevel.WATCH
        elif (calc_val > exp_val and exp_val == 0.0 and calc_val > 0):
            if reliability == BaselineReliability.STABLE_BASELINE:
                signal_level = SignalLevel.WATCH
            else:
                signal_level = SignalLevel.NO_SIGNAL
                is_downgraded = True
                downgrade_reason = "Signal suppressed: Baseline expectation of 0 with insufficient historical depth."
        else:
            if reliability in (
                BaselineReliability.INSUFFICIENT_HISTORY,
                BaselineReliability.INCOMPATIBLE_GRANULARITY,
                BaselineReliability.NOT_EVALUABLE,
            ):
                is_downgraded = True
                downgrade_reason = f"Statistical baseline comparison suppressed: {reliability.value}."

        # Construct Explainable Rationale
        obs_disp = f"{obs_val:.1f}" if obs_val is not None else "Not reported"
        rationale_lines = [
            f"1. Observed: {obs_disp} {value_type} across {target_bin.fused_event_count} fused events ({independent_sources} independent sources).",
            f"2. Expected: {exp_val:.2f} {value_type} (baseline median: {baseline.baseline_median:.2f}, std: {baseline.baseline_std:.2f}).",
            f"3. Deviation: {dev:+.2f} ({f'Z-score: {z_score:+.2f}' if z_score is not None else 'N/A'}).",
            f"4. Detectors Triggered: {[m.value for m in alert_methods] if alert_methods else 'None'}.",
            f"5. Historical Support: {baseline.number_of_historical_bins} historical weeks ({baseline.number_of_nonzero_bins} non-zero periods), status: {reliability.value}.",
            f"6. Source Support: {independent_sources} independent source groups ({target_bin.supporting_observation_count} total articles).",
            f"7. Classification: {signal_level.value.upper()} ({downgrade_reason or 'Criterion satisfied under baseline parameters'}).",
        ]
        explainable_rationale = "\n".join(rationale_lines)

        seed = f"{target_bin.disease_key}:{target_bin.geo_key}:{target_bin.period_start.isoformat()}:signal"
        deterministic_signal_id = uuid5(NAMESPACE_DNS, seed)

        return SignalObservation(
            signal_id=deterministic_signal_id,
            disease_key=target_bin.disease_key,
            geo_key=target_bin.geo_key,
            target_period_start=target_bin.period_start,
            target_period_end=target_bin.period_end,
            observed_value=obs_val,
            expected_value=round(exp_val, 3),
            deviation=round(dev, 3),
            standardized_score=z_score,
            threshold=round(primary_threshold, 3),
            origin=getattr(target_bin, "origin", OriginClassification.HISTORICAL_CORPUS),
            detection_method=primary_method,
            signal_level=signal_level,
            supporting_fused_event_ids=target_bin.fused_event_ids,
            supporting_source_count=independent_sources,
            reliability_status=reliability,
            is_downgraded=is_downgraded,
            downgrade_reason=downgrade_reason,
            explainable_rationale=explainable_rationale,
            provenance_references=target_bin.provenance_references,
            created_at=target_bin.period_end,
        )

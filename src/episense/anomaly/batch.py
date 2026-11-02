"""
Batch Processing Engine for EpiSense Signal Detection (Phase 8).
Executes end-to-end time-series aggregation, rolling baseline estimation,
and statistical anomaly detection across FusedEvent collections.
"""

from collections import defaultdict
import json
from pathlib import Path
import time
from typing import Dict, List, Optional, Tuple
from pydantic import BaseModel, Field

from episense.schemas.base import utc_now
from episense.schemas.event import FusedEvent
from episense.schemas.signal import (
    BaselineEstimate,
    BaselineReliability,
    EpidemiologicalTimeBin,
    SignalLevel,
    SignalObservation,
)
from episense.baseline.timeseries import TimeSeriesBuilder
from episense.baseline.engine import BaselineEngine
from episense.anomaly.detector import SignalDetector
from episense.logging import get_logger

logger = get_logger("anomaly.batch")


class SignalBatchReport(BaseModel):
    """
    Deterministic summary report for a signal detection batch run.
    """
    total_fused_events_consumed: int = Field(ge=0)
    total_time_series_bins: int = Field(ge=0)
    total_distinct_series: int = Field(ge=0)
    total_baseline_estimates: int = Field(ge=0)
    insufficient_history_estimates: int = Field(ge=0)
    sparse_history_estimates: int = Field(ge=0)
    stable_baseline_estimates: int = Field(ge=0)
    total_signals_detected: int = Field(ge=0)
    signals_by_level: Dict[str, int] = Field(default_factory=dict)
    signals_by_detector: Dict[str, int] = Field(default_factory=dict)
    signals_by_disease: Dict[str, int] = Field(default_factory=dict)
    signals_by_geo: Dict[str, int] = Field(default_factory=dict)
    elapsed_seconds: float = Field(ge=0.0)
    pipeline_version: str = "1.0.0"
    generated_at: str = Field(default_factory=lambda: utc_now().isoformat())


class SignalBatchRunner:
    """
    Coordinates batch execution of Phase 8 statistical baselines and signal detection.
    """

    def __init__(
        self,
        output_dir: str = "data/signals",
        ears_threshold: float = 2.0,
        farrington_z: float = 1.96,
        min_sample_size: int = 3,
        value_type: str = "cases",
    ):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.value_type = value_type

        self.ts_builder = TimeSeriesBuilder()
        self.baseline_engine = BaselineEngine(min_sample_size=min_sample_size)
        self.detector = SignalDetector(
            ears_threshold=ears_threshold,
            farrington_z=farrington_z,
        )

    def process_fused_events(
        self,
        fused_events: List[FusedEvent],
        run_name: str = "batch_run",
    ) -> Tuple[SignalBatchReport, List[EpidemiologicalTimeBin], List[BaselineEstimate], List[SignalObservation]]:
        """
        Executes end-to-end signal processing on a collection of FusedEvents.
        """
        t0 = time.time()

        # 1. Build weekly EpidemiologicalTimeBins
        all_bins = self.ts_builder.build_weekly_bins(fused_events)

        # 2. Group bins by distinct series: (disease_key, geo_key)
        series_map: Dict[Tuple[str, str], List[EpidemiologicalTimeBin]] = defaultdict(list)
        for b in all_bins:
            series_map[(b.disease_key, b.geo_key)].append(b)

        # 3. For each series, compute baselines and signals chronologically
        all_baselines: List[BaselineEstimate] = []
        all_signals: List[SignalObservation] = []

        insufficient_count = 0
        sparse_count = 0
        stable_count = 0

        # Sort series keys deterministically
        sorted_series_keys = sorted(series_map.keys())

        for key in sorted_series_keys:
            bins = sorted(series_map[key], key=lambda x: x.period_start)

            for i, target_bin in enumerate(bins):
                # Segregated historical background bins (e.g. ISO 1970) are historical reference data only
                if target_bin.iso_year < 2000 or target_bin.completeness_status == "historical_background":
                    continue

                historical_bins = bins[:i]

                # Compute baseline estimate
                baseline = self.baseline_engine.compute_baseline(
                    historical_bins=historical_bins,
                    target_bin=target_bin,
                    value_type=self.value_type,
                )
                all_baselines.append(baseline)

                rel = baseline.reliability_status
                if rel == BaselineReliability.INSUFFICIENT_HISTORY:
                    insufficient_count += 1
                elif rel == BaselineReliability.SPARSE_HISTORY:
                    sparse_count += 1
                elif rel == BaselineReliability.STABLE_BASELINE:
                    stable_count += 1

                # Detect early warning signal
                signal = self.detector.detect_signal(
                    historical_bins=historical_bins,
                    target_bin=target_bin,
                    baseline=baseline,
                    value_type=self.value_type,
                )
                all_signals.append(signal)

        elapsed = round(time.time() - t0, 3)

        # 4. Generate summary report metrics
        signals_by_level = defaultdict(int)
        signals_by_detector = defaultdict(int)
        signals_by_disease = defaultdict(int)
        signals_by_geo = defaultdict(int)

        for sig in all_signals:
            signals_by_level[sig.signal_level.value] += 1
            if sig.signal_level in (SignalLevel.WATCH, SignalLevel.SIGNAL, SignalLevel.STRONG_SIGNAL):
                signals_by_detector[sig.detection_method.value] += 1
                signals_by_disease[sig.disease_key] += 1
                signals_by_geo[sig.geo_key] += 1

        active_signals = sum(
            1 for s in all_signals if s.signal_level in (SignalLevel.WATCH, SignalLevel.SIGNAL, SignalLevel.STRONG_SIGNAL)
        )

        report = SignalBatchReport(
            total_fused_events_consumed=len(fused_events),
            total_time_series_bins=len(all_bins),
            total_distinct_series=len(series_map),
            total_baseline_estimates=len(all_baselines),
            insufficient_history_estimates=insufficient_count,
            sparse_history_estimates=sparse_count,
            stable_baseline_estimates=stable_count,
            total_signals_detected=active_signals,
            signals_by_level=dict(signals_by_level),
            signals_by_detector=dict(signals_by_detector),
            signals_by_disease=dict(signals_by_disease),
            signals_by_geo=dict(signals_by_geo),
            elapsed_seconds=elapsed,
        )

        # 5. Serialize outputs deterministically
        run_dir = self.output_dir / run_name
        run_dir.mkdir(parents=True, exist_ok=True)

        (run_dir / "time_series_bins.json").write_text(
            json.dumps([b.model_dump(mode="json") for b in all_bins], indent=2),
            encoding="utf-8",
        )
        (run_dir / "baseline_estimates.json").write_text(
            json.dumps([b.model_dump(mode="json") for b in all_baselines], indent=2),
            encoding="utf-8",
        )
        (run_dir / "signal_observations.json").write_text(
            json.dumps([s.model_dump(mode="json") for s in all_signals], indent=2),
            encoding="utf-8",
        )
        (run_dir / "signal_batch_report.json").write_text(
            report.model_dump_json(indent=2),
            encoding="utf-8",
        )

        return report, all_bins, all_baselines, all_signals

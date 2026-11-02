"""
Batch Alert Scoring Engine for EpiSense (Phase 9).
Processes SignalObservation collections into prioritized, deterministic
EpidemiologicalAlert streams with comprehensive summary reports.
"""

from collections import defaultdict
import json
from pathlib import Path
import time
from typing import Dict, List, Optional, Tuple
from uuid import UUID
from pydantic import BaseModel, Field

from episense.schemas.base import utc_now
from episense.schemas.alert import AlertTier, EpidemiologicalAlert, PathogenThreatTier
from episense.schemas.event import FusedEvent
from episense.schemas.signal import BaselineEstimate, EpidemiologicalTimeBin, SignalObservation
from episense.scoring.scorer import AlertScorer
from episense.logging import get_logger

logger = get_logger("scoring.batch")


class AlertBatchReport(BaseModel):
    """
    Deterministic summary report for an alert scoring batch execution.
    """
    total_signals_consumed: int = Field(ge=0)
    total_alerts_generated: int = Field(ge=0)
    alerts_by_tier: Dict[str, int] = Field(default_factory=dict)
    alerts_by_threat_tier: Dict[str, int] = Field(default_factory=dict)
    gated_alerts_count: int = Field(ge=0)
    alerts_by_disease: Dict[str, int] = Field(default_factory=dict)
    alerts_by_geo: Dict[str, int] = Field(default_factory=dict)
    high_alerts_count: int = Field(ge=0)
    medium_alerts_count: int = Field(ge=0)
    low_alerts_count: int = Field(ge=0)
    informational_alerts_count: int = Field(ge=0)
    elapsed_seconds: float = Field(ge=0.0)
    pipeline_version: str = "1.0.0"
    generated_at: str = Field(default_factory=lambda: utc_now().isoformat())


class AlertBatchRunner:
    """
    Coordinates batch execution of Phase 9 alert scoring and triage.
    """

    def __init__(
        self,
        output_dir: str = "data/alerts",
        scorer: Optional[AlertScorer] = None,
    ):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.scorer = scorer or AlertScorer()

    def process_signals(
        self,
        signals: List[SignalObservation],
        fused_events: Optional[List[FusedEvent]] = None,
        time_bins: Optional[List[EpidemiologicalTimeBin]] = None,
        baselines: Optional[List[BaselineEstimate]] = None,
        run_name: str = "batch_run",
    ) -> Tuple[AlertBatchReport, List[EpidemiologicalAlert]]:
        """
        Scores all provided SignalObservations against fused events and baseline context.
        """
        t0 = time.time()

        # Build lookup indices for fast, exact association
        events_by_id: Dict[UUID, FusedEvent] = {}
        if fused_events:
            for fe in fused_events:
                events_by_id[fe.fused_event_id] = fe

        bins_by_period: Dict[Tuple[str, str, str], EpidemiologicalTimeBin] = {}
        if time_bins:
            for b in time_bins:
                key = (b.disease_key, b.geo_key, b.period_start.isoformat())
                bins_by_period[key] = b

        baselines_by_period: Dict[Tuple[str, str, str], BaselineEstimate] = {}
        if baselines:
            for base in baselines:
                key = (base.disease_key, base.geo_key, base.target_period_start.isoformat())
                baselines_by_period[key] = base

        alerts: List[EpidemiologicalAlert] = []

        # Sort signals deterministically by (disease_key, geo_key, target_period_start)
        sorted_signals = sorted(
            signals,
            key=lambda s: (s.disease_key, s.geo_key, s.target_period_start)
        )

        for sig in sorted_signals:
            # Find associated fused events
            related_fused: List[FusedEvent] = []
            for fid in sig.supporting_fused_event_ids:
                if fid in events_by_id:
                    related_fused.append(events_by_id[fid])

            lookup_key = (sig.disease_key, sig.geo_key, sig.target_period_start.isoformat())
            target_bin = bins_by_period.get(lookup_key)
            target_base = baselines_by_period.get(lookup_key)

            alert = self.scorer.score_signal(
                signal=sig,
                fused_events=related_fused,
                time_bin=target_bin,
                baseline=target_base,
            )
            alerts.append(alert)

        # Sort alerts deterministically: priority order (composite_score desc, period_start desc, disease_key, geo_key)
        alerts.sort(
            key=lambda a: (-a.composite_score, -a.period_start.timestamp(), a.disease_key, a.geo_key)
        )

        elapsed = round(time.time() - t0, 3)

        # Compile report metrics
        tier_counts = defaultdict(int)
        threat_counts = defaultdict(int)
        disease_counts = defaultdict(int)
        geo_counts = defaultdict(int)
        gated_count = 0

        for a in alerts:
            tier_counts[a.alert_tier.value] += 1
            threat_counts[a.pathogen_threat_tier.value] += 1
            if a.alert_tier in (AlertTier.MEDIUM, AlertTier.HIGH):
                disease_counts[a.disease_key] += 1
                geo_counts[a.geo_key] += 1
            if a.is_gated:
                gated_count += 1

        report = AlertBatchReport(
            total_signals_consumed=len(signals),
            total_alerts_generated=len(alerts),
            alerts_by_tier=dict(tier_counts),
            alerts_by_threat_tier=dict(threat_counts),
            gated_alerts_count=gated_count,
            alerts_by_disease=dict(disease_counts),
            alerts_by_geo=dict(geo_counts),
            high_alerts_count=tier_counts[AlertTier.HIGH.value],
            medium_alerts_count=tier_counts[AlertTier.MEDIUM.value],
            low_alerts_count=tier_counts[AlertTier.LOW.value],
            informational_alerts_count=tier_counts[AlertTier.INFORMATIONAL.value],
            elapsed_seconds=elapsed,
        )

        # Serialize outputs deterministically
        run_dir = self.output_dir / run_name
        run_dir.mkdir(parents=True, exist_ok=True)

        (run_dir / "alerts.json").write_text(
            json.dumps([a.model_dump(mode="json") for a in alerts], indent=2),
            encoding="utf-8",
        )
        (run_dir / "alert_batch_report.json").write_text(
            report.model_dump_json(indent=2),
            encoding="utf-8",
        )

        # Generate human-readable alert summary
        summary_data = {
            "total_alerts": len(alerts),
            "high_alerts": tier_counts[AlertTier.HIGH.value],
            "medium_alerts": tier_counts[AlertTier.MEDIUM.value],
            "low_alerts": tier_counts[AlertTier.LOW.value],
            "informational_alerts": tier_counts[AlertTier.INFORMATIONAL.value],
            "top_actionable_alerts": [
                {
                    "alert_id": str(a.alert_id),
                    "disease": a.disease_key,
                    "geography": a.geo_key,
                    "period": a.period_start.strftime("%Y-%m-%d"),
                    "tier": a.alert_tier.value.upper(),
                    "score": a.composite_score,
                    "threat": a.pathogen_threat_tier.value,
                    "sources": a.supporting_source_count,
                    "summary": a.explanation.summary,
                    "is_gated": a.is_gated,
                    "gating_reason": a.gating_reason,
                }
                for a in alerts if a.alert_tier in (AlertTier.MEDIUM, AlertTier.HIGH)
            ]
        }
        (run_dir / "alert_summary.json").write_text(
            json.dumps(summary_data, indent=2),
            encoding="utf-8",
        )

        return report, alerts

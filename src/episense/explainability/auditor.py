"""
Audit Trail Engine for EpiSense (Phase 10).
Records the complete, deterministic decision path from statistical signals
and pathogen threat evaluation to final operational alert tier assignment,
securing integrity with SHA-256 cryptographic state checksums.
"""

import hashlib
import json
from typing import Any, Dict, List, Optional
from uuid import NAMESPACE_DNS, UUID, uuid5

from episense.schemas.alert import EpidemiologicalAlert
from episense.schemas.explainability import AlertAuditTrail, AuditDecisionStep
from episense.schemas.signal import BaselineEstimate, SignalObservation


class AuditTrailEngine:
    """
    Constructs tamper-evident, reproducible audit trails for epidemiological alert decisions.
    """

    def build_audit_trail(
        self,
        alert: EpidemiologicalAlert,
        signal: Optional[SignalObservation] = None,
        baseline: Optional[BaselineEstimate] = None,
    ) -> AlertAuditTrail:
        """
        Records the step-by-step decision sequence and computes a SHA-256 integrity checksum.
        """
        steps: List[AuditDecisionStep] = []
        bd = alert.score_breakdown

        # Step 1: Statistical Anomaly Evaluation
        z_score = signal.standardized_score if signal else None
        method_str = signal.detection_method.value if signal else "unknown"
        level_str = signal.signal_level.value if signal else "unknown"
        steps.append(
            AuditDecisionStep(
                step_number=1,
                step_name="Statistical Anomaly Evaluation",
                inputs={
                    "standardized_z_score": z_score,
                    "detection_method": method_str,
                    "signal_level": level_str,
                },
                rule_applied="Scaled Z-score normalized to [0, 1] with detector consensus bonus and signal level bounds",
                output_value=bd.anomaly_score,
                is_gated=False,
                gating_detail=None,
            )
        )

        # Step 2: Pathogen Clinical Threat Classification
        steps.append(
            AuditDecisionStep(
                step_number=2,
                step_name="Pathogen Clinical Threat Classification",
                inputs={
                    "disease_key": alert.disease_key,
                    "assigned_tier": alert.pathogen_threat_tier.value,
                },
                rule_applied="Deterministic pathogen clinical severity and CFR taxonomy",
                output_value=bd.threat_score,
                is_gated=False,
                gating_detail=None,
            )
        )

        # Step 3: Source Diversity & Authority Corroboration
        steps.append(
            AuditDecisionStep(
                step_number=3,
                step_name="Source Diversity & Authority Corroboration",
                inputs={
                    "independent_source_count": alert.supporting_source_count,
                },
                rule_applied="Independent source count scaling with +0.15 official public health agency bonus",
                output_value=bd.evidence_score,
                is_gated=False,
                gating_detail=None,
            )
        )

        # Step 4: Clinical Assertion & Mortality Assessment
        steps.append(
            AuditDecisionStep(
                step_number=4,
                step_name="Clinical Certainty & Mortality Assessment",
                inputs={
                    "fused_event_count": len(alert.supporting_fused_event_ids),
                },
                rule_applied="Diagnostic assertion weighting (Confirmed 1.0, Suspected 0.7) with +0.20 mortality confirmation",
                output_value=bd.certainty_score,
                is_gated=False,
                gating_detail=None,
            )
        )

        # Step 5: Spatial Granularity Resolution
        steps.append(
            AuditDecisionStep(
                step_number=5,
                step_name="Spatial Granularity Resolution",
                inputs={
                    "geo_key": alert.geo_key,
                },
                rule_applied="Administrative level weighting (Admin 2-4: 1.00, State: 0.75, National: 0.50, Global: 0.30)",
                output_value=bd.spatial_score,
                is_gated=False,
                gating_detail=None,
            )
        )

        # Step 6: Multi-Criteria Composite Scoring
        steps.append(
            AuditDecisionStep(
                step_number=6,
                step_name="Multi-Criteria Composite Scoring",
                inputs={
                    "weights": bd.applied_weights,
                    "dimension_scores": {
                        "anomaly": bd.anomaly_score,
                        "threat": bd.threat_score,
                        "evidence": bd.evidence_score,
                        "certainty": bd.certainty_score,
                        "spatial": bd.spatial_score,
                    },
                },
                rule_applied="Configurable linear weighted sum bounded within [0, 1]",
                output_value=bd.raw_composite_score,
                is_gated=False,
                gating_detail=None,
            )
        )

        # Step 7: Reliability Safety Gating & Ceilings
        gating_reasons_list = [alert.gating_reason] if alert.gating_reason else []
        steps.append(
            AuditDecisionStep(
                step_number=7,
                step_name="Reliability Safety Gating & Ceilings",
                inputs={
                    "raw_score": bd.raw_composite_score,
                    "penalty_applied": bd.penalty_applied,
                    "is_gated": alert.is_gated,
                    "gating_reason": alert.gating_reason,
                },
                rule_applied="Strict enforcement of data reliability ceilings (INSUFFICIENT_HISTORY, CONFLICTING_DATA, Single Source)",
                output_value=bd.final_score,
                is_gated=alert.is_gated,
                gating_detail=alert.gating_reason,
            )
        )

        # Step 8: Operational Alert Tier Assignment
        steps.append(
            AuditDecisionStep(
                step_number=8,
                step_name="Operational Alert Tier Assignment",
                inputs={
                    "final_score": bd.final_score,
                },
                rule_applied="Calibrated operational thresholds: <0.40 INFORMATIONAL, 0.40-0.64 LOW, 0.65-0.79 MEDIUM, >=0.80 HIGH",
                output_value=alert.alert_tier.value,
                is_gated=alert.is_gated,
                gating_detail=None,
            )
        )

        # Compute deterministic SHA-256 integrity checksum over the canonical JSON representation
        state_dict = {
            "alert_id": str(alert.alert_id),
            "signal_id": str(alert.signal_id),
            "score": bd.final_score,
            "tier": alert.alert_tier.value,
            "weights": bd.applied_weights,
            "steps": [s.model_dump(mode="json") for s in steps],
        }
        canonical_json = json.dumps(state_dict, sort_keys=True)
        checksum = hashlib.sha256(canonical_json.encode("utf-8")).hexdigest()

        deterministic_audit_id = uuid5(
            NAMESPACE_DNS, f"{alert.alert_id}:{checksum[:16]}:audit_trail"
        )

        return AlertAuditTrail(
            audit_id=deterministic_audit_id,
            alert_id=alert.alert_id,
            signal_id=alert.signal_id,
            decision_steps=steps,
            applied_weights=bd.applied_weights,
            score_breakdown=bd,
            final_score=bd.final_score,
            final_alert_tier=alert.alert_tier,
            is_gated=alert.is_gated,
            gating_reasons=gating_reasons_list,
            audit_checksum=checksum,
            created_at=alert.period_end,
        )

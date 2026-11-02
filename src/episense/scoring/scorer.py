"""
Epidemiological Alert Scorer and Risk Assessment Engine for EpiSense (Phase 9).
Calculates multi-criteria composite risk scores, applies data-reliability
safety ceilings, and outputs deterministic, explainable EpidemiologicalAlert records.
"""

from typing import Any, Dict, List, Optional
from uuid import NAMESPACE_DNS, UUID, uuid5

from episense.schemas.alert import (
    AlertExplanation,
    AlertTier,
    EpidemiologicalAlert,
    PathogenThreatTier,
    RecommendedReviewAction,
    RiskScoreBreakdown,
)
from episense.schemas.document import OriginClassification
from episense.schemas.assertion import AssertionStatus
from episense.schemas.event import FusedEvent
from episense.schemas.signal import (
    BaselineEstimate,
    BaselineReliability,
    DetectionMethod,
    EpidemiologicalTimeBin,
    SignalLevel,
    SignalObservation,
)
from episense.scoring.threat import PathogenThreatClassifier
from episense.scoring.explainer import AlertExplainer


class AlertScorer:
    """
    Coordinates multi-criteria epidemiological risk assessment for surveillance signals.
    """

    OFFICIAL_SOURCE_KEYWORDS = (
        "pib", "mohfw", "who", "cdc", "promed", "idsp", "gov", "ministry", "health"
    )

    STATE_GEOS = {
        "kerala", "gujarat", "karnataka", "odisha", "delhi",
        "west bengal", "rajasthan", "telangana", "bihar", "maharashtra",
        "tamil nadu", "uttar pradesh", "assam", "punjab", "haryana"
    }

    DISTRICT_GEOS = {
        "kozhikode", "malda", "rayagada", "pune", "kolkata",
        "bengaluru", "ahmedabad", "surat", "patna", "jaipur"
    }

    def __init__(
        self,
        weight_anomaly: float = 0.30,
        weight_threat: float = 0.25,
        weight_evidence: float = 0.20,
        weight_certainty: float = 0.15,
        weight_spatial: float = 0.10,
        threat_classifier: Optional[PathogenThreatClassifier] = None,
        explainer: Optional[AlertExplainer] = None,
    ):
        self.weights = {
            "anomaly": weight_anomaly,
            "threat": weight_threat,
            "evidence": weight_evidence,
            "certainty": weight_certainty,
            "spatial": weight_spatial,
        }
        total_w = sum(self.weights.values())
        if abs(total_w - 1.0) > 1e-4:
            raise ValueError(f"AlertScorer weights must sum to 1.0; got {total_w:.4f}")

        self.threat_classifier = threat_classifier or PathogenThreatClassifier()
        self.explainer = explainer or AlertExplainer()

    @classmethod
    def from_config(cls, scoring_config: Any) -> "AlertScorer":
        """
        Creates an AlertScorer from a ScoringConfig instance.
        """
        if getattr(scoring_config, "weight_threat", None) is not None:
            w_ev = scoring_config.weight_evidence or scoring_config.weight_diversity
            w_cert = scoring_config.weight_certainty or scoring_config.weight_assertion
            return cls(
                weight_anomaly=scoring_config.weight_anomaly,
                weight_threat=scoring_config.weight_threat,
                weight_evidence=w_ev,
                weight_certainty=w_cert,
                weight_spatial=scoring_config.weight_spatial,
            )
        return cls()

    def score_signal(
        self,
        signal: SignalObservation,
        fused_events: Optional[List[FusedEvent]] = None,
        time_bin: Optional[EpidemiologicalTimeBin] = None,
        baseline: Optional[BaselineEstimate] = None,
    ) -> EpidemiologicalAlert:
        """
        Calculates a multi-criteria risk score for a SignalObservation and emits
        a fully explained, provenance-preserving EpidemiologicalAlert.
        """
        fused_events = fused_events or []
        gating_reasons: List[str] = []

        # -------------------------------------------------------------
        # 1. Dimension: Statistical Anomaly (S_anomaly)
        # -------------------------------------------------------------
        if signal.signal_level == SignalLevel.NO_SIGNAL:
            s_anomaly = 0.0
        else:
            z = signal.standardized_score
            if z is not None:
                # Scaled Z: Z=1.0 -> 0.0, Z=2.0 -> 0.33, Z=3.0 -> 0.67, Z>=4.0 -> 1.0
                s_z = min(1.0, max(0.0, (z - 1.0) / 3.0))
            else:
                s_z = 0.33

            # Consensus boost
            if signal.detection_method == DetectionMethod.MULTI_DETECTOR:
                s_z = min(1.0, s_z + 0.15)

            # Signal level bounds
            if signal.signal_level == SignalLevel.STRONG_SIGNAL:
                s_anomaly = max(s_z, 0.85)
            elif signal.signal_level == SignalLevel.SIGNAL:
                s_anomaly = max(s_z, 0.65)
            elif signal.signal_level == SignalLevel.WATCH:
                s_anomaly = min(0.60, max(0.25, s_z))
            else:
                s_anomaly = s_z

        # -------------------------------------------------------------
        # 2. Dimension: Pathogen Clinical Threat (S_threat)
        # -------------------------------------------------------------
        threat_tier = self.threat_classifier.classify(signal.disease_key)
        s_threat = self.threat_classifier.get_score(threat_tier)

        # -------------------------------------------------------------
        # 3. Dimension: Source Evidence & Diversity (S_evidence)
        # -------------------------------------------------------------
        source_count = signal.supporting_source_count
        if time_bin and time_bin.independent_source_count > source_count:
            source_count = time_bin.independent_source_count

        if source_count >= 3:
            s_evidence_base = 1.00
        elif source_count == 2:
            s_evidence_base = 0.70
        else:
            s_evidence_base = 0.35

        # Check official public health agency presence
        has_official = False
        for fe in fused_events:
            for sg in fe.independent_sources:
                combined = f"{sg.source_id} {sg.independence_group}".lower()
                if any(k in combined for k in self.OFFICIAL_SOURCE_KEYWORDS):
                    has_official = True
                    break
            if has_official:
                break

        if not has_official and signal.provenance_references:
            for ref in signal.provenance_references:
                if any(k in ref.source_id.lower() for k in self.OFFICIAL_SOURCE_KEYWORDS):
                    has_official = True
                    break

        s_evidence = min(1.00, s_evidence_base + (0.15 if has_official else 0.0))

        # -------------------------------------------------------------
        # 4. Dimension: Clinical Certainty & Mortality (S_certainty)
        # -------------------------------------------------------------
        has_confirmed = any(fe.assertion_status == AssertionStatus.CONFIRMED for fe in fused_events)
        has_suspected = any(fe.assertion_status == AssertionStatus.SUSPECTED for fe in fused_events)
        has_historical = any(fe.assertion_status == AssertionStatus.HISTORICAL for fe in fused_events)
        all_negated = len(fused_events) > 0 and all(fe.assertion_status == AssertionStatus.NEGATED for fe in fused_events)

        if all_negated:
            s_certainty_base = 0.00
            assertion_str = "negated"
        elif has_confirmed:
            s_certainty_base = 1.00
            assertion_str = "confirmed"
        elif has_suspected:
            s_certainty_base = 0.70
            assertion_str = "suspected"
        elif has_historical:
            s_certainty_base = 0.20
            assertion_str = "historical"
        else:
            s_certainty_base = 0.70  # Default assumption for structured observation
            assertion_str = "observed"

        # Check verified mortality
        has_mortality = False
        if time_bin and time_bin.observed_death_count and time_bin.observed_death_count > 0:
            has_mortality = True
        else:
            for fe in fused_events:
                q = fe.aggregated_quantities
                if q.death_count and q.death_count > 0:
                    has_mortality = True
                    break

        s_certainty = min(1.00, s_certainty_base + (0.20 if has_mortality else 0.0))

        # -------------------------------------------------------------
        # 5. Dimension: Spatial Resolution & Granularity (S_spatial)
        # -------------------------------------------------------------
        geo_norm = signal.geo_key.lower().strip()
        if geo_norm in ("unspecified_or_global", "unspecified", "global"):
            s_spatial = 0.30
        elif any(fe.canonical_location and fe.canonical_location.geographic_level in ("district", "city", "subdistrict") for fe in fused_events):
            s_spatial = 1.00
        elif any(fe.canonical_location and fe.canonical_location.geographic_level == "state" for fe in fused_events):
            s_spatial = 0.75
        elif any(fe.canonical_location and fe.canonical_location.geographic_level == "country" for fe in fused_events):
            s_spatial = 0.50
        elif geo_norm in self.DISTRICT_GEOS:
            s_spatial = 1.00
        elif geo_norm in self.STATE_GEOS:
            s_spatial = 0.75
        elif geo_norm == "india":
            s_spatial = 0.50
        else:
            s_spatial = 0.75

        # -------------------------------------------------------------
        # 6. Composite Score Calculation
        # -------------------------------------------------------------
        raw_composite = (
            self.weights["anomaly"] * s_anomaly
            + self.weights["threat"] * s_threat
            + self.weights["evidence"] * s_evidence
            + self.weights["certainty"] * s_certainty
            + self.weights["spatial"] * s_spatial
        )
        raw_composite = round(min(1.0, max(0.0, raw_composite)), 3)

        # -------------------------------------------------------------
        # 7. Reliability-Aware Gating & Safety Ceilings
        # -------------------------------------------------------------
        is_gated = False
        penalty = 0.0

        # Safety Check A: Explicit Negation
        if all_negated:
            final_score = 0.0
            alert_tier = AlertTier.INFORMATIONAL
            is_gated = True
            gating_reasons.append("Negated mention: suppressed to INFORMATIONAL tier (Score: 0.0)")
        elif threat_tier == PathogenThreatTier.NONE:
            # Safety Check A2: Non-communicable or non-pathogen entity
            final_score = min(0.35, round(raw_composite * 0.4, 3))
            alert_tier = AlertTier.INFORMATIONAL
            is_gated = True
            gating_reasons.append("Non-communicable condition / non-pathogen entity: alert locked to INFORMATIONAL (outbreak not applicable)")
        else:
            # Safety Check B: Conflicting Data
            has_conflicts = (
                signal.reliability_status == BaselineReliability.CONFLICTING_DATA
                or (time_bin and time_bin.has_conflicts)
                or any(fe.has_conflicts for fe in fused_events)
            )
            if has_conflicts:
                penalty += 0.10
                is_gated = True
                gating_reasons.append("Conflicting quantity reports detected across sources: -0.10 penalty applied")

            candidate_score = max(0.0, raw_composite - penalty)

            # Safety Check C: Insufficient Historical Baseline
            if signal.reliability_status == BaselineReliability.INSUFFICIENT_HISTORY:
                is_gated = True
                # If high-consequence pathogen with multi-source corroboration, allow up to MEDIUM
                if threat_tier == PathogenThreatTier.TIER_4_HIGH_CONSEQUENCE and source_count >= 2:
                    if candidate_score > 0.79:
                        candidate_score = 0.79
                        gating_reasons.append("Insufficient historical baseline (N < 3): score capped at MEDIUM (0.79)")
                else:
                    if candidate_score > 0.64:
                        candidate_score = 0.64
                        gating_reasons.append("Insufficient historical baseline (N < 3): score capped at LOW (0.64)")

            # Safety Check D: Conflicting Data Ceiling (cannot reach HIGH)
            if has_conflicts and candidate_score > 0.79:
                candidate_score = 0.79
                gating_reasons.append("Conflicting data ceiling: alert capped at MEDIUM (0.79)")

            # Safety Check E: Single Source Isolation (cannot reach HIGH)
            if source_count == 1 and candidate_score > 0.79:
                candidate_score = 0.79
                is_gated = True
                gating_reasons.append("Single reporting source: alert capped at MEDIUM (0.79)")

            final_score = round(min(1.0, max(0.0, candidate_score)), 3)

            # Assign AlertTier
            if final_score < 0.40:
                alert_tier = AlertTier.INFORMATIONAL
            elif final_score < 0.65:
                alert_tier = AlertTier.LOW
            elif final_score < 0.80:
                alert_tier = AlertTier.MEDIUM
            else:
                alert_tier = AlertTier.HIGH

        # -------------------------------------------------------------
        # 8. Dossier Generation & Deterministic ID
        # -------------------------------------------------------------
        breakdown = RiskScoreBreakdown(
            anomaly_score=round(s_anomaly, 3),
            threat_score=round(s_threat, 3),
            evidence_score=round(s_evidence, 3),
            certainty_score=round(s_certainty, 3),
            spatial_score=round(s_spatial, 3),
            raw_composite_score=raw_composite,
            penalty_applied=round(penalty, 3),
            final_score=final_score,
            applied_weights=dict(self.weights),
        )

        explanation = self.explainer.generate_explanation(
            disease_key=signal.disease_key,
            geo_key=signal.geo_key,
            pathogen_threat_tier=threat_tier,
            breakdown=breakdown,
            alert_tier=alert_tier,
            is_gated=is_gated,
            gating_reasons=gating_reasons,
            signal=signal,
            source_count=source_count,
            has_mortality=has_mortality,
            assertion_status=assertion_str,
        )

        # Deterministic UUID5 alert_id
        seed = f"{signal.disease_key}:{signal.geo_key}:{signal.target_period_start.isoformat()}:{signal.signal_id}:alert"
        alert_id = uuid5(NAMESPACE_DNS, seed)

        # Aggregate supporting provenance references
        all_provenance = list(signal.provenance_references)
        for fe in fused_events:
            all_provenance.extend(fe.evidence_references)

        # Deduplicate provenance references by (doc_id, start_char, end_char)
        seen_prov = set()
        deduped_prov = []
        for p in all_provenance:
            prov_key = (str(p.document_id), p.start_char, p.end_char)
            if prov_key not in seen_prov:
                seen_prov.add(prov_key)
                deduped_prov.append(p)

        fused_ids = list(signal.supporting_fused_event_ids)
        for fe in fused_events:
            if fe.fused_event_id not in fused_ids:
                fused_ids.append(fe.fused_event_id)

        # Determine alert origin from constituent fused events
        fe_origins = {getattr(fe, "primary_origin", None) for fe in fused_events}
        if OriginClassification.LIVE_EXTERNAL in fe_origins:
            alert_origin = OriginClassification.LIVE_EXTERNAL
        elif OriginClassification.MANUAL_SUBMISSION in fe_origins:
            alert_origin = OriginClassification.MANUAL_SUBMISSION
        elif OriginClassification.BENCHMARK in fe_origins:
            alert_origin = OriginClassification.BENCHMARK
        else:
            alert_origin = OriginClassification.HISTORICAL_CORPUS

        # Determine operational recommended review action
        if all_negated or threat_tier == PathogenThreatTier.NONE:
            recommended_action = RecommendedReviewAction.DISCARD
        elif alert_tier == AlertTier.HIGH:
            recommended_action = RecommendedReviewAction.INVESTIGATE
        elif alert_tier == AlertTier.MEDIUM:
            if threat_tier == PathogenThreatTier.TIER_4_HIGH_CONSEQUENCE or source_count >= 2:
                recommended_action = RecommendedReviewAction.INVESTIGATE
            else:
                recommended_action = RecommendedReviewAction.MONITOR
        elif alert_tier == AlertTier.LOW:
            recommended_action = RecommendedReviewAction.MONITOR
        else:
            recommended_action = RecommendedReviewAction.INFORMATIONAL

        indicator_anomaly = {
            "baseline_eligibility": signal.reliability_status.value if hasattr(signal.reliability_status, "value") else str(signal.reliability_status),
            "standardized_score": signal.standardized_score,
            "signal_level": signal.signal_level.value if hasattr(signal.signal_level, "value") else str(signal.signal_level),
            "primary_method": signal.detection_method.value if hasattr(signal.detection_method, "value") else str(signal.detection_method),
            "is_gated": is_gated,
            "gating_reasons": list(gating_reasons),
        }

        return EpidemiologicalAlert(
            alert_id=alert_id,
            signal_id=signal.signal_id,
            disease_key=signal.disease_key,
            geo_key=signal.geo_key,
            pathogen_threat_tier=threat_tier,
            period_start=signal.target_period_start,
            period_end=signal.target_period_end,
            composite_score=final_score,
            event_triage_score=final_score,
            alert_tier=alert_tier,
            recommended_action=recommended_action,
            origin=alert_origin,
            is_gated=is_gated,
            gating_reason="; ".join(gating_reasons) if gating_reasons else None,
            indicator_anomaly_result=indicator_anomaly,
            score_breakdown=breakdown,
            explanation=explanation,
            supporting_fused_event_ids=fused_ids,
            supporting_source_count=source_count,
            provenance_references=deduped_prov,
            created_at=signal.target_period_end,
        )

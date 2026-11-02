"""
Explainability Dossier Generator for EpiSense Alert Scoring (Phase 9).
Synthesizes transparent, auditable narratives and driving factors
for every emitted EpidemiologicalAlert.
"""

from typing import List, Optional
from episense.schemas.alert import (
    AlertExplanation,
    AlertTier,
    PathogenThreatTier,
    RiskScoreBreakdown,
)
from episense.schemas.signal import SignalObservation


class AlertExplainer:
    """
    Constructs deterministic, human-readable explainability dossiers for public health alerts.
    """

    def generate_explanation(
        self,
        disease_key: str,
        geo_key: str,
        pathogen_threat_tier: PathogenThreatTier,
        breakdown: RiskScoreBreakdown,
        alert_tier: AlertTier,
        is_gated: bool,
        gating_reasons: List[str],
        signal: SignalObservation,
        source_count: int,
        has_mortality: bool = False,
        assertion_status: str = "confirmed",
    ) -> AlertExplanation:
        """
        Synthesizes an AlertExplanation with summary, driving factors, and detailed narrative.
        """
        # 1. Summary
        obs_disp = f"{signal.observed_value:.1f}" if signal.observed_value is not None else "Not reported"
        summary = (
            f"[{alert_tier.value.upper()}] {disease_key.title()} in {geo_key} "
            f"(Score: {breakdown.final_score:.2f}, {alert_tier.value.upper()}) - "
            f"Observed: {obs_disp} vs Expected: {signal.expected_value:.2f}."
        )

        # 2. Key Driving Factors
        driving_factors: List[str] = []

        # Threat
        if pathogen_threat_tier == PathogenThreatTier.TIER_4_HIGH_CONSEQUENCE:
            driving_factors.append(f"High-Consequence Pathogen (Tier 4): Extreme clinical severity/CFR ({disease_key.title()})")
        elif pathogen_threat_tier == PathogenThreatTier.TIER_3_SEVERE:
            driving_factors.append(f"Severe Epidemic Pathogen (Tier 3): High morbidity/outbreak risk ({disease_key.title()})")
        elif pathogen_threat_tier == PathogenThreatTier.TIER_2_MODERATE:
            driving_factors.append(f"Outbreak-Prone Endemic Pathogen (Tier 2): Vector-borne/seasonal risk ({disease_key.title()})")
        else:
            driving_factors.append(f"Mild/Syndromic Condition (Tier 1): Routine baseline ({disease_key.title()})")

        # Anomaly
        z_str = f"+{signal.standardized_score:.2f}" if signal.standardized_score is not None else "N/A"
        driving_factors.append(
            f"Statistical Aberration: {signal.detection_method.value.upper()} triggered (Z-score: {z_str}, deviation: {signal.deviation:+.2f})"
        )

        # Evidence & Corroboration
        driving_factors.append(
            f"Evidence Corroboration: {source_count} independent source group(s)"
        )

        # Assertion & Mortality
        mort_str = "with reported mortality" if has_mortality else "without reported deaths"
        driving_factors.append(
            f"Clinical Assertion: {assertion_status.upper()} {mort_str}"
        )

        # Spatial
        driving_factors.append(
            f"Geospatial Resolution: {geo_key} (spatial score: {breakdown.spatial_score:.2f})"
        )

        # 3. Gating Rationale
        gating_rationale: Optional[str] = None
        if is_gated and gating_reasons:
            gating_rationale = "; ".join(gating_reasons)

        # 4. Detailed Narrative Audit Trail
        narrative_lines = [
            f"EPIDEMIOLOGICAL ALERT AUDIT DOSSIER",
            f"--------------------------------------------------",
            f"Target: {disease_key.title()} in {geo_key}",
            f"Surveillance Period: {signal.target_period_start.strftime('%Y-%m-%d')} to {signal.target_period_end.strftime('%Y-%m-%d')}",
            f"Composite Risk Score: {breakdown.final_score:.3f} (Raw: {breakdown.raw_composite_score:.3f}, Penalty: -{breakdown.penalty_applied:.2f})",
            f"Assigned Operational Tier: {alert_tier.value.upper()}",
            f"",
            f"DIMENSION EVALUATION:",
            f"1. Statistical Anomaly: score={breakdown.anomaly_score:.2f} (weight={breakdown.applied_weights.get('anomaly', 0.30):.2f})",
            f"   - Phase 8 Method: {signal.detection_method.value}",
            f"   - Phase 8 Level: {signal.signal_level.value.upper()}",
            f"   - Standardized Z: {z_str}",
            f"2. Pathogen Threat: score={breakdown.threat_score:.2f} (weight={breakdown.applied_weights.get('threat', 0.25):.2f})",
            f"   - Tier: {pathogen_threat_tier.value.upper()}",
            f"3. Source Evidence: score={breakdown.evidence_score:.2f} (weight={breakdown.applied_weights.get('evidence', 0.20):.2f})",
            f"   - Independent Sources: {source_count}",
            f"4. Clinical Certainty: score={breakdown.certainty_score:.2f} (weight={breakdown.applied_weights.get('certainty', 0.15):.2f})",
            f"   - Status: {assertion_status.upper()}, Mortality Reported: {has_mortality}",
            f"5. Spatial Granularity: score={breakdown.spatial_score:.2f} (weight={breakdown.applied_weights.get('spatial', 0.10):.2f})",
            f"   - Location Locus: {geo_key}",
            f"",
            f"SAFETY GATING & CEILINGS:",
            f"   - Gated Status: {'ACTIVE' if is_gated else 'NONE'}",
            f"   - Gating Details: {gating_rationale or 'All criteria met without reliability constraints.'}",
        ]
        detailed_narrative = "\n".join(narrative_lines)

        return AlertExplanation(
            summary=summary,
            driving_factors=driving_factors,
            gating_rationale=gating_rationale,
            detailed_narrative=detailed_narrative,
        )

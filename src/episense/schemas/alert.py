"""
Epidemiological Alert and Risk Assessment Schemas for EpiSense (Phase 9).
Defines strongly typed Pydantic models for multi-criteria risk scoring,
threat tiering, safety gating, explainability audit dossiers, and evidence-based decision categories.
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4
from pydantic import Field, model_validator

from episense.schemas.base import EpiSenseBaseModel, utc_now
from episense.schemas.document import OriginClassification
from episense.schemas.event import EvidenceReference


class AlertTier(str, Enum):
    """
    Cautious operational alert tier for public health triage.
    NOTE: An alert represents an epidemiological risk prioritization,
    NEVER an automated clinical diagnosis or official outbreak declaration.
    """
    INFORMATIONAL = "informational"  # [0.00, 0.40) - Routine observation or background noise
    LOW = "low"                      # [0.40, 0.65) - Mild aberration or uncorroborated single source
    MEDIUM = "medium"                # [0.65, 0.80) - Notable aberration with corroboration or unverified high threat
    HIGH = "high"                    # [0.80, 1.00] - Multi-source corroborated high-threat event on stable baseline


class DecisionCategory(str, Enum):
    """
    Explainable, evidence-based user decision categories.
    Replaces arbitrary risk-score decimals in the primary user workflow.
    """
    INFORMATIONAL = "informational"             # Relevant report detected, but insufficient evidence for stronger conclusion
    NEEDS_REVIEW = "needs_review"               # Credible relevant report with unresolved clinical cases or potentially actionable event
    CORROBORATED_EVENT = "corroborated_event"   # Genuinely independent sources corroborate the same event
    STATISTICAL_ANOMALY = "statistical_anomaly" # Valid numerical observation deviates from an eligible baseline under detector
    FORECAST_AVAILABLE = "forecast_available"   # Eligible model returns forecast with documented limitations
    SUPPRESSED = "suppressed"                   # Data quality or baseline requirements not met
    HISTORICAL_REFERENCE = "historical_reference" # Relevant evidence about an old event, not a current incident
    DISMISSED_RESOLVED = "dismissed_resolved"   # Investigated and resolved or dismissed


class RecommendedReviewAction(str, Enum):
    """
    Operational review actions for public health analysts.
    """
    INVESTIGATE = "investigate"      # Immediate epidemiologist investigation & verification
    MONITOR = "monitor"              # Active tracking for escalation or geographical spread
    INFORMATIONAL = "informational"  # Passive surveillance logging; baseline-gated or routine
    DISCARD = "discard"              # Ruled out, negated, or non-communicable event


class PathogenThreatTier(str, Enum):
    """
    Categorization of intrinsic biological hazard based on case-fatality rate,
    epidemic potential, and availability of medical countermeasures.
    """
    NONE = "none"                                        # Non-pathogen, non-communicable, or unclassified
    TIER_1_MILD = "tier_1_mild"                          # Common endemic: Influenza, Chickenpox, Mumps
    TIER_2_MODERATE = "tier_2_moderate"                  # Outbreak-prone vector: Dengue, Malaria, Chikungunya
    TIER_3_SEVERE = "tier_3_severe"                      # High morbidity/fatality: Cholera, Leptospirosis, KFD, Rabies
    TIER_4_HIGH_CONSEQUENCE = "tier_4_high_consequence"  # Severe emerging: Nipah, CCHF, Ebola, Marburg, Avian Flu


class RiskScoreBreakdown(EpiSenseBaseModel):
    """
    Auditable breakdown of multi-criteria risk scoring dimensions.
    """
    anomaly_score: float = Field(ge=0.0, le=1.0)
    threat_score: float = Field(ge=0.0, le=1.0)
    evidence_score: float = Field(ge=0.0, le=1.0)
    certainty_score: float = Field(ge=0.0, le=1.0)
    spatial_score: float = Field(ge=0.0, le=1.0)
    raw_composite_score: float = Field(ge=0.0, le=1.0)
    penalty_applied: float = Field(default=0.0, ge=0.0, le=1.0)
    final_score: float = Field(ge=0.0, le=1.0)
    applied_weights: Dict[str, float] = Field(default_factory=dict)


class AlertExplanation(EpiSenseBaseModel):
    """
    Human-readable explainability dossier for an epidemiological alert.
    """
    summary: str
    driving_factors: List[str] = Field(default_factory=list)
    gating_rationale: Optional[str] = None
    detailed_narrative: str = ""


class EpidemiologicalAlert(EpiSenseBaseModel):
    """
    Represents an explainable, prioritized epidemiological risk alert synthesized
    from statistical signals, pathogen threat levels, and source corroboration.
    """
    alert_id: UUID = Field(default_factory=uuid4)
    signal_id: UUID
    disease_key: str = Field(min_length=1)
    geo_key: str = Field(min_length=1)
    pathogen_threat_tier: PathogenThreatTier
    period_start: datetime
    period_end: datetime
    composite_score: float = Field(ge=0.0, le=1.0)
    event_triage_score: float = Field(default=0.0, ge=0.0, le=1.0, description="Operational prioritization score (heuristic index in [0,1], NOT outbreak probability)")
    alert_tier: AlertTier
    decision_category: DecisionCategory = Field(
        default=DecisionCategory.INFORMATIONAL,
        description="Explainable, evidence-based decision category (not an uncalibrated probability)"
    )
    currentness_status: str = Field(
        default="CURRENT_EVENT",
        description="Derived currentness classification based on publication/event date"
    )
    recommended_action: RecommendedReviewAction = Field(default=RecommendedReviewAction.INFORMATIONAL, description="Recommended operational triage review action")
    origin: OriginClassification = Field(default=OriginClassification.HISTORICAL_CORPUS)
    is_gated: bool = False
    gating_reason: Optional[str] = None
    indicator_anomaly_result: Optional[Dict[str, Any]] = Field(default=None, description="Statistical detector result with baseline eligibility, statistic, and method")
    score_breakdown: RiskScoreBreakdown
    explanation: AlertExplanation
    supporting_fused_event_ids: List[UUID] = Field(default_factory=list)
    supporting_source_count: int = Field(default=1, ge=0)
    provenance_references: List[EvidenceReference] = Field(default_factory=list)
    status: str = Field(default="active", description="Lifecycle status: 'active', 'superseded', or 'retracted'")
    superseded_by: Optional[UUID] = Field(default=None, description="UUID of superseding alert if superseded")
    retraction_reason: Optional[str] = Field(default=None, description="Audit reason if retracted or superseded")
    created_at: datetime = Field(default_factory=utc_now)

    @model_validator(mode="after")
    def sync_triage_score_and_action(self) -> "EpidemiologicalAlert":
        if self.event_triage_score == 0.0 and self.composite_score > 0.0:
            object.__setattr__(self, "event_triage_score", self.composite_score)
        
        now = datetime.now(timezone.utc)
        current_month_start = datetime(now.year, now.month, 1, 0, 0, 0, tzinfo=timezone.utc)

        p_start = self.period_start
        if p_start.tzinfo is None:
            p_start = p_start.replace(tzinfo=timezone.utc)
        p_end = self.period_end
        if p_end.tzinfo is None:
            p_end = p_end.replace(tzinfo=timezone.utc)

        # Determine temporal currentness
        is_historical = (
            self.origin == OriginClassification.HISTORICAL_CORPUS
            or p_end < current_month_start
        )
        if is_historical:
            object.__setattr__(self, "currentness_status", "HISTORICAL_REFERENCE")
            object.__setattr__(self, "decision_category", DecisionCategory.HISTORICAL_REFERENCE)
            if self.recommended_action == RecommendedReviewAction.INFORMATIONAL:
                object.__setattr__(self, "recommended_action", RecommendedReviewAction.INFORMATIONAL)
        else:
            object.__setattr__(self, "currentness_status", "CURRENT_EVENT")
            # Determine explainable decision category
            if self.is_gated:
                if self.supporting_source_count >= 2:
                    object.__setattr__(self, "decision_category", DecisionCategory.CORROBORATED_EVENT)
                elif self.alert_tier in (AlertTier.HIGH, AlertTier.MEDIUM) or self.pathogen_threat_tier == PathogenThreatTier.TIER_4_HIGH_CONSEQUENCE:
                    object.__setattr__(self, "decision_category", DecisionCategory.NEEDS_REVIEW)
                else:
                    object.__setattr__(self, "decision_category", DecisionCategory.INFORMATIONAL)
            elif self.indicator_anomaly_result and self.indicator_anomaly_result.get("is_anomaly") and not self.indicator_anomaly_result.get("is_gated"):
                object.__setattr__(self, "decision_category", DecisionCategory.STATISTICAL_ANOMALY)
            elif self.supporting_source_count >= 2:
                object.__setattr__(self, "decision_category", DecisionCategory.CORROBORATED_EVENT)
            elif self.alert_tier in (AlertTier.HIGH, AlertTier.MEDIUM):
                object.__setattr__(self, "decision_category", DecisionCategory.NEEDS_REVIEW)
            else:
                object.__setattr__(self, "decision_category", DecisionCategory.INFORMATIONAL)

            if self.recommended_action == RecommendedReviewAction.INFORMATIONAL:
                if self.alert_tier in (AlertTier.HIGH, AlertTier.MEDIUM) or self.pathogen_threat_tier == PathogenThreatTier.TIER_4_HIGH_CONSEQUENCE:
                    object.__setattr__(self, "recommended_action", RecommendedReviewAction.INVESTIGATE)
                elif self.alert_tier == AlertTier.LOW:
                    object.__setattr__(self, "recommended_action", RecommendedReviewAction.MONITOR)

        return self

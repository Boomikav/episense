"""
Explainability, Audit Trail, and Provenance Traversal Schemas for EpiSense (Phase 10).
Defines strongly typed Pydantic models for provenance graphs, reconstructed evidence spans,
deterministic audit decision trails, and human-readable explainability dossiers.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4
from pydantic import Field

from episense.schemas.base import EpiSenseBaseModel, utc_now
from episense.schemas.alert import AlertTier, PathogenThreatTier, RiskScoreBreakdown
from episense.schemas.event import EvidenceReference


class ProvenanceNodeType(str, Enum):
    """Type of entity represented in the provenance graph."""
    ALERT = "alert"
    SIGNAL = "signal"
    BASELINE = "baseline"
    TIME_BIN = "time_bin"
    FUSED_EVENT = "fused_event"
    DOCUMENT = "document"
    EVIDENCE_SPAN = "evidence_span"


class ProvenanceEdgeType(str, Enum):
    """Relationship between two provenance nodes in the directed acyclic graph."""
    SCORED_FROM = "scored_from"              # Alert -> Signal
    BASELINE_FOR = "baseline_for"            # Signal -> Baseline
    AGGREGATED_INTO = "aggregated_into"      # TimeBin -> Signal
    COMPOSED_OF = "composed_of"              # TimeBin -> FusedEvent
    GROUNDED_IN = "grounded_in"              # FusedEvent -> Document
    EVIDENCED_BY = "evidenced_by"            # FusedEvent / Signal -> EvidenceReference
    SPAN_OF = "span_of"                      # EvidenceReference -> Document


class ReconstructedEvidenceSpan(EpiSenseBaseModel):
    """
    Represents an exact character span extracted and validated against raw source document text.
    """
    document_id: UUID
    source_id: str
    start_char: int = Field(ge=0)
    end_char: int = Field(ge=0)
    expected_text: Optional[str] = None
    extracted_text: str = ""
    surrounding_context: str = ""
    attribute_role: str = ""
    extraction_method: str = ""
    is_valid: bool = True
    validation_error: Optional[str] = None


class ProvenanceNode(EpiSenseBaseModel):
    """
    A discrete node in the provenance graph.
    """
    node_id: str
    node_type: ProvenanceNodeType
    entity_id: UUID
    label: str
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ProvenanceEdge(EpiSenseBaseModel):
    """
    A directed edge connecting two provenance nodes.
    """
    source_node_id: str
    target_node_id: str
    edge_type: ProvenanceEdgeType
    description: str = ""


class ProvenanceGraph(EpiSenseBaseModel):
    """
    A directed acyclic graph representing the complete lineage of an epidemiological alert.
    """
    graph_id: UUID = Field(default_factory=uuid4)
    alert_id: UUID
    nodes: List[ProvenanceNode] = Field(default_factory=list)
    edges: List[ProvenanceEdge] = Field(default_factory=list)
    is_acyclic: bool = True
    completeness_ratio: float = Field(ge=0.0, le=1.0, default=1.0)
    missing_nodes: List[str] = Field(default_factory=list)


class AuditDecisionStep(EpiSenseBaseModel):
    """
    A discrete, auditable step in the alert scoring decision path.
    """
    step_number: int = Field(ge=1)
    step_name: str
    inputs: Dict[str, Any] = Field(default_factory=dict)
    rule_applied: str
    output_value: Any
    is_gated: bool = False
    gating_detail: Optional[str] = None


class AlertAuditTrail(EpiSenseBaseModel):
    """
    Complete immutable audit trail recording the exact decision path from input signal to final alert tier.
    Includes a cryptographic SHA-256 checksum of inputs and decisions for audit verification.
    """
    audit_id: UUID = Field(default_factory=uuid4)
    alert_id: UUID
    signal_id: UUID
    decision_steps: List[AuditDecisionStep] = Field(default_factory=list)
    applied_weights: Dict[str, float] = Field(default_factory=dict)
    score_breakdown: RiskScoreBreakdown
    final_score: float = Field(ge=0.0, le=1.0)
    final_alert_tier: AlertTier
    is_gated: bool = False
    gating_reasons: List[str] = Field(default_factory=list)
    audit_checksum: str = Field(description="SHA-256 checksum of decision state")
    created_at: datetime = Field(default_factory=utc_now)


class Epidemiological5W1H(EpiSenseBaseModel):
    """
    Structured epidemiological briefing answering Who, What, When, Where, Why, How, and Action.
    Maintains separate fields for event date, reporting date, active surveillance window,
    and historical baseline window.
    """
    who_pathogen: str
    what_event: str
    when_period: str
    where_location: str
    why_aberration: str
    how_corroboration: str
    recommended_action: str = ""
    event_date: Optional[str] = Field(default=None, description="Clinical onset or start date of outbreak (YYYY-MM-DD)")
    reporting_date: Optional[str] = Field(default=None, description="Official bulletin publication or notification date (YYYY-MM-DD)")
    active_surveillance_window: Optional[str] = Field(default=None, description="Current ISO surveillance calendar week bounds (YYYY-MM-DD to YYYY-MM-DD)")
    historical_baseline_window: Optional[str] = Field(default=None, description="Historical reference period bounds used for comparison")


class ExplainabilityDossier(EpiSenseBaseModel):
    """
    Comprehensive, human-reviewable explainability dossier for an epidemiological alert.
    Synthesizes executive briefing, 5W1H, reconstructed evidence spans, audit trail, and provenance graph.
    """
    dossier_id: UUID = Field(default_factory=uuid4)
    alert_id: UUID
    disease_key: str
    geo_key: str
    period_start: datetime
    period_end: datetime
    alert_tier: AlertTier
    composite_score: float
    pathogen_threat_tier: PathogenThreatTier
    briefing: Epidemiological5W1H
    executive_summary: str
    analyst_action_playbook: str = Field(default="")
    driving_risk_factors: List[str] = Field(default_factory=list)
    applied_safety_constraints: List[str] = Field(default_factory=list)
    reconstructed_evidence: List[ReconstructedEvidenceSpan] = Field(default_factory=list)
    audit_trail: AlertAuditTrail
    provenance_graph: ProvenanceGraph
    provenance_complete: bool = True
    completeness_notes: Optional[str] = None
    event_date: Optional[str] = Field(default=None, description="Clinical onset date (YYYY-MM-DD)")
    reporting_date: Optional[str] = Field(default=None, description="Official notification/publication date (YYYY-MM-DD)")
    active_surveillance_window: Optional[str] = Field(default=None, description="Active surveillance window (YYYY-MM-DD to YYYY-MM-DD)")
    historical_baseline_window: Optional[str] = Field(default=None, description="Aligned historical comparison baseline period")
    created_at: datetime = Field(default_factory=utc_now)

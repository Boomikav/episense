"""
Streaming Surveillance and Incremental State Schemas for EpiSense (Phase 11).
Defines strongly-typed models for ingestion, failure isolation, state management,
alert lifecycle tracking, and deterministic checkpointing.
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Set
from uuid import UUID, uuid4

from pydantic import Field

from episense.schemas.base import EpiSenseBaseModel, utc_now


class IngestionStatus(str, Enum):
    """Status of an ingested document through the streaming validation gate."""
    ACCEPTED = "accepted"
    DUPLICATE_SKIPPED = "duplicate_skipped"
    REJECTED_MALFORMED = "rejected_malformed"
    REJECTED_ERROR = "rejected_error"


class AlertLifecycleState(str, Enum):
    """Lifecycle tracking states for surveillance alerts in continuous streaming."""
    NEW = "new"
    UPDATED = "updated"
    CONFIRMED_UNCHANGED = "confirmed_unchanged"
    RESOLVED = "resolved"


class DeadLetterRecord(EpiSenseBaseModel):
    """
    Structured isolation record for failed, corrupted, or malformed documents.
    Prevents unhandled runtime exceptions from crashing the continuous surveillance stream.
    """
    record_id: UUID = Field(default_factory=uuid4)
    document_id: Optional[UUID] = None
    source_id: Optional[str] = None
    stage: str = Field(description="Processing stage where failure occurred (e.g. validation, nlp, fusion)")
    error_type: str = Field(description="Exception class name or error classification")
    error_message: str = Field(description="Descriptive diagnostic details")
    timestamp: datetime = Field(default_factory=utc_now)
    raw_payload_preview: Optional[str] = Field(default=None, description="Truncated preview of raw payload")


class SurveillanceMetrics(EpiSenseBaseModel):
    """
    Deterministic operational metrics tracking the streaming surveillance engine.
    """
    model_config = {"frozen": False, "extra": "forbid"}

    documents_received: int = Field(default=0, ge=0)
    documents_accepted: int = Field(default=0, ge=0)
    duplicates_skipped: int = Field(default=0, ge=0)
    documents_rejected: int = Field(default=0, ge=0)
    fused_events_created: int = Field(default=0, ge=0)
    fused_events_updated: int = Field(default=0, ge=0)
    bins_created: int = Field(default=0, ge=0)
    bins_updated: int = Field(default=0, ge=0)
    signals_generated: int = Field(default=0, ge=0)
    alerts_generated: int = Field(default=0, ge=0)
    alerts_updated: int = Field(default=0, ge=0)
    processing_failures: int = Field(default=0, ge=0)
    provenance_failures: int = Field(default=0, ge=0)


class SurveillanceEventUpdate(EpiSenseBaseModel):
    """
    Output record emitted by the pipeline upon processing an ingested document.
    """
    update_id: UUID = Field(default_factory=uuid4)
    document_id: Optional[UUID] = None
    status: IngestionStatus
    fused_events_affected: List[UUID] = Field(default_factory=list)
    bins_affected: List[UUID] = Field(default_factory=list)
    signals_generated: List[UUID] = Field(default_factory=list)
    alerts_generated: List[UUID] = Field(default_factory=list)
    alert_lifecycle_states: Dict[str, AlertLifecycleState] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=utc_now)
    message: Optional[str] = None


class SurveillanceStateCheckpoint(EpiSenseBaseModel):
    """
    Immutable state snapshot for deterministic recovery and zero-loss restart.
    """
    checkpoint_id: UUID = Field(default_factory=uuid4)
    sequence_number: int = Field(ge=0)
    timestamp: datetime = Field(default_factory=utc_now)
    metrics: SurveillanceMetrics
    state_checksum_sha256: str = Field(min_length=64, max_length=64)
    total_documents_processed: int = Field(ge=0)
    total_fused_events: int = Field(ge=0)
    total_bins: int = Field(ge=0)
    total_alerts: int = Field(ge=0)
    dead_letter_count: int = Field(ge=0)

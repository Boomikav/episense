"""
Schemas for External Public Health Source Connectors and Polling Telemetry.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4
from pydantic import ConfigDict, Field

from episense.schemas.base import EpiSenseBaseModel, utc_now
from episense.schemas.document import OriginClassification, SourceType


class SourceConnectorStatus(str, Enum):
    OPERATIONAL = "OPERATIONAL"
    DEGRADED = "DEGRADED"
    UNAVAILABLE = "UNAVAILABLE"
    AUTHENTICATION_REQUIRED = "AUTHENTICATION_REQUIRED"
    NOT_CONFIGURED = "NOT_CONFIGURED"


class SourceConnectorConfig(EpiSenseBaseModel):
    """Configuration and live status of a public-health source connector."""
    model_config = ConfigDict(frozen=False, extra="forbid")

    source_id: str = Field(description="Unique source connector identifier")
    name: str = Field(description="Official name of health agency or reporting feed")
    category: SourceType = Field(default=SourceType.OFFICIAL_BULLETIN)
    official_source_url: str = Field(description="Public website or feed URL")
    endpoint_url: str = Field(description="Actual RSS/API/Atom endpoint queried")
    poll_interval_seconds: int = Field(default=600, ge=60, description="Polling frequency")
    is_enabled: bool = Field(default=True)
    is_configured: bool = Field(default=True)
    status: SourceConnectorStatus = Field(default=SourceConnectorStatus.OPERATIONAL)
    last_polled_at: Optional[datetime] = None
    last_attempted_at: Optional[datetime] = None
    last_success_at: Optional[datetime] = None
    last_successful_fetch_at: Optional[datetime] = None
    last_new_content_at: Optional[datetime] = None
    http_network_result: Optional[int] = None
    next_scheduled_attempt_at: Optional[datetime] = None
    last_cursor: Optional[str] = None
    consecutive_failures: int = Field(default=0)
    error_message: Optional[str] = None
    operational_status_rationale: Optional[str] = None
    total_retrievals: int = Field(default=0)
    total_documents_ingested: int = Field(default=0)
    new_documents_ingested: int = Field(default=0)
    last_document_count: int = Field(default=0)
    items_discovered: int = Field(default=0)
    items_skipped_duplicates: int = Field(default=0)
    items_deferred: int = Field(default=0, description="Items discovered but deferred due to batch processing limits")
    etag: Optional[str] = None
    last_modified: Optional[str] = None
    retryable_failures: int = Field(default=0)
    permanent_failures: int = Field(default=0)
    source_freshness_seconds: Optional[float] = Field(
        default=None,
        description="Elapsed time in seconds since the last successful HTTP check (network retrieval freshness). Resets on HTTP 200 or 304.",
    )
    seconds_since_last_fetch: Optional[float] = Field(
        default=None,
        description="Elapsed time in seconds since the last successful HTTP network check. Resets to ~0.0s on HTTP 200 or HTTP 304.",
    )
    content_age_seconds: Optional[float] = Field(
        default=None,
        description="Elapsed time in seconds since newest evidence was published/ingested. Computed from last_new_content_at. NOT reset by HTTP 304.",
    )
    last_retrieval_status: Optional[str] = None
    parsing_errors: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class SourcePollRecord(EpiSenseBaseModel):
    """Audit record of an individual polling execution."""
    model_config = ConfigDict(frozen=False, extra="forbid")

    poll_id: UUID = Field(default_factory=uuid4)
    source_id: str
    polled_at: datetime = Field(default_factory=utc_now)
    status: SourceConnectorStatus = Field(default=SourceConnectorStatus.OPERATIONAL)
    http_status: Optional[int] = None
    etag: Optional[str] = None
    last_modified: Optional[str] = None
    is_conditional_304: bool = False
    failure_classification: Optional[str] = None
    documents_found: int = 0
    items_discovered: int = 0
    documents_ingested: int = 0
    new_documents_ingested: int = 0
    duplicates_skipped: int = 0
    items_skipped_duplicates: int = 0
    items_deferred: int = 0
    duration_ms: float = 0.0
    error_message: Optional[str] = None
    parsing_errors: List[str] = Field(default_factory=list)
    details: Dict[str, Any] = Field(default_factory=dict)


class SourceHealthSummary(EpiSenseBaseModel):
    """Global system-wide health and telemetry summary across all configured feeds."""
    model_config = ConfigDict(frozen=False, extra="forbid")

    total_configured_sources: int
    operational_sources: int
    degraded_sources: int
    unavailable_sources: int
    auth_required_sources: int
    sources_health: List[SourceConnectorConfig]
    scheduler_running: bool = False
    overall_system_freshness: str = "fresh"
    audited_at: datetime = Field(default_factory=utc_now)


class RawDocumentPayload(EpiSenseBaseModel):
    """Standardized document payload retrieved from an external connector."""
    source_id: str
    source_type: SourceType
    origin: OriginClassification = OriginClassification.LIVE_EXTERNAL
    title: str
    text: str
    publication_date: Optional[datetime] = None
    retrieval_timestamp: datetime = Field(default_factory=utc_now)
    url: Optional[str] = None
    source_doc_id: Optional[str] = None
    language: str = "en"
    http_status: int = 200
    provenance_metadata: Dict[str, str] = Field(default_factory=dict)
    metadata: Dict[str, Any] = Field(default_factory=dict)

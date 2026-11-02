"""
Production API Request and Response Domain Schemas for EpiSense (Phase 12).
Strongly typed models for health, ingestion, pagination, GeoJSON GIS layers, and WebSockets.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, Generic, List, Optional, TypeVar
from uuid import UUID

from pydantic import Field

from episense.schemas.base import EpiSenseBaseModel, utc_now
from episense.schemas.document import SourceType
from episense.schemas.alert import AlertTier, EpidemiologicalAlert
from episense.schemas.event import FusedEvent
from episense.schemas.signal import SignalObservation
from episense.schemas.streaming import (
    AlertLifecycleState,
    IngestionStatus,
    SurveillanceEventUpdate,
)


class HealthStatus(str, Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"


class ServiceHealthResponse(EpiSenseBaseModel):
    """Overall service status, pipeline readiness, and component health."""
    status: HealthStatus = HealthStatus.HEALTHY
    version: str = "1.0.0"
    environment: str = "production"
    pipeline_available: bool = True
    state_store_available: bool = True
    timestamp: datetime = Field(default_factory=utc_now)


class ReadinessResponse(EpiSenseBaseModel):
    """Readiness probe response indicating ability to ingest documents."""
    status: str = "ready"
    ready: bool = True
    state_documents_count: int = 0
    state_alerts_count: int = 0
    state_events_count: int = 0


class LivenessResponse(EpiSenseBaseModel):
    """Liveness probe response indicating service process responsiveness."""
    status: str = "live"
    live: bool = True


class DocumentIngestionRequest(EpiSenseBaseModel):
    """Canonical document ingestion request payload."""
    document_id: Optional[UUID] = None
    source_id: str = "api_submission"
    source_name: Optional[str] = None
    source_type: Optional[SourceType] = None
    origin: Optional[str] = None
    title: str = Field(min_length=1, max_length=1000)
    text: str = Field(min_length=1)
    publication_timestamp: Optional[datetime] = None
    publication_date: Optional[datetime] = None
    url: Optional[str] = None
    source_url: Optional[str] = None
    content_hash_sha256: Optional[str] = None
    language: Optional[str] = None
    provenance_metadata: Dict[str, str] = Field(default_factory=dict)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class DocumentIngestionResponse(EpiSenseBaseModel):
    """Response returned upon submitting a document to the surveillance pipeline."""
    status: IngestionStatus
    document_id: Optional[UUID] = None
    update_id: UUID
    fused_events_affected: int = 0
    bins_affected: int = 0
    signals_generated: int = 0
    alerts_generated: int = 0
    alerts_updated: int = 0
    alerts_evaluated_total: int = 0
    alert_lifecycle_states: Dict[str, AlertLifecycleState] = Field(default_factory=dict)
    message: Optional[str] = None
    timestamp: datetime


ItemT = TypeVar("ItemT")


class PaginatedResponse(EpiSenseBaseModel, Generic[ItemT]):
    """Standardized deterministic paginated collection wrapper."""
    total: int = Field(ge=0)
    page: int = Field(ge=1)
    page_size: int = Field(ge=1)
    total_pages: int = Field(ge=0)
    has_next: bool
    has_prev: bool
    items: List[ItemT]


# ---------------------------------------------------------------------------
# GeoJSON / Geospatial Models (RFC 7946)
# ---------------------------------------------------------------------------

class GeoJSONGeometry(EpiSenseBaseModel):
    """GeoJSON Point geometry [longitude, latitude]."""
    type: str = "Point"
    coordinates: List[float] = Field(
        min_length=2,
        max_length=2,
        description="[longitude, latitude] in WGS 84 (EPSG:4326)",
    )


class GeoJSONFeature(EpiSenseBaseModel):
    """
    GeoJSON Feature representation.
    If geometry is unknown, geometry is None. NEVER fabricated.
    """
    type: str = "Feature"
    id: Optional[str] = None
    geometry: Optional[GeoJSONGeometry] = None
    properties: Dict[str, Any] = Field(default_factory=dict)


class GeoJSONFeatureCollection(EpiSenseBaseModel):
    """RFC 7946 compliant FeatureCollection."""
    type: str = "FeatureCollection"
    features: List[GeoJSONFeature] = Field(default_factory=list)
    total_features: int = Field(ge=0)
    features_with_geometry: int = Field(ge=0)
    unresolved_locations: int = Field(ge=0)


class GeoSummaryRegion(EpiSenseBaseModel):
    """Regional summary aggregating alerts and events for surveillance maps."""
    region: str
    total_events: int = 0
    total_alerts: int = 0
    high_alerts: int = 0
    medium_alerts: int = 0
    low_alerts: int = 0
    informational: int = 0
    pathogens: List[str] = Field(default_factory=list)
    latest_event_date: Optional[datetime] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    has_geometry: bool = False


class GeoSummaryResponse(EpiSenseBaseModel):
    """Dashboard-ready regional distribution summary."""
    total_regions: int = Field(ge=0)
    regions: List[GeoSummaryRegion] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# WebSocket Subscription & Message Models
# ---------------------------------------------------------------------------

class WSSubscriptionFilter(EpiSenseBaseModel):
    """Optional subscription filter for streaming surveillance clients."""
    pathogen: Optional[str] = None
    alert_tier: Optional[AlertTier] = None
    region: Optional[str] = None
    min_score: Optional[float] = Field(default=None, ge=0.0, le=1.0)


class WSClientMessage(EpiSenseBaseModel):
    """Message sent from client to server."""
    action: str = Field(default="subscribe", description="'subscribe', 'unsubscribe', 'ping'")
    filter: Optional[WSSubscriptionFilter] = None


class WSServerMessage(EpiSenseBaseModel):
    """Standardized server-to-client WebSocket frame."""
    type: str = Field(description="'connection_ack', 'event_update', 'pong', 'error'")
    client_id: Optional[str] = None
    status: Optional[str] = None
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    timestamp: datetime = Field(default_factory=utc_now)

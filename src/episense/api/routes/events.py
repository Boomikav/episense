"""
Canonical Fused Event Query Routes for EpiSense (Phase 12).
Exposes cross-document fused epidemiological events synthesized by the fusion engine.
"""

from datetime import datetime
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query

from episense.schemas.assertion import AssertionStatus
from episense.schemas.event import FusedEvent
from episense.api.dependencies import get_event_query_service
from episense.api.errors import APIResourceNotFoundError
from episense.api.models import PaginatedResponse
from episense.api.services import EventQueryService

router = APIRouter(prefix="/api/v1/events", tags=["Fused Events"])


@router.get(
    "",
    response_model=PaginatedResponse[FusedEvent],
    summary="Query Canonical Fused Events",
    description="Returns deterministically filtered, sorted, and paginated fused events synthesized across source documents.",
)
async def list_events(
    pathogen: Optional[str] = Query(None, description="Substring filter on canonical disease name"),
    location: Optional[str] = Query(None, description="Substring filter on location name"),
    assertion_status: Optional[AssertionStatus] = Query(None, description="Filter by assertion status (CONFIRMED, SUSPECTED, etc.)"),
    source_group: Optional[str] = Query(None, description="Filter by source independence group"),
    start_date: Optional[datetime] = Query(None, description="Filter events with window start on or after timestamp"),
    end_date: Optional[datetime] = Query(None, description="Filter events with window end on or before timestamp"),
    origin: Optional[str] = Query(None, description="Filter by origin: LIVE_EXTERNAL, HISTORICAL_CORPUS, MANUAL_SUBMISSION, BENCHMARK"),
    status: Optional[str] = Query("active", description="Filter by lifecycle status: 'active', 'superseded', or 'all'"),
    decision_category: Optional[str] = Query(None, description="Filter by explainable decision category (NEEDS_REVIEW, CORROBORATED_EVENT, etc.)"),
    currentness: Optional[str] = Query(None, description="Filter by currentness status (CURRENT_EVENT, HISTORICAL_REFERENCE, etc.)"),
    priority_only: bool = Query(False, description="Filter strictly to the 8 canonical priority surveillance diseases"),
    current_only: bool = Query(False, description="Filter strictly to events active in current operational window"),
    page: int = Query(1, ge=1, description="Page number (1-indexed)"),
    page_size: int = Query(20, ge=1, le=100, description="Page size (max 100)"),
    service: EventQueryService = Depends(get_event_query_service),
) -> PaginatedResponse[FusedEvent]:
    return service.list_events(
        pathogen=pathogen,
        location=location,
        assertion_status=assertion_status,
        source_group=source_group,
        start_date=start_date,
        end_date=end_date,
        origin=origin,
        status=status,
        decision_category=decision_category,
        currentness=currentness,
        priority_only=priority_only,
        current_only=current_only,
        page=page,
        page_size=page_size,
    )


@router.get(
    "/{event_id}",
    response_model=FusedEvent,
    summary="Get Fused Event Detail",
    description="Retrieves a single canonical fused event by its unique UUID.",
)
async def get_event_detail(
    event_id: UUID,
    service: EventQueryService = Depends(get_event_query_service),
) -> FusedEvent:
    event = service.get_by_id(event_id)
    if not event:
        raise APIResourceNotFoundError("event", event_id)
    return event

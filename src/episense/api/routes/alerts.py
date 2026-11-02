"""
Alert Query Routes for EpiSense (Phase 12).
Provides deterministic filtering, pagination, and retrieval for epidemiological alerts.
"""

from datetime import datetime
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query

from episense.schemas.alert import AlertTier, EpidemiologicalAlert, PathogenThreatTier
from episense.api.dependencies import get_alert_query_service
from episense.api.errors import APIResourceNotFoundError
from episense.api.models import PaginatedResponse
from episense.api.services import AlertQueryService

router = APIRouter(prefix="/api/v1/alerts", tags=["Alerts"])


@router.get(
    "",
    response_model=PaginatedResponse[EpidemiologicalAlert],
    summary="Query Epidemiological Alerts",
    description="Returns deterministically filtered, sorted, and paginated epidemiological alerts.",
)
async def list_alerts(
    tier: Optional[AlertTier] = Query(None, description="Filter by Alert Tier (INFORMATIONAL, LOW, MEDIUM, HIGH)"),
    pathogen: Optional[str] = Query(None, description="Substring filter on canonical disease key"),
    location: Optional[str] = Query(None, description="Substring filter on geographic key"),
    threat_tier: Optional[PathogenThreatTier] = Query(None, description="Filter by pathogen clinical threat tier"),
    min_score: Optional[float] = Query(None, ge=0.0, le=1.0, description="Minimum composite risk score"),
    max_score: Optional[float] = Query(None, ge=0.0, le=1.0, description="Maximum composite risk score"),
    period_start: Optional[datetime] = Query(None, description="Filter alerts active on or after timestamp"),
    period_end: Optional[datetime] = Query(None, description="Filter alerts active on or before timestamp"),
    origin: Optional[str] = Query(None, description="Filter by origin: LIVE_EXTERNAL, HISTORICAL_CORPUS, MANUAL_SUBMISSION, BENCHMARK"),
    status: Optional[str] = Query("active", description="Filter by lifecycle status: 'active', 'superseded', or 'all'"),
    decision_category: Optional[str] = Query(None, description="Filter by explainable decision category (NEEDS_REVIEW, CORROBORATED_EVENT, etc.)"),
    currentness: Optional[str] = Query(None, description="Filter by currentness status (CURRENT_EVENT, HISTORICAL_REFERENCE, etc.)"),
    priority_only: bool = Query(False, description="Filter strictly to the 8 canonical priority surveillance diseases"),
    current_only: bool = Query(False, description="Filter strictly to alerts active in current operational window"),
    page: int = Query(1, ge=1, description="Page number (1-indexed)"),
    page_size: int = Query(20, ge=1, le=100, description="Page size (max 100)"),
    service: AlertQueryService = Depends(get_alert_query_service),
) -> PaginatedResponse[EpidemiologicalAlert]:
    return service.list_alerts(
        tier=tier,
        pathogen=pathogen,
        location=location,
        threat_tier=threat_tier,
        min_score=min_score,
        max_score=max_score,
        period_start=period_start,
        period_end=period_end,
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
    "/{alert_id}",
    response_model=EpidemiologicalAlert,
    summary="Get Alert Detail",
    description="Retrieves a single epidemiological alert by its unique UUID.",
)
async def get_alert_detail(
    alert_id: UUID,
    service: AlertQueryService = Depends(get_alert_query_service),
) -> EpidemiologicalAlert:
    alert = service.get_by_id(alert_id)
    if not alert:
        raise APIResourceNotFoundError("alert", alert_id)
    return alert

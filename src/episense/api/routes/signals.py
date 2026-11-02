"""
Statistical Early Signal Query Routes for EpiSense (Phase 12).
Exposes Phase 8 EARS C1/C2/C3 and Farrington anomaly signals.
"""

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query

from episense.schemas.signal import (
    BaselineReliability,
    DetectionMethod,
    SignalLevel,
    SignalObservation,
)
from episense.api.dependencies import get_signal_query_service
from episense.api.errors import APIResourceNotFoundError
from episense.api.models import PaginatedResponse
from episense.api.services import SignalQueryService

router = APIRouter(prefix="/api/v1/signals", tags=["Early Signals"])


@router.get(
    "",
    response_model=PaginatedResponse[SignalObservation],
    summary="Query Early Epidemiological Signals",
    description="Returns deterministically filtered, sorted, and paginated statistical early signals.",
)
async def list_signals(
    pathogen: Optional[str] = Query(None, description="Substring filter on canonical disease key"),
    location: Optional[str] = Query(None, description="Substring filter on geographic key"),
    signal_level: Optional[SignalLevel] = Query(None, description="Signal severity level (WATCH, SIGNAL, STRONG_SIGNAL)"),
    detection_method: Optional[DetectionMethod] = Query(None, description="Algorithm (EARS_C1, EARS_C2, EARS_C3, FARRINGTON, MULTI_DETECTOR)"),
    reliability_status: Optional[BaselineReliability] = Query(None, description="Baseline reliability state"),
    origin: Optional[str] = Query(None, description="Filter by origin: LIVE_EXTERNAL, HISTORICAL_CORPUS, MANUAL_SUBMISSION, BENCHMARK"),
    priority_only: bool = Query(False, description="Filter strictly to the 8 canonical priority diseases"),
    current_only: bool = Query(False, description="Filter strictly to signals active in current operational window"),
    page: int = Query(1, ge=1, description="Page number (1-indexed)"),
    page_size: int = Query(20, ge=1, le=100, description="Page size (max 100)"),
    service: SignalQueryService = Depends(get_signal_query_service),
) -> PaginatedResponse[SignalObservation]:
    return service.list_signals(
        pathogen=pathogen,
        location=location,
        signal_level=signal_level,
        detection_method=detection_method,
        reliability_status=reliability_status,
        origin=origin,
        priority_only=priority_only,
        current_only=current_only,
        page=page,
        page_size=page_size,
    )


@router.get(
    "/{signal_id}",
    response_model=SignalObservation,
    summary="Get Early Signal Detail",
    description="Retrieves a single statistical early signal by its unique UUID.",
)
async def get_signal_detail(
    signal_id: UUID,
    service: SignalQueryService = Depends(get_signal_query_service),
) -> SignalObservation:
    signal = service.get_by_id(signal_id)
    if not signal:
        raise APIResourceNotFoundError("signal", signal_id)
    return signal

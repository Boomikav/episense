"""
Service Health, Readiness, and Liveness Probe Routes for EpiSense (Phase 12).
"""

from fastapi import APIRouter, Depends

from episense.streaming.state import SurveillanceStateStore
from episense.api.dependencies import get_state_store
from episense.api.models import (
    HealthStatus,
    LivenessResponse,
    ReadinessResponse,
    ServiceHealthResponse,
)

router = APIRouter(tags=["Health"])


@router.get(
    "/health",
    response_model=ServiceHealthResponse,
    summary="Service Health",
    description="Returns high-level system availability, version, and component status.",
)
@router.get(
    "/api/v1/health",
    response_model=ServiceHealthResponse,
    summary="Service Health (v1 Alias)",
    include_in_schema=False,
)
async def get_health(
    state: SurveillanceStateStore = Depends(get_state_store),
) -> ServiceHealthResponse:
    return ServiceHealthResponse(
        status=HealthStatus.HEALTHY,
        version="1.0.0",
        environment="production",
        pipeline_available=True,
        state_store_available=state is not None,
    )


@router.get(
    "/health/ready",
    response_model=ReadinessResponse,
    summary="Readiness Probe",
    description="Indicates whether the pipeline and state store are ready to accept document ingestion.",
)
async def get_readiness(
    state: SurveillanceStateStore = Depends(get_state_store),
) -> ReadinessResponse:
    doc_count = len(state.processed_document_ids) if state else 0
    alert_count = len(state.alerts) if state else 0
    event_count = len(state.fused_events) if state else 0
    return ReadinessResponse(
        status="ready",
        ready=True,
        state_documents_count=doc_count,
        state_alerts_count=alert_count,
        state_events_count=event_count,
    )


@router.get(
    "/health/live",
    response_model=LivenessResponse,
    summary="Liveness Probe",
    description="Standard container/process liveness check verifying API responsiveness.",
)
async def get_liveness() -> LivenessResponse:
    return LivenessResponse(status="live", live=True)

"""
API Router for Public Health Source Connectors and Polling Telemetry (EpiSense).
Provides endpoints to list external feeds, trigger immediate polling, and inspect audit logs.
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status

from episense.api.dependencies import get_persistence_db, get_source_polling_service
from episense.connectors.service import SourcePollingService
from episense.persistence.database import SurveillanceDatabase
from episense.schemas.source import (
    SourceConnectorConfig,
    SourceHealthSummary,
    SourcePollRecord,
)

router = APIRouter(prefix="/api/v1/sources", tags=["Sources & Connectors"])


@router.get(
    "/health",
    response_model=SourceHealthSummary,
    summary="Get aggregated live health, readiness, and freshness telemetry across all sources",
)
def get_sources_health(
    polling_service: SourcePollingService = Depends(get_source_polling_service),
) -> SourceHealthSummary:
    return polling_service.get_health_summary()


@router.post(
    "/scheduler/start",
    summary="Start background scheduled polling loop for enabled sources",
)
def start_scheduler(
    check_interval: float = Query(default=30.0, ge=5.0, le=3600.0),
    polling_service: SourcePollingService = Depends(get_source_polling_service),
) -> dict:
    polling_service.start_scheduler(check_interval_seconds=check_interval)
    return {"status": "started", "check_interval_seconds": check_interval}


@router.post(
    "/scheduler/stop",
    summary="Stop background scheduled polling loop",
)
def stop_scheduler(
    polling_service: SourcePollingService = Depends(get_source_polling_service),
) -> dict:
    polling_service.stop_scheduler()
    return {"status": "stopped"}


@router.get(
    "",
    response_model=List[SourceConnectorConfig],
    summary="List all configured source connectors and their operational status",
)
def list_sources(
    polling_service: SourcePollingService = Depends(get_source_polling_service),
) -> List[SourceConnectorConfig]:
    return polling_service.list_connectors()


@router.post(
    "/{source_id}/poll",
    response_model=SourcePollRecord,
    summary="Trigger immediate poll for an individual source connector",
)
def poll_source(
    source_id: str,
    polling_service: SourcePollingService = Depends(get_source_polling_service),
) -> SourcePollRecord:
    try:
        return polling_service.poll_source(source_id)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Source polling failed: {e}",
        )


@router.post(
    "/poll-all",
    response_model=List[SourcePollRecord],
    summary="Trigger immediate poll across all active source connectors",
)
def poll_all_sources(
    polling_service: SourcePollingService = Depends(get_source_polling_service),
) -> List[SourcePollRecord]:
    return polling_service.poll_all()


@router.get(
    "/{source_id}/history",
    response_model=List[SourcePollRecord],
    summary="Retrieve polling history and network diagnostics for a source connector",
)
def get_source_history(
    source_id: str,
    limit: int = Query(default=20, ge=1, le=100),
    db: SurveillanceDatabase = Depends(get_persistence_db),
) -> List[SourcePollRecord]:
    return db.list_poll_history(source_id=source_id, limit=limit)

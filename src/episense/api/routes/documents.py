"""
Document Ingestion Routes for EpiSense (Phase 12).
Receives documents, runs continuous surveillance pipeline, and publishes updates.
"""

from datetime import datetime, timezone
from fastapi import APIRouter, Depends, status

from episense.streaming.pipeline import ContinuousSurveillancePipeline
from episense.streaming.state import SurveillanceStateStore
from episense.schemas.streaming import IngestionStatus, AlertLifecycleState
from episense.api.dependencies import get_pipeline, get_publisher, get_state_store
from episense.api.errors import APIBadRequestError, APIValidationError
from episense.api.models import (
    DocumentIngestionRequest,
    DocumentIngestionResponse,
)
from episense.api.websocket import SurveillanceEventPublisher

router = APIRouter(prefix="/api/v1/documents", tags=["Documents"])


@router.post(
    "",
    response_model=DocumentIngestionResponse,
    status_code=status.HTTP_200_OK,
    summary="Submit Document for Ingestion",
    description="Submits a news dispatch, bulletin, or health report to the continuous surveillance pipeline. Enforces strict idempotency.",
)
async def submit_document(
    payload: DocumentIngestionRequest,
    pipeline: ContinuousSurveillancePipeline = Depends(get_pipeline),
    publisher: SurveillanceEventPublisher = Depends(get_publisher),
    state: SurveillanceStateStore = Depends(get_state_store),
) -> DocumentIngestionResponse:
    # 1. Process document through continuous surveillance pipeline
    dict_payload = payload.model_dump(exclude_none=True)
    if "publication_timestamp" not in dict_payload:
        dict_payload["publication_timestamp"] = payload.publication_date
    if "source_url" not in dict_payload and payload.url:
        dict_payload["source_url"] = payload.url
    if "origin" not in dict_payload:
        dict_payload["origin"] = "MANUAL_SUBMISSION"
    update = pipeline.process_document(dict_payload)

    # 2. Check for failure or rejection
    if update.status == IngestionStatus.REJECTED_MALFORMED:
        raise APIValidationError(
            message=f"Document rejected: {update.message or 'Schema or timestamp validation failed'}"
        )
    elif update.status == IngestionStatus.REJECTED_ERROR:
        raise APIBadRequestError(
            message=f"Document processing failed: {update.message or 'Unexpected pipeline execution error'}",
            code="INGESTION_FAILED",
        )

    # 3. Broadcast update to active WebSocket subscribers
    await publisher.broadcast(update, alerts_lookup=state.alerts)

    # 4. Construct response with strictly reconciled alert counters
    new_alerts_count = sum(
        1 for s in update.alert_lifecycle_states.values()
        if s == AlertLifecycleState.NEW
    )
    updated_alerts_count = sum(
        1 for s in update.alert_lifecycle_states.values()
        if s == AlertLifecycleState.UPDATED
    )

    return DocumentIngestionResponse(
        status=update.status,
        document_id=update.document_id,
        update_id=update.update_id,
        fused_events_affected=len(update.fused_events_affected),
        bins_affected=len(update.bins_affected),
        signals_generated=len(update.signals_generated),
        alerts_generated=new_alerts_count,
        alerts_updated=updated_alerts_count,
        alerts_evaluated_total=len(update.alerts_generated),
        alert_lifecycle_states=update.alert_lifecycle_states,
        message=update.message,
        timestamp=update.timestamp,
    )

"""
Explainability, Audit Trail, and Provenance Routes for EpiSense (Phase 12).
Exposes Phase 10 forensic explainability dossiers, 8-step decision paths, and lineage DAGs.
"""

from uuid import UUID
from fastapi import APIRouter, Depends

from episense.schemas.explainability import (
    AlertAuditTrail,
    ExplainabilityDossier,
    ProvenanceGraph,
)
from episense.api.dependencies import get_provenance_query_service
from episense.api.errors import APIResourceNotFoundError
from episense.api.services import ProvenanceQueryService

router = APIRouter(prefix="/api/v1/alerts", tags=["Explainability & Provenance"])


@router.get(
    "/{alert_id}/dossier",
    response_model=ExplainabilityDossier,
    summary="Get Alert Explainability Dossier",
    description="Returns full explainability dossier including 5W1H briefing, reconstructed evidence spans, and lineage graph.",
)
async def get_alert_dossier(
    alert_id: UUID,
    service: ProvenanceQueryService = Depends(get_provenance_query_service),
) -> ExplainabilityDossier:
    dossier = service.get_dossier(alert_id)
    if not dossier:
        raise APIResourceNotFoundError("dossier_for_alert", alert_id)
    return dossier


@router.get(
    "/{alert_id}/audit",
    response_model=AlertAuditTrail,
    summary="Get Alert Decision Audit Trail",
    description="Returns the formal 8-step decision path and cryptographic SHA-256 state checksum.",
)
async def get_alert_audit_trail(
    alert_id: UUID,
    service: ProvenanceQueryService = Depends(get_provenance_query_service),
) -> AlertAuditTrail:
    audit = service.get_audit_trail(alert_id)
    if not audit:
        raise APIResourceNotFoundError("audit_trail_for_alert", alert_id)
    return audit


@router.get(
    "/{alert_id}/provenance",
    response_model=ProvenanceGraph,
    summary="Get Alert Provenance Graph",
    description="Returns directed acyclic graph (DAG) tracing the alert backward to documents and evidence spans.",
)
async def get_alert_provenance_graph(
    alert_id: UUID,
    service: ProvenanceQueryService = Depends(get_provenance_query_service),
) -> ProvenanceGraph:
    graph = service.get_provenance_graph(alert_id)
    if not graph:
        raise APIResourceNotFoundError("provenance_graph_for_alert", alert_id)
    return graph

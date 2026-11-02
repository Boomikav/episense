"""
Dependency Injection Providers for EpiSense API (Phase 12).
Allows cleanly swapping StateStore, Pipeline, Services, and Publisher in unit/integration tests.
"""

from typing import Optional
from fastapi import Depends

from episense.streaming.state import SurveillanceStateStore
from episense.streaming.pipeline import ContinuousSurveillancePipeline
from episense.persistence.database import SurveillanceDatabase
from episense.connectors.service import SourcePollingService
from episense.api.websocket import SurveillanceEventPublisher
from episense.api.services import (
    AlertQueryService,
    EventQueryService,
    GeoQueryService,
    GeoResolver,
    ProvenanceQueryService,
    SignalQueryService,
)

# Shared module-level instances (can be overridden via set_dependencies)
_GLOBAL_STATE_STORE: Optional[SurveillanceStateStore] = None
_GLOBAL_PIPELINE: Optional[ContinuousSurveillancePipeline] = None
_GLOBAL_PUBLISHER: Optional[SurveillanceEventPublisher] = None
_GLOBAL_GEO_RESOLVER: Optional[GeoResolver] = None
_GLOBAL_DB: Optional[SurveillanceDatabase] = None
_GLOBAL_POLLING_SERVICE: Optional[SourcePollingService] = None


def get_persistence_db() -> SurveillanceDatabase:
    """Returns the persistent SQLite database instance."""
    global _GLOBAL_DB
    if _GLOBAL_DB is None:
        _GLOBAL_DB = SurveillanceDatabase()
    return _GLOBAL_DB


def get_state_store() -> SurveillanceStateStore:
    """Returns the surveillance state store instance."""
    global _GLOBAL_STATE_STORE
    if _GLOBAL_STATE_STORE is None:
        db = get_persistence_db()
        _GLOBAL_STATE_STORE = SurveillanceStateStore(db=db)
    return _GLOBAL_STATE_STORE


def get_publisher() -> SurveillanceEventPublisher:
    """Returns the surveillance event publisher instance."""
    global _GLOBAL_PUBLISHER
    if _GLOBAL_PUBLISHER is None:
        _GLOBAL_PUBLISHER = SurveillanceEventPublisher()
    return _GLOBAL_PUBLISHER


def get_pipeline(
    state: SurveillanceStateStore = Depends(get_state_store),
) -> ContinuousSurveillancePipeline:
    """Returns the continuous surveillance pipeline instance."""
    global _GLOBAL_PIPELINE
    if _GLOBAL_PIPELINE is None:
        _GLOBAL_PIPELINE = ContinuousSurveillancePipeline(state=state)
    return _GLOBAL_PIPELINE


def get_source_polling_service(
    pipeline: ContinuousSurveillancePipeline = Depends(get_pipeline),
    db: SurveillanceDatabase = Depends(get_persistence_db),
    publisher: SurveillanceEventPublisher = Depends(get_publisher),
) -> SourcePollingService:
    """Returns the source polling orchestration service instance."""
    global _GLOBAL_POLLING_SERVICE
    if _GLOBAL_POLLING_SERVICE is None:
        _GLOBAL_POLLING_SERVICE = SourcePollingService(
            pipeline=pipeline,
            db=db,
            publisher=publisher,
        )
    return _GLOBAL_POLLING_SERVICE


def get_geo_resolver() -> GeoResolver:
    """Returns the gazetteer geo-resolver instance."""
    global _GLOBAL_GEO_RESOLVER
    if _GLOBAL_GEO_RESOLVER is None:
        _GLOBAL_GEO_RESOLVER = GeoResolver()
    return _GLOBAL_GEO_RESOLVER


def get_alert_query_service(
    state: SurveillanceStateStore = Depends(get_state_store),
) -> AlertQueryService:
    return AlertQueryService(state)


def get_event_query_service(
    state: SurveillanceStateStore = Depends(get_state_store),
) -> EventQueryService:
    return EventQueryService(state)


def get_signal_query_service(
    state: SurveillanceStateStore = Depends(get_state_store),
) -> SignalQueryService:
    return SignalQueryService(state)


def get_provenance_query_service(
    state: SurveillanceStateStore = Depends(get_state_store),
) -> ProvenanceQueryService:
    return ProvenanceQueryService(state)


def get_geo_query_service(
    state: SurveillanceStateStore = Depends(get_state_store),
    resolver: GeoResolver = Depends(get_geo_resolver),
) -> GeoQueryService:
    return GeoQueryService(state=state, geo_resolver=resolver)


def set_dependencies(
    state: Optional[SurveillanceStateStore] = None,
    pipeline: Optional[ContinuousSurveillancePipeline] = None,
    publisher: Optional[SurveillanceEventPublisher] = None,
    geo_resolver: Optional[GeoResolver] = None,
    db: Optional[SurveillanceDatabase] = None,
    polling_service: Optional[SourcePollingService] = None,
):
    """Sets or overrides global dependencies for test execution or custom initialization."""
    global _GLOBAL_STATE_STORE, _GLOBAL_PIPELINE, _GLOBAL_PUBLISHER, _GLOBAL_GEO_RESOLVER, _GLOBAL_DB, _GLOBAL_POLLING_SERVICE
    if state is not None:
        _GLOBAL_STATE_STORE = state
    if pipeline is not None:
        _GLOBAL_PIPELINE = pipeline
    if publisher is not None:
        _GLOBAL_PUBLISHER = publisher
    if geo_resolver is not None:
        _GLOBAL_GEO_RESOLVER = geo_resolver
    if db is not None:
        _GLOBAL_DB = db
    if polling_service is not None:
        _GLOBAL_POLLING_SERVICE = polling_service


def reset_dependencies():
    """Resets global singletons to None."""
    global _GLOBAL_STATE_STORE, _GLOBAL_PIPELINE, _GLOBAL_PUBLISHER, _GLOBAL_GEO_RESOLVER, _GLOBAL_DB, _GLOBAL_POLLING_SERVICE
    _GLOBAL_STATE_STORE = None
    _GLOBAL_PIPELINE = None
    _GLOBAL_PUBLISHER = None
    _GLOBAL_GEO_RESOLVER = None
    _GLOBAL_DB = None
    _GLOBAL_POLLING_SERVICE = None

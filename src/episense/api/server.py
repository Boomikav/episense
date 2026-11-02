"""
Production and Development Server Entrypoint for EpiSense API (Phase 12).

Provides an active server instance with pre-loaded authoritative surveillance
data (110 documents, 170 fused events, 170 signals, 170 alerts, 170 dossiers)
for immediate, rich frontend and integration use.
"""

import logging
import os
from pathlib import Path
import sys
from typing import Optional, Union

from episense.streaming.state import SurveillanceStateStore
from episense.streaming.pipeline import ContinuousSurveillancePipeline
from episense.streaming.ingestion import FileStreamIngestionSource
from episense.persistence.database import SurveillanceDatabase
from episense.connectors.service import SourcePollingService
from episense.api.websocket import SurveillanceEventPublisher
from episense.api.services import GeoResolver
from episense.api.app import create_app

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("episense.server")


def create_surveillance_server(
    preload: bool = True,
    db: Optional[SurveillanceDatabase] = None,
    db_path: Optional[Union[str, Path]] = None,
):
    """Initializes server with optional authoritative corpus pre-loading and persistent state hydration."""
    if db is None:
        db = SurveillanceDatabase(db_path) if db_path else SurveillanceDatabase()
    state_store = SurveillanceStateStore(db=db)
    pipeline = ContinuousSurveillancePipeline(state=state_store)
    publisher = SurveillanceEventPublisher()
    geo_resolver = GeoResolver()
    polling_service = SourcePollingService(pipeline=pipeline, db=db, publisher=publisher)

    # 1. Preload authoritative benchmark & background manifests
    if preload:
        manifest_paths = [
            Path("data/benchmarks/episense_benchmark_v1.json"),
            Path("data/benchmarks/episense_background_v1.json"),
        ]
        existing_manifests = [p for p in manifest_paths if p.exists()]
        if existing_manifests:
            logger.info("Pre-loading authoritative surveillance corpus into state store...")
            source = FileStreamIngestionSource(existing_manifests)
            updates = pipeline.process_stream(source)
            logger.info(
                "Ingestion completed: %d documents accepted, %d fused events, %d signals, %d alerts.",
                state_store.metrics.documents_accepted,
                len(state_store.fused_events),
                len(state_store.signals),
                len(state_store.alerts),
            )
        else:
            logger.warning("Corpus manifest files not found. Starting with empty state store.")

    # 2. Deterministically hydrate persisted live surveillance records from SQLite store
    if db:
        logger.info("Hydrating persisted live surveillance records from durable SQLite store...")
        counts = state_store.hydrate_from_db(db)
        logger.info(
            "Live state hydration completed: %d live docs, %d fused events, %d signals, %d alerts restored.",
            counts.get("documents", 0),
            counts.get("fused_events", 0),
            counts.get("signals", 0),
            counts.get("alerts", 0),
        )

    app = create_app(
        state=state_store,
        pipeline=pipeline,
        publisher=publisher,
        geo_resolver=geo_resolver,
        db=db,
        polling_service=polling_service,
    )

    return app


# Environment flag: EPISENSE_PRELOAD_CORPUS (default: 1)
preload_flag = os.environ.get("EPISENSE_PRELOAD_CORPUS", "1").lower() not in ("0", "false", "no")
app = create_surveillance_server(preload=preload_flag)

if __name__ == "__main__":
    import uvicorn

    port = int(os.environ.get("PORT", 8000))
    host = os.environ.get("HOST", "0.0.0.0")
    logger.info("Starting EpiSense API server on http://%s:%d", host, port)
    uvicorn.run("episense.api.server:app", host=host, port=port, reload=False)

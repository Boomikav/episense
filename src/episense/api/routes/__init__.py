"""
API Routes Package for EpiSense (Phase 12).
"""

from episense.api.routes.health import router as health_router
from episense.api.routes.documents import router as documents_router
from episense.api.routes.alerts import router as alerts_router
from episense.api.routes.provenance import router as provenance_router
from episense.api.routes.events import router as events_router
from episense.api.routes.signals import router as signals_router
from episense.api.routes.geo import router as geo_router
from episense.api.routes.sources import router as sources_router
from episense.api.routes.workbench import router as workbench_router
from episense.api.routes.fusion_inspector import router as fusion_router
from episense.api.routes.evaluation import router as evaluation_router
from episense.api.routes.live_metrics import router as metrics_router
from episense.api.routes.taxonomy import router as taxonomy_router
from episense.api.routes.forecasting import router as forecasting_router, models_router

__all__ = [
    "health_router",
    "documents_router",
    "alerts_router",
    "provenance_router",
    "events_router",
    "signals_router",
    "geo_router",
    "sources_router",
    "workbench_router",
    "fusion_router",
    "evaluation_router",
    "metrics_router",
    "taxonomy_router",
    "forecasting_router",
    "models_router",
]

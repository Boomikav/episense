"""
FastAPI Application Factory and Server Lifecycle for EpiSense (Phase 12).
Configures CORS, request correlation, payload limits, exception handling, routers, and WebSocket feeds.
"""

import os
from typing import Any, Optional
from uuid import uuid4

from fastapi import FastAPI, Request, Response, WebSocket, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.middleware.base import BaseHTTPMiddleware

from episense.config.settings import APIConfig
from episense.exceptions import EpiSenseError
from episense.streaming.pipeline import ContinuousSurveillancePipeline
from episense.streaming.state import SurveillanceStateStore
from episense.api.dependencies import (
    get_publisher,
    set_dependencies,
)
from episense.api.errors import (
    APIError,
    api_error_handler,
    domain_exception_handler,
    http_exception_handler,
    unhandled_exception_handler,
    validation_exception_handler,
)
from episense.api.routes import (
    alerts_router,
    documents_router,
    evaluation_router,
    events_router,
    fusion_router,
    geo_router,
    health_router,
    metrics_router,
    provenance_router,
    signals_router,
    sources_router,
    taxonomy_router,
    workbench_router,
    forecasting_router,
    models_router,
)
from episense.api.services import GeoResolver
from episense.api.websocket import SurveillanceEventPublisher
from episense.logging import get_logger

logger = get_logger("api.app")


class RequestCorrelationMiddleware(BaseHTTPMiddleware):
    """Assigns or propagates X-Request-ID for forensic tracing without mutating domain IDs."""
    async def dispatch(self, request: Request, call_next):
        req_id = request.headers.get("X-Request-ID") or f"req_{uuid4().hex[:16]}"
        request.state.request_id = req_id
        response: Response = await call_next(request)
        response.headers["X-Request-ID"] = req_id
        return response


class PayloadSizeLimitMiddleware(BaseHTTPMiddleware):
    """Rejects incoming payloads exceeding configured byte threshold."""
    def __init__(self, app, max_bytes: int):
        super().__init__(app)
        self.max_bytes = max_bytes

    async def dispatch(self, request: Request, call_next):
        cl = request.headers.get("Content-Length")
        if cl:
            try:
                content_len = int(cl)
                if content_len > self.max_bytes:
                    return Response(
                        status_code=getattr(status, "HTTP_413_CONTENT_TOO_LARGE", 413),
                        content=f'{{"error":{{"code":"PAYLOAD_TOO_LARGE","message":"Request payload exceeds maximum allowed size of {self.max_bytes} bytes."}}}}',
                        media_type="application/json",
                    )
            except ValueError:
                pass
        return await call_next(request)


def create_app(
    config: Optional[APIConfig] = None,
    state: Optional[SurveillanceStateStore] = None,
    pipeline: Optional[ContinuousSurveillancePipeline] = None,
    publisher: Optional[SurveillanceEventPublisher] = None,
    geo_resolver: Optional[GeoResolver] = None,
    db: Optional[Any] = None,
    polling_service: Optional[Any] = None,
) -> FastAPI:
    """
    Creates and configures a production-ready FastAPI application instance.
    Accepts injected components for deterministic testing.
    """
    cfg = config or APIConfig()

    # Configure dependency injection singletons
    set_dependencies(
        state=state,
        pipeline=pipeline,
        publisher=publisher,
        geo_resolver=geo_resolver,
        db=db,
        polling_service=polling_service,
    )

    app = FastAPI(
        title="EpiSense Epidemiological Surveillance API",
        version="1.0.0",
        description=(
            "Production REST and WebSocket API for the EpiSense continuous epidemic intelligence platform. "
            "Exposes explainable alerts, cross-document fused events, early statistical signals, "
            "RFC 7946 GeoJSON layers, and real-time streaming surveillance updates."
        ),
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
    )

    # 1. Register Middlewares
    app.add_middleware(RequestCorrelationMiddleware)
    app.add_middleware(PayloadSizeLimitMiddleware, max_bytes=cfg.max_payload_bytes)

    # Production CORS configuration: supports env overrides, Vercel deployments, and test origins
    env_cors = os.environ.get("CORS_ORIGINS")
    if env_cors:
        cors_origins = [o.strip() for o in env_cors.split(",") if o.strip()]
        allow_origin_regex = r"https://.*\.vercel\.app"
    elif cfg.cors_origins:
        cors_origins = cfg.cors_origins
        allow_origin_regex = None if "*" in cors_origins else r"https://.*\.vercel\.app"
    else:
        cors_origins = ["*"]
        allow_origin_regex = None

    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins,
        allow_origin_regex=allow_origin_regex,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # 2. Register Exception Handlers
    app.add_exception_handler(APIError, api_error_handler)
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(EpiSenseError, domain_exception_handler)
    app.add_exception_handler(Exception, unhandled_exception_handler)

    # 3. Include Routers
    app.include_router(health_router)
    app.include_router(documents_router)
    app.include_router(alerts_router)
    app.include_router(provenance_router)
    app.include_router(events_router)
    app.include_router(signals_router)
    app.include_router(geo_router)
    app.include_router(sources_router)
    app.include_router(workbench_router)
    app.include_router(fusion_router)
    app.include_router(evaluation_router)
    app.include_router(metrics_router)
    app.include_router(taxonomy_router)
    app.include_router(forecasting_router)
    app.include_router(models_router)

    # 4. WebSocket Surveillance Feed Route
    @app.websocket("/api/v1/ws/surveillance")
    async def websocket_endpoint(websocket: WebSocket):
        pub = get_publisher()
        client_id = await pub.connect(websocket)
        await pub.handle_client_loop(client_id)

    return app


# Default singleton instance
app = create_app()

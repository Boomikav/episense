"""
Geospatial Surveillance and GIS Layer Routes for EpiSense (Phase 12).
Emits RFC 7946 compliant GeoJSON layers and regional dashboard aggregations without fabricating coordinates.
"""

from typing import Optional
from fastapi import APIRouter, Depends, Query

from episense.schemas.alert import AlertTier
from episense.schemas.assertion import AssertionStatus
from episense.api.dependencies import get_geo_query_service
from episense.api.models import (
    GeoJSONFeatureCollection,
    GeoSummaryResponse,
)
from episense.api.services import GeoQueryService

router = APIRouter(prefix="/api/v1/geo", tags=["Geospatial Surveillance"])


@router.get(
    "/alerts",
    response_model=GeoJSONFeatureCollection,
    summary="Get Alerts GeoJSON Layer",
    description="Returns a valid GeoJSON FeatureCollection of epidemiological alerts grounded to gazetteer coordinates.",
)
async def get_geo_alerts(
    tier: Optional[AlertTier] = Query(None, description="Filter by Alert Tier"),
    pathogen: Optional[str] = Query(None, description="Filter by pathogen substring"),
    min_score: Optional[float] = Query(None, ge=0.0, le=1.0, description="Minimum composite score"),
    current_only: bool = Query(False, description="Filter strictly to current operational window"),
    priority_only: bool = Query(False, description="Filter strictly to the 8 canonical priority diseases"),
    service: GeoQueryService = Depends(get_geo_query_service),
) -> GeoJSONFeatureCollection:
    return service.get_alerts_geojson(
        tier=tier,
        pathogen=pathogen,
        min_score=min_score,
        current_only=current_only,
        priority_only=priority_only,
    )


@router.get(
    "/events",
    response_model=GeoJSONFeatureCollection,
    summary="Get Fused Events GeoJSON Layer",
    description="Returns a valid GeoJSON FeatureCollection of canonical fused events grounded to gazetteer coordinates.",
)
async def get_geo_events(
    pathogen: Optional[str] = Query(None, description="Filter by pathogen substring"),
    assertion_status: Optional[AssertionStatus] = Query(None, description="Filter by assertion status"),
    current_only: bool = Query(False, description="Filter strictly to current operational window"),
    priority_only: bool = Query(False, description="Filter strictly to the 8 canonical priority diseases"),
    service: GeoQueryService = Depends(get_geo_query_service),
) -> GeoJSONFeatureCollection:
    return service.get_events_geojson(
        pathogen=pathogen,
        assertion_status=assertion_status,
        current_only=current_only,
        priority_only=priority_only,
    )


@router.get(
    "/heatmap",
    response_model=GeoJSONFeatureCollection,
    summary="Get Surveillance Heatmap Layer",
    description="Returns Point features weighted by composite outbreak risk score for GIS heatmap rendering.",
)
async def get_geo_heatmap(
    service: GeoQueryService = Depends(get_geo_query_service),
) -> GeoJSONFeatureCollection:
    return service.get_heatmap_geojson()


@router.get(
    "/summary",
    response_model=GeoSummaryResponse,
    summary="Get Regional Surveillance Summary",
    description="Aggregates alerts, cases, and active pathogens across administrative regions for map visualization.",
)
async def get_geo_summary(
    service: GeoQueryService = Depends(get_geo_query_service),
) -> GeoSummaryResponse:
    return service.get_regional_summary()

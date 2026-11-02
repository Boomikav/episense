"""
FusedEventCluster schema representing cross-source aggregated event clusters.
"""

from datetime import datetime
from typing import List, Optional
from uuid import UUID, uuid4
from pydantic import Field

from episense.schemas.base import EpiSenseBaseModel, utc_now
from episense.schemas.location import Location


class FusedEventCluster(EpiSenseBaseModel):
    """
    Spatiotemporally aggregated cluster of health events from one or more sources.
    """
    cluster_id: UUID = Field(default_factory=uuid4)
    canonical_disease: str
    canonical_location: Location
    start_date: datetime
    end_date: datetime
    event_ids: List[UUID]
    source_ids: List[str]
    distinct_source_count: int = Field(ge=1)
    aggregated_case_estimate: Optional[int] = Field(default=None, ge=0)
    created_at: datetime = Field(default_factory=utc_now)

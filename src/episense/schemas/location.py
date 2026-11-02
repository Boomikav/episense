"""
Geographic location schema representing resolved toponyms with administrative hierarchy.
"""

from enum import Enum
from typing import Optional
from uuid import UUID, uuid4
from pydantic import Field

from episense.schemas.base import EpiSenseBaseModel


class GeographicLevel(str, Enum):
    COUNTRY = "country"      # Admin 0
    REGION = "region"        # Admin 1 (State/Province)
    DISTRICT = "district"    # Admin 2 (District/County)
    SUBDISTRICT = "subdistrict" # Admin 3 (Tehsil/Mandal/Block)
    CITY = "city"            # Admin 4 (Municipality/Town)
    POINT = "point"          # Specific coordinate centroid


class Location(EpiSenseBaseModel):
    """
    A geographic location grounded in an administrative gazetteer.
    """
    location_id: UUID = Field(default_factory=uuid4)
    original_text: str = Field(min_length=1)
    normalized_name: str = Field(min_length=1)
    geographic_level: GeographicLevel = GeographicLevel.DISTRICT
    parent_location: Optional[str] = Field(default=None, description="e.g. State or Country name")
    gazetteer_id: Optional[str] = Field(default=None, description="Identifier in gazetteer database")
    latitude: Optional[float] = Field(default=None, ge=-90.0, le=90.0)
    longitude: Optional[float] = Field(default=None, ge=-180.0, le=180.0)
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    provenance_method: str = Field(default="gazetteer_lookup")

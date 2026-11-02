"""
Provenance record schema linking any extracted concept back to raw source text.
"""

from datetime import datetime
from uuid import UUID
from pydantic import Field

from episense.schemas.base import EpiSenseBaseModel, utc_now


class ProvenanceRecord(EpiSenseBaseModel):
    """
    Immutable audit record linking an entity, event, or alert
    back to the exact source document, extraction method, and token spans.
    """
    document_id: UUID
    source_id: str
    start_char: int = Field(ge=0, description="Character start offset in source text")
    end_char: int = Field(ge=0, description="Character end offset in source text")
    extraction_method: str = Field(description="Name/version of extractor or model that produced this")
    extraction_timestamp: datetime = Field(default_factory=utc_now)
    confidence: float = Field(ge=0.0, le=1.0, description="Confidence metric of extraction")

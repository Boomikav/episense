"""
Base model and shared primitives for all EpiSense schemas.
"""

from datetime import datetime, timezone
from pydantic import BaseModel, ConfigDict


class EpiSenseBaseModel(BaseModel):
    """Base schema enforcing immutability and strict field types."""
    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        arbitrary_types_allowed=False,
    )


def utc_now() -> datetime:
    """Returns timezone-aware UTC current timestamp."""
    return datetime.now(timezone.utc)

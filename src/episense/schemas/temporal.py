"""
Temporal expression schema representing dates, intervals, and relative time expressions.
"""

from datetime import datetime
from enum import Enum
from typing import Optional
from uuid import UUID, uuid4
from pydantic import Field

from episense.schemas.base import EpiSenseBaseModel


class TemporalType(str, Enum):
    POINT = "point"
    INTERVAL = "interval"
    RELATIVE = "relative"
    RECURRENT = "recurrent"
    DURATION = "duration"
    UNKNOWN = "unknown"


class DatePrecision(str, Enum):
    YEAR = "YEAR"
    MONTH = "MONTH"
    DAY = "DAY"
    REPORTING_PERIOD = "REPORTING_PERIOD"


class TemporalExpression(EpiSenseBaseModel):
    """
    A normalized temporal expression extracted from public health text.
    """
    temporal_id: UUID = Field(default_factory=uuid4)
    original_expression: str = Field(min_length=1)
    normalized_start: datetime
    normalized_end: datetime
    start_char: int = Field(ge=0)
    end_char: int = Field(ge=0)
    temporal_type: TemporalType = TemporalType.POINT
    date_precision: DatePrecision = DatePrecision.DAY
    event_date_precision: DatePrecision = DatePrecision.DAY
    event_period_start: Optional[datetime] = None
    event_period_end: Optional[datetime] = None
    is_relative: bool = False
    is_duration: bool = False
    duration_unit: Optional[str] = None
    duration_value: Optional[float] = None
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)

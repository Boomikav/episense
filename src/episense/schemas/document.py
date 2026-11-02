"""
Document schema representing ingested public health textual records.
Enforces strict separation between external retrieval time, publication time,
event window, and derived currentness classification.
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Dict, Optional
from uuid import UUID, uuid4
from pydantic import Field, model_validator

from episense.schemas.base import EpiSenseBaseModel, utc_now
from episense.schemas.temporal import DatePrecision


class SourceType(str, Enum):
    OFFICIAL_BULLETIN = "official_bulletin"
    GOVERNMENT_REPORT = "government_report"
    PUBLIC_SYNDICATION = "public_syndication"
    NEWS_MEDIA = "news_media"
    NEWS_ARTICLE = "news_media"
    SOCIAL_MEDIA = "social_media"
    BENCHMARK_CORPUS = "benchmark_corpus"


class OriginClassification(str, Enum):
    LIVE_EXTERNAL = "LIVE_EXTERNAL"
    MANUAL_SUBMISSION = "MANUAL_SUBMISSION"
    HISTORICAL_CORPUS = "HISTORICAL_CORPUS"
    BENCHMARK = "BENCHMARK"
    SYNTHETIC_TEST = "SYNTHETIC_TEST"


class FreshnessClassification(str, Enum):
    """
    Explicit temporal freshness of public health documents.
    Decouples source retrieval channel (LIVE_EXTERNAL vs HISTORICAL_CORPUS)
    from the actual epidemiological timeliness of the report.
    """
    CURRENT = "CURRENT"                 # Occurred / published in current operational window (current month)
    RECENT = "RECENT"                   # Occurred within recent weeks (1-3 months prior)
    HISTORICAL = "HISTORICAL"           # Occurred prior to recent operational horizon (> 3 months or archival)
    BACKFILLED = "BACKFILLED"           # Historical surveillance data published / ingested retroactively
    UNKNOWN_DATE = "UNKNOWN_DATE"       # Date could not be grounded in text


class CurrentnessClassification(str, Enum):
    """
    Explainable temporal classification of epidemiological reports.
    Prevents newly discovered historical documents from masquerading as current alerts.
    """
    CURRENT_EVENT = "CURRENT_EVENT"                                         # Active recent event within current operational window (current month)
    RECENTLY_PUBLISHED_HISTORICAL_EVENT = "RECENTLY_PUBLISHED_HISTORICAL_EVENT" # Newly published/discovered document describing past event
    HISTORICAL_REFERENCE = "HISTORICAL_REFERENCE"                           # Archival report or historical publication prior to current month
    RETROSPECTIVE_REPORT = "RETROSPECTIVE_REPORT"                           # Recent publication analyzing or reviewing a past event
    EVENT_DATE_UNKNOWN = "EVENT_DATE_UNKNOWN"                               # Event timestamp could not be grounded in text


class DocumentLifecycleState(str, Enum):
    """
    Formal lifecycle state of an ingested document through the surveillance pipeline.
    """
    DISCOVERED = "DISCOVERED"
    FETCHED = "FETCHED"
    RAW_STORED = "RAW_STORED"
    TEXT_EXTRACTED = "TEXT_EXTRACTED"
    NLP_COMPLETED = "NLP_COMPLETED"
    EVENT_CANDIDATE = "EVENT_CANDIDATE"
    VALIDATED = "VALIDATED"
    REJECTED = "REJECTED"
    DUPLICATE = "DUPLICATE"


class Document(EpiSenseBaseModel):
    """
    Represents an immutable ingested public health document with multi-axis temporal provenance.
    """
    document_id: UUID = Field(default_factory=uuid4)
    source_id: str = Field(description="Identifier of publishing source or feed")
    source_type: SourceType = Field(default=SourceType.BENCHMARK_CORPUS)
    origin: OriginClassification = Field(default=OriginClassification.HISTORICAL_CORPUS)
    title: str = Field(min_length=1)
    text: str = Field(min_length=1)
    publication_timestamp: Optional[datetime] = None
    retrieval_timestamp: Optional[datetime] = None
    ingestion_timestamp: datetime = Field(default_factory=utc_now)
    first_seen_at: Optional[datetime] = None
    event_start: Optional[datetime] = None
    event_end: Optional[datetime] = None
    event_date_precision: Optional[DatePrecision] = None
    event_period_start: Optional[datetime] = None
    event_period_end: Optional[datetime] = None
    source_reporting_week: Optional[int] = Field(default=None, description="Official bulletin reporting week supplied by source")
    source_reporting_year: Optional[int] = Field(default=None, description="Official bulletin reporting year supplied by source")
    observation_period_start: Optional[datetime] = None
    observation_period_end: Optional[datetime] = None
    currentness_status: CurrentnessClassification = Field(
        default=CurrentnessClassification.CURRENT_EVENT,
        description="Explainable classification based on event and publication time"
    )
    freshness: FreshnessClassification = Field(
        default=FreshnessClassification.HISTORICAL,
        description="Decoupled temporal freshness of epidemiological content"
    )
    lifecycle_state: DocumentLifecycleState = Field(
        default=DocumentLifecycleState.FETCHED,
        description="Document processing lifecycle state"
    )
    source_url: Optional[str] = None
    language: str = Field(default="en")
    content_hash_sha256: str = Field(min_length=64, max_length=64)
    provenance_metadata: Dict[str, str] = Field(default_factory=dict)

    @model_validator(mode="after")
    def compute_currentness(self) -> "Document":
        if self.retrieval_timestamp is None:
            object.__setattr__(self, "retrieval_timestamp", self.ingestion_timestamp)
        if self.first_seen_at is None:
            object.__setattr__(self, "first_seen_at", self.ingestion_timestamp)

        # If explicitly assigned RECENTLY_PUBLISHED_HISTORICAL_EVENT, preserve it
        if self.currentness_status == CurrentnessClassification.RECENTLY_PUBLISHED_HISTORICAL_EVENT:
            if self.origin == OriginClassification.HISTORICAL_CORPUS:
                object.__setattr__(self, "freshness", FreshnessClassification.HISTORICAL)
            else:
                object.__setattr__(self, "freshness", FreshnessClassification.RECENT)
            return self

        now = datetime.now(timezone.utc)
        current_month_start = datetime(now.year, now.month, 1, 0, 0, 0, tzinfo=timezone.utc)

        # Evaluate currentness and decoupled freshness
        if self.origin == OriginClassification.HISTORICAL_CORPUS:
            object.__setattr__(self, "currentness_status", CurrentnessClassification.HISTORICAL_REFERENCE)
            object.__setattr__(self, "freshness", FreshnessClassification.HISTORICAL)
        elif self.publication_timestamp:
            pub_dt = self.publication_timestamp
            if pub_dt.tzinfo is None:
                pub_dt = pub_dt.replace(tzinfo=timezone.utc)
            ev_dt = self.event_start or pub_dt
            if ev_dt.tzinfo is None:
                ev_dt = ev_dt.replace(tzinfo=timezone.utc)

            days_old = (now - ev_dt).total_seconds() / 86400.0

            if ev_dt < current_month_start:
                if pub_dt >= current_month_start or days_old <= 90:
                    object.__setattr__(self, "currentness_status", CurrentnessClassification.RECENTLY_PUBLISHED_HISTORICAL_EVENT)
                    object.__setattr__(self, "freshness", FreshnessClassification.RECENT if days_old <= 90 else FreshnessClassification.HISTORICAL)
                else:
                    object.__setattr__(self, "currentness_status", CurrentnessClassification.HISTORICAL_REFERENCE)
                    object.__setattr__(self, "freshness", FreshnessClassification.HISTORICAL)
            elif pub_dt < current_month_start:
                object.__setattr__(self, "currentness_status", CurrentnessClassification.HISTORICAL_REFERENCE)
                object.__setattr__(self, "freshness", FreshnessClassification.HISTORICAL)
            else:
                object.__setattr__(self, "currentness_status", CurrentnessClassification.CURRENT_EVENT)
                object.__setattr__(self, "freshness", FreshnessClassification.CURRENT)
        else:
            if self.event_start:
                ev_dt = self.event_start
                if ev_dt.tzinfo is None:
                    ev_dt = ev_dt.replace(tzinfo=timezone.utc)
                days_old = (now - ev_dt).total_seconds() / 86400.0
                if ev_dt < current_month_start:
                    if days_old <= 90:
                        object.__setattr__(self, "currentness_status", CurrentnessClassification.RECENTLY_PUBLISHED_HISTORICAL_EVENT)
                        object.__setattr__(self, "freshness", FreshnessClassification.RECENT)
                    else:
                        object.__setattr__(self, "currentness_status", CurrentnessClassification.HISTORICAL_REFERENCE)
                        object.__setattr__(self, "freshness", FreshnessClassification.HISTORICAL)
                else:
                    object.__setattr__(self, "currentness_status", CurrentnessClassification.CURRENT_EVENT)
                    object.__setattr__(self, "freshness", FreshnessClassification.CURRENT)
            elif self.origin == OriginClassification.LIVE_EXTERNAL:
                object.__setattr__(self, "currentness_status", CurrentnessClassification.EVENT_DATE_UNKNOWN)
                object.__setattr__(self, "freshness", FreshnessClassification.UNKNOWN_DATE)
            else:
                object.__setattr__(self, "currentness_status", CurrentnessClassification.HISTORICAL_REFERENCE)
                object.__setattr__(self, "freshness", FreshnessClassification.HISTORICAL)
        return self

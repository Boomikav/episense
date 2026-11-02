"""
Schemas for Detailed 17-Stage Document Processing Pipeline Traces and NLP Workbench.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4
from pydantic import Field

from episense.schemas.base import EpiSenseBaseModel, utc_now
from episense.schemas.document import OriginClassification, SourceType
from episense.schemas.nlp import NLPOutput


class StageStatus(str, Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    SKIPPED = "SKIPPED"
    FAILED = "FAILED"


class PipelineStageExecution(EpiSenseBaseModel):
    """Execution telemetry and output for a single pipeline stage."""
    stage_number: int = Field(ge=1, le=17)
    stage_name: str
    status: StageStatus = StageStatus.PENDING
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    duration_ms: float = 0.0
    input_summary: str = ""
    output_summary: str = ""
    warnings: List[str] = Field(default_factory=list)
    error_details: Optional[str] = None
    details: Dict[str, Any] = Field(default_factory=dict)


class DocumentPipelineTrace(EpiSenseBaseModel):
    """
    Complete inspectable trace of a document through all 17 pipeline stages.
    Serves as the data backbone for the NLP Workbench and forensic audit.
    """
    trace_id: UUID = Field(default_factory=uuid4)
    document_id: UUID
    source_id: str
    source_type: SourceType = SourceType.OFFICIAL_BULLETIN
    origin: OriginClassification = OriginClassification.LIVE_EXTERNAL
    title: str
    raw_text: str
    source_url: Optional[str] = None
    publication_timestamp: Optional[datetime] = None
    retrieval_timestamp: datetime = Field(default_factory=utc_now)
    content_hash_sha256: str
    overall_status: str = "completed"  # completed, failed, duplicate_skipped
    total_duration_ms: float = 0.0
    stages: List[PipelineStageExecution] = Field(default_factory=list)
    nlp_output: Optional[NLPOutput] = None
    candidate_event_ids: List[UUID] = Field(default_factory=list)
    fused_event_ids: List[UUID] = Field(default_factory=list)
    signal_ids: List[UUID] = Field(default_factory=list)
    alert_ids: List[UUID] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=utc_now)

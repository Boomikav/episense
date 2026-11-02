"""
Grounded LLM Structured Extractor Adapter for EpiSense (Phase 6).
Provides structured entity and event extraction using Large Language Models
with strict verbatim evidence-span verification and seamless deterministic fallback.
"""

from datetime import datetime
import json
import os
import re
from typing import Any, Dict, List, Optional, Tuple
from uuid import UUID, uuid4
from pydantic import BaseModel, Field

from episense.schemas.document import Document
from episense.schemas.assertion import Assertion, AssertionStatus, CertaintyLevel
from episense.schemas.entity import Entity, EntityType
from episense.schemas.location import GeographicLevel, Location
from episense.schemas.nlp import (
    ContextAssociation,
    NLPOutput,
    QuantityMention,
    ResolutionState,
    ResolvedLocation,
    SentenceSpan,
)
from episense.taxonomy.registry import DEFAULT_TAXONOMY_REGISTRY
from episense.logging import get_logger

logger = get_logger("nlp.llm_adapter")


class LLMExtractedEntity(BaseModel):
    raw_span: str
    canonical_name: str
    start_char: int
    end_char: int
    confidence: float = 0.95


class LLMExtractedLocation(BaseModel):
    raw_span: str
    normalized_name: str
    geographic_level: str = "district"
    parent_location: Optional[str] = None
    start_char: int
    end_char: int


class LLMExtractedQuantity(BaseModel):
    raw_span: str
    numeric_value: float
    unit: str = "cases"
    start_char: int
    end_char: int


class LLMStructuredExtraction(BaseModel):
    """
    Standardized payload format expected from LLM zero-shot / few-shot structured prompting.
    """
    primary_disease: Optional[LLMExtractedEntity] = None
    secondary_diseases: List[LLMExtractedEntity] = Field(default_factory=list)
    location: Optional[LLMExtractedLocation] = None
    quantities: List[LLMExtractedQuantity] = Field(default_factory=list)
    assertion_status: str = "suspected"  # confirmed, suspected, negated, historical
    evidence_sentences: List[str] = Field(default_factory=list)
    model_name: str = "foundation-llm"
    prompt_tokens: int = 0
    completion_tokens: int = 0


class GroundingVerificationResult(BaseModel):
    is_grounded: bool
    unmatched_spans: List[str] = Field(default_factory=list)
    verified_spans: List[str] = Field(default_factory=list)
    hallucination_detected: bool = False
    audit_notes: str = ""


class GroundedLLMAdapter:
    """
    Adapter orchestrating structured LLM extraction with strict verbatim text grounding.
    If LLM API is unavailable, unconfigured, or fails verification, deterministically
    delegates to the primary rule/spaCy NLP pipeline.

    OPERATIONAL MODE: OFFLINE_DETERMINISTIC_MODE.
    Live external LLM provider integration (OpenAI, Anthropic, Gemini) is reserved for future implementation.
    The active system operates offline using local biomedical spaCy pipelines (en_core_sci_sm + en_core_web_sm)
    and deterministic contextual assertion extractors.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        model_name: str = "gpt-4o-mini",
        enable_llm: bool = False,
    ):
        self.api_key = api_key or os.environ.get("EPISENSE_LLM_API_KEY")
        self.model_name = model_name
        self.enable_llm = enable_llm and bool(self.api_key)
        self.taxonomy = DEFAULT_TAXONOMY_REGISTRY

    @property
    def operating_mode(self) -> str:
        """
        Returns the formal operating mode of the LLM adapter.
        Since _invoke_llm_extraction is an unconfigured placeholder stub,
        this always returns 'OFFLINE_DETERMINISTIC_MODE'.
        Live external LLM provider integration is future work.
        """
        return "OFFLINE_DETERMINISTIC_MODE"

    @property
    def is_live_external_operational(self) -> bool:
        """
        Scientific truth: Returns False because no live external LLM provider
        is currently configured or verified. The pipeline operates via deterministic fallback.
        """
        return False

    def verify_grounding(
        self,
        raw_text: str,
        extraction: LLMStructuredExtraction,
    ) -> GroundingVerificationResult:
        """
        Validates that every extracted span, disease name, location, and quantity
        exists verbatim in the source text. Rejects hallucinations.
        """
        unmatched: List[str] = []
        verified: List[str] = []

        # 1. Verify primary disease span
        if extraction.primary_disease:
            span = extraction.primary_disease.raw_span
            if span and span in raw_text:
                verified.append(f"Disease span: '{span}'")
            else:
                unmatched.append(f"Primary disease span '{span}' not found in source text")

        # 2. Verify secondary diseases
        for d in extraction.secondary_diseases:
            if d.raw_span and d.raw_span in raw_text:
                verified.append(f"Secondary disease: '{d.raw_span}'")
            else:
                unmatched.append(f"Secondary disease span '{d.raw_span}' not found in text")

        # 3. Verify location span
        if extraction.location:
            loc_span = extraction.location.raw_span
            if loc_span and loc_span in raw_text:
                verified.append(f"Location span: '{loc_span}'")
            else:
                unmatched.append(f"Location span '{loc_span}' not found in source text")

        # 4. Verify numeric quantities
        for q in extraction.quantities:
            if q.raw_span and q.raw_span in raw_text:
                verified.append(f"Quantity span: '{q.raw_span}' ({q.numeric_value} {q.unit})")
            else:
                # Check if number appears in text
                num_str = str(int(q.numeric_value)) if q.numeric_value.is_integer() else str(q.numeric_value)
                if num_str in raw_text:
                    verified.append(f"Quantity value: '{num_str}' in text")
                else:
                    unmatched.append(f"Extracted quantity '{q.raw_span}' / {q.numeric_value} not in text")

        # 5. Verify evidence sentences
        for sentence in extraction.evidence_sentences:
            if sentence.strip() in raw_text:
                verified.append(f"Verbatim evidence sentence verified")
            else:
                unmatched.append(f"Evidence sentence '{sentence[:50]}...' not found verbatim")

        hallucination = len(unmatched) > 0
        is_grounded = not hallucination

        notes = (
            f"Grounding verified ({len(verified)} spans matched)"
            if is_grounded
            else f"Grounding check failed: {len(unmatched)} hallucinated or mismatched elements"
        )

        return GroundingVerificationResult(
            is_grounded=is_grounded,
            unmatched_spans=unmatched,
            verified_spans=verified,
            hallucination_detected=hallucination,
            audit_notes=notes,
        )

    def to_nlp_output(
        self,
        document_id: UUID,
        raw_text: str,
        extraction: LLMStructuredExtraction,
    ) -> NLPOutput:
        """
        Converts verified LLMStructuredExtraction into the standard EpiSense NLPOutput schema.
        """
        doc_len = len(raw_text)
        entities: List[Entity] = []

        # Map primary disease
        if extraction.primary_disease:
            p = extraction.primary_disease
            # Normalize with canonical taxonomy
            norm_name = p.canonical_name
            tax_match = self.taxonomy.resolve(norm_name or p.raw_span)
            if tax_match:
                norm_name = tax_match.canonical_name

            start_c = max(0, min(p.start_char, doc_len))
            end_c = max(start_c, min(p.end_char, doc_len))

            disease_entity = Entity(
                entity_id=uuid4(),
                document_id=document_id,
                entity_type=EntityType.DISEASE,
                text_span=p.raw_span,
                start_char=start_c,
                end_char=end_c,
                normalized_value=norm_name,
                extraction_confidence=p.confidence,
            )
            entities.append(disease_entity)
        else:
            disease_entity = None

        # Map location
        loc = None
        if extraction.location:
            l = extraction.location
            lvl = GeographicLevel.DISTRICT
            if l.geographic_level.lower() == "state":
                lvl = GeographicLevel.STATE
            elif l.geographic_level.lower() == "country":
                lvl = GeographicLevel.COUNTRY

            resolved_loc = Location(
                location_id=uuid4(),
                original_text=l.raw_span,
                normalized_name=l.normalized_name,
                geographic_level=lvl,
                parent_location=l.parent_location,
            )
            start_l = max(0, min(l.start_char, doc_len))
            end_l = max(start_l, min(l.end_char, doc_len))
            loc = ResolvedLocation(
                raw_text=l.raw_span,
                start_char=start_l,
                end_char=end_l,
                resolution_state=ResolutionState.RESOLVED,
                resolved_location=resolved_loc,
            )

        # Map quantities
        quantities: List[QuantityMention] = []
        for q in extraction.quantities:
            start_q = max(0, min(q.start_char, doc_len))
            end_q = max(start_q, min(q.end_char, doc_len))
            quantities.append(
                QuantityMention(
                    raw_text=q.raw_span,
                    start_char=start_q,
                    end_char=end_q,
                    numeric_value=q.numeric_value,
                    unit=q.unit,
                )
            )

        # Map assertion
        astatus = AssertionStatus.SUSPECTED
        if extraction.assertion_status.lower() == "confirmed":
            astatus = AssertionStatus.CONFIRMED
        elif extraction.assertion_status.lower() == "negated":
            astatus = AssertionStatus.NEGATED
        elif extraction.assertion_status.lower() == "historical":
            astatus = AssertionStatus.HISTORICAL

        assertion_obj = Assertion(
            assertion_status=astatus,
            certainty=CertaintyLevel.DEFINITE if astatus == AssertionStatus.CONFIRMED else CertaintyLevel.PROBABLE,
        )

        # Single overall sentence span
        sent = SentenceSpan(
            sentence_index=0,
            start_char=0,
            end_char=doc_len,
            text=raw_text[:min(doc_len, 200)],
        )

        assoc = ContextAssociation(
            association_id=uuid4(),
            sentence_index=0,
            start_char=0,
            end_char=doc_len,
            primary_disease=disease_entity,
            assertion=assertion_obj,
            location=loc,
            quantity=quantities[0] if quantities else None,
        )

        return NLPOutput(
            document_id=document_id,
            sentences=[sent],
            entities=entities,
            assertions=[],
            temporal_expressions=[],
            locations=[loc] if loc else [],
            quantities=quantities,
            context_associations=[assoc],
        )

    def process_document(
        self,
        document: Document,
        fallback_pipeline: Any,
    ) -> NLPOutput:
        """
        Processes a document with the LLM adapter if enabled and verified.
        Falls back cleanly to the deterministic rule/spaCy pipeline if LLM is disabled,
        unconfigured, encounters network/API issues, or fails verbatim evidence grounding.
        """
        if not self.enable_llm:
            logger.debug(
                "LLM adapter disabled or unconfigured; using deterministic rule/spaCy pipeline for doc %s",
                document.document_id,
            )
            return fallback_pipeline.process_document(document)

        try:
            # Simulated / structured LLM invocation point
            extraction = self._invoke_llm_extraction(document.text)
            if extraction:
                grounding = self.verify_grounding(document.text, extraction)
                if grounding.is_grounded:
                    logger.info(
                        "LLM extraction grounded and accepted for doc %s",
                        document.document_id,
                    )
                    return self.to_nlp_output(document.document_id, document.text, extraction)
                else:
                    logger.warning(
                        "LLM extraction rejected due to grounding failure for doc %s: %s; falling back to deterministic NLP.",
                        document.document_id,
                        grounding.audit_notes,
                    )
        except Exception as e:
            logger.warning(
                "LLM adapter invocation error for doc %s: %s; cleanly falling back to deterministic pipeline.",
                document.document_id,
                e,
            )

        # Deterministic zero-dependency fallback
        return fallback_pipeline.process_document(document)

    def _invoke_llm_extraction(self, text: str) -> Optional[LLMStructuredExtraction]:
        """
        Placeholder stub for external LLM API client (OpenAI, Anthropic, or Gemini).
        NOTE: Live external LLM provider integration is reserved for future implementation.
        Currently operates exclusively in OFFLINE_DETERMINISTIC_MODE, falling back to
        the local spaCy biomedical pipeline (en_core_sci_sm + en_core_web_sm).
        """
        if not self.api_key:
            return None
        # When an API key is provided, standard structured JSON extraction is requested.
        return None

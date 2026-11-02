"""
Provenance Verification and Audit Record Generation for EpiSense NLP Pipeline.
Guarantees character-level traceability back to uncleaned raw text.
"""

from typing import Any, List
from uuid import UUID

from episense.schemas.provenance import ProvenanceRecord
from episense.schemas.entity import Entity
from episense.schemas.temporal import TemporalExpression
from episense.schemas.nlp import ResolvedLocation, QuantityMention
from episense.exceptions import ProvenanceError


class ProvenanceValidator:
    """
    Validates character-level offset integrity and generates immutable
    ProvenanceRecords linking extracted concepts to source documents.
    """

    @staticmethod
    def validate_offset(raw_text: str, start_char: int, end_char: int, expected_text: str, label: str = "span"):
        """
        Validates raw_text[start_char:end_char] == expected_text.
        Raises ProvenanceError on mismatch.
        """
        if start_char < 0 or end_char > len(raw_text) or start_char >= end_char:
            raise ProvenanceError(
                f"Invalid offset bounds [{start_char}:{end_char}] for text of length {len(raw_text)}"
            )

        actual = raw_text[start_char:end_char]
        if actual != expected_text:
            raise ProvenanceError(
                f"Offset provenance failure for {label}: raw_text[{start_char}:{end_char}]='{actual}' "
                f"does not match expected='{expected_text}'"
            )

    @classmethod
    def generate_records(
        cls,
        document_id: UUID,
        source_id: str,
        raw_text: str,
        entities: List[Entity],
        temporals: List[TemporalExpression],
        locations: List[ResolvedLocation],
        quantities: List[QuantityMention],
    ) -> List[ProvenanceRecord]:
        """
        Validates all extractions against raw_text and generates ProvenanceRecords.
        """
        records: List[ProvenanceRecord] = []

        for e in entities:
            cls.validate_offset(raw_text, e.start_char, e.end_char, e.text_span, f"Entity({e.entity_type.value})")
            records.append(
                ProvenanceRecord(
                    document_id=document_id,
                    source_id=source_id,
                    start_char=e.start_char,
                    end_char=e.end_char,
                    extraction_method=f"ner:{e.model_info}",
                    confidence=e.extraction_confidence,
                )
            )

        for t in temporals:
            cls.validate_offset(raw_text, t.start_char, t.end_char, t.original_expression, "TemporalExpression")
            records.append(
                ProvenanceRecord(
                    document_id=document_id,
                    source_id=source_id,
                    start_char=t.start_char,
                    end_char=t.end_char,
                    extraction_method="temporal:rule_based+dateparser",
                    confidence=t.confidence,
                )
            )

        for loc in locations:
            cls.validate_offset(raw_text, loc.start_char, loc.end_char, loc.raw_text, "ResolvedLocation")
            records.append(
                ProvenanceRecord(
                    document_id=document_id,
                    source_id=source_id,
                    start_char=loc.start_char,
                    end_char=loc.end_char,
                    extraction_method=f"geospatial:{loc.resolution_state.value}",
                    confidence=loc.confidence,
                )
            )

        for q in quantities:
            cls.validate_offset(raw_text, q.start_char, q.end_char, q.raw_text, "QuantityMention")
            records.append(
                ProvenanceRecord(
                    document_id=document_id,
                    source_id=source_id,
                    start_char=q.start_char,
                    end_char=q.end_char,
                    extraction_method="quantity:regex+pattern",
                    confidence=1.0,
                )
            )

        return records

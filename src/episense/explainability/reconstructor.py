"""
Evidence Span Reconstructor for EpiSense (Phase 10).
Reconstructs exact character spans from source document text, validates offset bounds
and textual integrity, and provides surrounding context windows.
"""

from typing import Dict, List, Optional, Union
from uuid import UUID

from episense.schemas.document import Document
from episense.schemas.event import EvidenceReference
from episense.schemas.explainability import ReconstructedEvidenceSpan
from episense.logging import get_logger

logger = get_logger("explainability.reconstructor")


class EvidenceSpanReconstructor:
    """
    Validates and reconstructs character-level evidence spans against raw source document text.
    Enforces the zero-fabrication safety constraint.
    """

    def __init__(self, default_context_window: int = 50):
        self.default_context_window = default_context_window

    def reconstruct_span(
        self,
        reference: EvidenceReference,
        document_text: Optional[str] = None,
        context_window: Optional[int] = None,
    ) -> ReconstructedEvidenceSpan:
        """
        Reconstructs and validates a single EvidenceReference against document_text.
        """
        ctx_win = context_window if context_window is not None else self.default_context_window

        if document_text is None:
            return ReconstructedEvidenceSpan(
                document_id=reference.document_id,
                source_id=reference.source_id,
                start_char=reference.start_char,
                end_char=reference.end_char,
                expected_text=reference.span_text,
                extracted_text="",
                surrounding_context="",
                attribute_role=reference.attribute_role,
                extraction_method=reference.extraction_method,
                is_valid=False,
                validation_error="Source document text not found in registry (missing provenance target)",
            )

        doc_len = len(document_text)
        start = reference.start_char
        end = reference.end_char

        # Bounds checks
        if start < 0 or end < start:
            return ReconstructedEvidenceSpan(
                document_id=reference.document_id,
                source_id=reference.source_id,
                start_char=start,
                end_char=end,
                expected_text=reference.span_text,
                extracted_text="",
                surrounding_context="",
                attribute_role=reference.attribute_role,
                extraction_method=reference.extraction_method,
                is_valid=False,
                validation_error=f"Invalid offset range [{start}:{end}] (negative or reversed)",
            )

        if end > doc_len:
            return ReconstructedEvidenceSpan(
                document_id=reference.document_id,
                source_id=reference.source_id,
                start_char=start,
                end_char=end,
                expected_text=reference.span_text,
                extracted_text="",
                surrounding_context="",
                attribute_role=reference.attribute_role,
                extraction_method=reference.extraction_method,
                is_valid=False,
                validation_error=f"Character end offset {end} exceeds document length ({doc_len})",
            )

        extracted = document_text[start:end]

        # Text integrity check against expected span_text
        is_valid = True
        val_error = None
        if reference.span_text:
            expected_clean = reference.span_text.strip().lower()
            extracted_clean = extracted.strip().lower()
            if expected_clean != extracted_clean:
                is_valid = False
                val_error = (
                    f"Text mismatch at [{start}:{end}]: expected '{reference.span_text}', "
                    f"found '{extracted}'"
                )

        # Surrounding context extraction
        ctx_start = max(0, start - ctx_win)
        ctx_end = min(doc_len, end + ctx_win)
        context = document_text[ctx_start:ctx_end]

        return ReconstructedEvidenceSpan(
            document_id=reference.document_id,
            source_id=reference.source_id,
            start_char=start,
            end_char=end,
            expected_text=reference.span_text,
            extracted_text=extracted,
            surrounding_context=context,
            attribute_role=reference.attribute_role,
            extraction_method=reference.extraction_method,
            is_valid=is_valid,
            validation_error=val_error,
        )

    def reconstruct_spans(
        self,
        references: List[EvidenceReference],
        documents_map: Dict[UUID, Union[Document, str]],
        context_window: Optional[int] = None,
    ) -> List[ReconstructedEvidenceSpan]:
        """
        Reconstructs a collection of EvidenceReferences against a document lookup map.
        Guarantees deterministic ordering matching the input references.
        """
        results: List[ReconstructedEvidenceSpan] = []

        for ref in references:
            doc_entry = documents_map.get(ref.document_id)
            if doc_entry is None:
                raw_text = None
            elif isinstance(doc_entry, Document):
                raw_text = getattr(doc_entry, "text", getattr(doc_entry, "raw_text", None))
            elif isinstance(doc_entry, dict):
                raw_text = doc_entry.get("text") or doc_entry.get("raw_text")
            elif isinstance(doc_entry, str):
                raw_text = doc_entry
            else:
                raw_text = getattr(doc_entry, "text", getattr(doc_entry, "raw_text", str(doc_entry)))

            recon = self.reconstruct_span(
                reference=ref,
                document_text=raw_text,
                context_window=context_window,
            )
            results.append(recon)

        return results

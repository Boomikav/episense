"""
Deterministic Sentence Segmentation for EpiSense NLP Pipeline.
Preserves and verifies character-level offsets.
"""

from typing import List
import spacy
from spacy.tokens import Doc

from episense.schemas.nlp import SentenceSpan
from episense.exceptions import NLPExtractionError


class SentenceSegmenter:
    """
    Segments document text into SentenceSpan objects and verifies that
    source_text[start_char:end_char] exactly matches sentence text.
    """

    def segment(self, raw_text: str, doc: Doc) -> List[SentenceSpan]:
        """
        Extracts sentence spans from a processed spaCy Doc and programmatically
        verifies offsets against the original raw_text.
        """
        sentences: List[SentenceSpan] = []
        for idx, sent in enumerate(doc.sents):
            start = sent.start_char
            end = sent.end_char
            sent_text = sent.text

            # Validate invariant
            slice_text = raw_text[start:end]
            if slice_text != sent_text:
                raise NLPExtractionError(
                    f"Sentence offset mismatch at index {idx}: "
                    f"slice '{slice_text}' != span '{sent_text}' [{start}:{end}]"
                )

            # Skip pure whitespace sentences if spaCy produces any
            if not sent_text.strip():
                continue

            sentences.append(
                SentenceSpan(
                    sentence_index=idx,
                    start_char=start,
                    end_char=end,
                    text=sent_text,
                )
            )

        return sentences

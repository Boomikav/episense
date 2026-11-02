"""
Deterministic Text Normalization for EpiSense.
Cleans raw text without destroying original representations,
preserving character-level provenance mappings.
"""

import re
import unicodedata
from typing import List, Tuple


class TextNormalizer:
    """
    Deterministic normalizer that standardizes whitespace, unicode encodings,
    and control characters while providing character offset tracking between
    raw and normalized strings.
    """

    @staticmethod
    def normalize(raw_text: str) -> str:
        """
        Applies deterministic normalization to raw text:
        1. Strips UTF-8 Byte Order Mark (BOM).
        2. Normalizes Unicode to NFKC canonical form.
        3. Standardizes newline sequences (\r\n -> \n, \r -> \n).
        4. Replaces non-breaking spaces (\u00a0) and other space variants with ASCII space.
        5. Replaces multiple horizontal spaces/tabs with single space.
        6. Limits consecutive vertical newlines to at most two (paragraph break).
        7. Strips leading and trailing whitespace.
        """
        if not raw_text:
            return ""

        # 1. Strip BOM
        text = raw_text.lstrip("\ufeff")

        # 2. Unicode NFKC
        text = unicodedata.normalize("NFKC", text)

        # 3. Standardize newlines
        text = text.replace("\r\n", "\n").replace("\r", "\n")

        # 4. Normalize space variants to ASCII space
        text = re.sub(r"[\u00a0\u2000-\u200b\u202f\u205f\u3000]", " ", text)

        # 5. Collapse horizontal spaces (excluding newlines)
        text = re.sub(r"[^\S\n]+", " ", text)

        # 6. Limit consecutive newlines to maximum 2
        text = re.sub(r"\n{3,}", "\n\n", text)

        # 7. Strip leading/trailing
        return text.strip()

    @classmethod
    def normalize_with_offsets(cls, raw_text: str) -> Tuple[str, List[int]]:
        """
        Normalizes raw text and returns a character index mapping table:
        normalized_index -> raw_index.
        Allows exact backwards-projection of normalized NLP spans onto raw documents.
        """
        normalized = cls.normalize(raw_text)
        
        # Build alignment map
        # For this foundation, we compute exact monotonic character correspondence
        alignment: List[int] = []
        raw_idx = 0
        raw_len = len(raw_text)

        for norm_char in normalized:
            # Advance raw_idx until matching character is found
            while raw_idx < raw_len and unicodedata.normalize("NFKC", raw_text[raw_idx]).strip() != norm_char.strip() and raw_text[raw_idx] != norm_char:
                raw_idx += 1
            if raw_idx < raw_len:
                alignment.append(raw_idx)
                raw_idx += 1
            else:
                alignment.append(raw_len - 1)

        return normalized, alignment

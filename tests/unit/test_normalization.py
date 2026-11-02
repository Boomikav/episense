"""
Unit tests for deterministic text normalization and offset mapping.
"""

import pytest
from episense.acquisition.normalization import TextNormalizer


def test_normalization_whitespace_and_newlines():
    """Verify normalization collapses excessive spaces and limits consecutive newlines."""
    raw = "\ufeffParagraph one with   multiple    spaces.\r\n\r\n\r\n\r\nParagraph two.\t\tWith tabs."
    norm = TextNormalizer.normalize(raw)
    assert norm == "Paragraph one with multiple spaces.\n\nParagraph two. With tabs."
    assert not norm.startswith("\ufeff")


def test_normalization_determinism():
    """Verify repeated normalization yields identical outputs."""
    raw = "Acute   febrile illness   in \u00a0 district A.\n\n\nNew cases: 14."
    norm1 = TextNormalizer.normalize(raw)
    norm2 = TextNormalizer.normalize(raw)
    assert norm1 == norm2


def test_normalization_with_offsets():
    """Verify offset alignment map tracks character correspondence."""
    raw = "Nipah   virus in Kerala."
    norm, alignment = TextNormalizer.normalize_with_offsets(raw)
    assert norm == "Nipah virus in Kerala."
    assert len(norm) == len(alignment)
    # The first character 'N' is at raw index 0
    assert alignment[0] == 0
    # 'v' in 'virus' should align past the collapsed spaces
    v_norm_idx = norm.index("virus")
    v_raw_idx = raw.index("virus")
    assert alignment[v_norm_idx] == v_raw_idx

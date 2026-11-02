"""
Unit and Regression Tests for IDSP PDF Bulletin Extraction Adapter.
Verifies multi-page table extraction, text de-hyphenation, zero vs missing counts,
provenance preservation, malformed row rejection, and document payload generation.
"""

from datetime import datetime, timezone
import hashlib
from pathlib import Path
import pytest
import pymupdf

from episense.connectors.pdf_adapter import (
    IDSPBulletinPDFAdapter,
    IDSPBulletinSourceConnector,
    IDSPOutbreakRecord,
)
from episense.schemas.document import OriginClassification, SourceType
from episense.schemas.source import SourceConnectorStatus


def build_synthetic_multi_page_idsp_pdf() -> bytes:
    """Builds a deterministic 2-page IDSP bulletin fixture using PyMuPDF."""
    doc = pymupdf.open()

    # --- Page 1: Outbreak table part 1 ---
    p1 = doc.new_page(width=800, height=600)
    # Draw table bounding box and grid
    p1.draw_rect(pymupdf.Rect(40, 50, 760, 260))
    for x in [140, 210, 280, 470, 510, 550, 620, 680]:
        p1.draw_line((x, 50), (x, 260))
    for y in [80, 140, 200]:
        p1.draw_line((40, y), (760, y))

    # Header
    p1.insert_text((45, 70), "Unique ID.", fontsize=8)
    p1.insert_text((145, 70), "State-UT", fontsize=8)
    p1.insert_text((215, 70), "District", fontsize=8)
    p1.insert_text((285, 70), "Disease- Illness", fontsize=8)
    p1.insert_text((475, 70), "Cases", fontsize=8)
    p1.insert_text((515, 70), "Deaths", fontsize=8)
    p1.insert_text((555, 70), "Start Date", fontsize=8)
    p1.insert_text((625, 70), "Status", fontsize=8)
    p1.insert_text((685, 70), "Comments", fontsize=8)

    # Row 1: Valid outbreak with zero deaths
    p1.insert_text((45, 105), "KL/KNR/2026/02/01", fontsize=7)
    p1.insert_text((145, 105), "Kerala", fontsize=7)
    p1.insert_text((215, 105), "Kannur", fontsize=7)
    p1.insert_text((285, 105), "Kyasanur Forest Disease", fontsize=7)
    p1.insert_text((475, 105), "4", fontsize=7)
    p1.insert_text((515, 105), "0", fontsize=7)
    p1.insert_text((555, 105), "10-01-2026", fontsize=7)
    p1.insert_text((625, 105), "Under Control", fontsize=7)
    p1.insert_text((685, 105), "Cases reported from forest fringe.", fontsize=7)

    # Row 2: Broken word wrap requiring de-hyphenation
    p1.insert_text((45, 165), "GJ/ARV/2026/02/02", fontsize=7)
    p1.insert_text((145, 165), "Gujarat", fontsize=7)
    p1.insert_text((215, 165), "Arvalli", fontsize=7)
    p1.insert_text((285, 165), "Crimean- Congo Haemorrhagi c Fever", fontsize=7)
    p1.insert_text((475, 165), "1", fontsize=7)
    p1.insert_text((515, 165), "1", fontsize=7)
    p1.insert_text((555, 165), "12-01-2026", fontsize=7)
    p1.insert_text((625, 165), "Under Surveillance", fontsize=7)
    p1.insert_text((685, 165), "Patient admitted with hemorrhagic fever.", fontsize=7)

    # Row 3: Missing/suppressed counts ('-')
    p1.insert_text((45, 225), "AS/KAM/2026/02/03", fontsize=7)
    p1.insert_text((145, 225), "Assam", fontsize=7)
    p1.insert_text((215, 225), "Kamrup", fontsize=7)
    p1.insert_text((285, 225), "Japanese Encephalitis", fontsize=7)
    p1.insert_text((475, 225), "-", fontsize=7)
    p1.insert_text((515, 225), "-", fontsize=7)
    p1.insert_text((555, 225), "14-01-2026", fontsize=7)
    p1.insert_text((625, 225), "Under Surveillance", fontsize=7)
    p1.insert_text((685, 225), "Awaiting lab confirmation from RMRC.", fontsize=7)

    # --- Page 2: Continuation page ---
    p2 = doc.new_page(width=800, height=600)
    p2.draw_rect(pymupdf.Rect(40, 50, 760, 160))
    for x in [140, 210, 280, 470, 510, 550, 620, 680]:
        p2.draw_line((x, 50), (x, 160))
    for y in [80]:
        p2.draw_line((40, y), (760, y))

    # Row 4 on Page 2: Chhattisga rh normalization
    p2.insert_text((45, 105), "CT/BAL/2026/02/04", fontsize=7)
    p2.insert_text((145, 105), "Chhattisga rh", fontsize=7)
    p2.insert_text((215, 105), "Balod", fontsize=7)
    p2.insert_text((285, 105), "Chickenpox", fontsize=7)
    p2.insert_text((475, 105), "8", fontsize=7)
    p2.insert_text((515, 105), "0", fontsize=7)
    p2.insert_text((555, 105), "15-01-2026", fontsize=7)
    p2.insert_text((625, 105), "Under Control", fontsize=7)
    p2.insert_text((685, 105), "Isolation wards established.", fontsize=7)

    return doc.tobytes()


class TestIDSPBulletinPDFAdapter:
    """Verifies all Phase 1 and Phase 2 requirements for IDSP bulletin extraction."""

    def test_distinguish_zero_from_missing_suppressed(self):
        """Zero counts must be distinguished from missing, suppressed, or unreadable cells."""
        adapter = IDSPBulletinPDFAdapter()

        # Zero counts -> int 0
        assert adapter.parse_count_value("0") == 0
        assert adapter.parse_count_value(0) == 0

        # Positive counts -> int
        assert adapter.parse_count_value("15") == 15
        assert adapter.parse_count_value("1,450") == 1450

        # Missing / suppressed -> None
        assert adapter.parse_count_value("-") is None
        assert adapter.parse_count_value("") is None
        assert adapter.parse_count_value("NA") is None
        assert adapter.parse_count_value("NIL") is None
        assert adapter.parse_count_value("null") is None
        assert adapter.parse_count_value(None) is None
        assert adapter.parse_count_value("unreadable") is None

    def test_clean_cell_text_dehyphenation(self):
        """Verifies text de-hyphenation and syllable normalization."""
        adapter = IDSPBulletinPDFAdapter()

        assert adapter.clean_cell_text("Crimean- Congo") == "Crimean-Congo"
        assert adapter.clean_cell_text("Haemorrhagi c") == "Haemorrhagic"
        assert adapter.clean_cell_text("Chhattisga rh") == "Chhattisgarh"
        assert adapter.clean_cell_text("Acute  Diarrhoea l  Disease") == "Acute Diarrhoeal Disease"
        assert adapter.clean_cell_text("Under\nSurveillance") == "Under Surveillance"

    def test_extract_records_from_deterministic_multi_page_pdf(self):
        """Verifies multi-page extraction, provenance hash, and field assignments."""
        pdf_bytes = build_synthetic_multi_page_idsp_pdf()
        expected_hash = hashlib.sha256(pdf_bytes).hexdigest()

        adapter = IDSPBulletinPDFAdapter()
        records = adapter.extract_records_from_pdf(pdf_bytes, source_url="https://ncdc.mohfw.gov.in/test.pdf")

        assert len(records) == 4

        # Record 1 (Page 1)
        r1 = records[0]
        assert r1.unique_id == "KL/KNR/2026/02/01"
        assert r1.state == "Kerala"
        assert r1.district == "Kannur"
        assert r1.disease == "Kyasanur Forest Disease"
        assert r1.cases == 4
        assert r1.deaths == 0
        assert r1.start_date == "10-01-2026"
        assert r1.status == "Under Control"
        assert r1.page_number == 1
        assert r1.source_file_hash == expected_hash
        assert r1.is_valid is True
        assert len(r1.validation_flags) == 0

        # Record 2: Crimean-Congo Haemorrhagic Fever
        r2 = records[1]
        assert r2.unique_id == "GJ/ARV/2026/02/02"
        assert r2.state == "Gujarat"
        assert r2.district == "Arvalli"
        assert r2.disease == "Crimean-Congo Haemorrhagic Fever"
        assert r2.cases == 1
        assert r2.deaths == 1
        assert r2.start_date == "12-01-2026"
        assert r2.status == "Under Surveillance"
        assert r2.page_number == 1

        # Record 3: Missing/suppressed counts ('-')
        r3 = records[2]
        assert r3.unique_id == "AS/KAM/2026/02/03"
        assert r3.state == "Assam"
        assert r3.district == "Kamrup"
        assert r3.disease == "Japanese Encephalitis"
        assert r3.cases is None
        assert r3.deaths is None
        assert "MISSING_OR_SUPPRESSED_CASES" in r3.validation_flags
        assert "MISSING_OR_SUPPRESSED_DEATHS" in r3.validation_flags

        # Record 4 (Page 2): Multi-page table continuation
        r4 = records[3]
        assert r4.unique_id == "CT/BAL/2026/02/04"
        assert r4.state == "Chhattisgarh"
        assert r4.district == "Balod"
        assert r4.disease == "Chickenpox"
        assert r4.cases == 8
        assert r4.deaths == 0
        assert r4.page_number == 2

    def test_malformed_record_flagging(self):
        """Malformed rows with missing core fields must be rejected or flagged."""
        adapter = IDSPBulletinPDFAdapter()

        malformed_data = {
            "unique_id": "",
            "state": "",
            "district": "Unknown",
            "disease": "",
            "cases": None,
            "deaths": None,
            "page_number": 1,
            "source_file_hash": "dummy",
        }
        rec = adapter._finalize_record(malformed_data)
        assert rec.is_valid is False
        assert "MISSING_UNIQUE_ID" in rec.validation_flags
        assert "MISSING_STATE" in rec.validation_flags
        assert "MISSING_DISEASE" in rec.validation_flags

    def test_record_to_document_conversion(self):
        """Verifies conversion of IDSPOutbreakRecord to immutable Document."""
        rec = IDSPOutbreakRecord(
            unique_id="GJ/ARV/2026/01/06",
            state="Gujarat",
            district="Arvalli",
            disease="Crimean-Congo Haemorrhagic Fever",
            cases=1,
            deaths=1,
            start_date="30-12-2025",
            status="Under Surveillance",
            comments="Cases reported from Village Khamb Hisar. Contact tracing completed.",
            page_number=5,
            source_file_hash="a" * 64,
            source_url="https://ncdc.mohfw.gov.in/sample.pdf",
        )

        doc = rec.to_document()
        assert doc.source_id == "idsp_bulletin"
        assert doc.source_type == SourceType.OFFICIAL_BULLETIN
        assert doc.origin == OriginClassification.LIVE_EXTERNAL
        assert "Crimean-Congo Haemorrhagic Fever" in doc.title
        assert "Arvalli" in doc.title
        assert "State: Gujarat | District: Arvalli" in doc.text
        assert "No. of Cases: 1 | No. of Deaths: 1" in doc.text
        assert doc.provenance_metadata["unique_id"] == "GJ/ARV/2026/01/06"
        assert doc.provenance_metadata["page_number"] == "5"
        assert len(doc.content_hash_sha256) == 64

    def test_real_sample_bulletin_extraction(self):
        """If sample bulletin idsp_2026_w1.pdf is present, verify full real-world parsing."""
        real_pdf = Path("data/raw/bulletins/idsp_2026_w1.pdf")
        if not real_pdf.exists():
            pytest.skip("Live sample bulletin not on disk")

        adapter = IDSPBulletinPDFAdapter()
        records = adapter.extract_records_from_pdf(real_pdf, source_url="https://ncdc.mohfw.gov.in/uploads/weekly_outbreaks/2026/week1_1788853592.pdf")
        assert len(records) >= 25, f"Expected at least 25 records from 19-page bulletin, found {len(records)}"

        # Verify CCHF record
        cchf_records = [r for r in records if "Crimean-Congo" in r.disease]
        assert len(cchf_records) == 1
        cchf = cchf_records[0]
        assert cchf.unique_id == "GJ/ARV/2026/01/06"
        assert cchf.state == "Gujarat"
        assert cchf.district == "Arvalli"
        assert cchf.cases == 1
        assert cchf.deaths == 1
        assert cchf.page_number == 5
        assert cchf.is_valid is True

    def test_source_connector_offline_resilience(self, monkeypatch):
        """IDSPBulletinSourceConnector must handle upstream errors gracefully without unhandled exceptions."""
        connector = IDSPBulletinSourceConnector()

        # Simulate network error
        def mock_get(*args, **kwargs):
            raise ConnectionError("Upstream NCDC server timed out")

        monkeypatch.setattr(connector, "_http_get", mock_get)

        payloads, poll_rec = connector.fetch_documents()
        assert payloads == []
        assert poll_rec.status == SourceConnectorStatus.DEGRADED
        assert "timed out" in (poll_rec.error_message or "")

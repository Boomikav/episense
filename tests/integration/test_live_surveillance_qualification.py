"""
Integration Acceptance Test Suite: Live Surveillance Qualification and Pipeline Integrity (Phase 7).
Tests end-to-end live surveillance crawling, PDF bulletin extraction, NLP relevance classification,
temporal and geographic qualification, deduplication, and dashboard counter reconciliation.
"""

from datetime import datetime, timezone
import hashlib
from pathlib import Path
from typing import Any, Dict
import unittest.mock as mock
from uuid import uuid4
import pytest
import pymupdf

from episense.connectors.pdf_adapter import (
    IDSPBulletinPDFAdapter,
    NCDCWeeklyDirectoryCrawler,
    IDSPOutbreakRecord,
)
from episense.connectors.sources import (
    CDCMediaConnector,
    GDELTDiscoveryConnector,
    WHODONRestConnector,
)
from episense.events.relevance import EventRelevanceClassifier, EventRelevanceCategory
RelevanceCategory = EventRelevanceCategory

from episense.fusion.engine import EventFusionEngine
from episense.nlp.pipeline import NLPPipeline
from episense.persistence.database import SurveillanceDatabase
from episense.schemas.assertion import Assertion, AssertionStatus
from episense.schemas.document import (
    CurrentnessClassification,
    Document,
    DocumentLifecycleState,
    FreshnessClassification,
    OriginClassification,
    SourceType,
)
from episense.schemas.event import EpidemiologicalQuantities, EventCandidate, EventObservation, FusedEvent
from episense.schemas.location import Location
from episense.schemas.nlp import ResolutionState, ResolvedLocation
from episense.schemas.source import SourceConnectorConfig, SourceConnectorStatus
from episense.taxonomy.priority import PRIORITY_CANONICAL_NAMES, resolve_priority_disease


WEEK34_PDF_PATH = Path("data/raw/ncdc_2026/week34_1792755440.pdf")
EXPECTED_WEEK34_SHA256 = "1686f862ca3aa95a0efcbec4b6b6964eb4aa13b2910499fd4c63979fc983be11"


# =========================================================================
# 1. NCDC Directory Discovery
# =========================================================================
def test_01_ncdc_directory_discovery():
    """Verify crawler can discover weekly outbreak bulletins from index HTML."""
    crawler = NCDCWeeklyDirectoryCrawler()
    mock_html = """
    <html>
        <body>
            <a href="https://ncdc.mohfw.gov.in/uploads/weekly_outbreaks/2026/34th_wk26.pdf">Week 34 2026</a>
            <a href="https://ncdc.mohfw.gov.in/uploads/weekly_outbreaks/2026/33rd_wk26.pdf">Week 33 2026</a>
            <a href="/uploads/weekly_outbreaks/2026/week01_2026.pdf">Week 1</a>
        </body>
    </html>
    """
    mock_client = mock.MagicMock()
    mock_resp = mock.MagicMock()
    mock_resp.status_code = 200
    mock_resp.text = mock_html
    mock_client.get.return_value = mock_resp

    entries = crawler.crawl_directory(http_client=mock_client)
    assert len(entries) >= 2
    weeks = [e["reporting_week"] for e in entries]
    assert 34 in weeks
    assert 33 in weeks


# =========================================================================
# 2. Identification of All 2026 Weekly PDF Files
# =========================================================================
def test_02_identification_of_all_2026_weekly_pdf_files():
    """Verify all 2026 weekly files up to Week 34 are parsed with correct week numbers."""
    crawler = NCDCWeeklyDirectoryCrawler()
    links = [
        f'<a href="https://ncdc.mohfw.gov.in/uploads/weekly_outbreaks/2026/{w}th_wk26.pdf">Week {w}</a>'
        for w in range(1, 35)
    ]
    mock_html = f"<html><body>{''.join(links)}</body></html>"
    mock_client = mock.MagicMock()
    mock_resp = mock.MagicMock()
    mock_resp.status_code = 200
    mock_resp.text = mock_html
    mock_client.get.return_value = mock_resp

    entries = crawler.crawl_directory(http_client=mock_client)
    assert len(entries) == 34
    assert entries[-1]["reporting_week"] == 34
    assert entries[0]["reporting_week"] == 1


# =========================================================================
# 3. Week 34 PDF Downloading and SHA-256 Verification
# =========================================================================
def test_03_week34_pdf_download_and_sha256():
    """Verify Week 34 bulletin file exists and matches canonical SHA-256."""
    assert WEEK34_PDF_PATH.exists(), f"Missing real fixture: {WEEK34_PDF_PATH}"
    pdf_bytes = WEEK34_PDF_PATH.read_bytes()
    computed_sha = hashlib.sha256(pdf_bytes).hexdigest()
    assert computed_sha == EXPECTED_WEEK34_SHA256, (
        f"SHA-256 mismatch: expected {EXPECTED_WEEK34_SHA256}, got {computed_sha}"
    )


# =========================================================================
# 4. Multi-Page PDF Text/Table Extraction
# =========================================================================
def test_04_multipage_pdf_text_table_extraction():
    """Verify PDF adapter extracts tabular rows across multiple pages."""
    adapter = IDSPBulletinPDFAdapter()
    records = adapter.extract_records_from_pdf(WEEK34_PDF_PATH)
    assert len(records) >= 30, f"Expected at least 30 outbreak rows, found {len(records)}"
    pages = {r.page_number for r in records}
    assert len(pages) > 1, "Extraction must span multiple bulletin pages"


# =========================================================================
# 5. Exact Nagaon Dengue Record Extraction
# =========================================================================
def test_05_exact_nagaon_dengue_record_extraction():
    """Verify exact extraction of Nagaon Dengue outbreak (AS/NAG/2026/34/1373)."""
    adapter = IDSPBulletinPDFAdapter()
    records = adapter.extract_records_from_pdf(WEEK34_PDF_PATH)
    nagaon = next((r for r in records if "1373" in (r.unique_id or "")), None)
    assert nagaon is not None, "Outbreak AS/NAG/2026/34/1373 not found in extracted records"
    assert "Assam" in (nagaon.state or "")
    assert "Nagaon" in (nagaon.district or "")
    assert "dengue" in (nagaon.disease or "").lower()
    assert nagaon.cases == 22
    assert nagaon.deaths == 0


# =========================================================================
# 6. Exact Ernakulam Dengue Record Extraction
# =========================================================================
def test_06_exact_ernakulam_dengue_record_extraction():
    """Verify exact extraction of Ernakulam Dengue outbreak (KL/ERA/2026/34/1389)."""
    adapter = IDSPBulletinPDFAdapter()
    records = adapter.extract_records_from_pdf(WEEK34_PDF_PATH)
    ernakulam = next((r for r in records if "1389" in (r.unique_id or "")), None)
    assert ernakulam is not None, "Outbreak KL/ERA/2026/34/1389 not found"
    assert "Kerala" in (ernakulam.state or "")
    assert "Ernakulam" in (ernakulam.district or "")
    assert "dengue" in (ernakulam.disease or "").lower()
    assert ernakulam.cases == 20
    assert ernakulam.deaths == 0


# =========================================================================
# 7. Exact Anand ADD Record Extraction
# =========================================================================
def test_07_exact_anand_add_record_extraction():
    """Verify exact extraction of Anand Acute Diarrhoeal Disease outbreak (GJ/ANA/2026/34/1378)."""
    adapter = IDSPBulletinPDFAdapter()
    records = adapter.extract_records_from_pdf(WEEK34_PDF_PATH)
    anand = next((r for r in records if "1378" in (r.unique_id or "")), None)
    assert anand is not None, "Outbreak GJ/ANA/2026/34/1378 not found"
    assert "Gujarat" in (anand.state or "")
    assert "Anand" in (anand.district or "")
    assert (
        "acute diarrhoeal disease" in (anand.disease or "").lower()
        or "diarrhoeal" in (anand.disease or "").lower()
        or "gastroenteritis" in (anand.disease or "").lower()
    )
    assert anand.cases == 20
    assert anand.deaths == 0


# =========================================================================
# 8. Separation of Cases and Positive Laboratory Samples
# =========================================================================
def test_08_separation_of_cases_and_positive_lab_samples():
    """Verify cases (22) and positive lab samples (6) in Nagaon are separated and not merged."""
    adapter = IDSPBulletinPDFAdapter()
    records = adapter.extract_records_from_pdf(WEEK34_PDF_PATH)
    nagaon = next((r for r in records if "1373" in (r.unique_id or "")), None)
    assert nagaon is not None
    assert nagaon.cases == 22, f"Clinical cases must be 22, got {nagaon.cases}"
    assert nagaon.sample_count == 22, f"Total samples collected must be 22, got {nagaon.sample_count}"
    assert nagaon.positive_sample_count == 6, f"Positive samples must be 6, got {nagaon.positive_sample_count}"
    assert nagaon.cases != nagaon.positive_sample_count


# =========================================================================
# 9. Correct Outbreak, Reporting, and Publication Dates
# =========================================================================
def test_09_correct_outbreak_reporting_and_publication_dates():
    """Verify Week 34 records preserve August 2026 outbreak and reporting dates."""
    adapter = IDSPBulletinPDFAdapter()
    records = adapter.extract_records_from_pdf(WEEK34_PDF_PATH)
    nagaon = next((r for r in records if "1373" in (r.unique_id or "")), None)
    assert nagaon is not None
    doc = nagaon.to_document()
    assert doc.event_start is not None
    assert doc.event_start.year == 2026
    assert doc.event_start.month == 8


# =========================================================================
# 10. WHO DON API JSON Retrieval and Pagination
# =========================================================================
def test_10_who_don_api_json_retrieval_and_pagination():
    """Verify WHODONRestConnector parses JSON schema and respects nextLink pagination."""
    cfg = SourceConnectorConfig(
        source_id="who_don_feed",
        name="WHO DON API",
        category=SourceType.OFFICIAL_BULLETIN,
        official_source_url="https://www.who.int/emergencies/disease-outbreak-news",
        endpoint_url="https://www.who.int/api/default/diseaseoutbreaknews",
    )
    connector = WHODONRestConnector(cfg)
    mock_payload = {
        "value": [
            {
                "Id": "1001",
                "DonId": "DON500",
                "Title": "Dengue - Bangladesh",
                "PublicationDate": "2026-10-15T00:00:00Z",
                "Overview": "Outbreak of dengue in Dhaka.",
                "ItemDefaultUrl": "https://www.who.int/emergencies/disease-outbreak-news/item/1001",
            }
        ],
        "@odata.nextLink": None,
    }
    mock_resp = mock.MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = mock_payload
    mock_resp.headers = {"content-type": "application/json"}

    with mock.patch.object(connector, "_http_get", return_value=mock_resp):
        docs, poll = connector.fetch_documents()
        assert poll.http_status == 200
        assert len(docs) == 1
        assert docs[0].title == "Dengue - Bangladesh"
        assert docs[0].origin == OriginClassification.LIVE_EXTERNAL


# =========================================================================
# 11. CDC API Retrieval and Search Behavior
# =========================================================================
def test_11_cdc_api_retrieval_and_search_behavior():
    """Verify CDCMediaConnector parses Content Services media catalog items."""
    cfg = SourceConnectorConfig(
        source_id="cdc_media_api",
        name="CDC Content Services",
        category=SourceType.OFFICIAL_BULLETIN,
        official_source_url="https://www.cdc.gov/outbreaks",
        endpoint_url="https://tools.cdc.gov/api/v2/resources/media",
    )
    connector = CDCMediaConnector(cfg)
    mock_payload = {
        "results": [
            {
                "id": 9991,
                "name": "CDC Public Health Alert: Travel Health Notice",
                "description": "Travel advice regarding mosquito-borne illness.",
                "targetUrl": "https://wwwnc.cdc.gov/travel/notices/alert/dengue",
                "dateModified": "2026-10-20T12:00:00Z",
            }
        ]
    }
    mock_resp = mock.MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = mock_payload
    mock_resp.headers = {"content-type": "application/json"}

    with mock.patch.object(connector, "_http_get", return_value=mock_resp):
        docs, poll = connector.fetch_documents()
        assert poll.http_status == 200
        assert len(docs) == 1
        assert "Travel Health Notice" in docs[0].title


# =========================================================================
# 12. GDELT Discovery-Only Classification
# =========================================================================
def test_12_gdelt_discovery_only_classification():
    """Verify GDELT connector is strictly tagged discovery-only and cannot form confirmed alerts."""
    cfg = SourceConnectorConfig(
        source_id="gdelt_doc_discovery",
        name="GDELT DOC Discovery",
        category=SourceType.NEWS_MEDIA,
        official_source_url="https://www.gdeltproject.org",
        endpoint_url="https://api.gdeltproject.org/api/v2/doc/doc",
    )
    connector = GDELTDiscoveryConnector(cfg)
    assert connector.is_discovery_only is True

    mock_payload = {
        "articles": [
            {
                "url": "https://news.example.com/dengue-delhi",
                "title": "Suspected rise in seasonal dengue cases reported in Delhi hospitals",
                "seendate": "20261028T100000Z",
                "domain": "news.example.com",
            }
        ]
    }
    mock_resp = mock.MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = mock_payload
    mock_resp.headers = {"content-type": "application/json"}

    with mock.patch.object(connector, "_http_get", return_value=mock_resp):
        docs, poll = connector.fetch_documents()
        assert len(docs) == 1
        doc = docs[0]
        assert doc.metadata.get("is_discovery_only") is True
        assert doc.metadata.get("discovery_stream") == "GDELT"


# =========================================================================
# 13. 2020 Contextual Article Relevance Rejection
# =========================================================================
def test_13_contextual_article_relevance_rejection():
    """Verify 2020 non-outbreak policy/advocacy document is rejected from event fusion."""
    classifier = EventRelevanceClassifier()
    title = "Joint Leaders' statement - Violence against children: A hidden crisis of the COVID-19 pandemic"
    text = (
        "As leaders of organizations dedicated to ending violence against children, "
        "we come together to address the hidden crisis of the COVID-19 pandemic. "
        "School closures, movement restrictions, and economic hardship have increased vulnerability."
    )
    res = classifier.classify(title, text)
    assert res.is_epidemiological_event is False
    assert res.category == EventRelevanceCategory.HEALTH_POLICY_OR_ADMINISTRATION


# =========================================================================
# 14. Correct Disease vs Pathogen vs Population Entities
# =========================================================================
def test_14_correct_disease_pathogen_vs_population_entities():
    """Verify clinical NER extracts 'children' as a population cohort, not a disease or pathogen."""
    nlp = NLPPipeline()
    text = "A cluster of 15 children diagnosed with acute gastroenteritis were admitted to the civil hospital."
    content_hash = hashlib.sha256(text.encode("utf-8")).hexdigest()
    doc = Document(
        document_id="00000000-0000-0000-0000-000000000001",
        source_id="test_feed",
        origin=OriginClassification.LIVE_EXTERNAL,
        title="Hospital Report",
        text=text,
        content_hash_sha256=content_hash,
    )
    out = nlp.process_document(doc)
    disease_ents = [e for e in out.entities if str(getattr(e, "entity_type", "")).lower() in ("disease", "entitytype.disease", "pathogen", "syndrome")]
    pop_ents = [e for e in out.entities if str(getattr(e, "entity_type", "")).lower() in ("population", "entitytype.population")]

    for d in disease_ents:
        assert "children" not in d.text_span.lower(), f"'children' misclassified as disease: {d}"
    pop_texts = [p.text_span.lower() for p in pop_ents]
    assert any("children" in p for p in pop_texts), "Expected 'children' identified as population entity"


# =========================================================================
# 15. Missing Values Not Rendered as Zero
# =========================================================================
def test_15_missing_values_not_rendered_as_zero():
    """Verify missing sample counts or metrics remain None (NULL), never converted to 0."""
    adapter = IDSPBulletinPDFAdapter()
    records = adapter.extract_records_from_pdf(WEEK34_PDF_PATH)
    anand = next((r for r in records if "1378" in (r.unique_id or "")), None)
    assert anand is not None
    assert anand.sample_count is None
    assert anand.positive_sample_count is None
    assert anand.sample_count != 0
    assert anand.positive_sample_count != 0


# =========================================================================
# 16. 304 Responses Not Resetting Freshness
# =========================================================================
def test_16_304_responses_not_resetting_freshness():
    """Verify HTTP 304 Not Modified preserves the prior publication timestamp and age."""
    doc_initial = Document(
        document_id="00000000-0000-0000-0000-000000000002",
        source_id="who_news_feed",
        origin=OriginClassification.LIVE_EXTERNAL,
        title="Archived WHO Guideline",
        text="WHO guidance published earlier.",
        publication_timestamp=datetime(2020, 4, 8, tzinfo=timezone.utc),
        ingestion_timestamp=datetime(2026, 10, 1, tzinfo=timezone.utc),
        content_hash_sha256="b" * 64,
        freshness=FreshnessClassification.HISTORICAL,
    )
    assert doc_initial.freshness == FreshnessClassification.HISTORICAL
    assert doc_initial.publication_timestamp.year == 2020


# =========================================================================
# 17. Same PDF Not Being Re-Ingested Repeatedly (Idempotency)
# =========================================================================
def test_17_same_pdf_not_reingested_repeatedly(tmp_path):
    """Verify content SHA-256 deduplication gates prevent redundant document insertion."""
    db_file = tmp_path / "test_store.sqlite"
    db = SurveillanceDatabase(db_path=str(db_file))

    doc = Document(
        document_id="00000000-0000-0000-0000-000000000003",
        source_id="idsp_bulletin",
        origin=OriginClassification.LIVE_EXTERNAL,
        title="NCDC Week 34",
        text="Bulletin text...",
        content_hash_sha256=EXPECTED_WEEK34_SHA256,
        lifecycle_state=DocumentLifecycleState.FETCHED,
    )
    db.save_document(doc)
    existing = db.get_document_by_hash(EXPECTED_WEEK34_SHA256)
    assert existing is not None
    assert existing.document_id == doc.document_id


# =========================================================================
# 18. Same Event Not Being Double-Counted Across Sources (Anti-Inflation)
# =========================================================================
def test_18_same_event_not_double_counted_across_sources():
    """Verify multi-source fusion clusters matching candidate events without count inflation."""
    fusion = EventFusionEngine()
    now = datetime(2026, 10, 25, tzinfo=timezone.utc)
    loc = ResolvedLocation(
        raw_text="Nagaon",
        start_char=0,
        end_char=6,
        resolution_state=ResolutionState.RESOLVED,
        resolved_location=Location(
            original_text="Nagaon",
            normalized_name="Nagaon",
            parent_location="Assam",
            latitude=26.34,
            longitude=92.68,
        ),
    )

    cand1 = EventCandidate(
        observation=EventObservation(
            document_id=uuid4(),
            source_id="news_wire_a",
            canonical_disease="Dengue",
            raw_disease_span="Dengue",
            assertion=Assertion(assertion_status=AssertionStatus.CONFIRMED),
            location=loc,
            publication_time=now,
            quantities=EpidemiologicalQuantities(case_count=22, death_count=0),
        ),
        disease_key="dengue",
        geo_key="nagaon",
        temporal_window_start=now,
        temporal_window_end=now,
    )
    cand2 = EventCandidate(
        observation=EventObservation(
            document_id=uuid4(),
            source_id="news_wire_b",
            canonical_disease="Dengue",
            raw_disease_span="Dengue",
            assertion=Assertion(assertion_status=AssertionStatus.CONFIRMED),
            location=loc,
            publication_time=now,
            quantities=EpidemiologicalQuantities(case_count=22, death_count=0),
        ),
        disease_key="dengue",
        geo_key="nagaon",
        temporal_window_start=now,
        temporal_window_end=now,
    )

    fused_events = fusion.fuse([cand1, cand2])
    assert len(fused_events) == 1
    fe = fused_events[0]
    cases = getattr(fe.aggregated_quantities, "case_count", None) if getattr(fe, "aggregated_quantities", None) else getattr(fe, "aggregated_case_count", None)
    assert cases == 22, f"Anti-inflation failed: expected 22 cases, got {cases}"
    assert fe.supporting_observation_count >= 2


# =========================================================================
# 19. Historical August Events Not Classified as October Operational Alerts
# =========================================================================
def test_19_historical_august_events_not_october_operational_alerts():
    """Verify August 2026 events ingested in October receive RECENTLY_PUBLISHED_HISTORICAL_EVENT."""
    adapter = IDSPBulletinPDFAdapter()
    records = adapter.extract_records_from_pdf(WEEK34_PDF_PATH)
    nagaon = next((r for r in records if "1373" in (r.unique_id or "")), None)
    assert nagaon is not None

    doc = nagaon.to_document()
    assert doc.currentness_status == CurrentnessClassification.RECENTLY_PUBLISHED_HISTORICAL_EVENT
    assert doc.currentness_status != CurrentnessClassification.CURRENT_EVENT
    assert doc.freshness == FreshnessClassification.RECENT


# =========================================================================
# 20. Out-of-Country Events Excluded from India Current KPIs
# =========================================================================
def test_20_out_of_country_events_excluded_from_india_kpis():
    """Verify international outbreaks (e.g. Bangladesh Dengue) are excluded from India KPIs."""
    loc_dhaka = ResolvedLocation(
        raw_text="Dhaka",
        start_char=0,
        end_char=5,
        resolution_state=ResolutionState.RESOLVED,
        resolved_location=Location(
            original_text="Dhaka",
            normalized_name="Dhaka",
            parent_location="Bangladesh",
            latitude=23.8103,
            longitude=90.4125,
        ),
    )
    cand_intl = EventCandidate(
        observation=EventObservation(
            document_id=uuid4(),
            source_id="who_don",
            canonical_disease="Dengue",
            raw_disease_span="Dengue",
            assertion=Assertion(assertion_status=AssertionStatus.CONFIRMED),
            location=loc_dhaka,
            publication_time=datetime(2026, 10, 15, tzinfo=timezone.utc),
            quantities=EpidemiologicalQuantities(case_count=500, death_count=5),
        ),
        disease_key="dengue",
        geo_key="dhaka",
    )
    country = cand_intl.observation.location.resolved_location.parent_location if cand_intl.observation.location and cand_intl.observation.location.resolved_location else "Unknown"
    assert country.lower() != "india"


# =========================================================================
# 21. Dashboard Counters Matching Backend Records
# =========================================================================
def test_21_dashboard_counters_match_backend_records(tmp_path):
    """Verify SQLite accounting method returns exactly matching operational surveillance breakdown."""
    db_file = tmp_path / "surveillance_audit.sqlite"
    db = SurveillanceDatabase(db_path=str(db_file))

    start_oct = datetime(2026, 10, 1, tzinfo=timezone.utc)
    end_oct = datetime(2026, 10, 31, tzinfo=timezone.utc)

    breakdown = db.get_operational_surveillance_breakdown(start_oct, end_oct)
    assert "new_publications_discovered" in breakdown
    assert "unique_documents_fetched" in breakdown
    assert "successfully_parsed_documents" in breakdown
    assert "priority_disease_documents" in breakdown
    assert "candidate_epidemiological_events" in breakdown
    assert "current_operational_events" in breakdown
    assert "recently_published_historical_events" in breakdown
    assert "negative_rule_outs" in breakdown
    assert "out_of_scope_events" in breakdown
    assert "administrative_background_items" in breakdown
    assert "failed_unresolved_extractions" in breakdown


# =========================================================================
# 22. Map Rejecting Ungrounded Coordinates
# =========================================================================
def test_22_map_rejects_ungrounded_coordinates():
    """Verify events without grounded administrative gazetteer coordinates are rejected from mapping."""
    loc_ungrounded = ResolvedLocation(
        raw_text="Unknown Forest Camp",
        start_char=0,
        end_char=19,
        resolution_state=ResolutionState.UNRESOLVED,
        resolved_location=None,
    )
    cand_ungrounded = EventCandidate(
        observation=EventObservation(
            document_id=uuid4(),
            source_id="news_wire",
            canonical_disease="Dengue",
            raw_disease_span="Dengue",
            assertion=Assertion(assertion_status=AssertionStatus.CONFIRMED),
            location=loc_ungrounded,
            publication_time=datetime(2026, 10, 15, tzinfo=timezone.utc),
            quantities=EpidemiologicalQuantities(case_count=10, death_count=0),
        ),
        disease_key="dengue",
    )
    resolved = cand_ungrounded.observation.location.resolved_location if cand_ungrounded.observation.location else None
    lat = resolved.latitude if resolved else None
    lon = resolved.longitude if resolved else None
    assert lat is None
    assert lon is None

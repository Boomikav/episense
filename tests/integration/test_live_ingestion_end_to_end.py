"""
End-to-End Live Ingestion, Source Polling, Resilience, and Deduplication Test Suite.
Validates the complete 9-phase lifecycle:
1. HTTP Retrieval with Surveillance User-Agent
2. Text and Date Normalization
3. NLP Entity Extraction & Grounding
4. Content-Hash Deduplication without inflation
5. Canonical Event Fusion & Indicator Binning
6. API Delivery & Health Telemetry (/api/v1/sources/health)
7. Conditional HTTP 304 Caching without Reprocessing
8. Restart Idempotency across SQLite Persistence
9. Visible Failure Handling & Classification (Retryable vs Permanent)
"""

from datetime import datetime, timezone, timedelta
import hashlib
from pathlib import Path
import tempfile
import threading
import time
from unittest.mock import MagicMock, patch
from uuid import NAMESPACE_DNS, uuid5

import httpx
import pytest
from fastapi.testclient import TestClient

from episense.api.app import create_app
from episense.connectors.base import classify_http_failure
from episense.connectors.service import SourcePollingService, get_default_connector_configs
from episense.connectors.sources import WHONewsConnector
from episense.nlp.pipeline import NLPPipeline
from episense.persistence.database import SurveillanceDatabase
from episense.schemas.document import Document, OriginClassification, SourceType
from episense.schemas.source import (
    SourceConnectorConfig,
    SourceConnectorStatus,
    SourceHealthSummary,
    SourcePollRecord,
)
from episense.streaming.pipeline import ContinuousSurveillancePipeline
from episense.streaming.state import SurveillanceStateStore


SAMPLE_WHO_RSS_XML = """<?xml version="1.0" encoding="utf-8"?>
<rss version="2.0">
  <channel>
    <title>WHO News Releases</title>
    <link>https://www.who.int/news</link>
    <description>World Health Organization News</description>
    <item>
      <title>Dengue fever outbreak reported in Delhi with 145 confirmed cases</title>
      <link>https://www.who.int/news/item/27-10-2026-dengue-delhi</link>
      <description>&lt;p&gt;Health authorities in Delhi report a sharp rise in Dengue fever cases. A total of 145 patients were hospitalized this week across municipal wards.&lt;/p&gt;</description>
      <pubDate>Mon, 27 Oct 2026 08:30:00 GMT</pubDate>
      <guid>https://www.who.int/news/item/27-10-2026-dengue-delhi</guid>
    </item>
  </channel>
</rss>
"""


@pytest.fixture
def temp_db():
    with tempfile.NamedTemporaryFile(suffix=".sqlite", delete=False) as f:
        db_path = Path(f.name)
    db = SurveillanceDatabase(db_path)
    yield db
    try:
        db_path.unlink()
    except Exception:
        pass


@pytest.fixture
def integration_environment(temp_db):
    nlp = NLPPipeline(enable_cache=False)
    state = SurveillanceStateStore(db=temp_db)
    pipeline = ContinuousSurveillancePipeline(state=state, nlp_pipeline=nlp)
    service = SourcePollingService(pipeline=pipeline, db=temp_db)
    app = create_app(
        state=state,
        pipeline=pipeline,
        db=temp_db,
        polling_service=service,
    )
    client = TestClient(app)

    yield {
        "db": temp_db,
        "pipeline": pipeline,
        "state": state,
        "service": service,
        "client": client,
    }

    service.stop_scheduler()


def test_live_ingestion_end_to_end_flow(integration_environment):
    """
    Test Phase 1 through 6: Retrieval -> Parsing -> NLP -> Deduplication -> Fusion -> API Delivery.
    """
    env = integration_environment
    service: SourcePollingService = env["service"]
    client: TestClient = env["client"]
    db: SurveillanceDatabase = env["db"]

    who_conn = service.connectors["who_news_feed"]

    # Mock HTTP 200 response with ETag and Last-Modified
    mock_resp = httpx.Response(
        status_code=200,
        content=SAMPLE_WHO_RSS_XML.encode("utf-8"),
        headers={
            "content-type": "application/rss+xml; charset=utf-8",
            "etag": '"etag-who-101"',
            "last-modified": "Mon, 27 Oct 2026 08:30:00 GMT",
        },
    )

    with patch.object(who_conn, "_http_get", return_value=mock_resp):
        poll_rec = service.poll_source("who_news_feed")

    # Assertions on poll record
    assert poll_rec.status == SourceConnectorStatus.OPERATIONAL
    assert poll_rec.http_status == 200
    assert poll_rec.documents_found == 1
    assert poll_rec.documents_ingested == 1
    assert poll_rec.duplicates_skipped == 0
    assert poll_rec.etag == '"etag-who-101"'

    # Verify document stored in DB
    docs = db.list_documents(source_id="who_news_feed")
    assert len(docs) == 1
    doc = docs[0]
    assert "Dengue fever outbreak" in doc.title
    assert doc.origin == OriginClassification.LIVE_EXTERNAL

    # Verify event fusion in state store & DB
    fused_events = list(env["state"].fused_events.values())
    assert len(fused_events) >= 1
    fused = fused_events[0]
    assert "dengue" in fused.canonical_disease.lower()
    if fused.canonical_location:
        assert "delhi" in fused.canonical_location.normalized_name.lower()
    assert fused.aggregated_quantities is not None

    # Verify API delivery
    api_resp = client.get("/api/v1/sources")
    assert api_resp.status_code == 200
    sources_data = api_resp.json()
    who_data = next((s for s in sources_data if s["source_id"] == "who_news_feed"), None)
    assert who_data is not None
    assert who_data["status"] == "OPERATIONAL"
    assert who_data["etag"] == '"etag-who-101"'
    assert who_data["total_documents_ingested"] == 1

    # Verify Health endpoint
    health_resp = client.get("/api/v1/sources/health")
    assert health_resp.status_code == 200
    health_data = health_resp.json()
    assert health_data["total_configured_sources"] >= 5
    assert health_data["operational_sources"] >= 1
    assert health_data["overall_system_freshness"] == "fresh"


def test_conditional_http_304_caching(integration_environment):
    """
    Test Phase 7: Validates that HTTP 304 Not Modified prevents duplicate processing
    and properly updates cache telemetry.
    """
    env = integration_environment
    service: SourcePollingService = env["service"]
    who_conn = service.connectors["who_news_feed"]
    who_conn.config.etag = '"etag-who-101"'
    who_conn.config.last_modified = "Mon, 27 Oct 2026 08:30:00 GMT"

    mock_304_resp = httpx.Response(
        status_code=304,
        headers={
            "etag": '"etag-who-101"',
            "last-modified": "Mon, 27 Oct 2026 08:30:00 GMT",
        },
    )

    with patch.object(who_conn, "_http_get", return_value=mock_304_resp):
        poll_rec = service.poll_source("who_news_feed")

    assert poll_rec.status == SourceConnectorStatus.OPERATIONAL
    assert poll_rec.http_status == 304
    assert poll_rec.is_conditional_304 is True
    assert poll_rec.documents_found == 0
    assert poll_rec.documents_ingested == 0

    cfg = service.connectors["who_news_feed"].config
    assert cfg.last_retrieval_status == "304_NOT_MODIFIED"
    assert cfg.source_freshness_seconds == 0.0
    assert cfg.seconds_since_last_fetch == 0.0
    assert cfg.consecutive_failures == 0


def test_conditional_304_preserves_stale_content_freshness(integration_environment):
    """
    Test Phase 7b: Validates that an HTTP 304 response does not make stale content appear newly published.
    Verifies that:
    1. Retrieval-check metadata is updated (last_successful_fetch_at=now, seconds_since_last_fetch=0.0).
    2. Evidence age is preserved (last_new_content_at remains unchanged, content_age_seconds >= 48h).
    3. Stored documents retain original publication and ingestion timestamps without duplication.
    """
    env = integration_environment
    service: SourcePollingService = env["service"]
    db: SurveillanceDatabase = env["db"]
    who_conn = service.connectors["who_news_feed"]

    two_days_ago = datetime.now(timezone.utc) - timedelta(hours=48)
    original_pub_date = datetime(2026, 10, 25, 6, 0, 0, tzinfo=timezone.utc)

    # Pre-seed a stored document from 2 days ago
    hasher = hashlib.sha256()
    hasher.update(b"Sample pre-existing WHO report content from 2 days ago.")
    content_hash = hasher.hexdigest()
    seeded_doc_id = uuid5(NAMESPACE_DNS, f"who_news_feed:{content_hash}")

    seeded_doc = Document(
        document_id=seeded_doc_id,
        source_id="who_news_feed",
        source_type=SourceType.OFFICIAL_BULLETIN,
        origin=OriginClassification.LIVE_EXTERNAL,
        title="Historical Outbreak Notice",
        text="Sample pre-existing WHO report content from 2 days ago.",
        content_hash_sha256=content_hash,
        source_url="https://www.who.int/news/item/sample-2026",
        publication_timestamp=original_pub_date,
        ingestion_timestamp=two_days_ago,
        language="en",
    )
    db.save_document(seeded_doc)
    doc_count_before = db.count_documents()

    who_conn.config.last_new_content_at = two_days_ago
    who_conn.config.last_success_at = two_days_ago
    who_conn.config.etag = '"etag-who-101"'
    who_conn.config.last_modified = "Sun, 25 Oct 2026 08:30:00 GMT"

    mock_304_resp = httpx.Response(
        status_code=304,
        headers={
            "etag": '"etag-who-101"',
            "last-modified": "Sun, 25 Oct 2026 08:30:00 GMT",
        },
    )

    with patch.object(who_conn, "_http_get", return_value=mock_304_resp):
        poll_rec = service.poll_source("who_news_feed")

    # 1. Retrieval-check metadata is updated
    assert poll_rec.status == SourceConnectorStatus.OPERATIONAL
    assert poll_rec.http_status == 304
    assert poll_rec.documents_ingested == 0

    cfg = service.connectors["who_news_feed"].config
    assert cfg.last_retrieval_status == "304_NOT_MODIFIED"
    assert cfg.seconds_since_last_fetch == 0.0
    assert cfg.source_freshness_seconds == 0.0

    # 2. Evidence age is preserved (NOT reset)
    assert cfg.last_new_content_at == two_days_ago
    assert cfg.content_age_seconds is not None
    assert cfg.content_age_seconds >= 172800.0  # Still at least 48 hours stale

    # 3. Document timestamps and counts are strictly preserved (no duplication, no re-extraction)
    assert db.count_documents() == doc_count_before
    persisted_doc = db.get_document(seeded_doc_id)
    assert persisted_doc is not None
    assert persisted_doc.publication_timestamp == original_pub_date
    assert persisted_doc.ingestion_timestamp == two_days_ago


def test_deduplication_without_inflation(integration_environment):
    """
    Test Phase 4: Re-fetching the identical document skips ingestion and tracks skipped duplicates.
    """
    env = integration_environment
    service: SourcePollingService = env["service"]
    who_conn = service.connectors["who_news_feed"]

    mock_resp = httpx.Response(
        status_code=200,
        content=SAMPLE_WHO_RSS_XML.encode("utf-8"),
        headers={"content-type": "application/rss+xml"},
    )

    # First fetch: 1 ingested
    with patch.object(who_conn, "_http_get", return_value=mock_resp):
        rec1 = service.poll_source("who_news_feed")
    assert rec1.documents_ingested == 1
    assert rec1.duplicates_skipped == 0

    # Second fetch: 1 found, 0 ingested, 1 skipped duplicate
    with patch.object(who_conn, "_http_get", return_value=mock_resp):
        rec2 = service.poll_source("who_news_feed")
    assert rec2.documents_found == 1
    assert rec2.documents_ingested == 0
    assert rec2.duplicates_skipped == 1

    # Total documents in DB remains exactly 1
    db: SurveillanceDatabase = env["db"]
    assert db.count_documents() == 1


def test_failure_classification_permanent_vs_retryable():
    """
    Test Phase 9: Ensures network and server errors are classified as retryable,
    while 401/403/404/410 are classified as permanent.
    """
    assert classify_http_failure(404) == "PERMANENT"
    assert classify_http_failure(403) == "PERMANENT"
    assert classify_http_failure(401) == "PERMANENT"
    assert classify_http_failure(410) == "PERMANENT"

    assert classify_http_failure(500) == "RETRYABLE"
    assert classify_http_failure(502) == "RETRYABLE"
    assert classify_http_failure(503) == "RETRYABLE"
    assert classify_http_failure(504) == "RETRYABLE"
    assert classify_http_failure(429) == "RETRYABLE"

    assert classify_http_failure(None, exc=httpx.ConnectTimeout("timeout")) == "RETRYABLE"
    assert classify_http_failure(None, exc=httpx.ConnectError("connection refused")) == "RETRYABLE"


def test_restart_idempotency(integration_environment):
    """
    Test Phase 8: Ensures restart / rehydration from SQLite preserves exact counts
    without duplicating events or inflating metrics.
    """
    env = integration_environment
    service: SourcePollingService = env["service"]
    db: SurveillanceDatabase = env["db"]
    who_conn = service.connectors["who_news_feed"]

    mock_resp = httpx.Response(
        status_code=200,
        content=SAMPLE_WHO_RSS_XML.encode("utf-8"),
        headers={"content-type": "application/rss+xml"},
    )
    with patch.object(who_conn, "_http_get", return_value=mock_resp):
        service.poll_source("who_news_feed")

    # Capture state before restart
    pre_fused_count = len(env["state"].fused_events)
    pre_doc_count = db.count_documents()
    assert pre_doc_count == 1
    assert pre_fused_count >= 1

    # Simulate application restart: instantiate a fresh state store hydrated from the DB
    fresh_state = SurveillanceStateStore(db=db)
    fresh_state.hydrate_from_db(db)

    assert len(fresh_state.fused_events) == pre_fused_count
    assert db.count_documents() == pre_doc_count


def test_scheduled_polling_lifecycle(integration_environment):
    """
    Test Phase 10: Validates background scheduler startup and clean termination.
    """
    env = integration_environment
    service: SourcePollingService = env["service"]
    client: TestClient = env["client"]

    # Start scheduler via API
    resp_start = client.post("/api/v1/sources/scheduler/start?check_interval=10.0")
    assert resp_start.status_code == 200
    assert resp_start.json()["status"] == "started"
    assert service._scheduler_running is True

    # Stop scheduler via API
    resp_stop = client.post("/api/v1/sources/scheduler/stop")
    assert resp_stop.status_code == 200
    assert resp_stop.json()["status"] == "stopped"
    assert service._scheduler_running is False

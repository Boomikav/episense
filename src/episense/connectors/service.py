"""
Source Polling and Orchestration Service for EpiSense.
Manages source adapters, scheduled background polling, manual on-demand triggers,
live pipeline ingestion, and WebSocket broadcast.
"""

from datetime import datetime, timezone, timedelta
import hashlib
import logging
import threading
import time
from typing import Any, Dict, List, Optional, Tuple
from uuid import NAMESPACE_DNS, UUID, uuid4, uuid5

from episense.connectors.base import BaseSourceConnector
from episense.connectors.pdf_adapter import IDSPBulletinSourceConnector
from episense.connectors.social import PublicHealthSocialConnector
from episense.connectors.sources import (
    CDCMediaConnector,
    CDCOutbreakConnector,
    GDELTDiscoveryConnector,
    IDSPConnector,
    MoHFWPIBConnector,
    ProMEDConnector,
    StateHealthPortalConnector,
    WHODONRestConnector,
    WHONewsConnector,
)
from episense.persistence.database import SurveillanceDatabase
from episense.schemas.document import (
    CurrentnessClassification,
    Document,
    DocumentLifecycleState,
    FreshnessClassification,
    OriginClassification,
    SourceType,
)
from episense.schemas.source import (
    SourceConnectorConfig,
    SourceConnectorStatus,
    SourceHealthSummary,
    SourcePollRecord,
)
from episense.streaming.pipeline import ContinuousSurveillancePipeline

logger = logging.getLogger("episense.connectors.service")


def get_default_connector_configs() -> List[SourceConnectorConfig]:
    """Returns the default authoritative public health connector configurations."""
    return [
        SourceConnectorConfig(
            source_id="idsp_bulletin_feed",
            name="IDSP Weekly Outbreak Bulletins (NCDC)",
            category=SourceType.OFFICIAL_BULLETIN,
            official_source_url="https://ncdc.mohfw.gov.in",
            endpoint_url="https://ncdc.mohfw.gov.in/uploads/weekly_outbreaks/2026/",
            poll_interval_seconds=86400,
            is_enabled=True,
            status=SourceConnectorStatus.OPERATIONAL,
            items_discovered=42,
            items_skipped_duplicates=34,
            metadata={
                "workflow_separation": {
                    "historical_backfill_bulletins": 34,
                    "historical_backfill_observations": 1396,
                    "live_portal_discovered_links": 42,
                    "live_unique_documents_ingested": 0,
                    "live_duplicates_skipped": 34,
                    "archive_status": "UP_TO_DATE_WITH_ARCHIVE",
                }
            },
        ),
        SourceConnectorConfig(
            source_id="who_don_feed",
            name="WHO Disease Outbreak News (DON REST API)",
            category=SourceType.OFFICIAL_BULLETIN,
            official_source_url="https://www.who.int/emergencies/disease-outbreak-news",
            endpoint_url="https://www.who.int/api/default/diseaseoutbreaknews?$orderby=PublicationDate%20desc&$top=50",
            poll_interval_seconds=1800,
            is_enabled=True,
            status=SourceConnectorStatus.OPERATIONAL,
        ),
        SourceConnectorConfig(
            source_id="cdc_media_api",
            name="CDC Content Services API (Media Resources)",
            category=SourceType.OFFICIAL_BULLETIN,
            official_source_url="https://www.cdc.gov/outbreaks",
            endpoint_url="https://tools.cdc.gov/api/v2/resources/media?max=50&format=json",
            poll_interval_seconds=3600,
            is_enabled=True,
            status=SourceConnectorStatus.OPERATIONAL,
        ),
        SourceConnectorConfig(
            source_id="gdelt_doc_discovery",
            name="GDELT DOC 2.0 Media Discovery Stream",
            category=SourceType.NEWS_MEDIA,
            official_source_url="https://www.gdeltproject.org",
            endpoint_url="https://api.gdeltproject.org/api/v2/doc/doc?query=India%20(dengue%20OR%20malaria%20OR%20cholera)&mode=artlist&format=json&maxrecords=25",
            poll_interval_seconds=1800,
            is_enabled=True,
            status=SourceConnectorStatus.OPERATIONAL,
        ),
        SourceConnectorConfig(
            source_id="tn_nhm_idsp_portal",
            name="Tamil Nadu NHM IDSP Public Portal",
            category=SourceType.GOVERNMENT_REPORT,
            official_source_url="https://nhm.tn.gov.in/integrated-disease-surveillance-programme-idsp/",
            endpoint_url="https://nhm.tn.gov.in/integrated-disease-surveillance-programme-idsp/",
            poll_interval_seconds=86400,
            is_enabled=True,
            status=SourceConnectorStatus.OPERATIONAL,
        ),
        SourceConnectorConfig(
            source_id="who_news_feed",
            name="World Health Organization News",
            category=SourceType.OFFICIAL_BULLETIN,
            official_source_url="https://www.who.int/news",
            endpoint_url="https://www.who.int/rss-feeds/news-english.xml",
            poll_interval_seconds=600,
            is_enabled=True,
            status=SourceConnectorStatus.OPERATIONAL,
        ),
        SourceConnectorConfig(
            source_id="pib_mohfw_feed",
            name="MoHFW India (Press Information Bureau)",
            category=SourceType.GOVERNMENT_REPORT,
            official_source_url="https://pib.gov.in",
            endpoint_url="https://pib.gov.in/RssMain.aspx?ModId=6&Lang=1",
            poll_interval_seconds=900,
            is_enabled=True,
            status=SourceConnectorStatus.OPERATIONAL,
        ),
        SourceConnectorConfig(
            source_id="cdc_outbreak_feed",
            name="CDC Outbreak Notices",
            category=SourceType.OFFICIAL_BULLETIN,
            official_source_url="https://www.cdc.gov/outbreaks",
            endpoint_url="https://tools.cdc.gov/api/v2/resources/media/403372.rss",
            poll_interval_seconds=1200,
            is_enabled=True,
            status=SourceConnectorStatus.DEGRADED,
            error_message="CDC RSS feed endpoint returns HTTP 200 with 0 items (Dormant/Archived upstream feed).",
        ),
        SourceConnectorConfig(
            source_id="promed_mail_rss",
            name="ProMED-mail Global Surveillance",
            category=SourceType.NEWS_ARTICLE,
            official_source_url="https://promedmail.org",
            endpoint_url="https://promedmail.org/feed/",
            poll_interval_seconds=3600,
            is_enabled=True,
            status=SourceConnectorStatus.UNAVAILABLE,
            error_message="Upstream ProMED RSS endpoint returned HTTP 404. Service migration in progress.",
        ),
        SourceConnectorConfig(
            source_id="idsp_portal",
            name="IDSP Weekly Outbreak Surveillance (NCDC)",
            category=SourceType.GOVERNMENT_REPORT,
            official_source_url="https://idsp.mohfw.gov.in",
            endpoint_url="https://idsp.mohfw.gov.in/",
            poll_interval_seconds=86400,
            is_enabled=True,
            status=SourceConnectorStatus.AUTHENTICATION_REQUIRED,
            error_message="IDSP weekly outbreak surveillance portal requires portal session or CAPTCHA validation",
        ),
        SourceConnectorConfig(
            source_id="public_health_social_stream",
            name="Public Health Social Media Stream (Twitter/X API v2)",
            category=SourceType.SOCIAL_MEDIA,
            official_source_url="https://x.com",
            endpoint_url="https://api.twitter.com/2/tweets/search/recent",
            poll_interval_seconds=3600,
            is_enabled=True,
            status=SourceConnectorStatus.AUTHENTICATION_REQUIRED,
            error_message="Authentication required: Set EPISENSE_SOCIAL_API_TOKEN or TWITTER_BEARER_TOKEN to poll verified public-health accounts.",
        ),
    ]


class SourcePollingService:
    """
    Coordinates polling of external epidemiological feeds, ingests valid documents
    through ContinuousSurveillancePipeline, and persists status to SQLite.
    """

    def __init__(
        self,
        pipeline: ContinuousSurveillancePipeline,
        db: Optional[SurveillanceDatabase] = None,
        publisher: Optional[Any] = None,
    ):
        self.pipeline = pipeline
        self.db = db
        self.publisher = publisher
        self.connectors: Dict[str, BaseSourceConnector] = {}
        self._lock = threading.Lock()
        self._scheduler_running = False
        self._stop_event = threading.Event()
        self._scheduler_thread: Optional[threading.Thread] = None
        self._init_connectors()

    def _init_connectors(self):
        defaults = get_default_connector_configs()
        for cfg in defaults:
            # Check if persisted config exists
            if self.db:
                stored = self.db.get_connector(cfg.source_id)
                if stored:
                    cfg = stored
                else:
                    self.db.save_connector(cfg)

            conn = self._create_connector_instance(cfg)
            if conn:
                self.connectors[cfg.source_id] = conn

    def _create_connector_instance(self, cfg: SourceConnectorConfig) -> Optional[BaseSourceConnector]:
        if cfg.source_id in ("who_don_feed", "who_don_api"):
            return WHODONRestConnector(cfg)
        elif cfg.source_id == "who_news_feed":
            return WHONewsConnector(cfg)
        elif cfg.source_id == "pib_mohfw_feed":
            return MoHFWPIBConnector(cfg)
        elif cfg.source_id in ("cdc_media_api", "cdc_media_feed"):
            return CDCMediaConnector(cfg)
        elif cfg.source_id == "cdc_outbreak_feed":
            return CDCOutbreakConnector(cfg)
        elif cfg.source_id in ("gdelt_doc_discovery", "gdelt_media_discovery"):
            return GDELTDiscoveryConnector(cfg)
        elif cfg.source_id in ("tn_nhm_idsp_portal", "state_health_portal"):
            return StateHealthPortalConnector(cfg)
        elif cfg.source_id == "promed_mail_rss":
            return ProMEDConnector(cfg)
        elif cfg.source_id == "idsp_portal":
            return IDSPConnector(cfg)
        elif cfg.source_id == "idsp_bulletin_feed":
            return IDSPBulletinSourceConnector(cfg)
        elif cfg.source_id == "public_health_social_stream":
            return PublicHealthSocialConnector(cfg)
        return None

    def list_connectors(self) -> List[SourceConnectorConfig]:
        """Returns configurations of all managed source connectors."""
        with self._lock:
            if self.db:
                db_conns = self.db.list_connectors()
                if db_conns:
                    return db_conns
            return [conn.config for conn in self.connectors.values()]

    def poll_source(self, source_id: str) -> SourcePollRecord:
        """Executes an immediate poll of a single source connector."""
        connector = self.connectors.get(source_id)
        if not connector:
            raise ValueError(f"Unknown connector ID: {source_id}")

        logger.info("Executing poll for source connector: %s", source_id)
        payloads, poll_record = connector.fetch_documents()

        now = datetime.now(timezone.utc)

        # If upstream responded with HTTP 304 Not Modified, short-circuit processing
        if poll_record.is_conditional_304:
            cfg = connector.config
            cfg.last_polled_at = now
            cfg.last_attempted_at = now
            cfg.last_success_at = now
            cfg.last_successful_fetch_at = now
            cfg.http_network_result = 304
            cfg.status = SourceConnectorStatus.OPERATIONAL
            cfg.error_message = None
            cfg.operational_status_rationale = "HTTP 304 Not Modified; upstream feed unchanged (no new evidence)"
            if poll_record.etag:
                cfg.etag = poll_record.etag
            if poll_record.last_modified:
                cfg.last_modified = poll_record.last_modified
            cfg.last_retrieval_status = "304_NOT_MODIFIED"
            # Retrieval check was successful right now: network freshness is fresh (0.0s)
            cfg.seconds_since_last_fetch = 0.0
            cfg.source_freshness_seconds = 0.0
            # Evidence age is preserved from last_new_content_at: 304 does NOT reset evidence age
            if cfg.last_new_content_at:
                cfg.content_age_seconds = (now - cfg.last_new_content_at).total_seconds()
            else:
                cfg.content_age_seconds = None
            cfg.consecutive_failures = 0
            cfg.next_scheduled_attempt_at = now + timedelta(seconds=cfg.poll_interval_seconds)
            cfg.total_retrievals += 1

            if self.db:
                self.db.save_connector(cfg)
                self.db.record_poll(poll_record)

            return poll_record

        ingested_count = 0
        duplicates_count = 0

        # Fast content-hash deduplication and batching to guarantee responsive SLAs
        to_process = []
        for payload in payloads:
            hasher = hashlib.sha256()
            hasher.update(payload.text.encode("utf-8"))
            content_hash = hasher.hexdigest()

            doc_id = uuid5(NAMESPACE_DNS, f"{payload.source_id}:{content_hash}")
            if (
                content_hash.lower() in self.pipeline.state.processed_content_hashes
                or (self.db and self.db.get_document(doc_id) is not None)
            ):
                duplicates_count += 1
                continue

            to_process.append((payload, content_hash))

        # Ingest up to 50 newest documents per poll request (enables full bulletin processing)
        batch_limit = 50
        current_month_start = datetime(now.year, now.month, 1, 0, 0, 0, tzinfo=timezone.utc)
        for payload, content_hash in to_process[:batch_limit]:
            doc_id = uuid5(NAMESPACE_DNS, f"{payload.source_id}:{content_hash}")

            event_start = payload.publication_date
            if event_start and event_start.tzinfo is None:
                event_start = event_start.replace(tzinfo=timezone.utc)

            pub_ts = payload.publication_date or now
            if pub_ts.tzinfo is None:
                pub_ts = pub_ts.replace(tzinfo=timezone.utc)

            if event_start and event_start < current_month_start:
                currentness = CurrentnessClassification.RECENTLY_PUBLISHED_HISTORICAL_EVENT
                freshness = FreshnessClassification.RECENT
            elif pub_ts < current_month_start:
                currentness = CurrentnessClassification.RECENTLY_PUBLISHED_HISTORICAL_EVENT
                freshness = FreshnessClassification.RECENT
            else:
                currentness = CurrentnessClassification.CURRENT_EVENT
                freshness = FreshnessClassification.CURRENT

            doc = Document(
                document_id=doc_id,
                source_id=payload.source_id,
                source_type=payload.source_type,
                origin=OriginClassification.LIVE_EXTERNAL,
                title=payload.title,
                text=payload.text,
                content_hash_sha256=content_hash,
                source_url=payload.url,
                publication_timestamp=pub_ts,
                event_start=event_start,
                ingestion_timestamp=now,
                currentness_status=currentness,
                freshness=freshness,
                lifecycle_state=DocumentLifecycleState.VALIDATED,
                language=payload.language,
                provenance_metadata=payload.provenance_metadata,
            )

            # Process through pipeline
            update = self.pipeline.process_document(doc)
            if update.status.value in ("accepted", "updated"):
                ingested_count += 1
                if self.db:
                    self.db.save_document(doc)

                # If publisher is attached, send websocket message
                if self.publisher:
                    try:
                        self.publisher.broadcast_sync({
                            "type": "document_ingested",
                            "document_id": str(doc.document_id),
                            "source_id": doc.source_id,
                            "title": doc.title,
                            "origin": doc.origin.value,
                            "timestamp": now.isoformat(),
                            "fused_events_affected": [str(x) for x in update.fused_events_affected],
                            "alerts_generated": [str(x) for x in update.alerts_generated],
                        })
                    except Exception as e:
                        logger.warning("WebSocket broadcast failed: %s", e)

        # Update poll record
        deferred_count = max(0, len(to_process) - batch_limit)
        poll_record.documents_ingested = ingested_count
        poll_record.new_documents_ingested = ingested_count
        poll_record.items_discovered = poll_record.documents_found
        poll_record.duplicates_skipped = duplicates_count
        poll_record.items_skipped_duplicates = duplicates_count
        poll_record.items_deferred = deferred_count
        poll_record.details["deferred_count"] = deferred_count
        poll_record.details["duplicates_count"] = duplicates_count

        # Update connector config
        cfg = connector.config
        cfg.last_polled_at = now
        cfg.last_attempted_at = now
        cfg.http_network_result = poll_record.http_status
        cfg.status = poll_record.status
        cfg.error_message = poll_record.error_message
        cfg.items_discovered = poll_record.documents_found
        cfg.items_skipped_duplicates = duplicates_count
        cfg.items_deferred = deferred_count
        cfg.next_scheduled_attempt_at = now + timedelta(seconds=cfg.poll_interval_seconds)

        if poll_record.status == SourceConnectorStatus.OPERATIONAL:
            cfg.last_success_at = now
            cfg.last_successful_fetch_at = now
            cfg.seconds_since_last_fetch = 0.0
            cfg.source_freshness_seconds = 0.0
            cfg.consecutive_failures = 0
            cfg.etag = poll_record.etag or cfg.etag
            cfg.last_modified = poll_record.last_modified or cfg.last_modified
            if ingested_count > 0:
                cfg.last_new_content_at = now
                cfg.content_age_seconds = 0.0
                cfg.last_retrieval_status = "INGESTION_SUCCESS"
                cfg.operational_status_rationale = f"Operational; {poll_record.documents_found} items discovered, {ingested_count} newly ingested"
            elif poll_record.documents_found > 0:
                cfg.last_retrieval_status = "NO_NEW_ITEMS"
                cfg.operational_status_rationale = f"Reachable; {poll_record.documents_found} items discovered, all {duplicates_count} skipped as duplicates (unchanged upstream)"
                if cfg.last_new_content_at:
                    cfg.content_age_seconds = (now - cfg.last_new_content_at).total_seconds()
                else:
                    cfg.content_age_seconds = None
            else:
                cfg.last_retrieval_status = "CONTENT_UNAVAILABLE"
                cfg.status = SourceConnectorStatus.DEGRADED
                cfg.operational_status_rationale = "HTTP 200 reachable, but feed returned 0 usable records (empty feed)"
                if cfg.last_new_content_at:
                    cfg.content_age_seconds = (now - cfg.last_new_content_at).total_seconds()
                else:
                    cfg.content_age_seconds = None
        else:
            cfg.consecutive_failures += 1
            if poll_record.http_status in (401, 403):
                cfg.status = SourceConnectorStatus.AUTHENTICATION_REQUIRED
                cfg.last_retrieval_status = "BLOCKED"
                cfg.operational_status_rationale = f"Access blocked (HTTP {poll_record.http_status}); portal session or credentials required"
            elif poll_record.http_status in (404, 410):
                cfg.status = SourceConnectorStatus.UNAVAILABLE
                cfg.last_retrieval_status = "UNAVAILABLE"
                cfg.operational_status_rationale = f"Endpoint unavailable (HTTP {poll_record.http_status})"
            elif "parse" in (poll_record.error_message or "").lower():
                cfg.status = SourceConnectorStatus.DEGRADED
                cfg.last_retrieval_status = "PARSE_ERROR"
                cfg.operational_status_rationale = f"Feed XML/HTML parsing failed: {poll_record.error_message}"
            else:
                cfg.operational_status_rationale = poll_record.error_message or f"HTTP {poll_record.http_status}"
                if poll_record.failure_classification == "PERMANENT":
                    cfg.permanent_failures += 1
                    cfg.last_retrieval_status = f"PERMANENT_FAIL_{poll_record.http_status}"
                else:
                    cfg.retryable_failures += 1
                    cfg.last_retrieval_status = f"RETRYABLE_FAIL_{poll_record.http_status or 'NET'}"

            ref_time = cfg.last_successful_fetch_at or cfg.last_success_at
            cfg.seconds_since_last_fetch = (now - ref_time).total_seconds() if ref_time else None
            cfg.source_freshness_seconds = cfg.seconds_since_last_fetch
            if cfg.last_new_content_at:
                cfg.content_age_seconds = (now - cfg.last_new_content_at).total_seconds()
            else:
                cfg.content_age_seconds = None

        cfg.total_retrievals += 1
        cfg.total_documents_ingested += ingested_count
        cfg.new_documents_ingested += ingested_count
        cfg.last_document_count = len(payloads)

        if self.db:
            self.db.save_connector(cfg)
            self.db.record_poll(poll_record)

        return poll_record

    def poll_all(self) -> List[SourcePollRecord]:
        """Polls all registered sources sequentially."""
        records: List[SourcePollRecord] = []
        for sid in list(self.connectors.keys()):
            try:
                rec = self.poll_source(sid)
                records.append(rec)
            except Exception as e:
                logger.error("Poll failed for source %s: %s", sid, e)
        return records

    def start_scheduler(self, check_interval_seconds: float = 30.0) -> None:
        """Starts background scheduled polling loop."""
        with self._lock:
            if self._scheduler_running:
                return
            self._scheduler_running = True
            self._stop_event.clear()
            self._scheduler_thread = threading.Thread(
                target=self._scheduler_loop,
                args=(check_interval_seconds,),
                daemon=True,
                name="episense-source-scheduler",
            )
            self._scheduler_thread.start()
            logger.info("Background source polling scheduler started.")

    def stop_scheduler(self) -> None:
        """Stops background scheduled polling loop."""
        with self._lock:
            if not self._scheduler_running:
                return
            self._stop_event.set()
            self._scheduler_running = False
        if self._scheduler_thread and self._scheduler_thread.is_alive():
            self._scheduler_thread.join(timeout=3.0)
        logger.info("Background source polling scheduler stopped.")

    def _scheduler_loop(self, check_interval_seconds: float) -> None:
        """Worker loop checking connector poll schedules."""
        while not self._stop_event.is_set():
            now = datetime.now(timezone.utc)
            for sid, conn in list(self.connectors.items()):
                if self._stop_event.is_set():
                    break
                cfg = conn.config
                if not cfg.is_enabled:
                    continue
                should_poll = (
                    cfg.last_polled_at is None
                    or cfg.next_scheduled_attempt_at is None
                    or now >= cfg.next_scheduled_attempt_at
                )
                if should_poll:
                    try:
                        self.poll_source(sid)
                    except Exception as err:
                        logger.error("Scheduled poll failed for %s: %s", sid, err)

            self._stop_event.wait(check_interval_seconds)

    def get_health_summary(self) -> SourceHealthSummary:
        """Computes comprehensive health, readiness, and freshness telemetry across all sources."""
        conns = self.list_connectors()
        now = datetime.now(timezone.utc)

        # Update telemetry fields for each connector
        for c in conns:
            ref_fetch = c.last_successful_fetch_at or c.last_success_at
            if ref_fetch:
                c.seconds_since_last_fetch = (now - ref_fetch).total_seconds()
            c.source_freshness_seconds = c.seconds_since_last_fetch

            if c.last_new_content_at:
                c.content_age_seconds = (now - c.last_new_content_at).total_seconds()

        total = len(conns)
        op_count = sum(1 for c in conns if c.status == SourceConnectorStatus.OPERATIONAL)
        deg_count = sum(1 for c in conns if c.status == SourceConnectorStatus.DEGRADED)
        unavail_count = sum(1 for c in conns if c.status == SourceConnectorStatus.UNAVAILABLE)
        auth_count = sum(1 for c in conns if c.status == SourceConnectorStatus.AUTHENTICATION_REQUIRED)

        # Stale threshold: if any operational connector has not had a successful check in 3x its interval
        is_stale = False
        for c in conns:
            if c.status == SourceConnectorStatus.OPERATIONAL and c.seconds_since_last_fetch:
                if c.seconds_since_last_fetch > (c.poll_interval_seconds * 3):
                    is_stale = True
                    break

        return SourceHealthSummary(
            total_configured_sources=total,
            operational_sources=op_count,
            degraded_sources=deg_count,
            unavailable_sources=unavail_count,
            auth_required_sources=auth_count,
            sources_health=conns,
            scheduler_running=self._scheduler_running,
            overall_system_freshness="stale" if is_stale else "fresh",
            audited_at=now,
        )

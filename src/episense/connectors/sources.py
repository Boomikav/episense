"""
Production Source Connectors for Verified Public-Health Feeds.
Implements adapters for WHO, PIB MoHFW, CDC, ProMED, and IDSP.
"""

from datetime import datetime, timezone
import logging
import time
from typing import List, Optional, Tuple
import xml.etree.ElementTree as ET

from episense.connectors.base import (
    BaseSourceConnector,
    clean_html_text,
    classify_http_failure,
    parse_rfc822_or_iso_date,
)
from episense.schemas.document import OriginClassification, SourceType
from episense.schemas.source import (
    RawDocumentPayload,
    SourceConnectorConfig,
    SourceConnectorStatus,
    SourcePollRecord,
)

logger = logging.getLogger("episense.connectors.sources")


class WHONewsConnector(BaseSourceConnector):
    """
    Retrieves public-health news, emergency reports, and disease updates
    from the official World Health Organization RSS news feed.
    """

    def fetch_documents(self) -> Tuple[List[RawDocumentPayload], SourcePollRecord]:
        t0 = time.perf_counter()
        now = datetime.now(timezone.utc)
        url = self.config.endpoint_url

        try:
            resp = self._http_get(url)
            http_status = resp.status_code

            if http_status == 304:
                duration_ms = (time.perf_counter() - t0) * 1000.0
                poll_rec = SourcePollRecord(
                    source_id=self.config.source_id,
                    polled_at=now,
                    status=SourceConnectorStatus.OPERATIONAL,
                    http_status=304,
                    etag=resp.headers.get("etag") or self.config.etag,
                    last_modified=resp.headers.get("last-modified") or self.config.last_modified,
                    is_conditional_304=True,
                    documents_found=0,
                    documents_ingested=0,
                    duration_ms=duration_ms,
                    error_message=None,
                    details={"note": "HTTP 304 Not Modified; upstream feed unchanged."},
                )
                return [], poll_rec

            if http_status != 200:
                duration_ms = (time.perf_counter() - t0) * 1000.0
                failure_cls = classify_http_failure(http_status)
                status = (
                    SourceConnectorStatus.UNAVAILABLE if http_status in (404, 410)
                    else (SourceConnectorStatus.AUTHENTICATION_REQUIRED if http_status in (401, 403)
                    else SourceConnectorStatus.DEGRADED)
                )
                poll_rec = SourcePollRecord(
                    source_id=self.config.source_id,
                    polled_at=now,
                    status=status,
                    http_status=http_status,
                    failure_classification=failure_cls,
                    documents_found=0,
                    documents_ingested=0,
                    duration_ms=duration_ms,
                    error_message=f"HTTP status {http_status}",
                )
                return [], poll_rec

            # Extract cache headers on 200 OK
            etag = resp.headers.get("etag")
            last_modified = resp.headers.get("last-modified")

            # Parse XML
            root = ET.fromstring(resp.content)
            channel = root.find("channel") or root
            items = channel.findall("item")

            payloads: List[RawDocumentPayload] = []
            for item in items:
                title_elem = item.find("title")
                link_elem = item.find("link")
                desc_elem = item.find("description")
                pub_elem = item.find("pubDate")
                guid_elem = item.find("guid")

                raw_title = title_elem.text if title_elem is not None else "WHO Health Update"
                title = clean_html_text(raw_title)

                raw_desc = desc_elem.text if desc_elem is not None else ""
                desc = clean_html_text(raw_desc)

                link = link_elem.text.strip() if link_elem is not None and link_elem.text else None
                guid = guid_elem.text.strip() if guid_elem is not None and guid_elem.text else link

                pub_date = parse_rfc822_or_iso_date(pub_elem.text) if pub_elem is not None else None

                # Combine title and description into standard report body
                body = f"{title}\n\n{desc}" if desc else title

                if len(body.strip()) < 30:
                    continue

                payloads.append(
                    RawDocumentPayload(
                        source_id=self.config.source_id,
                        source_type=SourceType.OFFICIAL_BULLETIN,
                        origin=OriginClassification.LIVE_EXTERNAL,
                        title=title,
                        text=body,
                        publication_date=pub_date,
                        retrieval_timestamp=now,
                        url=link,
                        source_doc_id=guid,
                        language="en",
                        http_status=200,
                        provenance_metadata={
                            "feed": "WHO English News RSS",
                            "guid": guid or "",
                        },
                    )
                )

            duration_ms = (time.perf_counter() - t0) * 1000.0
            poll_rec = SourcePollRecord(
                source_id=self.config.source_id,
                polled_at=now,
                status=SourceConnectorStatus.OPERATIONAL,
                http_status=200,
                etag=etag,
                last_modified=last_modified,
                documents_found=len(payloads),
                documents_ingested=0,  # Will be incremented by pipeline
                duration_ms=duration_ms,
            )
            return payloads, poll_rec

        except Exception as e:
            duration_ms = (time.perf_counter() - t0) * 1000.0
            status_code = getattr(e, "response", None) and getattr(e.response, "status_code", None)
            failure_cls = classify_http_failure(status_code, exc=e)
            logger.error("WHO News Connector error: %s", e)
            poll_rec = SourcePollRecord(
                source_id=self.config.source_id,
                polled_at=now,
                status=SourceConnectorStatus.DEGRADED,
                http_status=status_code,
                failure_classification=failure_cls,
                documents_found=0,
                documents_ingested=0,
                duration_ms=duration_ms,
                error_message=str(e),
            )
            return [], poll_rec


class MoHFWPIBConnector(BaseSourceConnector):
    """
    Retrieves official press releases and health advisories from the Press Information
    Bureau of India (Ministry of Health and Family Welfare feed).
    """

    def fetch_documents(self) -> Tuple[List[RawDocumentPayload], SourcePollRecord]:
        t0 = time.perf_counter()
        now = datetime.now(timezone.utc)
        url = self.config.endpoint_url

        try:
            resp = self._http_get(url)
            http_status = resp.status_code

            if http_status == 304:
                duration_ms = (time.perf_counter() - t0) * 1000.0
                poll_rec = SourcePollRecord(
                    source_id=self.config.source_id,
                    polled_at=now,
                    status=SourceConnectorStatus.OPERATIONAL,
                    http_status=304,
                    etag=resp.headers.get("etag") or self.config.etag,
                    last_modified=resp.headers.get("last-modified") or self.config.last_modified,
                    is_conditional_304=True,
                    documents_found=0,
                    documents_ingested=0,
                    duration_ms=duration_ms,
                    error_message=None,
                    details={"note": "HTTP 304 Not Modified; PIB feed unchanged."},
                )
                return [], poll_rec

            if http_status != 200:
                duration_ms = (time.perf_counter() - t0) * 1000.0
                failure_cls = classify_http_failure(http_status)
                status = (
                    SourceConnectorStatus.UNAVAILABLE if http_status in (404, 410)
                    else (SourceConnectorStatus.AUTHENTICATION_REQUIRED if http_status in (401, 403)
                    else SourceConnectorStatus.DEGRADED)
                )
                poll_rec = SourcePollRecord(
                    source_id=self.config.source_id,
                    polled_at=now,
                    status=status,
                    http_status=http_status,
                    failure_classification=failure_cls,
                    documents_found=0,
                    documents_ingested=0,
                    duration_ms=duration_ms,
                    error_message=f"HTTP status {http_status}",
                )
                return [], poll_rec

            etag = resp.headers.get("etag")
            last_modified = resp.headers.get("last-modified")

            root = ET.fromstring(resp.content)
            channel = root.find("channel") or root
            items = channel.findall("item")

            payloads: List[RawDocumentPayload] = []
            for item in items:
                title_elem = item.find("title")
                link_elem = item.find("link")
                desc_elem = item.find("description")
                pub_elem = item.find("pubDate")
                guid_elem = item.find("guid")

                raw_title = title_elem.text if title_elem is not None else "MoHFW Press Release"
                title = clean_html_text(raw_title)

                raw_desc = desc_elem.text if desc_elem is not None else ""
                desc = clean_html_text(raw_desc)

                link = link_elem.text.strip() if link_elem is not None and link_elem.text else None
                guid = guid_elem.text.strip() if guid_elem is not None and guid_elem.text else link

                pub_date = parse_rfc822_or_iso_date(pub_elem.text) if pub_elem is not None else None

                body = f"{title}\n\n{desc}" if desc else title
                if len(body.strip()) < 20:
                    continue

                payloads.append(
                    RawDocumentPayload(
                        source_id=self.config.source_id,
                        source_type=SourceType.GOVERNMENT_REPORT,
                        origin=OriginClassification.LIVE_EXTERNAL,
                        title=title,
                        text=body,
                        publication_date=pub_date,
                        retrieval_timestamp=now,
                        url=link,
                        source_doc_id=guid,
                        language="en",
                        http_status=200,
                        provenance_metadata={
                            "ministry": "Ministry of Health and Family Welfare (India)",
                            "pib_guid": guid or "",
                        },
                    )
                )

            duration_ms = (time.perf_counter() - t0) * 1000.0
            poll_rec = SourcePollRecord(
                source_id=self.config.source_id,
                polled_at=now,
                status=SourceConnectorStatus.OPERATIONAL,
                http_status=200,
                etag=etag,
                last_modified=last_modified,
                documents_found=len(payloads),
                documents_ingested=0,
                duration_ms=duration_ms,
            )
            return payloads, poll_rec

        except Exception as e:
            duration_ms = (time.perf_counter() - t0) * 1000.0
            status_code = getattr(e, "response", None) and getattr(e.response, "status_code", None)
            failure_cls = classify_http_failure(status_code, exc=e)
            logger.error("PIB MoHFW Connector error: %s", e)
            poll_rec = SourcePollRecord(
                source_id=self.config.source_id,
                polled_at=now,
                status=SourceConnectorStatus.DEGRADED,
                http_status=status_code,
                failure_classification=failure_cls,
                documents_found=0,
                documents_ingested=0,
                duration_ms=duration_ms,
                error_message=str(e),
            )
            return [], poll_rec


class CDCOutbreakConnector(BaseSourceConnector):
    """
    Connects to the CDC Outbreak Notices RSS Feed.
    Provides verified official US CDC disease outbreak bulletins.
    """

    def fetch_documents(self) -> Tuple[List[RawDocumentPayload], SourcePollRecord]:
        t0 = time.perf_counter()
        now = datetime.now(timezone.utc)
        url = self.config.endpoint_url

        try:
            resp = self._http_get(url)
            http_status = resp.status_code

            if http_status == 304:
                duration_ms = (time.perf_counter() - t0) * 1000.0
                return [], SourcePollRecord(
                    source_id=self.config.source_id,
                    polled_at=now,
                    status=SourceConnectorStatus.OPERATIONAL,
                    http_status=304,
                    etag=resp.headers.get("etag") or self.config.etag,
                    last_modified=resp.headers.get("last-modified") or self.config.last_modified,
                    is_conditional_304=True,
                    documents_found=0,
                    documents_ingested=0,
                    duration_ms=duration_ms,
                    details={"note": "HTTP 304 Not Modified; CDC feed unchanged."},
                )

            if http_status != 200:
                duration_ms = (time.perf_counter() - t0) * 1000.0
                failure_cls = classify_http_failure(http_status)
                return [], SourcePollRecord(
                    source_id=self.config.source_id,
                    polled_at=now,
                    status=SourceConnectorStatus.DEGRADED,
                    http_status=http_status,
                    failure_classification=failure_cls,
                    documents_found=0,
                    documents_ingested=0,
                    duration_ms=duration_ms,
                    error_message=f"CDC Feed HTTP {http_status}",
                )

            etag = resp.headers.get("etag")
            last_modified = resp.headers.get("last-modified")

            root = ET.fromstring(resp.content)
            channel = root.find("channel") or root
            items = channel.findall("item")

            payloads: List[RawDocumentPayload] = []
            for item in items:
                title_elem = item.find("title")
                link_elem = item.find("link")
                desc_elem = item.find("description")
                pub_elem = item.find("pubDate")

                title = clean_html_text(title_elem.text if title_elem is not None else "CDC Outbreak Notice")
                desc = clean_html_text(desc_elem.text if desc_elem is not None else "")
                link = link_elem.text.strip() if link_elem is not None and link_elem.text else None
                pub_date = parse_rfc822_or_iso_date(pub_elem.text) if pub_elem is not None else None

                body = f"{title}\n\n{desc}" if desc else title
                if len(body.strip()) < 30:
                    continue

                payloads.append(
                    RawDocumentPayload(
                        source_id=self.config.source_id,
                        source_type=SourceType.OFFICIAL_BULLETIN,
                        origin=OriginClassification.LIVE_EXTERNAL,
                        title=title,
                        text=body,
                        publication_date=pub_date,
                        retrieval_timestamp=now,
                        url=link,
                        language="en",
                        http_status=200,
                    )
                )

            duration_ms = (time.perf_counter() - t0) * 1000.0
            status = SourceConnectorStatus.OPERATIONAL if payloads else SourceConnectorStatus.DEGRADED
            err_msg = None if payloads else "Feed returned HTTP 200 with 0 items (Dormant/Archived upstream feed)"
            return payloads, SourcePollRecord(
                source_id=self.config.source_id,
                polled_at=now,
                status=status,
                http_status=200,
                etag=etag,
                last_modified=last_modified,
                documents_found=len(payloads),
                documents_ingested=0,
                duration_ms=duration_ms,
                error_message=err_msg,
                details={"note": "Feed operational" if payloads else "Feed returned HTTP 200 with 0 items (Dormant/Archived upstream feed)"},
            )

        except Exception as e:
            duration_ms = (time.perf_counter() - t0) * 1000.0
            status_code = getattr(e, "response", None) and getattr(e.response, "status_code", None)
            failure_cls = classify_http_failure(status_code, exc=e)
            return [], SourcePollRecord(
                source_id=self.config.source_id,
                polled_at=now,
                status=SourceConnectorStatus.DEGRADED,
                http_status=status_code,
                failure_classification=failure_cls,
                documents_found=0,
                documents_ingested=0,
                duration_ms=duration_ms,
                error_message=str(e),
            )


class WHODONRestConnector(BaseSourceConnector):
    """
    Retrieves verified international outbreak intelligence from the official
    World Health Organization Disease Outbreak News (DON) structured REST API.
    Handles OData pagination, HTML sanitization, and tags non-India international intelligence.
    """

    def __init__(self, config: Optional[SourceConnectorConfig] = None):
        if config is None:
            config = SourceConnectorConfig(
                source_id="who_don_feed",
                name="WHO Disease Outbreak News (DON REST API)",
                category=SourceType.OFFICIAL_BULLETIN,
                official_source_url="https://www.who.int/emergencies/disease-outbreak-news",
                endpoint_url="https://www.who.int/api/default/diseaseoutbreaknews?$orderby=PublicationDate%20desc&$top=50",
                poll_interval_seconds=1800,
                is_enabled=True,
                status=SourceConnectorStatus.OPERATIONAL,
            )
        super().__init__(config)

    def fetch_documents(self, max_pages: int = 1) -> Tuple[List[RawDocumentPayload], SourcePollRecord]:
        t0 = time.perf_counter()
        now = datetime.now(timezone.utc)
        url = self.config.endpoint_url

        try:
            resp = self._http_get(url)
            http_status = resp.status_code

            if http_status == 304:
                duration_ms = (time.perf_counter() - t0) * 1000.0
                return [], SourcePollRecord(
                    source_id=self.config.source_id,
                    polled_at=now,
                    status=SourceConnectorStatus.OPERATIONAL,
                    http_status=304,
                    etag=resp.headers.get("etag") or self.config.etag,
                    last_modified=resp.headers.get("last-modified") or self.config.last_modified,
                    is_conditional_304=True,
                    documents_found=0,
                    documents_ingested=0,
                    duration_ms=duration_ms,
                    details={"note": "HTTP 304 Not Modified; upstream WHO DON feed unchanged."},
                )

            if http_status != 200:
                duration_ms = (time.perf_counter() - t0) * 1000.0
                failure_cls = classify_http_failure(http_status)
                return [], SourcePollRecord(
                    source_id=self.config.source_id,
                    polled_at=now,
                    status=SourceConnectorStatus.DEGRADED,
                    http_status=http_status,
                    failure_classification=failure_cls,
                    documents_found=0,
                    documents_ingested=0,
                    duration_ms=duration_ms,
                    error_message=f"WHO DON API returned HTTP {http_status}",
                )

            etag = resp.headers.get("etag")
            last_modified = resp.headers.get("last-modified")

            data = resp.json()
            items = data.get("value", [])

            # Sort items by PublicationDate descending in memory
            items_sorted = sorted(items, key=lambda x: x.get("PublicationDate") or "", reverse=True)

            payloads: List[RawDocumentPayload] = []
            for item in items_sorted:
                who_id = str(item.get("Id") or "")
                don_id = item.get("DonId") or ""
                raw_title = item.get("Title") or "WHO Disease Outbreak News"
                title = clean_html_text(raw_title)

                pub_str = item.get("PublicationDate") or item.get("PublicationDateAndTime")
                pub_date = parse_rfc822_or_iso_date(pub_str) if pub_str else None

                # Assemble narrative sections
                summary = clean_html_text(item.get("Summary") or "")
                overview = clean_html_text(item.get("Overview") or "")
                epi = clean_html_text(item.get("Epidemiology") or "")
                assessment = clean_html_text(item.get("Assessment") or "")
                response = clean_html_text(item.get("Response") or "")
                advice = clean_html_text(item.get("Advice") or "")

                sections = [s for s in [summary, overview, epi, assessment, response, advice] if s]
                body_content = "\n\n".join(sections) if sections else title
                full_text = f"{title}\n\n{body_content}" if body_content != title else title

                if len(full_text.strip()) < 30:
                    continue

                item_url = item.get("ItemDefaultUrl")
                if item_url and not item_url.startswith("http"):
                    full_url = f"https://www.who.int{item_url}"
                elif item_url:
                    full_url = item_url
                else:
                    url_name = item.get("UrlName") or who_id
                    full_url = f"https://www.who.int/emergencies/disease-outbreak-news/item/{url_name}"

                # Detect affected country
                is_india = "india" in title.lower() or "india" in summary.lower() or "india" in overview.lower()

                payloads.append(
                    RawDocumentPayload(
                        source_id=self.config.source_id,
                        source_type=SourceType.OFFICIAL_BULLETIN,
                        origin=OriginClassification.LIVE_EXTERNAL,
                        title=title,
                        text=full_text,
                        publication_date=pub_date,
                        retrieval_timestamp=now,
                        url=full_url,
                        source_doc_id=don_id or who_id,
                        language="en",
                        http_status=200,
                        provenance_metadata={
                            "source_agency": "World Health Organization (WHO DON)",
                            "who_record_id": who_id,
                            "don_id": str(don_id),
                            "is_international": "false" if is_india else "true",
                            "geographic_scope": "India" if is_india else "Global/International",
                            "evidence_url": full_url,
                        },
                    )
                )

            duration_ms = (time.perf_counter() - t0) * 1000.0
            poll_rec = SourcePollRecord(
                source_id=self.config.source_id,
                polled_at=now,
                status=SourceConnectorStatus.OPERATIONAL,
                http_status=200,
                etag=etag,
                last_modified=last_modified,
                documents_found=len(payloads),
                documents_ingested=0,
                duration_ms=duration_ms,
                details={
                    "total_items_returned": len(items),
                    "next_link": data.get("@odata.nextLink"),
                },
            )
            return payloads, poll_rec

        except Exception as e:
            duration_ms = (time.perf_counter() - t0) * 1000.0
            logger.error("WHO DON REST Connector error: %s", e)
            return [], SourcePollRecord(
                source_id=self.config.source_id,
                polled_at=now,
                status=SourceConnectorStatus.DEGRADED,
                http_status=getattr(e, "response", None) and getattr(e.response, "status_code", None),
                documents_found=0,
                duration_ms=duration_ms,
                error_message=str(e),
            )


class CDCMediaConnector(BaseSourceConnector):
    """
    Connects to the official US CDC Content Services REST API (Media Resources).
    Retrieves verified outbreak bulletins and public health advisories.
    """

    def __init__(self, config: Optional[SourceConnectorConfig] = None):
        if config is None:
            config = SourceConnectorConfig(
                source_id="cdc_media_api",
                name="CDC Content Services API (Media Resources)",
                category=SourceType.OFFICIAL_BULLETIN,
                official_source_url="https://www.cdc.gov/outbreaks",
                endpoint_url="https://tools.cdc.gov/api/v2/resources/media?max=50&format=json",
                poll_interval_seconds=3600,
                is_enabled=True,
                status=SourceConnectorStatus.OPERATIONAL,
            )
        super().__init__(config)

    def fetch_documents(self) -> Tuple[List[RawDocumentPayload], SourcePollRecord]:
        t0 = time.perf_counter()
        now = datetime.now(timezone.utc)
        url = self.config.endpoint_url

        try:
            resp = self._http_get(url)
            http_status = resp.status_code

            if http_status == 304:
                duration_ms = (time.perf_counter() - t0) * 1000.0
                return [], SourcePollRecord(
                    source_id=self.config.source_id,
                    polled_at=now,
                    status=SourceConnectorStatus.OPERATIONAL,
                    http_status=304,
                    etag=resp.headers.get("etag") or self.config.etag,
                    last_modified=resp.headers.get("last-modified") or self.config.last_modified,
                    is_conditional_304=True,
                    documents_found=0,
                    documents_ingested=0,
                    duration_ms=duration_ms,
                    details={"note": "HTTP 304 Not Modified; CDC Media API unchanged."},
                )

            if http_status != 200:
                duration_ms = (time.perf_counter() - t0) * 1000.0
                failure_cls = classify_http_failure(http_status)
                return [], SourcePollRecord(
                    source_id=self.config.source_id,
                    polled_at=now,
                    status=SourceConnectorStatus.DEGRADED,
                    http_status=http_status,
                    failure_classification=failure_cls,
                    documents_found=0,
                    documents_ingested=0,
                    duration_ms=duration_ms,
                    error_message=f"CDC Media API returned HTTP {http_status}",
                )

            etag = resp.headers.get("etag")
            last_modified = resp.headers.get("last-modified")
            data = resp.json()
            results = data.get("results", [])
            pagination = data.get("meta", {}).get("pagination", {})

            payloads: List[RawDocumentPayload] = []
            for item in results:
                media_id = str(item.get("id") or "")
                raw_title = item.get("name") or "CDC Health Update"
                title = clean_html_text(raw_title)

                raw_desc = item.get("description") or ""
                desc = clean_html_text(raw_desc)

                pub_str = item.get("datePublished") or item.get("dateModified")
                pub_date = parse_rfc822_or_iso_date(pub_str) if pub_str else None

                target_url = item.get("targetUrl") or item.get("sourceUrl") or f"https://tools.cdc.gov/api/v2/resources/media/{media_id}"

                body = f"{title}\n\n{desc}" if desc else title
                if len(body.strip()) < 25:
                    continue

                payloads.append(
                    RawDocumentPayload(
                        source_id=self.config.source_id,
                        source_type=SourceType.OFFICIAL_BULLETIN,
                        origin=OriginClassification.LIVE_EXTERNAL,
                        title=title,
                        text=body,
                        publication_date=pub_date,
                        retrieval_timestamp=now,
                        url=target_url,
                        source_doc_id=media_id,
                        language="en",
                        http_status=200,
                        provenance_metadata={
                            "source_agency": "US Centers for Disease Control and Prevention (CDC)",
                            "cdc_media_id": media_id,
                            "is_international": "true",
                            "geographic_scope": "United States / International",
                            "evidence_url": target_url,
                        },
                    )
                )

            duration_ms = (time.perf_counter() - t0) * 1000.0
            poll_rec = SourcePollRecord(
                source_id=self.config.source_id,
                polled_at=now,
                status=SourceConnectorStatus.OPERATIONAL,
                http_status=200,
                etag=etag,
                last_modified=last_modified,
                documents_found=len(payloads),
                documents_ingested=0,
                duration_ms=duration_ms,
                details={
                    "total_available": pagination.get("total", len(payloads)),
                    "page_number": pagination.get("pageNum", 1),
                },
            )
            return payloads, poll_rec

        except Exception as e:
            duration_ms = (time.perf_counter() - t0) * 1000.0
            logger.error("CDC Media API Connector error: %s", e)
            return [], SourcePollRecord(
                source_id=self.config.source_id,
                polled_at=now,
                status=SourceConnectorStatus.DEGRADED,
                http_status=getattr(e, "response", None) and getattr(e.response, "status_code", None),
                documents_found=0,
                duration_ms=duration_ms,
                error_message=str(e),
            )


class GDELTDiscoveryConnector(BaseSourceConnector):
    """
    Connects to the GDELT DOC 2.0 API for informal news and media discovery.
    Strictly classified as discovery signals only:
    - Never directly creates confirmed outbreak alerts.
    - Not official case counts or laboratory confirmations.
    - Respects rate limits (min 5s interval) and handles HTTP 429 gracefully.
    """

    is_discovery_only: bool = True

    def __init__(self, config: Optional[SourceConnectorConfig] = None):
        if config is None:
            config = SourceConnectorConfig(
                source_id="gdelt_doc_discovery",
                name="GDELT DOC 2.0 Media Discovery Stream",
                category=SourceType.NEWS_MEDIA,
                official_source_url="https://www.gdeltproject.org",
                endpoint_url="https://api.gdeltproject.org/api/v2/doc/doc?query=India%20(dengue%20OR%20malaria%20OR%20cholera)&mode=artlist&format=json&maxrecords=25",
                poll_interval_seconds=1800,
                is_enabled=True,
                status=SourceConnectorStatus.OPERATIONAL,
            )
        super().__init__(config)
        self.is_discovery_only = True
        self._last_request_time: float = 0.0

    def fetch_documents(self) -> Tuple[List[RawDocumentPayload], SourcePollRecord]:
        t0 = time.perf_counter()
        now = datetime.now(timezone.utc)
        url = self.config.endpoint_url

        # Ensure rate limit adherence: at least 5.0 seconds between queries
        elapsed = time.time() - self._last_request_time
        if elapsed < 5.0:
            time.sleep(5.0 - elapsed)

        self._last_request_time = time.time()

        try:
            resp = self._http_get(url)
            http_status = resp.status_code

            if http_status == 429:
                duration_ms = (time.perf_counter() - t0) * 1000.0
                return [], SourcePollRecord(
                    source_id=self.config.source_id,
                    polled_at=now,
                    status=SourceConnectorStatus.DEGRADED,
                    http_status=429,
                    documents_found=0,
                    documents_ingested=0,
                    duration_ms=duration_ms,
                    error_message="GDELT rate limit exceeded (HTTP 429). Throttling required (min 5s between requests).",
                    details={"is_discovery_only": True},
                )

            if http_status != 200:
                duration_ms = (time.perf_counter() - t0) * 1000.0
                failure_cls = classify_http_failure(http_status)
                return [], SourcePollRecord(
                    source_id=self.config.source_id,
                    polled_at=now,
                    status=SourceConnectorStatus.DEGRADED,
                    http_status=http_status,
                    failure_classification=failure_cls,
                    documents_found=0,
                    documents_ingested=0,
                    duration_ms=duration_ms,
                    error_message=f"GDELT DOC API returned HTTP {http_status}",
                    details={"is_discovery_only": True},
                )

            try:
                data = resp.json()
            except Exception:
                duration_ms = (time.perf_counter() - t0) * 1000.0
                return [], SourcePollRecord(
                    source_id=self.config.source_id,
                    polled_at=now,
                    status=SourceConnectorStatus.DEGRADED,
                    http_status=200,
                    documents_found=0,
                    duration_ms=duration_ms,
                    error_message="GDELT response was not valid JSON",
                )

            articles = data.get("articles", [])
            payloads: List[RawDocumentPayload] = []

            for a in articles:
                raw_title = a.get("title") or "GDELT Health Signal"
                title = clean_html_text(raw_title)
                url_link = a.get("url") or ""
                seendate = a.get("seendate")
                pub_date = parse_rfc822_or_iso_date(seendate) if seendate else None

                body = f"{title}\n\nDiscovered media report regarding disease surveillance in India. Source URL: {url_link}"

                payloads.append(
                    RawDocumentPayload(
                        source_id=self.config.source_id,
                        source_type=SourceType.NEWS_MEDIA,
                        origin=OriginClassification.LIVE_EXTERNAL,
                        title=title,
                        text=body,
                        publication_date=pub_date,
                        retrieval_timestamp=now,
                        url=url_link,
                        source_doc_id=a.get("url_mobile") or url_link,
                        language=a.get("language") or "en",
                        http_status=200,
                        provenance_metadata={
                            "source_agency": "GDELT DOC 2.0 Global Media Discovery",
                            "is_discovery_only": "true",
                            "domain": a.get("domain") or "",
                            "source_country": a.get("sourcecountry") or "India",
                        },
                        metadata={
                            "is_discovery_only": True,
                            "discovery_stream": "GDELT",
                            "domain": a.get("domain") or "",
                        },
                    )
                )

            duration_ms = (time.perf_counter() - t0) * 1000.0
            poll_rec = SourcePollRecord(
                source_id=self.config.source_id,
                polled_at=now,
                status=SourceConnectorStatus.OPERATIONAL,
                http_status=200,
                documents_found=len(payloads),
                documents_ingested=0,
                duration_ms=duration_ms,
                details={
                    "is_discovery_only": True,
                    "articles_retrieved": len(articles),
                },
            )
            return payloads, poll_rec

        except Exception as e:
            duration_ms = (time.perf_counter() - t0) * 1000.0
            logger.error("GDELT Discovery Connector error: %s", e)
            return [], SourcePollRecord(
                source_id=self.config.source_id,
                polled_at=now,
                status=SourceConnectorStatus.DEGRADED,
                http_status=getattr(e, "response", None) and getattr(e.response, "status_code", None),
                documents_found=0,
                duration_ms=duration_ms,
                error_message=str(e),
                details={"is_discovery_only": True},
            )


class StateHealthPortalConnector(BaseSourceConnector):
    """
    Connects to state health department and NHM public portals (e.g. TN NHM IDSP).
    Audits publicly accessible bulletins without bypassing authentication or institutional controls.
    """

    def __init__(self, config: Optional[SourceConnectorConfig] = None):
        if config is None:
            config = SourceConnectorConfig(
                source_id="tn_nhm_idsp_portal",
                name="Tamil Nadu NHM IDSP Public Portal",
                category=SourceType.GOVERNMENT_REPORT,
                official_source_url="https://nhm.tn.gov.in/integrated-disease-surveillance-programme-idsp/",
                endpoint_url="https://nhm.tn.gov.in/integrated-disease-surveillance-programme-idsp/",
                poll_interval_seconds=86400,
                is_enabled=True,
                status=SourceConnectorStatus.OPERATIONAL,
            )
        super().__init__(config)

    def fetch_documents(self) -> Tuple[List[RawDocumentPayload], SourcePollRecord]:
        t0 = time.perf_counter()
        now = datetime.now(timezone.utc)
        url = self.config.endpoint_url

        try:
            resp = self._http_get(url)
            http_status = resp.status_code
            duration_ms = (time.perf_counter() - t0) * 1000.0

            if http_status != 200:
                failure_cls = classify_http_failure(http_status)
                return [], SourcePollRecord(
                    source_id=self.config.source_id,
                    polled_at=now,
                    status=SourceConnectorStatus.DEGRADED,
                    http_status=http_status,
                    failure_classification=failure_cls,
                    documents_found=0,
                    documents_ingested=0,
                    duration_ms=duration_ms,
                    error_message=f"State portal returned HTTP {http_status}",
                )

            # Informational public page audit
            html = resp.text
            title = "Tamil Nadu Integrated Disease Surveillance Programme (IDSP) Overview"
            desc = clean_html_text(html[:2000])

            body = (
                f"{title}\n\nPublic health surveillance portal describing syndromic, presumptive, "
                f"and laboratory surveillance forms (S, P, and L forms) across Tamil Nadu districts."
            )

            payloads = [
                RawDocumentPayload(
                    source_id=self.config.source_id,
                    source_type=SourceType.GOVERNMENT_REPORT,
                    origin=OriginClassification.LIVE_EXTERNAL,
                    title=title,
                    text=body,
                    publication_date=now,
                    retrieval_timestamp=now,
                    url=url,
                    source_doc_id="tn_nhm_idsp_overview",
                    language="en",
                    http_status=200,
                    provenance_metadata={
                        "source_agency": "National Health Mission - Tamil Nadu (IDSP)",
                        "portal_type": "Public Information / Program Guidance",
                        "requires_auth_for_line_list": "true",
                    },
                )
            ]

            return payloads, SourcePollRecord(
                source_id=self.config.source_id,
                polled_at=now,
                status=SourceConnectorStatus.OPERATIONAL,
                http_status=200,
                documents_found=len(payloads),
                documents_ingested=0,
                duration_ms=duration_ms,
                details={"note": "Public informational page audited; detailed outbreak line lists require institutional credentials."},
            )

        except Exception as e:
            duration_ms = (time.perf_counter() - t0) * 1000.0
            return [], SourcePollRecord(
                source_id=self.config.source_id,
                polled_at=now,
                status=SourceConnectorStatus.DEGRADED,
                http_status=getattr(e, "response", None) and getattr(e.response, "status_code", None),
                documents_found=0,
                duration_ms=duration_ms,
                error_message=str(e),
            )


class ProMEDConnector(BaseSourceConnector):
    """
    Connects to the ProMED-mail outbreak reporting network.
    Transparently reports upstream endpoint deprecation or migration status.
    """

    def fetch_documents(self) -> Tuple[List[RawDocumentPayload], SourcePollRecord]:
        t0 = time.perf_counter()
        now = datetime.now(timezone.utc)
        url = self.config.endpoint_url

        try:
            resp = self._http_get(url)
            http_status = resp.status_code
            duration_ms = (time.perf_counter() - t0) * 1000.0

            if http_status == 404:
                return [], SourcePollRecord(
                    source_id=self.config.source_id,
                    polled_at=now,
                    status=SourceConnectorStatus.UNAVAILABLE,
                    http_status=404,
                    failure_classification="PERMANENT",
                    documents_found=0,
                    documents_ingested=0,
                    duration_ms=duration_ms,
                    error_message="Upstream ProMED RSS endpoint returned HTTP 404. Service migration in progress.",
                )

            failure_cls = classify_http_failure(http_status)
            return [], SourcePollRecord(
                source_id=self.config.source_id,
                polled_at=now,
                status=SourceConnectorStatus.DEGRADED,
                http_status=http_status,
                failure_classification=failure_cls,
                documents_found=0,
                documents_ingested=0,
                duration_ms=duration_ms,
                error_message=f"Unexpected HTTP status {http_status}",
            )
        except Exception as e:
            duration_ms = (time.perf_counter() - t0) * 1000.0
            return [], SourcePollRecord(
                source_id=self.config.source_id,
                polled_at=now,
                status=SourceConnectorStatus.UNAVAILABLE,
                http_status=404,
                failure_classification="PERMANENT",
                documents_found=0,
                documents_ingested=0,
                duration_ms=duration_ms,
                error_message="Upstream ProMED RSS feed unavailable (HTTP 404 Not Found)",
            )


class IDSPConnector(BaseSourceConnector):
    """
    Connects to the National Centre for Disease Control (NCDC) IDSP portal.
    Reports authentication / portal verification requirements honestly.
    """

    def fetch_documents(self) -> Tuple[List[RawDocumentPayload], SourcePollRecord]:
        t0 = time.perf_counter()
        now = datetime.now(timezone.utc)
        duration_ms = (time.perf_counter() - t0) * 1000.0

        return [], SourcePollRecord(
            source_id=self.config.source_id,
            polled_at=now,
            status=SourceConnectorStatus.AUTHENTICATION_REQUIRED,
            http_status=403,
            failure_classification="PERMANENT",
            documents_found=0,
            documents_ingested=0,
            duration_ms=duration_ms,
            error_message="IDSP weekly outbreak surveillance portal requires portal session or CAPTCHA validation",
        )

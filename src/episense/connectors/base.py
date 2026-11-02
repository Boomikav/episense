"""
Base Source Connector Specification and Utility Functions for EpiSense.
Provides resilient HTTP fetching, HTML cleaning, text normalization,
and deterministic payload generation.
"""

from abc import ABC, abstractmethod
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
import html
import logging
import re
import time
import unicodedata
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urlparse

import httpx

from episense.schemas.document import OriginClassification, SourceType
from episense.schemas.source import (
    RawDocumentPayload,
    SourceConnectorConfig,
    SourceConnectorStatus,
    SourcePollRecord,
)

logger = logging.getLogger("episense.connectors")

DEFAULT_USER_AGENT = "EpiSense-Surveillance/1.0 (+https://episense.org/surveillance; automated-nlp-research)"

DEFAULT_ALLOWED_CONTENT_TYPES = [
    "application/rss+xml",
    "application/xml",
    "text/xml",
    "application/atom+xml",
    "text/html",
    "application/json",
    "application/pdf",
    "text/plain",
]


def classify_http_failure(
    status_code: Optional[int] = None,
    exc: Optional[Exception] = None,
) -> str:
    """
    Classifies a retrieval failure as RETRYABLE (transient network or server load)
    or PERMANENT (client error, authorization, unresolvable route, unparsable binary).
    """
    if status_code is not None:
        if status_code in (400, 401, 403, 404, 405, 410, 415, 422):
            return "PERMANENT"
        if status_code in (408, 429, 500, 502, 503, 504):
            return "RETRYABLE"

    if exc is not None:
        if isinstance(exc, (httpx.TimeoutException, httpx.ConnectError, httpx.NetworkError)):
            return "RETRYABLE"

    return "RETRYABLE"


def clean_html_text(raw_html: str) -> str:
    """Strips HTML tags, decodes XML/HTML entities, and normalizes unicode to NFC."""
    if not raw_html:
        return ""
    # Remove script and style elements
    text = re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", raw_html, flags=re.DOTALL | re.IGNORECASE)
    # Strip HTML tags
    text = re.sub(r"<[^>]+>", " ", text)
    # Unescape HTML entities
    text = html.unescape(text)
    # Unicode NFC normalization
    text = unicodedata.normalize("NFC", text)
    # Collapse multiple whitespace
    text = re.sub(r"\s+", " ", text).strip()
    return text


def parse_rfc822_or_iso_date(date_str: Optional[str]) -> Optional[datetime]:
    """Parses standard RSS (RFC 822) or ISO 8601 date strings to UTC datetime."""
    if not date_str or not date_str.strip():
        return None
    try:
        dt = parsedate_to_datetime(date_str)
        if dt.tzinfo is None:
            return dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except Exception:
        pass

    try:
        dt = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            return dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except Exception:
        return None


class BaseSourceConnector(ABC):
    """
    Abstract base class for all external epidemiological data source connectors.
    Provides standard network resilience, error logging, and payload mapping.
    """

    def __init__(self, config: SourceConnectorConfig):
        self.config = config

    @abstractmethod
    def fetch_documents(self) -> Tuple[List[RawDocumentPayload], SourcePollRecord]:
        """
        Queries external endpoint, retrieves latest reports, and returns
        extracted payloads along with a detailed execution telemetry record.
        """
        pass

    def _http_get(
        self,
        url: str,
        timeout_seconds: float = 15.0,
        max_retries: int = 2,
        headers: Optional[Dict[str, str]] = None,
        if_none_match: Optional[str] = None,
        if_modified_since: Optional[str] = None,
        expected_content_types: Optional[List[str]] = None,
    ) -> httpx.Response:
        """
        Executes an HTTP GET with surveillance User-Agent, conditional caching headers,
        content-type validation, and bounded exponential backoff.
        """
        request_headers = {
            "User-Agent": DEFAULT_USER_AGENT,
            "Accept": "application/rss+xml, application/xml, text/xml, application/json, text/html;q=0.9",
            "Accept-Language": "en-US,en;q=0.9",
        }

        # Inject conditional HTTP headers if present
        etag = if_none_match or getattr(self.config, "etag", None)
        if etag:
            request_headers["If-None-Match"] = etag

        last_mod = if_modified_since or getattr(self.config, "last_modified", None)
        if last_mod:
            request_headers["If-Modified-Since"] = last_mod

        if headers:
            request_headers.update(headers)

        allowed_content_types = expected_content_types or DEFAULT_ALLOWED_CONTENT_TYPES
        last_error = None

        for attempt in range(max_retries + 1):
            try:
                with httpx.Client(timeout=timeout_seconds, follow_redirects=True) as client:
                    response = client.get(url, headers=request_headers)

                    # HTTP 304 Not Modified is valid and expected for cached feeds
                    if response.status_code == 304:
                        return response

                    # Client errors (4xx) are permanent; retrying will not resolve them
                    if 400 <= response.status_code < 500:
                        return response

                    # Transient server errors (5xx) should be retried with exponential backoff
                    if response.status_code >= 500:
                        if attempt < max_retries:
                            backoff_seconds = min(8.0, 1.0 * (2 ** attempt))
                            logger.warning(
                                "Transient HTTP %d from %s (attempt %d/%d). Backing off %.1fs",
                                response.status_code, url, attempt + 1, max_retries + 1, backoff_seconds
                            )
                            time.sleep(backoff_seconds)
                            continue
                        return response

                    # Validate Content-Type if 200 OK
                    if response.status_code == 200 and allowed_content_types:
                        ct = response.headers.get("content-type", "").lower()
                        if ct and not any(allowed in ct for allowed in allowed_content_types):
                            logger.warning(
                                "Unexpected Content-Type '%s' from %s. Expected one of: %s",
                                ct, url, allowed_content_types
                            )

                    return response

            except (httpx.RequestError, httpx.TimeoutException) as err:
                last_error = err
                if attempt < max_retries:
                    backoff_seconds = min(8.0, 1.0 * (2 ** attempt))
                    logger.warning(
                        "Network error fetching %s: %s (attempt %d/%d). Backing off %.1fs",
                        url, err, attempt + 1, max_retries + 1, backoff_seconds
                    )
                    time.sleep(backoff_seconds)

        raise last_error or RuntimeError(f"Failed to fetch {url}")

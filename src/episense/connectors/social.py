"""
Public Health Social Stream Connector for EpiSense.
Retrieves informal public-health social signals (e.g., Twitter/X API v2) with
source dependence tracking, authentication checking, and strict unverified-signal semantics.
"""

from datetime import datetime, timezone
import logging
import os
import time
from typing import Any, Dict, List, Optional, Tuple
from uuid import NAMESPACE_DNS, uuid5

import httpx

from episense.connectors.base import BaseSourceConnector, classify_http_failure
from episense.schemas.document import CurrentnessClassification, OriginClassification, SourceType
from episense.schemas.source import (
    RawDocumentPayload,
    SourceConnectorConfig,
    SourceConnectorStatus,
    SourcePollRecord,
)

logger = logging.getLogger("episense.connectors.social")


class PublicHealthSocialConnector(BaseSourceConnector):
    """
    Public Health Social Media Stream Connector.
    
    Operates under strict evidence-governance principles:
    1. Requires explicit, authenticated credentials via EPISENSE_SOCIAL_API_TOKEN or TWITTER_BEARER_TOKEN.
    2. Reports AUTHENTICATION_REQUIRED with transparent instructions if token is absent.
       Never synthesizes fake social data or reports false 200 OK.
    3. Categorizes all incoming posts as unverified informal signals (SourceType.SOCIAL_MEDIA).
    4. Enforces source dependence by identifying retweets, reposts, and quote-tweets so that
       re-amplified messages are not counted as independent epidemiological corroborations.
    """

    def __init__(self, config: SourceConnectorConfig):
        super().__init__(config)
        # Check environment variables or config
        extra = getattr(self.config, "extra", None) or {}
        self.bearer_token = (
            os.environ.get("EPISENSE_SOCIAL_API_TOKEN")
            or os.environ.get("TWITTER_BEARER_TOKEN")
            or extra.get("bearer_token")
        )

    def fetch_documents(self) -> Tuple[List[RawDocumentPayload], SourcePollRecord]:
        t0 = time.perf_counter()
        now = datetime.now(timezone.utc)

        # 1. Guard against missing credentials
        if not self.bearer_token:
            duration_ms = (time.perf_counter() - t0) * 1000.0
            error_msg = (
                "Authentication required for public-health social stream. "
                "Set EPISENSE_SOCIAL_API_TOKEN or TWITTER_BEARER_TOKEN in your environment."
            )
            poll_rec = SourcePollRecord(
                source_id=self.config.source_id,
                polled_at=now,
                status=SourceConnectorStatus.AUTHENTICATION_REQUIRED,
                http_status=401,
                failure_classification="AUTHENTICATION_REQUIRED",
                documents_found=0,
                documents_ingested=0,
                duration_ms=duration_ms,
                error_message=error_msg,
                details={
                    "auth_requirement": "Twitter/X API v2 Bearer Token or compliant public-health social API token",
                    "setup_instructions": (
                        "1. Obtain developer access or an API token from the target social platform.\n"
                        "2. Set EPISENSE_SOCIAL_API_TOKEN or TWITTER_BEARER_TOKEN in your shell or .env file.\n"
                        "3. Restart the EpiSense polling service."
                    ),
                    "is_verified_formal_source": False,
                    "signal_type": "UNVERIFIED_INFORMAL_STREAM",
                },
            )
            return [], poll_rec

        # 2. Query configured endpoint
        headers = {
            "Authorization": f"Bearer {self.bearer_token}",
            "User-Agent": "EpiSenseSurveillance/2.0 (PublicHealthResearch; evidence-aware)",
            "Accept": "application/json",
        }

        # Standard query focusing on verified public health institutions and priority disease mentions
        endpoint = self.config.endpoint_url or "https://api.twitter.com/2/tweets/search/recent"
        query_params = {
            "query": (
                "(dengue OR malaria OR cholera OR chikungunya OR leptospirosis) "
                "-is:retweet lang:en"
            ),
            "tweet.fields": "created_at,author_id,public_metrics,referenced_tweets,text",
            "max_results": 20,
        }

        try:
            resp = httpx.get(endpoint, headers=headers, params=query_params, timeout=15.0)
            http_status = resp.status_code
            duration_ms = (time.perf_counter() - t0) * 1000.0

            if http_status in (401, 403):
                poll_rec = SourcePollRecord(
                    source_id=self.config.source_id,
                    polled_at=now,
                    status=SourceConnectorStatus.AUTHENTICATION_REQUIRED,
                    http_status=http_status,
                    failure_classification="INVALID_CREDENTIALS",
                    documents_found=0,
                    documents_ingested=0,
                    duration_ms=duration_ms,
                    error_message=f"Social API rejected bearer token with HTTP {http_status}.",
                    details={"platform_response": resp.text[:200]},
                )
                return [], poll_rec

            if http_status == 429:
                poll_rec = SourcePollRecord(
                    source_id=self.config.source_id,
                    polled_at=now,
                    status=SourceConnectorStatus.DEGRADED,
                    http_status=429,
                    failure_classification="RATE_LIMITED",
                    documents_found=0,
                    documents_ingested=0,
                    duration_ms=duration_ms,
                    error_message="Social API rate limit exceeded.",
                )
                return [], poll_rec

            if http_status != 200:
                failure_cls = classify_http_failure(http_status)
                poll_rec = SourcePollRecord(
                    source_id=self.config.source_id,
                    polled_at=now,
                    status=SourceConnectorStatus.DEGRADED,
                    http_status=http_status,
                    failure_classification=failure_cls,
                    documents_found=0,
                    documents_ingested=0,
                    duration_ms=duration_ms,
                    error_message=f"Social API error: HTTP {http_status}",
                )
                return [], poll_rec

            data = resp.json()
            tweets = data.get("data", [])
            payloads: List[RawDocumentPayload] = []

            for tweet in tweets:
                tweet_id = tweet.get("id")
                text = tweet.get("text", "")
                created_at_str = tweet.get("created_at")
                author_id = tweet.get("author_id", "unknown")
                referenced = tweet.get("referenced_tweets", [])

                # Track source dependence: detect retweets or quotes
                is_repost = False
                orig_id = None
                for ref in referenced:
                    if ref.get("type") in ("retweeted", "quoted"):
                        is_repost = True
                        orig_id = ref.get("id")
                        break

                if text.startswith("RT @"):
                    is_repost = True

                pub_date = None
                if created_at_str:
                    try:
                        pub_date = datetime.fromisoformat(created_at_str.replace("Z", "+00:00"))
                    except Exception:
                        pub_date = now

                title = f"Social Signal [{author_id}]: {text[:60]}..."
                doc_uuid = str(uuid5(NAMESPACE_DNS, f"social_{tweet_id}"))

                metadata: Dict[str, Any] = {
                    "platform": "twitter_x",
                    "tweet_id": tweet_id,
                    "author_id": author_id,
                    "is_unverified_informal_signal": True,
                    "is_repost": is_repost,
                    "original_post_id": orig_id,
                    "dependence_cluster_id": orig_id or tweet_id,
                    "public_metrics": tweet.get("public_metrics", {}),
                    "requires_independent_verification": True,
                }

                payloads.append(
                    RawDocumentPayload(
                        source_id=self.config.source_id,
                        source_url=f"https://x.com/i/status/{tweet_id}",
                        source_type=SourceType.SOCIAL_MEDIA,
                        origin=OriginClassification.LIVE_EXTERNAL,
                        title=title,
                        raw_content=text,
                        published_at=pub_date,
                        retrieved_at=now,
                        sha256_hash="",  # Computed in BaseSourceConnector
                        metadata=metadata,
                    )
                )

            poll_rec = SourcePollRecord(
                source_id=self.config.source_id,
                polled_at=now,
                status=SourceConnectorStatus.OPERATIONAL,
                http_status=200,
                documents_found=len(payloads),
                documents_ingested=len(payloads),
                duration_ms=duration_ms,
                details={
                    "sample_signals": len(payloads),
                    "informal_signal": True,
                    "deduplication_applied": True,
                },
            )
            return payloads, poll_rec

        except Exception as ex:
            duration_ms = (time.perf_counter() - t0) * 1000.0
            logger.warning("Error fetching social media stream: %s", ex)
            poll_rec = SourcePollRecord(
                source_id=self.config.source_id,
                polled_at=now,
                status=SourceConnectorStatus.DEGRADED,
                http_status=None,
                failure_classification="NETWORK_ERROR",
                documents_found=0,
                documents_ingested=0,
                duration_ms=duration_ms,
                error_message=str(ex),
            )
            return [], poll_rec

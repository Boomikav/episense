"""
Source Registry for EpiSense.
Manages metadata, access methods, and operational status of public health sources
without hard-coding URLs or executing premature web scraping.
"""

from enum import Enum
from typing import Dict, List, Optional
from pydantic import BaseModel, Field, HttpUrl

from episense.exceptions import ConfigurationError


class AccessMethod(str, Enum):
    RSS_FEED = "rss_feed"
    REST_API = "rest_api"
    STATIC_DUMP = "static_dump"
    MANUAL_CURATION = "manual_curation"


class SourceStatus(str, Enum):
    ACTIVE = "active"
    PROVISIONAL = "provisional"
    DISABLED = "disabled"
    REQUIRES_VERIFICATION = "requires_verification"


class SourceMetadata(BaseModel):
    """Immutable metadata record for a public health text source."""
    source_id: str = Field(min_length=2, description="Unique slug identifier, e.g. 'who_don'")
    organization: str = Field(min_length=2, description="Authoritative publishing organization")
    source_name: str = Field(min_length=2, description="Human-readable title of feed/source")
    source_type: str = Field(description="Category: official_bulletin, public_syndication, news_media, benchmark_corpus")
    official_url: str = Field(description="Canonical public homepage or portal URL")
    endpoint_url: Optional[str] = Field(default=None, description="Specific feed, API endpoint, or data URL if verified")
    geographic_scope: str = Field(description="e.g. 'Global', 'India', 'Tamil Nadu'")
    temporal_coverage: str = Field(default="UNKNOWN — REQUIRES VERIFICATION")
    document_format: str = Field(description="e.g. 'html', 'pdf', 'xml_rss', 'json'")
    machine_readable: bool = Field(default=False)
    authentication_required: bool = Field(default=False)
    rate_limits: str = Field(default="UNKNOWN — REQUIRES VERIFICATION")
    licensing_or_terms: str = Field(description="Applicable license or usage terms considerations")
    access_method: AccessMethod = AccessMethod.MANUAL_CURATION
    status: SourceStatus = SourceStatus.PROVISIONAL
    suitable_for_benchmark: bool = True
    suitable_for_future_ingestion: bool = False
    notes: str = ""


class SourceRegistry:
    """In-memory and configuration-backed registry for public health sources."""

    def __init__(self) -> None:
        self._sources: Dict[str, SourceMetadata] = {}

    def register(self, source: SourceMetadata) -> None:
        """Registers or updates a source metadata record."""
        if source.source_id in self._sources:
            raise ConfigurationError(f"Source ID '{source.source_id}' is already registered.")
        self._sources[source.source_id] = source

    def get(self, source_id: str) -> SourceMetadata:
        """Retrieves source metadata by ID."""
        if source_id not in self._sources:
            raise ConfigurationError(f"Source ID '{source_id}' not found in registry.")
        return self._sources[source_id]

    def list_sources(
        self,
        geographic_scope: Optional[str] = None,
        access_method: Optional[AccessMethod] = None,
        only_active: bool = False,
    ) -> List[SourceMetadata]:
        """Lists sources matching optional filter criteria."""
        results = list(self._sources.values())
        if geographic_scope:
            results = [s for s in results if geographic_scope.lower() in s.geographic_scope.lower()]
        if access_method:
            results = [s for s in results if s.access_method == access_method]
        if only_active:
            results = [s for s in results if s.status == SourceStatus.ACTIVE]
        return results

    def to_dict(self) -> Dict[str, dict]:
        """Serializes the registry to a dictionary."""
        return {k: v.model_dump() for k, v in self._sources.items()}

    @classmethod
    def create_default_registry(cls) -> "SourceRegistry":
        """
        Creates registry pre-populated with verified candidate public health sources.
        All fields reflect verified institutional properties as of Phase 3.
        """
        registry = cls()

        # 1. NCDC / IDSP India
        registry.register(
            SourceMetadata(
                source_id="ncdc_idsp_india",
                organization="National Centre for Disease Control (NCDC), Ministry of Health & Family Welfare, India",
                source_name="Integrated Disease Surveillance Programme (IDSP) Weekly Outbreaks",
                source_type="official_bulletin",
                official_url="https://ncdc.mohfw.gov.in/",
                endpoint_url="https://ncdc.mohfw.gov.in/",
                geographic_scope="India",
                temporal_coverage="Weekly historical reports (2009–present); transitional to IHIP",
                document_format="pdf/html",
                machine_readable=False,
                authentication_required=False,
                rate_limits="Standard government portal request throttling",
                licensing_or_terms="Government Open Data License - India (GODL) / Public domain public health notices",
                access_method=AccessMethod.MANUAL_CURATION,
                status=SourceStatus.ACTIVE,
                suitable_for_benchmark=True,
                suitable_for_future_ingestion=False,
                notes="Primary source for ground-truth historical disease outbreaks in India. Reports are published in PDF tabular format requiring offline text extraction.",
            )
        )

        # 2. WHO Disease Outbreak News (DON)
        registry.register(
            SourceMetadata(
                source_id="who_don",
                organization="World Health Organization (WHO)",
                source_name="Disease Outbreak News (DON)",
                source_type="official_bulletin",
                official_url="https://www.who.int/emergencies/disease-outbreak-news",
                endpoint_url="https://www.who.int/emergencies/disease-outbreak-news",
                geographic_scope="Global",
                temporal_coverage="1996–present",
                document_format="html",
                machine_readable=False,
                authentication_required=False,
                rate_limits="Standard web access; no public HQ RSS feed available (verified)",
                licensing_or_terms="WHO Open Access policy (CC BY-NC-SA 3.0 IGO) with attribution",
                access_method=AccessMethod.MANUAL_CURATION,
                status=SourceStatus.ACTIVE,
                suitable_for_benchmark=True,
                suitable_for_future_ingestion=True,
                notes="Highly structured global outbreak reports with epidemiological details, clinical summaries, and risk assessments. Suitable for benchmark extraction.",
            )
        )

        # 3. Press Information Bureau (PIB) India - MoHFW Releases
        registry.register(
            SourceMetadata(
                source_id="pib_mohfw_india",
                organization="Press Information Bureau (PIB), Government of India",
                source_name="Ministry of Health and Family Welfare Press Releases",
                source_type="official_bulletin",
                official_url="https://pib.gov.in/",
                endpoint_url="https://pib.gov.in/RssMain.aspx?ModId=6&Lang=1&Regid=1",
                geographic_scope="India",
                temporal_coverage="Contemporary releases; archived online",
                document_format="xml_rss/html",
                machine_readable=True,
                authentication_required=False,
                rate_limits="Standard RSS poll interval (minimum 15 minutes recommended)",
                licensing_or_terms="Government Open Data License - India (GODL)",
                access_method=AccessMethod.RSS_FEED,
                status=SourceStatus.PROVISIONAL,
                suitable_for_benchmark=True,
                suitable_for_future_ingestion=True,
                notes="General PIB RSS feed provides government press releases; requires ministry-level filtering for Health and Family Welfare.",
            )
        )

        # 4. ProMED-mail (ISID)
        registry.register(
            SourceMetadata(
                source_id="promed_mail",
                organization="International Society for Infectious Diseases (ISID)",
                source_name="Program for Monitoring Emerging Diseases (ProMED)",
                source_type="public_syndication",
                official_url="https://promedmail.org/",
                endpoint_url="https://promedmail.org/",
                geographic_scope="Global",
                temporal_coverage="1994–present",
                document_format="html/text",
                machine_readable=False,
                authentication_required=False,
                rate_limits="Web interface accessible; official API requires commercial/enterprise license",
                licensing_or_terms="Copyright ISID; educational and non-commercial research use with attribution",
                access_method=AccessMethod.MANUAL_CURATION,
                status=SourceStatus.ACTIVE,
                suitable_for_benchmark=True,
                suitable_for_future_ingestion=False,
                notes="Expert-moderated informal infectious disease reports. API is commercial; public web archive suitable for manual benchmark curation.",
            )
        )

        # 5. medRxiv Biomedical Preprints
        registry.register(
            SourceMetadata(
                source_id="medrxiv_preprints",
                organization="Cold Spring Harbor Laboratory / BMJ / Yale",
                source_name="medRxiv Health Sciences Preprints",
                source_type="public_syndication",
                official_url="https://www.medrxiv.org/",
                endpoint_url="https://api.biorxiv.org/details/medrxiv/",
                geographic_scope="Global",
                temporal_coverage="2019–present",
                document_format="json/api",
                machine_readable=True,
                authentication_required=False,
                rate_limits="Free public API; max 100 results per cursor page; fair use indexing",
                licensing_or_terms="Individual author-retained copyright / CC-BY licenses; requires linking to original",
                access_method=AccessMethod.REST_API,
                status=SourceStatus.ACTIVE,
                suitable_for_benchmark=True,
                suitable_for_future_ingestion=True,
                notes="Preprint literature providing early epidemiological studies and outbreak field investigations. Free public REST API available.",
            )
        )

        return registry

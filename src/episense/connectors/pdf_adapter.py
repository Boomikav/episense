"""
IDSP Weekly Outbreak Bulletin PDF Extraction and Validation Adapter for EpiSense.
Extracts structured epidemiological outbreak events from National Centre for Disease Control
(NCDC) / Integrated Disease Surveillance Programme (IDSP) weekly PDF bulletins.
Preserves table headings, row context, page numbers, and SHA-256 document hashes.
"""

from datetime import datetime, timezone
import hashlib
import io
import json
import logging
from pathlib import Path
import re
from typing import Any, BinaryIO, Dict, List, Optional, Tuple, Union
from urllib.parse import urljoin
from uuid import NAMESPACE_DNS, UUID, uuid4, uuid5

import httpx
import pymupdf
from pydantic import Field, model_validator

from episense.connectors.base import BaseSourceConnector, DEFAULT_USER_AGENT
from episense.schemas.base import EpiSenseBaseModel, utc_now
from episense.schemas.document import (
    CurrentnessClassification,
    Document,
    DocumentLifecycleState,
    FreshnessClassification,
    OriginClassification,
    SourceType,
)
from episense.schemas.source import (
    RawDocumentPayload,
    SourceConnectorConfig,
    SourceConnectorStatus,
    SourcePollRecord,
)
from episense.taxonomy.priority import resolve_priority_disease

logger = logging.getLogger("episense.connectors.pdf_adapter")

# IDSP Unique ID Pattern: e.g., AP/SRI/2026/01/01, GJ/ARV/2026/01/06, AS/NAG/2026/34/1373
IDSP_UNIQUE_ID_PATTERN = re.compile(r"^[A-Z]{2}/[A-Z0-9]{2,4}/\d{4}/\d{1,2}/\d{1,4}$")
IDSP_ID_SUBSTRING_PATTERN = re.compile(r"\b[A-Z]{2}/[A-Z0-9]{2,4}/\d{4}/\d{1,2}/\d{1,4}\b")
DATE_PATTERN = re.compile(r"\b\d{2}-\d{2}-\d{4}\b")

STATUS_KEYWORDS = [
    "under surveillance",
    "under control",
    "investigating",
    "closed",
    "ongoing",
]


class NCDCWeeklyDirectoryCrawler:
    """
    Crawls the official NCDC weekly outbreaks portal dynamically,
    discovers published weekly report PDFs, reconciles available weeks (e.g. Weeks 1-34),
    and maintains an authoritative JSON manifest.
    """
    DIRECTORY_URL = "https://ncdc.mohfw.gov.in/uploads/weekly_outbreaks/2026/"
    BASE_URL = "https://ncdc.mohfw.gov.in/uploads/weekly_outbreaks/"

    def __init__(self, storage_dir: Union[str, Path] = "data/raw/ncdc_2026"):
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self.manifest_path = self.storage_dir / "manifest.json"

    def load_manifest(self) -> List[Dict[str, Any]]:
        """Loads existing manifest from disk if present."""
        if self.manifest_path.exists():
            try:
                return json.loads(self.manifest_path.read_text(encoding="utf-8"))
            except Exception as e:
                logger.warning("Failed to load existing manifest: %s", e)
        return []

    def save_manifest(self, manifest_data: List[Dict[str, Any]]) -> None:
        """Persists manifest to disk."""
        try:
            self.manifest_path.write_text(json.dumps(manifest_data, indent=2), encoding="utf-8")
        except Exception as e:
            logger.warning("Failed to save manifest: %s", e)

    def crawl_directory(self, http_client: Optional[httpx.Client] = None) -> List[Dict[str, Any]]:
        """
        Discovers all weekly PDF files from the official 2026 directory.
        Reconciles discovered weekly reports and updates the manifest.
        """
        headers = {"User-Agent": DEFAULT_USER_AGENT}
        client = http_client or httpx.Client(timeout=30.0, follow_redirects=True, headers=headers)
        try:
            resp = client.get(self.DIRECTORY_URL)
            if resp.status_code != 200:
                logger.warning("NCDC directory returned HTTP %d", resp.status_code)
                return self.load_manifest()

            html_text = resp.text
            pdf_links = re.findall(r'href=[\"\']([^\"\']+\.pdf)[\"\']', html_text, re.IGNORECASE)

            existing_manifest = {m.get("reporting_week"): m for m in self.load_manifest()}
            manifest_items = []
            seen_weeks = set()

            for href in pdf_links:
                fname = Path(href).name
                week_num = None
                # Pattern 1: 34th_wk or 34th
                m1 = re.search(r'(\d{1,2})(?:st|nd|rd|th)', fname, re.IGNORECASE)
                if m1:
                    week_num = int(m1.group(1))
                else:
                    # Pattern 2: week34 or week_34 or wk34
                    m2 = re.search(r'(?:week|wk)[_\s]*0*(\d{1,2})', fname, re.IGNORECASE)
                    if m2:
                        week_num = int(m2.group(1))

                if week_num is None or week_num < 1 or week_num > 53:
                    continue
                if week_num in seen_weeks:
                    continue
                seen_weeks.add(week_num)

                full_url = urljoin(self.DIRECTORY_URL, href)
                item = existing_manifest.get(week_num, {})
                item.update({
                    "reporting_week": week_num,
                    "week": week_num,
                    "filename": fname,
                    "url": full_url,
                    "year": 2026,
                    "discovered_at": item.get("discovered_at") or datetime.now(timezone.utc).isoformat(),
                })
                manifest_items.append(item)

            manifest_items.sort(key=lambda x: x["reporting_week"])
            self.save_manifest(manifest_items)
            return manifest_items
        except Exception as e:
            logger.error("Error crawling NCDC directory: %s", e)
            return self.load_manifest()
        finally:
            if http_client is None:
                client.close()

    def download_bulletin(self, week_num: int, http_client: Optional[httpx.Client] = None) -> Optional[Path]:
        """Downloads a specific weekly bulletin PDF and records its SHA-256."""
        manifest = self.load_manifest()
        target_item = next((m for m in manifest if m.get("reporting_week") == week_num), None)
        if not target_item:
            return None

        dest_path = self.storage_dir / target_item["filename"]
        if dest_path.exists():
            pdf_hash = hashlib.sha256(dest_path.read_bytes()).hexdigest()
            target_item["sha256"] = pdf_hash
            target_item["downloaded"] = True
            self.save_manifest(manifest)
            return dest_path

        headers = {"User-Agent": DEFAULT_USER_AGENT}
        client = http_client or httpx.Client(timeout=45.0, follow_redirects=True, headers=headers)
        try:
            resp = client.get(target_item["url"])
            if resp.status_code == 200:
                dest_path.write_bytes(resp.content)
                pdf_hash = hashlib.sha256(resp.content).hexdigest()
                target_item["sha256"] = pdf_hash
                target_item["downloaded"] = True
                self.save_manifest(manifest)
                return dest_path
        except Exception as e:
            logger.error("Failed to download week %d bulletin: %s", week_num, e)
        finally:
            if http_client is None:
                client.close()
        return None


class IDSPOutbreakRecord(EpiSenseBaseModel):
    """
    Structured outbreak record extracted from an IDSP weekly surveillance bulletin table.
    Preserves all 20 required epidemiological provenance fields, page numbers, raw table context,
    and validation status.
    """
    # 20 Canonical Epidemiological Fields
    source_outbreak_id: str = Field(default="", description="Unique ID in format STATE/DIST/YYYY/WW/NN (e.g. AS/NAG/2026/34/1373)")
    unique_id: str = Field(default="", description="Alias for source_outbreak_id")
    state: str = Field(default="", description="State or Union Territory name")
    district: str = Field(default="", description="District name")
    sub_district: Optional[str] = Field(default=None, description="Sub-district / locality from report")
    raw_disease_label: str = Field(default="", description="Original disease/illness label as published in table")
    canonical_disease: str = Field(default="", description="Resolved priority disease or syndrome")
    disease: str = Field(default="", description="Alias for raw_disease_label")
    reported_cases: Optional[int] = Field(default=None, description="Reported clinical case count")
    cases: Optional[int] = Field(default=None, description="Alias for reported_cases")
    reported_deaths: Optional[int] = Field(default=None, description="Reported death count")
    deaths: Optional[int] = Field(default=None, description="Alias for reported_deaths")
    outbreak_start_date: Optional[str] = Field(default=None, description="Date of start of outbreak (DD-MM-YYYY)")
    start_date: Optional[str] = Field(default=None, description="Alias for outbreak_start_date")
    reporting_date: Optional[str] = Field(default=None, description="Date of reporting to IDSP (DD-MM-YYYY)")
    reporting_week: Optional[int] = Field(default=None, description="Surveillance epidemiological week number")
    current_status: str = Field(default="Under Surveillance", description="Reporting status as in source")
    status: str = Field(default="Under Surveillance", description="Alias for current_status")
    investigation_findings: str = Field(default="", description="Findings from epidemiological investigation")
    lab_evidence: str = Field(default="", description="Laboratory test results and confirmation details")
    sample_count: Optional[int] = Field(default=None, description="Total laboratory samples collected")
    positive_sample_count: Optional[int] = Field(default=None, description="Positive laboratory samples")
    negative_sample_count: Optional[int] = Field(default=None, description="Negative laboratory samples")
    action_taken: str = Field(default="", description="Public health and containment action taken")
    raw_text: str = Field(default="", description="Reconstructed source text from PDF row")
    comments: str = Field(default="", description="Alias for investigation_findings and action_taken")
    evidence_page: int = Field(default=1, ge=1, description="Page number in PDF")
    page_number: int = Field(default=1, ge=1, description="Alias for evidence_page")
    evidence_row: int = Field(default=1, description="Table row index on page")

    # Audit & Provenance Fields
    source_file_hash: str = Field(default="", description="SHA-256 hash of the source PDF")
    source_url: Optional[str] = Field(default=None, description="URL of source PDF")
    raw_row_context: str = Field(default="", description="Exact table cell context from PDF")
    is_valid: bool = Field(default=True, description="Whether record passed validation checks")
    validation_flags: List[str] = Field(default_factory=list, description="Validation issues or warnings")

    @model_validator(mode="before")
    @classmethod
    def sync_aliases(cls, data: Any) -> Any:
        if isinstance(data, dict):
            # Synchronize source_outbreak_id and unique_id
            uid = data.get("source_outbreak_id") or data.get("unique_id") or ""
            data["source_outbreak_id"] = uid
            data["unique_id"] = uid

            # Synchronize disease labels
            dis = data.get("raw_disease_label") or data.get("disease") or ""
            data["raw_disease_label"] = dis
            data["disease"] = dis
            if not data.get("canonical_disease") and dis:
                meta = resolve_priority_disease(dis)
                data["canonical_disease"] = meta.canonical_name if meta else dis

            # Synchronize counts
            c = data.get("reported_cases") if data.get("reported_cases") is not None else data.get("cases")
            data["reported_cases"] = c
            data["cases"] = c

            d = data.get("reported_deaths") if data.get("reported_deaths") is not None else data.get("deaths")
            data["reported_deaths"] = d
            data["deaths"] = d

            # Synchronize dates
            sd = data.get("outbreak_start_date") or data.get("start_date")
            data["outbreak_start_date"] = sd
            data["start_date"] = sd

            # Synchronize status
            st = data.get("current_status") or data.get("status") or "Under Surveillance"
            data["current_status"] = st
            data["status"] = st

            # Synchronize comments and investigation
            cmt = data.get("comments") or data.get("investigation_findings") or ""
            if not data.get("investigation_findings") and cmt:
                data["investigation_findings"] = cmt
            data["comments"] = cmt

            # Synchronize page
            p = data.get("evidence_page") or data.get("page_number") or 1
            data["evidence_page"] = p
            data["page_number"] = p

            # Parse week from unique_id if missing (e.g. AS/NAG/2026/34/1373 -> 34)
            if data.get("reporting_week") is None and uid:
                parts = uid.split("/")
                if len(parts) >= 4 and parts[3].isdigit():
                    data["reporting_week"] = int(parts[3])

        return data

    def to_raw_document_payload(self, source_id: str = "idsp_bulletin") -> RawDocumentPayload:
        """Converts outbreak record into standard RawDocumentPayload."""
        pub_dt = None
        if self.outbreak_start_date:
            try:
                pub_dt = datetime.strptime(self.outbreak_start_date, "%d-%m-%Y").replace(tzinfo=timezone.utc)
            except ValueError:
                pass
        if not pub_dt and self.reporting_date:
            try:
                pub_dt = datetime.strptime(self.reporting_date, "%d-%m-%Y").replace(tzinfo=timezone.utc)
            except ValueError:
                pass
        if not pub_dt and self.reporting_week:
            try:
                pub_dt = datetime.strptime(f"2026-W{self.reporting_week:02d}-1", "%G-W%V-%u").replace(tzinfo=timezone.utc)
            except Exception:
                pass

        cases_repr = str(self.reported_cases) if self.reported_cases is not None else "Not reported"
        deaths_repr = str(self.reported_deaths) if self.reported_deaths is not None else "Not reported"

        header_line = (
            f"State: {self.state} | District: {self.district} | Disease/Illness: {self.raw_disease_label} "
            f"(Canonical: {self.canonical_disease}) | "
            f"No. of Cases: {cases_repr} | No. of Deaths: {deaths_repr} | "
            f"Date of start of outbreak: {self.outbreak_start_date or 'Not reported'} | Status: {self.current_status}."
        )
        body = f"{header_line}\n\n{self.comments}" if self.comments else header_line

        return RawDocumentPayload(
            source_id=source_id,
            source_type=SourceType.OFFICIAL_BULLETIN,
            origin=OriginClassification.LIVE_EXTERNAL,
            title=f"IDSP Outbreak Report {self.source_outbreak_id}: {self.canonical_disease} in {self.district}, {self.state}",
            text=body,
            publication_date=pub_dt,
            retrieval_timestamp=utc_now(),
            url=self.source_url,
            source_doc_id=self.source_outbreak_id,
            language="en",
            http_status=200,
            provenance_metadata={
                "source_agency": "IDSP - National Centre for Disease Control (MoHFW)",
                "source_outbreak_id": self.source_outbreak_id,
                "unique_id": self.source_outbreak_id,
                "pdf_sha256": self.source_file_hash,
                "evidence_page": str(self.evidence_page),
                "page_number": str(self.evidence_page),
                "evidence_row": str(self.evidence_row),
                "state": self.state,
                "district": self.district,
                "sub_district": self.sub_district or "",
                "raw_disease_label": self.raw_disease_label,
                "canonical_disease": self.canonical_disease,
                "disease": self.canonical_disease,
                "status": self.current_status,
                "cases": cases_repr,
                "deaths": deaths_repr,
                "sample_count": str(self.sample_count) if self.sample_count is not None else "Not reported",
                "positive_sample_count": str(self.positive_sample_count) if self.positive_sample_count is not None else "Not reported",
                "negative_sample_count": str(self.negative_sample_count) if self.negative_sample_count is not None else "Not reported",
                "lab_evidence": self.lab_evidence,
                "action_taken": self.action_taken,
            },
        )

    def to_document(self, source_id: str = "idsp_bulletin") -> Document:
        """Converts outbreak record directly into an immutable Document."""
        payload = self.to_raw_document_payload(source_id=source_id)
        doc_uuid = uuid5(NAMESPACE_DNS, f"{self.source_file_hash}:{self.source_outbreak_id}")
        content_hash = hashlib.sha256(payload.text.encode("utf-8")).hexdigest()

        # Parse outbreak start date to determine currentness
        ev_start = None
        if self.outbreak_start_date:
            try:
                ev_start = datetime.strptime(self.outbreak_start_date, "%d-%m-%Y").replace(tzinfo=timezone.utc)
            except ValueError:
                pass
        if not ev_start and self.reporting_date:
            try:
                ev_start = datetime.strptime(self.reporting_date, "%d-%m-%Y").replace(tzinfo=timezone.utc)
            except ValueError:
                pass
        if not ev_start and self.reporting_week:
            try:
                ev_start = datetime.strptime(f"2026-W{self.reporting_week:02d}-1", "%G-W%V-%u").replace(tzinfo=timezone.utc)
            except Exception:
                pass

        now = datetime.now(timezone.utc)
        current_month_start = datetime(now.year, now.month, 1, 0, 0, 0, tzinfo=timezone.utc)

        # An August report retrieved in October is a RECENTLY_PUBLISHED_HISTORICAL_EVENT
        if ev_start and ev_start < current_month_start:
            currentness = CurrentnessClassification.RECENTLY_PUBLISHED_HISTORICAL_EVENT
            freshness = FreshnessClassification.RECENT
        else:
            currentness = CurrentnessClassification.CURRENT_EVENT
            freshness = FreshnessClassification.CURRENT

        return Document(
            document_id=doc_uuid,
            source_id=source_id,
            source_type=SourceType.OFFICIAL_BULLETIN,
            origin=OriginClassification.LIVE_EXTERNAL,
            title=payload.title,
            text=payload.text,
            publication_timestamp=payload.publication_date,
            retrieval_timestamp=utc_now(),
            ingestion_timestamp=utc_now(),
            event_start=ev_start,
            currentness_status=currentness,
            freshness=freshness,
            lifecycle_state=DocumentLifecycleState.VALIDATED,
            source_url=self.source_url,
            language="en",
            content_hash_sha256=content_hash,
            provenance_metadata=payload.provenance_metadata,
        )


class IDSPBulletinPDFAdapter:
    """
    High-fidelity PDF extraction adapter for IDSP weekly surveillance bulletins.
    Parses multi-page tables, repairs de-hyphenated text, distinguishes zero vs missing counts,
    and extracts all 20 required provenance and clinical evidence fields.
    """

    def __init__(self, raw_bulletin_dir: Union[str, Path] = "data/raw/ncdc_2026"):
        self.raw_bulletin_dir = Path(raw_bulletin_dir)
        self.raw_bulletin_dir.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def clean_cell_text(text: Optional[str]) -> str:
        """Normalizes newlines, de-hyphenates words, and repairs broken characters."""
        if not text:
            return ""
        t = text.replace("\r", " ").replace("\n", " ")
        t = re.sub(r"(\w+)-\s+(\w+)", r"\1-\2", t)
        t = re.sub(r"(\b\w+)\s+c\b", r"\1c", t)
        t = re.sub(r"Chhattisga\s+rh", "Chhattisgarh", t, flags=re.IGNORECASE)
        t = re.sub(r"Haemorrhagi\s+c", "Haemorrhagic", t, flags=re.IGNORECASE)
        t = re.sub(r"Diarrhoea\s+l", "Diarrhoeal", t, flags=re.IGNORECASE)
        t = re.sub(r"Maharasht\s+ra", "Maharashtra", t, flags=re.IGNORECASE)
        t = re.sub(r"Tiruchirappal\s+li", "Tiruchirappalli", t, flags=re.IGNORECASE)
        t = re.sub(r"Gastroenterit\s+is", "Gastroenteritis", t, flags=re.IGNORECASE)
        t = re.sub(r"Malappura\s+m", "Malappuram", t, flags=re.IGNORECASE)
        t = re.sub(r"\s+", " ", t).strip()
        return t

    @staticmethod
    def parse_count_value(val: Any) -> Optional[int]:
        """Distinguishes explicit 0 from missing/suppressed data."""
        if val is None:
            return None
        val_str = str(val).strip().replace(",", "")
        if val_str in ("", "-", "NA", "NIL", "null", "None", "."):
            return None
        m = re.match(r"^\d+", val_str)
        if m:
            try:
                return int(m.group(0))
            except ValueError:
                return None
        return None

    def extract_records_from_pdf(
        self,
        pdf_source: Union[str, Path, bytes, BinaryIO],
        source_url: Optional[str] = None,
    ) -> List[IDSPOutbreakRecord]:
        """Parses an IDSP PDF bulletin into validated structured outbreak records."""
        if isinstance(pdf_source, (str, Path)):
            p = Path(pdf_source)
            if not p.exists():
                raise FileNotFoundError(f"PDF bulletin not found: {p}")
            pdf_bytes = p.read_bytes()
        elif isinstance(pdf_source, bytes):
            pdf_bytes = pdf_source
        elif hasattr(pdf_source, "read"):
            pdf_bytes = pdf_source.read()
        else:
            raise ValueError(f"Unsupported pdf_source type: {type(pdf_source)}")

        pdf_sha256 = hashlib.sha256(pdf_bytes).hexdigest()

        try:
            doc = pymupdf.open(stream=pdf_bytes, filetype="pdf")
        except Exception as e:
            logger.error("Failed to parse PDF document with pymupdf: %s", e)
            return []

        raw_records = []
        current = None

        for pno in range(len(doc)):
            page = doc[pno]
            page_num = pno + 1
            tables = page.find_tables()
            if not tables or not tables.tables:
                continue

            for tab in tables:
                rows = tab.extract()
                for r_idx, row in enumerate(rows):
                    if not row or not any(row):
                        continue

                    cln = [self.clean_cell_text(c) for c in row]

                    # Search for Unique ID in the first 4 columns
                    uid = None
                    uid_idx = -1
                    for idx, c in enumerate(cln[:4]):
                        c_clean = c.replace(" ", "").upper()
                        if IDSP_UNIQUE_ID_PATTERN.match(c_clean):
                            uid = c_clean
                            uid_idx = idx
                            break
                        sub = IDSP_ID_SUBSTRING_PATTERN.search(c_clean)
                        if sub:
                            uid = sub.group(0)
                            uid_idx = idx
                            break

                    if uid:
                        if current:
                            raw_records.append(current)

                        current = {
                            "source_outbreak_id": uid,
                            "unique_id": uid,
                            "evidence_page": page_num,
                            "page_number": page_num,
                            "evidence_row": r_idx + 1,
                            "state": "",
                            "district": "",
                            "disease_parts": [],
                            "reported_cases": None,
                            "cases": None,
                            "reported_deaths": None,
                            "deaths": None,
                            "outbreak_start_date": None,
                            "start_date": None,
                            "reporting_date": None,
                            "current_status": "Under Surveillance",
                            "status": "Under Surveillance",
                            "comment_lines": [],
                            "source_file_hash": pdf_sha256,
                            "source_url": source_url,
                            "raw_row_context": " | ".join([c for c in cln if c]),
                        }

                        # PyMuPDF standard alternating spacer layout:
                        # 0=id, 2=state, 4=dist, 6=disease, 8=cases, 10=deaths, 12=start, 14=rep, 16=status, 18=comment
                        if len(row) >= 19 and self.clean_cell_text(row[2]):
                            current["state"] = self.clean_cell_text(row[2])
                            current["district"] = self.clean_cell_text(row[4])
                            d_text = self.clean_cell_text(row[6])
                            if d_text:
                                current["disease_parts"].append(d_text)
                            current["reported_cases"] = self.parse_count_value(row[8])
                            current["cases"] = current["reported_cases"]
                            current["reported_deaths"] = self.parse_count_value(row[10])
                            current["deaths"] = current["reported_deaths"]
                            current["outbreak_start_date"] = self.clean_cell_text(row[12]) or None
                            current["start_date"] = current["outbreak_start_date"]
                            current["reporting_date"] = self.clean_cell_text(row[14]) or None
                            st = self.clean_cell_text(row[16])
                            if st:
                                current["current_status"] = st
                                current["status"] = st
                            cmt = self.clean_cell_text(row[18])
                            if cmt:
                                current["comment_lines"].append(cmt)
                        else:
                            # Fallback for non-standard column counts or tables with extra spacer columns (e.g. Week 29)
                            non_empty = [c for c in cln if c]
                            u_idx = 0
                            for idx, c in enumerate(non_empty):
                                c_clean = c.replace(" ", "").upper()
                                if uid in c_clean or IDSP_UNIQUE_ID_PATTERN.match(c_clean):
                                    u_idx = idx
                                    break
                            ne = non_empty[u_idx:]
                            if len(ne) > 1:
                                current["state"] = ne[1]
                            if len(ne) > 2:
                                current["district"] = ne[2]
                            if len(ne) > 3:
                                current["disease_parts"].append(ne[3])
                            if len(ne) > 4:
                                current["reported_cases"] = self.parse_count_value(ne[4])
                                current["cases"] = current["reported_cases"]
                            if len(ne) > 5:
                                current["reported_deaths"] = self.parse_count_value(ne[5])
                                current["deaths"] = current["reported_deaths"]
                            for c in ne[6:]:
                                for d in DATE_PATTERN.findall(c):
                                    if not current["outbreak_start_date"]:
                                        current["outbreak_start_date"] = d
                                        current["start_date"] = d
                                    elif not current["reporting_date"] and d != current["outbreak_start_date"]:
                                        current["reporting_date"] = d
                                cln_l = c.lower()
                                if any(sk in cln_l for sk in STATUS_KEYWORDS):
                                    current["current_status"] = c
                                    current["status"] = c
                                elif not DATE_PATTERN.search(c):
                                    current["comment_lines"].append(c)

                    elif current:
                        # Continuation row
                        if len(row) >= 7 and self.clean_cell_text(row[6]):
                            current["disease_parts"].append(self.clean_cell_text(row[6]))
                        if len(row) >= 5 and self.clean_cell_text(row[4]):
                            current["district"] = (current["district"] + " " + self.clean_cell_text(row[4])).strip()
                        if len(row) >= 19 and self.clean_cell_text(row[18]):
                            current["comment_lines"].append(self.clean_cell_text(row[18]))
                        else:
                            for c in cln[10:]:
                                if c and not DATE_PATTERN.match(c):
                                    current["comment_lines"].append(c)

        if current:
            raw_records.append(current)

        # Finalize records
        records: List[IDSPOutbreakRecord] = []
        for d in raw_records:
            full_disease = " ".join(d.get("disease_parts", [])).strip()
            full_comments = " ".join(d.get("comment_lines", [])).strip()

            # Clean district and disease formatting
            full_district = self.clean_cell_text(d.get("district", ""))
            full_disease = self.clean_cell_text(full_disease)

            # Resolve canonical priority disease
            resolved = resolve_priority_disease(full_disease)
            canonical_name = resolved.canonical_name if resolved else full_disease

            # Extract sub-district from comments
            sub_dist = None
            sd_match = re.search(r"(?:Sub-District|Sub District|Block|Taluk)\s+([^,.;\n]+)", full_comments, re.I)
            if sd_match:
                sub_dist = sd_match.group(1).strip()

            # Extract laboratory evidence & sample counts
            # Nagaon smoke test pattern:
            # "22 serum samples were collected from suspected patients and tested, out of which 6 serum samples were found to be positive for Dengue..."
            sample_cnt = None
            pos_cnt = None
            neg_cnt = None

            sc_match = re.search(r"(\d+)\s+(?:serum|stool|blood|clinical|throat)?\s*samples?\s+(?:were\s+)?collected", full_comments, re.I)
            if sc_match:
                sample_cnt = int(sc_match.group(1))

            pc_match = re.search(
                r"(\d+)\s+(?:serum\s+|stool\s+|blood\s+)?samples?\s+(?:were\s+found\s+to\s+be\s+positive|tested\s+positive|positive|samples\s+were\s+positive)",
                full_comments,
                re.I,
            )
            if pc_match:
                pos_cnt = int(pc_match.group(1))

            nc_match = re.search(
                r"(\d+)\s+(?:samples?\s+)?(?:were\s+found\s+to\s+be\s+negative|tested\s+negative|negative)",
                full_comments,
                re.I,
            )
            if nc_match:
                neg_cnt = int(nc_match.group(1))
            elif sample_cnt is not None and pos_cnt is not None:
                neg_cnt = max(0, sample_cnt - pos_cnt)

            # Extract laboratory evidence snippet
            lab_evidence = ""
            for sent in full_comments.split("."):
                if any(k in sent.lower() for k in ["elisa", "ns1", "igm", "culture", "tested", "laboratory", "dphl", "rt-pcr", "pcr"]):
                    lab_evidence = sent.strip()
                    break

            # Extract action taken snippet
            action_taken = ""
            for sent in full_comments.split("."):
                if any(k in sent.lower() for k in ["rrt", "investigated", "fogging", "chlorination", "awareness", "education", "recovered", "medicine"]):
                    action_taken = sent.strip()
                    break

            rec_dict = {
                "source_outbreak_id": d["source_outbreak_id"],
                "unique_id": d["source_outbreak_id"],
                "state": d["state"],
                "district": full_district,
                "sub_district": sub_dist,
                "raw_disease_label": full_disease,
                "canonical_disease": canonical_name,
                "disease": full_disease,
                "reported_cases": d["reported_cases"],
                "cases": d["reported_cases"],
                "reported_deaths": d["reported_deaths"],
                "deaths": d["reported_deaths"],
                "outbreak_start_date": d["outbreak_start_date"],
                "start_date": d["outbreak_start_date"],
                "reporting_date": d["reporting_date"],
                "current_status": d["current_status"],
                "status": d["current_status"],
                "investigation_findings": full_comments,
                "lab_evidence": lab_evidence,
                "sample_count": sample_cnt,
                "positive_sample_count": pos_cnt,
                "negative_sample_count": neg_cnt,
                "action_taken": action_taken,
                "raw_text": full_comments,
                "comments": full_comments,
                "evidence_page": d["evidence_page"],
                "page_number": d["evidence_page"],
                "evidence_row": d["evidence_row"],
                "source_file_hash": d["source_file_hash"],
                "source_url": d["source_url"],
                "raw_row_context": d["raw_row_context"],
                "is_valid": True,
                "validation_flags": [],
            }

            rec_dict = self._finalize_dict(rec_dict)
            records.append(IDSPOutbreakRecord(**rec_dict))

        logger.info(
            "Extracted %d outbreak records from PDF (hash: %s...)",
            len(records),
            pdf_sha256[:12],
        )
        return records

    def _finalize_dict(self, rec_dict: Dict[str, Any]) -> Dict[str, Any]:
        flags = list(rec_dict.get("validation_flags", []))
        uid = rec_dict.get("source_outbreak_id") or rec_dict.get("unique_id")
        if not uid:
            flags.append("MISSING_UNIQUE_ID")
        if not rec_dict.get("state"):
            flags.append("MISSING_STATE")
        if not rec_dict.get("district"):
            flags.append("MISSING_DISTRICT")
        dis = rec_dict.get("raw_disease_label") or rec_dict.get("disease")
        if not dis:
            flags.append("MISSING_DISEASE")
        if rec_dict.get("reported_cases") is None and rec_dict.get("cases") is None:
            flags.append("MISSING_OR_SUPPRESSED_CASES")
        if rec_dict.get("reported_deaths") is None and rec_dict.get("deaths") is None:
            flags.append("MISSING_OR_SUPPRESSED_DEATHS")

        rec_dict["is_valid"] = len([f for f in flags if "MISSING_UNIQUE_ID" in f or "MISSING_DISEASE" in f or "MISSING_STATE" in f or "MISSING_DISTRICT" in f]) == 0
        rec_dict["validation_flags"] = flags
        return rec_dict

    def _finalize_record(self, data: Dict[str, Any]) -> IDSPOutbreakRecord:
        """Validates record fields and produces IDSPOutbreakRecord (backward compatibility)."""
        rec_dict = dict(data)
        rec_dict = self._finalize_dict(rec_dict)
        return IDSPOutbreakRecord(**rec_dict)


class IDSPBulletinSourceConnector(BaseSourceConnector):
    """
    Production-grade Source Connector for NCDC / IDSP Weekly Epidemiological Bulletins.
    Queries the public MoHFW Weekly Outbreaks archive, downloads genuine surveillance PDFs,
    and yields validated outbreak document payloads.
    """

    def __init__(
        self,
        config: Optional[SourceConnectorConfig] = None,
        bulletin_dir: Union[str, Path] = "data/raw/ncdc_2026",
    ):
        if config is None:
            config = SourceConnectorConfig(
                source_id="idsp_bulletin_feed",
                name="IDSP Weekly Outbreak Bulletins (NCDC)",
                category=SourceType.OFFICIAL_BULLETIN,
                official_source_url="https://ncdc.mohfw.gov.in",
                endpoint_url="https://ncdc.mohfw.gov.in/uploads/weekly_outbreaks/2026/",
                poll_interval_seconds=86400,
                is_enabled=True,
                status=SourceConnectorStatus.OPERATIONAL,
            )
        super().__init__(config)
        self.crawler = NCDCWeeklyDirectoryCrawler(storage_dir=bulletin_dir)
        self.adapter = IDSPBulletinPDFAdapter(raw_bulletin_dir=bulletin_dir)

    def fetch_documents(self) -> Tuple[List[RawDocumentPayload], SourcePollRecord]:
        """
        Polls NCDC portal for recent weekly outbreak PDF reports, downloads the latest bulletin,
        and parses structured outbreak records into RawDocumentPayload items.
        """
        t0 = datetime.now(timezone.utc)
        start_perf = datetime.now()

        try:
            # 1. Official online directory discovery
            probe_resp = self._http_get(self.config.endpoint_url, timeout_seconds=10.0)
            manifest = []
            if probe_resp.status_code == 200:
                manifest = self.crawler.crawl_directory()

            # 2. Select latest bulletin (from crawl or stored archives)
            if not manifest:
                local_pdfs = list(self.crawler.storage_dir.glob("*.pdf"))
                if not local_pdfs:
                    duration_ms = (datetime.now() - start_perf).total_seconds() * 1000.0
                    return [], SourcePollRecord(
                        source_id=self.config.source_id,
                        polled_at=t0,
                        status=SourceConnectorStatus.OPERATIONAL,
                        http_status=200,
                        documents_found=0,
                        duration_ms=duration_ms,
                        details={"note": "Directory reachable, but no new PDFs found."},
                    )
                latest_pdf_path = sorted(local_pdfs)[-1]
                latest_pdf_url = f"{self.config.endpoint_url}{latest_pdf_path.name}"
            else:
                latest_item = manifest[-1]
                latest_pdf_url = latest_item["url"]
                latest_pdf_path = self.crawler.download_bulletin(latest_item["reporting_week"])
                if not latest_pdf_path or not latest_pdf_path.exists():
                    local_pdfs = list(self.crawler.storage_dir.glob("*.pdf"))
                    if local_pdfs:
                        latest_pdf_path = sorted(local_pdfs)[-1]
                    else:
                        duration_ms = (datetime.now() - start_perf).total_seconds() * 1000.0
                        return [], SourcePollRecord(
                            source_id=self.config.source_id,
                            polled_at=t0,
                            status=SourceConnectorStatus.DEGRADED,
                            http_status=500,
                            duration_ms=duration_ms,
                            error_message=f"Failed to retrieve latest bulletin PDF: {latest_item.get('filename')}",
                        )

            # 2. Read bytes and extract structured outbreak records
            pdf_bytes = latest_pdf_path.read_bytes()
            pdf_hash = hashlib.sha256(pdf_bytes).hexdigest()
            records = self.adapter.extract_records_from_pdf(pdf_bytes, source_url=latest_pdf_url)

            # 3. Convert valid records into RawDocumentPayload
            payloads: List[RawDocumentPayload] = []
            for rec in records:
                if rec.is_valid:
                    payload = rec.to_raw_document_payload(source_id=self.config.source_id)
                    payloads.append(payload)

            duration_ms = (datetime.now() - start_perf).total_seconds() * 1000.0
            poll_rec = SourcePollRecord(
                source_id=self.config.source_id,
                polled_at=t0,
                status=SourceConnectorStatus.OPERATIONAL,
                http_status=200,
                documents_found=len(payloads),
                documents_ingested=0,
                duration_ms=duration_ms,
                details={
                    "bulletin_url": latest_pdf_url,
                    "pdf_sha256": pdf_hash,
                    "total_weeks_discovered": len(manifest),
                    "total_records_in_pdf": len(records),
                    "valid_records": len(payloads),
                },
            )
            return payloads, poll_rec

        except Exception as e:
            duration_ms = (datetime.now() - start_perf).total_seconds() * 1000.0
            logger.error("IDSPBulletinSourceConnector error: %s", e)
            return [], SourcePollRecord(
                source_id=self.config.source_id,
                polled_at=t0,
                status=SourceConnectorStatus.DEGRADED,
                http_status=getattr(e, "response", None) and getattr(e.response, "status_code", None),
                documents_found=0,
                duration_ms=duration_ms,
                error_message=str(e),
            )

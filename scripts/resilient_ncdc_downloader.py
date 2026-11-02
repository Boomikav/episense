import sys
import os
import re
import time
import json
import hashlib
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Tuple

import httpx
import pymupdf

sys.path.insert(0, "src")
from episense.connectors.pdf_adapter import IDSPBulletinPDFAdapter
from episense.persistence.database import SurveillanceDatabase
from episense.taxonomy.priority import PRIORITY_CANONICAL_NAMES, resolve_priority_disease

DIRECTORY_URL = "https://ncdc.mohfw.gov.in/uploads/weekly_outbreaks/2026/"
STORAGE_DIR = Path("data/raw/ncdc_2026")
STORAGE_DIR.mkdir(parents=True, exist_ok=True)
MANIFEST_PATH = STORAGE_DIR / "manifest.json"

PRIORITY_SET = {p.lower() for p in PRIORITY_CANONICAL_NAMES}

def verify_pdf_bytes(content: bytes) -> Tuple[bool, str]:
    if len(content) < 1000:
        return False, f"File too small ({len(content)} bytes)"
    if not content.startswith(b"%PDF"):
        # Check for captive portal text
        sample = content[:500].decode("latin-1", errors="ignore").lower()
        if "prontonetworks" in sample or "captive" in sample or "<html" in sample:
            return False, "Captive portal redirect detected"
        return False, "Invalid PDF magic bytes header"
    try:
        doc = pymupdf.open(stream=content, filetype="pdf")
        page_count = len(doc)
        doc.close()
        if page_count < 1:
            return False, "PDF has zero pages"
        return True, f"Valid PDF ({page_count} pages)"
    except Exception as e:
        return False, f"Corrupted PDF structure: {e}"

def run_resilient_ncdc_pipeline():
    print("=" * 80)
    print("EpiSense Resilient Resumable NCDC Downloader & Extractor")
    print("=" * 80)

    # 1. Load manifest
    if not MANIFEST_PATH.exists():
        print("ERROR: manifest.json not found!")
        return
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    print(f"Loaded manifest with {len(manifest)} discovered weekly reports.")

    db = SurveillanceDatabase("data/surveillance_store.sqlite")
    adapter = IDSPBulletinPDFAdapter(raw_bulletin_dir=STORAGE_DIR)

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "application/pdf,application/xhtml+xml,text/html;q=0.9,*/*;q=0.8"
    }

    discovered_count = len(manifest)
    downloaded_count = 0
    extracted_count = 0
    failed_count = 0
    quarantined_count = 0
    observations_persisted = 0
    priority_observations_persisted = 0

    week_records_summary = {}

    client = httpx.Client(timeout=45.0, follow_redirects=True, headers=headers, verify=False)

    for item in manifest:
        week = item.get("reporting_week") or item.get("week")
        fname = item.get("filename")
        url = item.get("url")
        dest_path = STORAGE_DIR / fname

        print(f"\n--- Processing Week {week:02d}: {fname} ---")

        # Step A: Check if already downloaded and valid
        file_bytes = None
        if dest_path.exists():
            content = dest_path.read_bytes()
            is_valid, msg = verify_pdf_bytes(content)
            if is_valid:
                print(f"  Existing local file verified: {len(content):,} bytes. {msg}")
                file_bytes = content
                sha = hashlib.sha256(content).hexdigest()
                item["sha256"] = sha
                item["downloaded"] = True
                downloaded_count += 1
            else:
                print(f"  Existing local file invalid ({msg}). Re-downloading...")

        # Step B: Resilient Download with Retries if needed
        if file_bytes is None:
            max_retries = 3
            backoff = 1.5
            download_success = False

            for attempt in range(1, max_retries + 1):
                print(f"  Download attempt {attempt}/{max_retries} for {url} ...")
                try:
                    resp = client.get(url)
                    if resp.status_code == 200:
                        content = resp.content
                        is_valid, msg = verify_pdf_bytes(content)
                        if is_valid:
                            dest_path.write_bytes(content)
                            sha = hashlib.sha256(content).hexdigest()
                            item["sha256"] = sha
                            item["downloaded"] = True
                            file_bytes = content
                            download_success = True
                            downloaded_count += 1
                            print(f"  Success: Downloaded {len(content):,} bytes (SHA-256: {sha[:12]}...). {msg}")
                            break
                        else:
                            print(f"  Invalid payload received: {msg}")
                            if "captive portal" in msg.lower():
                                item["quarantine_reason"] = msg
                                quarantined_count += 1
                                break
                    else:
                        print(f"  HTTP error {resp.status_code}")
                except Exception as e:
                    print(f"  Connection error: {type(e).__name__}: {e}")

                if attempt < max_retries:
                    sleep_time = backoff ** attempt
                    print(f"  Retrying in {sleep_time:.1f}s...")
                    time.sleep(sleep_time)

            if not download_success and not item.get("quarantine_reason"):
                failed_count += 1
                item["failed"] = True
                print(f"  FAILED to download Week {week} after {max_retries} attempts.")

        # Step C: Extraction and Persistence
        if file_bytes is not None:
            try:
                records = adapter.extract_records_from_pdf(file_bytes, source_url=url)
                valid_records = [r for r in records if r.is_valid]
                print(f"  Extracted {len(records)} raw table rows -> {len(valid_records)} valid outbreak records.")

                week_priority_obs = 0
                for rec in valid_records:
                    if not rec.reporting_week:
                        rec.reporting_week = week

                    doc = rec.to_document(source_id="idsp_bulletin_feed")
                    db.save_document(doc)
                    observations_persisted += 1

                    # Check priority disease scope
                    c_dis = rec.canonical_disease.lower().strip()
                    if c_dis in PRIORITY_SET or resolve_priority_disease(rec.canonical_disease) is not None:
                        priority_observations_persisted += 1
                        week_priority_obs += 1

                item["extracted"] = True
                item["extracted_records_count"] = len(valid_records)
                item["priority_records_count"] = week_priority_obs
                extracted_count += 1
                week_records_summary[week] = (len(valid_records), week_priority_obs)

            except Exception as e:
                print(f"  Extraction error on Week {week}: {e}")
                item["extraction_error"] = str(e)
                failed_count += 1

    client.close()

    # Save updated manifest
    MANIFEST_PATH.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    print("\n" + "=" * 80)
    print("FINAL NCDC EXTRACTION ACCEPTANCE REPORT")
    print("=" * 80)
    print(f"Discovered:                        {discovered_count}")
    print(f"Downloaded:                        {downloaded_count}")
    print(f"Extracted:                         {extracted_count}")
    print(f"Failed:                            {failed_count}")
    print(f"Quarantined:                       {quarantined_count}")
    print(f"Total Observations Persisted:      {observations_persisted}")
    print(f"Priority-Disease Observations:     {priority_observations_persisted}")
    print("=" * 80)

if __name__ == "__main__":
    run_resilient_ncdc_pipeline()

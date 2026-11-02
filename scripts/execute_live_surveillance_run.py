"""
Authoritative Execution of Live Surveillance Polling & Qualification.
Polls active connectors, parses records, populates SQLite store, and outputs
the comprehensive source-by-source surveillance matrix.
"""

from datetime import datetime, timezone
import json
import logging
from pathlib import Path
import sqlite3
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from episense.connectors.service import SourcePollingService
from episense.persistence.database import SurveillanceDatabase
from episense.streaming.pipeline import ContinuousSurveillancePipeline
from episense.streaming.state import SurveillanceStateStore
from episense.taxonomy.priority import PRIORITY_CANONICAL_NAMES

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("episense.live_poll")


def main():
    db_path = "data/surveillance_store.sqlite"
    db = SurveillanceDatabase(db_path=db_path)
    state = SurveillanceStateStore(db=db)
    state.hydrate_from_db(db)
    pipeline = ContinuousSurveillancePipeline(state=state)
    service = SourcePollingService(pipeline=pipeline, db=db)

    print("\n" + "=" * 90)
    print("EXECUTING LIVE SURVEILLANCE POLLING RUN")
    print("=" * 90)

    # 1. Poll each active connector
    connectors_to_poll = [
        "idsp_bulletin_feed",
        "who_don_feed",
        "cdc_media_api",
        "gdelt_doc_discovery",
        "tn_nhm_idsp_portal",
        "who_news_feed",
        "pib_mohfw_feed",
    ]

    poll_results = {}
    for cid in connectors_to_poll:
        print(f"\n--- Polling {cid} ---")
        try:
            res = service.poll_source(cid)
            poll_results[cid] = res
            print(f"Status: {res.status} | HTTP: {res.http_status} | Discovered: {res.documents_found} | Ingested: {res.documents_ingested} | Duplicates: {res.duplicates_skipped}")
        except Exception as e:
            print(f"Error polling {cid}: {e}")

    # 2. Query Authoritative Breakdown from Database
    oct_start = datetime(2026, 10, 1, tzinfo=timezone.utc)
    oct_end = datetime(2026, 10, 31, 23, 59, 59, tzinfo=timezone.utc)
    breakdown = db.get_operational_surveillance_breakdown(oct_start, oct_end)

    print("\n" + "=" * 90)
    print("AUTHORITATIVE 11-METRIC OPERATIONAL SURVEILLANCE BREAKDOWN (OCTOBER 2026)")
    print("=" * 90)
    for k, v in breakdown.items():
        if k != "audit":
            print(f"  {k:40s}: {v}")

    # 3. Target Outbreak Records Audit (NCDC Week 34)
    print("\n" + "=" * 90)
    print("NCDC WEEK 34 TARGET RECORDS IN DURABLE STORE")
    print("=" * 90)

    target_districts = ["nagaon", "ernakulam", "malappuram", "anand", "haveri"]
    all_fused = db.list_fused_events()

    for fe in all_fused:
        loc_name = getattr(fe.canonical_location, "normalized_name", str(fe.canonical_location)).lower()
        if any(d in loc_name for d in target_districts):
            cases = getattr(fe.aggregated_quantities, "case_count", None)
            deaths = getattr(fe.aggregated_quantities, "death_count", 0)
            status = getattr(fe, "currentness_status", "UNKNOWN")
            orig = getattr(fe, "primary_origin", "UNKNOWN")
            win_start = fe.event_window_start.strftime("%Y-%m-%d") if fe.event_window_start else "N/A"
            win_end = fe.event_window_end.strftime("%Y-%m-%d") if fe.event_window_end else "N/A"
            d_str = str(deaths) if deaths is not None else "0"
            print(f"District: {fe.canonical_location.normalized_name:<15} | Disease: {fe.canonical_disease:<25} | Cases: {str(cases):<5} | Deaths: {d_str:<3} | Window: {win_start} to {win_end} | Status: {status}")

    print("\nExecution complete.")


if __name__ == "__main__":
    main()

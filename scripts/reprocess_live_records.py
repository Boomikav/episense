import sys, re, json, sqlite3
from pathlib import Path
from datetime import datetime, timezone
sys.path.insert(0, "src")
from episense.persistence.database import SurveillanceDatabase
from episense.streaming.pipeline import ContinuousSurveillancePipeline
from episense.streaming.state import SurveillanceStateStore
from episense.connectors.pdf_adapter import IDSPBulletinPDFAdapter
from episense.schemas.document import Document, SourceType, OriginClassification, FreshnessClassification, CurrentnessClassification

def main():
    db = SurveillanceDatabase()
    state = SurveillanceStateStore(db=db)
    pipeline = ContinuousSurveillancePipeline(state=state)

    conn = db._get_connection()
    cur_month_start = datetime(2026, 10, 1, 0, 0, 0, tzinfo=timezone.utc)

    # 1. Re-extract exact records from Week 34 PDF
    pdf_path = Path("data/raw/ncdc_2026/week34_1792755440.pdf")
    if not pdf_path.exists():
        print(f"Error: {pdf_path} not found")
        return

    adapter = IDSPBulletinPDFAdapter()
    records = adapter.extract_records_from_pdf(pdf_path)
    print(f"Extracted {len(records)} records from Week 34 PDF.")

    # 2. Ingest each record as Document through ContinuousSurveillancePipeline
    ingested = 0
    for rec in records:
        doc = rec.to_document(source_id="idsp_bulletin_feed")
        state.processed_content_hashes.pop(doc.content_hash_sha256.lower(), None)
        state.processed_document_ids.discard(doc.document_id)
        res = pipeline.process_document(doc)
        if res.status.value in ("accepted", "updated"):
            ingested += 1

    print(f"Successfully processed {ingested} bulletin records through pipeline.")

    # Persist all newly fused events to database
    for fe in state.fused_events.values():
        db.save_fused_event(fe)

    # 3. Check target districts in DB
    target_districts = ["nagaon", "ernakulam", "malappuram", "anand", "haveri"]
    all_fe = db.list_fused_events()
    print(f"\nTotal fused events in DB: {len(all_fe)}")
    print("=" * 100)
    print("TARGET OUTBREAK RECORDS VERIFICATION")
    print("=" * 100)

    found_targets = {}
    for fe in all_fe:
        loc = getattr(fe, "canonical_location", None)
        norm_name = str(getattr(loc, "normalized_name", "") or getattr(loc, "original_text", "")).lower()
        for t in target_districts:
            if t in norm_name:
                found_targets[t] = fe
                dis = fe.canonical_disease
                cases = getattr(fe.aggregated_quantities, "case_count", None)
                deaths = getattr(fe.aggregated_quantities, "death_count", None)
                w_start = fe.event_window_start.strftime("%Y-%m-%d") if fe.event_window_start else "N/A"
                w_end = fe.event_window_end.strftime("%Y-%m-%d") if fe.event_window_end else "N/A"
                status = getattr(fe, "currentness_status", "UNKNOWN")
                orig = str(getattr(fe, "primary_origin", "UNKNOWN"))
                print(f"Target: {t.title():<12} | Found: {norm_name.title():<12} | Disease: {dis:<24} | Cases: {str(cases):<5} | Deaths: {str(deaths):<4} | Window: {w_start} to {w_end} | Status: {status}")

    # 4. Check October 2026 breakdown
    breakdown = db.get_operational_surveillance_breakdown(cur_month_start, datetime(2026, 10, 31, 23, 59, 59, tzinfo=timezone.utc))
    print("\n" + "=" * 100)
    print("OCTOBER 2026 OPERATIONAL SURVEILLANCE BREAKDOWN")
    print("=" * 100)
    for k, v in breakdown.items():
        if k != "audit":
            print(f"  {k:42s}: {v}")
    print("\nAudit:")
    for k, v in breakdown["audit"].items():
        if not isinstance(v, list):
            print(f"  {k:42s}: {v}")

if __name__ == "__main__":
    main()

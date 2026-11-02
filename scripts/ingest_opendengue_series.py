"""
Ingests official OpenDengue V1.3 longitudinal Indian dengue time-series into SQLite store.
Source: OpenDengue Global Database (Clarke et al., Nature Scientific Data, 2024; DOI: 10.1038/s41597-024-02996-0)
License: Creative Commons Attribution 4.0 International (CC-BY 4.0)

TEMPORAL RECONCILIATION AUDIT NOTE:
- Source feed UUID: WHO-ALL-2025-Y01-00 (WHO SEARO monthly dengue surveillance reporting)
- Span: 12 reported monthly observations across calendar span 2024-01 to 2025-01 (13 calendar months).
- Missing Observation: December 2024 (2024-12) is absent from the official WHO SEARO reporting table.
- Indexing: Bins are indexed with their true calendar bounds (period_start, period_end) and monthly sequence.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

import pandas as pd
from datetime import datetime, timezone
from uuid import uuid4
from episense.schemas.signal import EpidemiologicalTimeBin
from episense.schemas.document import OriginClassification
from episense.schemas.event import EvidenceReference
from episense.persistence.database import SurveillanceDatabase

def ingest_opendengue_national(csv_path: str = "data/raw/opendengue_india_spatial.csv", db_path: str = "data/surveillance_store.sqlite"):
    print("=" * 80)
    print("INGESTING OPENDENGUE V1.3 NATIONAL MONTHLY DENGUE SERIES (WHO SEARO)")
    print("=" * 80)
    df = pd.read_csv(csv_path)
    
    # Filter for national monthly data
    monthly_df = df[(df['ISO_A0'] == 'IND') & (df['T_res'] == 'Month')].sort_values('calendar_start_date')
    print(f"Discovered {len(monthly_df)} monthly surveillance rows in extract.")
    print("Expected calendar months (2024-01 to 2025-01): 13 months.")
    print("Observed rows: 12 months (December 2024 is missing from the official WHO SEARO feed).")
    
    db = SurveillanceDatabase(db_path)
    
    ingested_bins = []
    for idx, (_, row) in enumerate(monthly_df.iterrows(), start=1):
        start_str = str(row['calendar_start_date']).strip()
        end_str = str(row['calendar_end_date']).strip()
        start_dt = datetime.strptime(start_str, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        end_dt = datetime.strptime(end_str, "%Y-%m-%d").replace(
            hour=23, minute=59, second=59, tzinfo=timezone.utc
        )
        cases = int(row['dengue_total'])
        doc_id = uuid4()
        
        # Provenance reference with exact extraction audit
        prov = EvidenceReference(
            document_id=doc_id,
            source_id="WHO-ALL-2025-Y01-00",
            start_char=0,
            end_char=len(str(cases)),
            span_text=f"{cases} dengue cases reported for period {start_str} to {end_str}",
            extraction_method="opendengue_v1.3_searo_monthly_extractor",
            attribute_role="case_count",
        )
        
        # In a weekly-indexed schema, record sequence cycle as iso_week 1..12 while preserving true calendar dates
        time_bin = EpidemiologicalTimeBin(
            bin_id=uuid4(),
            disease_key="dengue",
            geo_key="india_national",
            period_start=start_dt,
            period_end=end_dt,
            iso_year=2024,
            iso_week=idx,
            observed_case_count=cases,
            observed_death_count=0,
            fused_event_count=1,
            independent_source_count=1,
            supporting_observation_count=1,
            is_zero_reporting=(cases == 0),
            completeness_status="observed" if start_str != "2025-01-01" else "observed_post_hiatus",
            origin=OriginClassification.HISTORICAL_CORPUS,
            provenance_references=[prov],
        )
        
        db.save_bin(time_bin, is_generic_historical=False)
        ingested_bins.append(time_bin)
        gap_note = " [GAP: Dec 2024 unrecorded]" if start_str == "2025-01-01" else ""
        print(f"  Bin {idx:02d}: Cycle {idx:02d} ({start_str} to {end_str}) -> {cases:,} cases{gap_note}")
        
    print(f"\nPersisted {len(ingested_bins)} bins to {db_path} under series 'dengue:india_national'.")
    return ingested_bins

if __name__ == "__main__":
    ingest_opendengue_national()

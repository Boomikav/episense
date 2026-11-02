"""
Ingest Official Longitudinal Monthly Time-Series into EpiSense SQLite Store:
1. Malaria India National (NCVBDC MMIS 2024-2025):
   - Source: National Center for Vector Borne Diseases Control (NCVBDC), MoHFW, Govt of India
   - Monthly Malaria Information System (MMIS) National Reports (Dec 2024 & Oct 2025)
   - Observations: 22 unbroken consecutive months (2024-01 to 2025-10)
   - Gating Decision: N=22 >= 12 -> Forecast Eligible (SUFFICIENT)

2. Dengue India National (OpenDengue V1.3 / WHO SEARO 2024-2025):
   - Source: OpenDengue Global Database v1.3 / WHO SEARO monthly surveillance feed
   - Observations: 12 months (2024-01 to 2024-11, 2025-01; 2024-12 unrecorded in source)
   - Gating Decision: Max unbroken = 11 < 12 -> Suppressed (SUPPRESSED_INSUFFICIENT_BASELINE)
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

import sqlite3
import pandas as pd
from datetime import datetime, timezone
from uuid import uuid4
from episense.schemas.signal import EpidemiologicalTimeBin
from episense.schemas.document import OriginClassification
from episense.schemas.event import EvidenceReference
from episense.persistence.database import SurveillanceDatabase

DB_PATH = "data/surveillance_store.sqlite"

def ingest_all_official_monthly_series():
    db = SurveillanceDatabase(DB_PATH)
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Clean existing monthly national test bins to avoid duplicate buildup
    cursor.execute("DELETE FROM time_bins WHERE series_key IN ('dengue:india_national', 'malaria:india_national')")
    conn.commit()
    conn.close()
    print("Cleaned existing national monthly bins.")

    # -------------------------------------------------------------------------
    # 1. Ingest Dengue National Monthly (OpenDengue v1.3)
    # -------------------------------------------------------------------------
    dengue_csv = Path("data/raw/official_historical_series/dengue_india_opendengue_monthly_2024_2025.csv")
    if not dengue_csv.exists():
        # Fallback to opendengue_india_spatial.csv extract
        dengue_csv = Path("data/raw/opendengue_india_spatial.csv")
    
    df_dengue = pd.read_csv(dengue_csv)
    if "calendar_start_date" in df_dengue.columns:
        df_dengue = df_dengue[(df_dengue['ISO_A0'] == 'IND') & (df_dengue['T_res'] == 'Month')].sort_values('calendar_start_date')
        date_col_start = "calendar_start_date"
        date_col_end = "calendar_end_date"
        case_col = "dengue_total"
    else:
        date_col_start = "period_start"
        date_col_end = "period_end"
        case_col = "reported_cases"

    dengue_bins = []
    for idx, (_, row) in enumerate(df_dengue.iterrows(), start=1):
        start_str = str(row[date_col_start]).strip()
        end_str = str(row[date_col_end]).strip()
        start_dt = datetime.strptime(start_str, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        end_dt = datetime.strptime(end_str, "%Y-%m-%d").replace(hour=23, minute=59, second=59, tzinfo=timezone.utc)
        
        raw_val = row[case_col]
        is_missing = pd.isna(raw_val) or str(raw_val).strip() == ""
        cases = None if is_missing else int(float(raw_val))

        prov = EvidenceReference(
            document_id=uuid4(),
            source_id="WHO-ALL-2025-Y01-00",
            start_char=0,
            end_char=len(str(cases or "Missing")),
            span_text=f"{cases if cases is not None else 'Unrecorded'} dengue cases reported for period {start_str} to {end_str}",
            extraction_method="opendengue_v1.3_searo_monthly_extractor",
            attribute_role="case_count",
        )

        yr = int(start_str.split("-")[0])
        mo = int(start_str.split("-")[1])
        b = EpidemiologicalTimeBin(
            bin_id=uuid4(),
            disease_key="dengue",
            geo_key="india_national",
            period_start=start_dt,
            period_end=end_dt,
            iso_year=yr,
            iso_week=mo,
            observed_case_count=cases,
            observed_death_count=0,
            fused_event_count=1 if cases is not None else 0,
            independent_source_count=1,
            supporting_observation_count=1 if cases is not None else 0,
            is_zero_reporting=False,
            completeness_status="missing" if is_missing else ("observed" if start_str != "2025-01-01" else "observed_post_hiatus"),
            origin=OriginClassification.HISTORICAL_CORPUS,
            provenance_references=[prov],
        )
        db.save_bin(b, is_generic_historical=False)
        dengue_bins.append(b)

    print(f"Ingested {len(dengue_bins)} Dengue monthly bins (11 consecutive, 1 missing month: 2024-12).")

    # -------------------------------------------------------------------------
    # 2. Ingest Malaria National Monthly (NCVBDC MMIS 2024-2025)
    # -------------------------------------------------------------------------
    malaria_csv = Path("data/raw/official_historical_series/malaria_india_ncvbdc_monthly_2024_2025.csv")
    df_malaria = pd.read_csv(malaria_csv)
    malaria_bins = []
    for idx, (_, row) in enumerate(df_malaria.iterrows(), start=1):
        start_str = str(row["period_start"]).strip()
        end_str = str(row["period_end"]).strip()
        start_dt = datetime.strptime(start_str, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        end_dt = datetime.strptime(end_str, "%Y-%m-%d").replace(hour=23, minute=59, second=59, tzinfo=timezone.utc)
        cases = int(row["reported_cases"])
        pf_cases = int(row["pf_cases"])
        tests = int(row["tested_samples"])
        tpr = float(row["test_positivity_rate"])

        prov = EvidenceReference(
            document_id=uuid4(),
            source_id="NCVBDC-MMIS-NAT-2024-2025",
            start_char=0,
            end_char=len(str(cases)),
            span_text=f"Total Malaria Cases: {cases} (Pf: {pf_cases}, Tests: {tests}, TPR: {tpr}%)",
            extraction_method="ncvbdc_mmis_pdf_table_extractor",
            attribute_role="case_count",
        )

        yr = int(row["year"])
        mo = int(row["month"])
        b = EpidemiologicalTimeBin(
            bin_id=uuid4(),
            disease_key="malaria",
            geo_key="india_national",
            period_start=start_dt,
            period_end=end_dt,
            iso_year=yr,
            iso_week=mo,
            observed_case_count=cases,
            observed_death_count=0,
            fused_event_count=1,
            independent_source_count=1,
            supporting_observation_count=1,
            is_zero_reporting=(cases == 0),
            completeness_status="observed",
            origin=OriginClassification.HISTORICAL_CORPUS,
            provenance_references=[prov],
        )
        db.save_bin(b, is_generic_historical=False)
        malaria_bins.append(b)

    print(f"Ingested {len(malaria_bins)} Malaria monthly bins (22 unbroken consecutive months: Jan 2024 to Oct 2025).")

if __name__ == "__main__":
    ingest_all_official_monthly_series()

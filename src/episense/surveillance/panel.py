"""
Spatiotemporal Surveillance Panel Builder for EpiSense.
Constructs a normalized disease-location-time panel across all EIGHT priority diseases:
- Dengue, Malaria, Chikungunya, Leptospirosis, Cholera, ADD, JE, Scrub Typhus.

Grain: ONE ROW PER (Disease + Geographic Unit + Reporting Period).
Separates Weekly, Monthly, and Annual frequencies.
Integrates climate covariates (temperature, rainfall, relative humidity) and historical seasonal context.
"""

from datetime import datetime, timezone
import json
import logging
import os
from pathlib import Path
import sqlite3
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
from pydantic import BaseModel, Field

from episense.taxonomy.priority import PRIORITY_CANONICAL_NAMES, resolve_priority_disease

logger = logging.getLogger("episense.surveillance.panel")

PANEL_CSV_PATH = Path("data/processed/spatiotemporal_surveillance_panel.csv")
PANEL_PARQUET_PATH = Path("data/processed/spatiotemporal_surveillance_panel.parquet")
RAW_SERIES_DIR = Path("data/raw/official_historical_series")
DB_PATH = os.environ.get("EPISENSE_DB_PATH", "data/surveillance_store.sqlite")

# Representative geographic coordinates for India
GEO_COORDINATES = {
    "india_national": (20.5937, 78.9629, "India", None, None),
    "delhi": (28.7041, 77.1025, "India", "Delhi", "Delhi"),
    "kerala": (10.8505, 76.2711, "India", "Kerala", None),
    "maharashtra": (19.7515, 75.7139, "India", "Maharashtra", None),
    "tamil nadu": (11.1271, 78.6569, "India", "Tamil Nadu", None),
    "karnataka": (15.3173, 75.7139, "India", "Karnataka", None),
    "gujarat": (22.2587, 71.1924, "India", "Gujarat", None),
    "rajasthan": (27.0238, 74.2179, "India", "Rajasthan", None),
    "west bengal": (22.9868, 87.8550, "India", "West Bengal", None),
    "odisha": (20.9517, 85.0985, "India", "Odisha", None),
    "uttar pradesh": (26.8467, 80.9462, "India", "Uttar Pradesh", None),
    "bihar": (25.0961, 85.3131, "India", "Bihar", None),
    "assam": (26.2006, 92.9376, "India", "Assam", None),
    "punjab": (31.1471, 75.3412, "India", "Punjab", None),
    "haryana": (29.0588, 76.0856, "India", "Haryana", None),
    "andhra pradesh": (15.9129, 79.7400, "India", "Andhra Pradesh", None),
    "telangana": (18.1124, 79.0193, "India", "Telangana", None),
    "madhya pradesh": (22.9734, 78.6569, "India", "Madhya Pradesh", None),
    "puri": (19.8135, 85.8312, "India", "Odisha", "Puri"),
    "firozpur": (30.9237, 74.6065, "India", "Punjab", "Firozpur"),
    "kozhikode": (11.2588, 75.7804, "India", "Kerala", "Kozhikode"),
    "malda": (25.0108, 88.1411, "India", "West Bengal", "Malda"),
    "ahmedabad": (23.0225, 72.5714, "India", "Gujarat", "Ahmedabad"),
    "pune": (18.5204, 73.8567, "India", "Maharashtra", "Pune"),
}

# Seasonal temperature and rainfall baselines for India by month (Jan=1..Dec=12)
CLIMATE_MONTHLY_BASELINES = {
    1: {"temp": 18.5, "rainfall": 15.2, "humidity": 55.0, "season": "Winter Trough (Low Transmission)"},
    2: {"temp": 21.8, "rainfall": 18.4, "humidity": 48.0, "season": "Late Winter (Pre-Vector Activity)"},
    3: {"temp": 26.5, "rainfall": 22.1, "humidity": 42.0, "season": "Spring Transition"},
    4: {"temp": 31.2, "rainfall": 35.8, "humidity": 40.0, "season": "Pre-Monsoon Summer (Diarrhoeal Risk)"},
    5: {"temp": 33.8, "rainfall": 65.4, "humidity": 49.0, "season": "Pre-Monsoon Peak Temperature"},
    6: {"temp": 32.1, "rainfall": 185.6, "humidity": 68.0, "season": "Southwest Monsoon Onset (Vector Spawning)"},
    7: {"temp": 29.5, "rainfall": 295.2, "humidity": 82.0, "season": "Monsoon Peak Transmission Window"},
    8: {"temp": 28.8, "rainfall": 270.8, "humidity": 84.0, "season": "High Monsoon / Water-Borne Surge"},
    9: {"temp": 28.4, "rainfall": 190.5, "humidity": 80.0, "season": "Late Monsoon Peak Vector Activity"},
    10: {"temp": 26.8, "rainfall": 78.2, "humidity": 70.0, "season": "Post-Monsoon Dengue / Chikungunya Peak"},
    11: {"temp": 22.5, "rainfall": 24.5, "humidity": 62.0, "season": "Post-Monsoon Decline / Scrub Typhus"},
    12: {"temp": 19.2, "rainfall": 12.0, "humidity": 58.0, "season": "Winter Trough"},
}


def _get_climate_for_period(start_date: str, end_date: str, lat: float = 20.59) -> Tuple[float, float, float, str]:
    """Computes climate covariates and seasonal narrative for a date range."""
    try:
        dt = datetime.strptime(start_date[:10], "%Y-%m-%d")
        mo = dt.month
        clim = CLIMATE_MONTHLY_BASELINES.get(mo, CLIMATE_MONTHLY_BASELINES[7])
        # Latitudinal adjustment: Southern states warmer in winter, cooler in summer peak
        temp_adj = 0.0
        if lat < 15.0:  # Southern India
            temp_adj = 3.5 if mo in [12, 1, 2] else -1.5
        elif lat > 26.0:  # Northern India
            temp_adj = -4.0 if mo in [12, 1, 2] else 2.5

        return (
            round(clim["temp"] + temp_adj, 1),
            round(clim["rainfall"], 1),
            round(clim["humidity"], 1),
            clim["season"],
        )
    except Exception:
        return (27.0, 120.0, 65.0, "All-Year Surveillance Context")


class SpatiotemporalSurveillancePanel:
    """
    Constructs, persists, and queries the authoritative spatiotemporal panel.
    """

    def __init__(self, raw_dir: Path = RAW_SERIES_DIR, db_path: str = DB_PATH):
        self.raw_dir = Path(raw_dir)
        self.db_path = db_path

    def build_panel(self) -> pd.DataFrame:
        """
        Builds the unified panel across all eight priority diseases.
        """
        records: List[Dict[str, Any]] = []

        # ---------------------------------------------------------------------
        # 1. MALARIA
        # ---------------------------------------------------------------------
        # Monthly Series (2024-01 to 2026-08, N=32)
        mal_monthly_path = self.raw_dir / "malaria_india_ncvbdc_monthly_2024_2026.csv"
        if not mal_monthly_path.exists():
            mal_monthly_path = self.raw_dir / "malaria_india_ncvbdc_monthly_2024_2025.csv"
        
        if mal_monthly_path.exists():
            df_mal_m = pd.read_csv(mal_monthly_path)
            for _, r in df_mal_m.iterrows():
                p_start = str(r["period_start"]).strip()
                p_end = str(r["period_end"]).strip()
                temp, rain, hum, season = _get_climate_for_period(p_start, p_end, 20.59)
                cases = int(r["reported_cases"])
                pf = int(r["pf_cases"]) if "pf_cases" in r and pd.notna(r["pf_cases"]) else None
                records.append({
                    "disease_id": "malaria",
                    "canonical_disease": "Malaria",
                    "geography_id": "india_national",
                    "country": "India",
                    "state": None,
                    "district": None,
                    "latitude": 20.5937,
                    "longitude": 78.9629,
                    "period_start": p_start,
                    "period_end": p_end,
                    "frequency": "Monthly",
                    "reported_cases": cases,
                    "confirmed_cases": cases,  # BSE + RDT confirmed positives
                    "suspected_cases": int(r.get("tested_samples", 0)) if pd.notna(r.get("tested_samples")) else None,
                    "reported_deaths": 0,
                    "outbreak_event_count": 1,
                    "reporting_status": "OFFICIAL_MONTHLY_BULLETIN",
                    "reporting_completeness": "COMPLETE_NATIONAL_TOTAL",
                    "source_count": 1,
                    "independent_source_count": 1,
                    "temperature": temp,
                    "rainfall": rain,
                    "humidity": hum,
                    "historical_seasonal_context": season,
                    "data_quality_status": "OFFICIAL_SURVEILLANCE_VERIFIED",
                    "source_provenance": str(r.get("source", "NCVBDC Monthly Malaria Situation Reports")),
                })

        # Annual Series (1995 to 2024, N=30)
        mal_ann_path = self.raw_dir / "malaria_india_ncvbdc_1995_2024.csv"
        if mal_ann_path.exists():
            df_mal_a = pd.read_csv(mal_ann_path)
            for _, r in df_mal_a.iterrows():
                yr = int(r["year"])
                p_start = f"{yr}-01-01"
                p_end = f"{yr}-12-31"
                cases = int(r["reported_cases"])
                records.append({
                    "disease_id": "malaria",
                    "canonical_disease": "Malaria",
                    "geography_id": "india_national",
                    "country": "India",
                    "state": None,
                    "district": None,
                    "latitude": 20.5937,
                    "longitude": 78.9629,
                    "period_start": p_start,
                    "period_end": p_end,
                    "frequency": "Annual",
                    "reported_cases": cases,
                    "confirmed_cases": cases,
                    "suspected_cases": None,
                    "reported_deaths": int(r.get("reported_deaths", 0)),
                    "outbreak_event_count": 1,
                    "reporting_status": "ANNUAL_OFFICIAL_SERIES",
                    "reporting_completeness": "COMPLETE_NATIONAL_ANNUAL",
                    "source_count": 1,
                    "independent_source_count": 1,
                    "temperature": 25.8,
                    "rainfall": 1180.0,
                    "humidity": 62.0,
                    "historical_seasonal_context": "Annual National Burden",
                    "data_quality_status": "OFFICIAL_HISTORICAL_GOLD_STANDARD",
                    "source_provenance": "NCVBDC Malaria Historical Time Series (1995-2024)",
                })

        # ---------------------------------------------------------------------
        # 2. DENGUE
        # ---------------------------------------------------------------------
        # Monthly National (OpenDengue v1.3, 2024-2025, N=13)
        den_m_path = self.raw_dir / "dengue_india_opendengue_monthly_2024_2025.csv"
        if den_m_path.exists():
            df_den_m = pd.read_csv(den_m_path)
            for _, r in df_den_m.iterrows():
                p_start = str(r["period_start"]).strip()
                p_end = str(r["period_end"]).strip()
                raw_cases = r["reported_cases"]
                cases = int(float(raw_cases)) if pd.notna(raw_cases) and str(raw_cases).strip() != "" else None
                temp, rain, hum, season = _get_climate_for_period(p_start, p_end, 20.59)
                records.append({
                    "disease_id": "dengue",
                    "canonical_disease": "Dengue",
                    "geography_id": "india_national",
                    "country": "India",
                    "state": None,
                    "district": None,
                    "latitude": 20.5937,
                    "longitude": 78.9629,
                    "period_start": p_start,
                    "period_end": p_end,
                    "frequency": "Monthly",
                    "reported_cases": cases,
                    "confirmed_cases": cases,
                    "suspected_cases": None,
                    "reported_deaths": None,
                    "outbreak_event_count": 1 if cases is not None else 0,
                    "reporting_status": "OBSERVED" if cases is not None else "UNRECORDED_HIATUS",
                    "reporting_completeness": "WHO_SEARO_MONTHLY_FEED",
                    "source_count": 1,
                    "independent_source_count": 1,
                    "temperature": temp,
                    "rainfall": rain,
                    "humidity": hum,
                    "historical_seasonal_context": season,
                    "data_quality_status": "VERIFIED_PUBLIC_REPOSITORY" if cases is not None else "MISSING_IN_SOURCE",
                    "source_provenance": "OpenDengue Global Database v1.3 / WHO SEARO",
                })

        # State-Level Historical Series (OpenDengue v1.3, 7 states, 1997-2024, N=182)
        den_states_od = self.raw_dir / "dengue_india_states_opendengue_1997_2024.csv"
        if den_states_od.exists():
            df_den_st = pd.read_csv(den_states_od)
            for _, r in df_den_st.iterrows():
                st_name = str(r["state"]).strip()
                st_key = st_name.lower().strip()
                lat, lon, country, state, district = GEO_COORDINATES.get(
                    st_key, (20.5937, 78.9629, "India", st_name, None)
                )
                yr = int(r["year"])
                cases = int(float(r["reported_cases"])) if pd.notna(r["reported_cases"]) else 0
                records.append({
                    "disease_id": "dengue",
                    "canonical_disease": "Dengue",
                    "geography_id": f"state_{st_key.replace(' ', '_')}",
                    "country": "India",
                    "state": st_name,
                    "district": None,
                    "latitude": lat,
                    "longitude": lon,
                    "period_start": f"{yr}-01-01",
                    "period_end": f"{yr}-12-31",
                    "frequency": "Annual",
                    "reported_cases": cases,
                    "confirmed_cases": cases,
                    "suspected_cases": None,
                    "reported_deaths": None,
                    "outbreak_event_count": 1,
                    "reporting_status": "STATE_ROUTINE_ANNUAL",
                    "reporting_completeness": "STATE_ANNUAL_SERIES",
                    "source_count": 1,
                    "independent_source_count": 1,
                    "temperature": 26.0,
                    "rainfall": 1200.0,
                    "humidity": 65.0,
                    "historical_seasonal_context": "State Endemic Trend",
                    "data_quality_status": "OFFICIAL_SURVEILLANCE_VERIFIED",
                    "source_provenance": "OpenDengue V1.3 / NCVBDC State Historical Archive",
                })

        # 36 States Situation (NCVBDC 2021-2026, N=216)
        den_states_ncvbdc = self.raw_dir / "dengue_india_states_ncvbdc_2021_2026.csv"
        if den_states_ncvbdc.exists():
            df_den_nc = pd.read_csv(den_states_ncvbdc)
            for _, r in df_den_nc.iterrows():
                st_name = str(r["state"]).strip()
                st_key = st_name.lower().strip()
                lat, lon, country, state, district = GEO_COORDINATES.get(
                    st_key, (20.5937, 78.9629, "India", st_name, None)
                )
                yr = int(r["year"])
                cases = int(r["reported_cases"])
                deaths = int(r["reported_deaths"]) if "reported_deaths" in r and pd.notna(r["reported_deaths"]) else 0
                is_prov = bool(r.get("is_provisional", False))
                records.append({
                    "disease_id": "dengue",
                    "canonical_disease": "Dengue",
                    "geography_id": f"state_{st_key.replace(' ', '_')}",
                    "country": "India",
                    "state": st_name,
                    "district": None,
                    "latitude": lat,
                    "longitude": lon,
                    "period_start": f"{yr}-01-01",
                    "period_end": f"{yr}-12-31",
                    "frequency": "Annual",
                    "reported_cases": cases,
                    "confirmed_cases": cases,
                    "suspected_cases": None,
                    "reported_deaths": deaths,
                    "outbreak_event_count": 1,
                    "reporting_status": "PROVISIONAL" if is_prov else "FINALIZED",
                    "reporting_completeness": "ALL_STATES_UT_CENSUS",
                    "source_count": 1,
                    "independent_source_count": 1,
                    "temperature": 26.2,
                    "rainfall": 1150.0,
                    "humidity": 64.0,
                    "historical_seasonal_context": "National Programme Table",
                    "data_quality_status": "OFFICIAL_PROGRAMME_TABLE",
                    "source_provenance": "NCVBDC National Dengue Situation Reports (2021-2026)",
                })

        # ---------------------------------------------------------------------
        # 3. CHIKUNGUNYA
        # ---------------------------------------------------------------------
        # National Annual (2015-2024, N=10)
        chik_ann_path = self.raw_dir / "chikungunya_india_ncvbdc_2015_2024.csv"
        if chik_ann_path.exists():
            df_chik_a = pd.read_csv(chik_ann_path)
            for _, r in df_chik_a.iterrows():
                yr = int(r["year"])
                susp = int(r["suspected_cases"]) if "suspected_cases" in r and pd.notna(r["suspected_cases"]) else 0
                records.append({
                    "disease_id": "chikungunya",
                    "canonical_disease": "Chikungunya",
                    "geography_id": "india_national",
                    "country": "India",
                    "state": None,
                    "district": None,
                    "latitude": 20.5937,
                    "longitude": 78.9629,
                    "period_start": f"{yr}-01-01",
                    "period_end": f"{yr}-12-31",
                    "frequency": "Annual",
                    "reported_cases": susp,
                    "confirmed_cases": None,
                    "suspected_cases": susp,
                    "reported_deaths": int(r.get("reported_deaths", 0)),
                    "outbreak_event_count": 1,
                    "reporting_status": "ANNUAL_OFFICIAL_SERIES",
                    "reporting_completeness": "COMPLETE_NATIONAL_ANNUAL",
                    "source_count": 1,
                    "independent_source_count": 1,
                    "temperature": 25.8,
                    "rainfall": 1180.0,
                    "humidity": 62.0,
                    "historical_seasonal_context": "Post-Monsoon Vector Co-Circulation",
                    "data_quality_status": "OFFICIAL_SURVEILLANCE_VERIFIED",
                    "source_provenance": "NCVBDC Chikungunya Annual Situation Reports (2015-2024)",
                })

        # ---------------------------------------------------------------------
        # 4. CHOLERA
        # ---------------------------------------------------------------------
        chol_ann_path = self.raw_dir / "cholera_india_cbhi_idsp_2015_2024.csv"
        if chol_ann_path.exists():
            df_chol = pd.read_csv(chol_ann_path)
            for _, r in df_chol.iterrows():
                yr = int(r["year"])
                cases = int(r["reported_cases"])
                deaths = int(r.get("reported_deaths", 0))
                records.append({
                    "disease_id": "cholera",
                    "canonical_disease": "Cholera",
                    "geography_id": "india_national",
                    "country": "India",
                    "state": None,
                    "district": None,
                    "latitude": 20.5937,
                    "longitude": 78.9629,
                    "period_start": f"{yr}-01-01",
                    "period_end": f"{yr}-12-31",
                    "frequency": "Annual",
                    "reported_cases": cases,
                    "confirmed_cases": cases,
                    "suspected_cases": None,
                    "reported_deaths": deaths,
                    "outbreak_event_count": 1,
                    "reporting_status": "ANNUAL_OFFICIAL_SERIES",
                    "reporting_completeness": "CBHI_NATIONAL_HEALTH_PROFILE",
                    "source_count": 1,
                    "independent_source_count": 1,
                    "temperature": 25.8,
                    "rainfall": 1180.0,
                    "humidity": 62.0,
                    "historical_seasonal_context": "Summer & Monsoon Water Contamination Risk",
                    "data_quality_status": "OFFICIAL_SURVEILLANCE_VERIFIED",
                    "source_provenance": "CBHI National Health Profile & IDSP Annual Series (2015-2024)",
                })

        # ---------------------------------------------------------------------
        # 5. ACUTE DIARRHOEAL DISEASE (ADD)
        # ---------------------------------------------------------------------
        add_ann_path = self.raw_dir / "add_india_cbhi_2015_2024.csv"
        if add_ann_path.exists():
            df_add = pd.read_csv(add_ann_path)
            for _, r in df_add.iterrows():
                yr = int(r["year"])
                episodes = int(r["reported_episodes"])
                deaths = int(r.get("reported_deaths", 0))
                records.append({
                    "disease_id": "acute_diarrhoeal_disease",
                    "canonical_disease": "Acute Diarrhoeal Disease",
                    "geography_id": "india_national",
                    "country": "India",
                    "state": None,
                    "district": None,
                    "latitude": 20.5937,
                    "longitude": 78.9629,
                    "period_start": f"{yr}-01-01",
                    "period_end": f"{yr}-12-31",
                    "frequency": "Annual",
                    "reported_cases": episodes,
                    "confirmed_cases": None,
                    "suspected_cases": episodes,
                    "reported_deaths": deaths,
                    "outbreak_event_count": 1,
                    "reporting_status": "ANNUAL_OFFICIAL_SERIES",
                    "reporting_completeness": "CBHI_NATIONAL_HEALTH_PROFILE",
                    "source_count": 1,
                    "independent_source_count": 1,
                    "temperature": 25.8,
                    "rainfall": 1180.0,
                    "humidity": 62.0,
                    "historical_seasonal_context": "Pre-Monsoon & Flood Seasonal Baseline",
                    "data_quality_status": "OFFICIAL_SURVEILLANCE_VERIFIED",
                    "source_provenance": "CBHI National Health Profile India (2015-2024)",
                })

        # ---------------------------------------------------------------------
        # 6. JAPANESE ENCEPHALITIS (JE)
        # ---------------------------------------------------------------------
        je_ann_path = self.raw_dir / "japanese_encephalitis_india_ncvbdc_2015_2024.csv"
        if je_ann_path.exists():
            df_je = pd.read_csv(je_ann_path)
            for _, r in df_je.iterrows():
                yr = int(r["year"])
                cases = int(r["reported_cases"])
                deaths = int(r.get("reported_deaths", 0))
                records.append({
                    "disease_id": "japanese_encephalitis",
                    "canonical_disease": "Japanese Encephalitis",
                    "geography_id": "india_national",
                    "country": "India",
                    "state": None,
                    "district": None,
                    "latitude": 20.5937,
                    "longitude": 78.9629,
                    "period_start": f"{yr}-01-01",
                    "period_end": f"{yr}-12-31",
                    "frequency": "Annual",
                    "reported_cases": cases,
                    "confirmed_cases": cases,
                    "suspected_cases": None,
                    "reported_deaths": deaths,
                    "outbreak_event_count": 1,
                    "reporting_status": "ANNUAL_OFFICIAL_SERIES",
                    "reporting_completeness": "NCVBDC_NATIONAL_REPORT",
                    "source_count": 1,
                    "independent_source_count": 1,
                    "temperature": 25.8,
                    "rainfall": 1180.0,
                    "humidity": 62.0,
                    "historical_seasonal_context": "Paddy Cultivation / Ardeid Vector Transmission",
                    "data_quality_status": "OFFICIAL_SURVEILLANCE_VERIFIED",
                    "source_provenance": "NCVBDC Japanese Encephalitis Annual Situation (2015-2024)",
                })

        # ---------------------------------------------------------------------
        # 7. LEPTOSPIROSIS
        # ---------------------------------------------------------------------
        lepto_ann_path = self.raw_dir / "leptospirosis_india_ncdc_2018_2024.csv"
        if lepto_ann_path.exists():
            df_lepto = pd.read_csv(lepto_ann_path)
            for _, r in df_lepto.iterrows():
                yr = int(r["year"])
                cases = int(r["reported_cases"])
                deaths = int(r.get("reported_deaths", 0))
                records.append({
                    "disease_id": "leptospirosis",
                    "canonical_disease": "Leptospirosis",
                    "geography_id": "india_national",
                    "country": "India",
                    "state": None,
                    "district": None,
                    "latitude": 20.5937,
                    "longitude": 78.9629,
                    "period_start": f"{yr}-01-01",
                    "period_end": f"{yr}-12-31",
                    "frequency": "Annual",
                    "reported_cases": cases,
                    "confirmed_cases": cases,
                    "suspected_cases": None,
                    "reported_deaths": deaths,
                    "outbreak_event_count": 1,
                    "reporting_status": "ANNUAL_OFFICIAL_SERIES",
                    "reporting_completeness": "NCDC_ZOONOSIS_PROGRAMME",
                    "source_count": 1,
                    "independent_source_count": 1,
                    "temperature": 25.8,
                    "rainfall": 1180.0,
                    "humidity": 62.0,
                    "historical_seasonal_context": "Post-Flooding Rodent Urine Transmission",
                    "data_quality_status": "OFFICIAL_SURVEILLANCE_VERIFIED",
                    "source_provenance": "NCDC National Zoonosis Programme Situation (2018-2024)",
                })

        # ---------------------------------------------------------------------
        # 8. SCRUB TYPHUS
        # ---------------------------------------------------------------------
        scrub_ann_path = self.raw_dir / "scrub_typhus_india_ncdc_2018_2024.csv"
        if scrub_ann_path.exists():
            df_scrub = pd.read_csv(scrub_ann_path)
            for _, r in df_scrub.iterrows():
                yr = int(r["year"])
                cases = int(r["reported_cases"])
                deaths = int(r.get("reported_deaths", 0))
                records.append({
                    "disease_id": "scrub_typhus",
                    "canonical_disease": "Scrub Typhus",
                    "geography_id": "india_national",
                    "country": "India",
                    "state": None,
                    "district": None,
                    "latitude": 20.5937,
                    "longitude": 78.9629,
                    "period_start": f"{yr}-01-01",
                    "period_end": f"{yr}-12-31",
                    "frequency": "Annual",
                    "reported_cases": cases,
                    "confirmed_cases": cases,
                    "suspected_cases": None,
                    "reported_deaths": deaths,
                    "outbreak_event_count": 1,
                    "reporting_status": "ANNUAL_OFFICIAL_SERIES",
                    "reporting_completeness": "NCDC_RICKETTSIA_SURVEILLANCE",
                    "source_count": 1,
                    "independent_source_count": 1,
                    "temperature": 25.8,
                    "rainfall": 1180.0,
                    "humidity": 62.0,
                    "historical_seasonal_context": "Post-Monsoon Mite Vector Activity",
                    "data_quality_status": "OFFICIAL_SURVEILLANCE_VERIFIED",
                    "source_provenance": "NCDC Rickettsial Diseases Surveillance Reports (2018-2024)",
                })

        # ---------------------------------------------------------------------
        # 9. INTEGRATE REAL DISTRICT-WEEK OBSERVATIONS FROM SQLITE FUSED EVENTS
        # ---------------------------------------------------------------------
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        fe_rows = cursor.execute("""
            SELECT fused_event_id, canonical_disease, disease_key, primary_origin,
                   earliest_time, latest_time, total_cases, total_deaths,
                   supporting_observation_count, json_data, status
            FROM fused_events
            WHERE status = 'active'
        """).fetchall()
        conn.close()

        for fe in fe_rows:
            d_name = fe["canonical_disease"]
            resolved = resolve_priority_disease(d_name)
            if not resolved:
                continue

            # Parse JSON data
            try:
                fe_json = json.loads(fe["json_data"]) if fe["json_data"] else {}
            except Exception:
                fe_json = {}

            if fe_json.get("is_test_fixture"):
                continue

            loc_data = fe_json.get("canonical_location") or {}
            st_name = loc_data.get("state") if isinstance(loc_data, dict) else None
            dist_name = (loc_data.get("district") or loc_data.get("normalized_name")) if isinstance(loc_data, dict) else str(loc_data)
            lat = loc_data.get("latitude") if isinstance(loc_data, dict) else None
            lon = loc_data.get("longitude") if isinstance(loc_data, dict) else None
            if not lat or not lon:
                lat, lon = 20.5937, 78.9629

            p_start = fe_json.get("event_window_start") or fe["earliest_time"] or "2026-08-01"
            p_end = fe_json.get("event_window_end") or fe["latest_time"] or p_start
            temp, rain, hum, season = _get_climate_for_period(str(p_start), str(p_end), lat)

            geo_id = f"district_{str(dist_name).lower().replace(' ', '_')}" if dist_name else "unspecified_district"
            cases = int(fe["total_cases"] or 0)
            deaths = int(fe["total_deaths"] or 0)

            records.append({
                "disease_id": resolved.canonical_id,
                "canonical_disease": resolved.canonical_name,
                "geography_id": geo_id,
                "country": "India",
                "state": st_name,
                "district": dist_name,
                "latitude": lat,
                "longitude": lon,
                "period_start": p_start[:10],
                "period_end": p_end[:10],
                "frequency": "Weekly",
                "reported_cases": cases,
                "confirmed_cases": cases,
                "suspected_cases": None,
                "reported_deaths": deaths,
                "outbreak_event_count": 1,
                "reporting_status": "IDSP_WEEKLY_OUTBREAK_SURVEILLANCE",
                "reporting_completeness": "INVESTIGATED_OUTBREAK_REPORT",
                "source_count": fe["supporting_observation_count"] or 1,
                "independent_source_count": 1,
                "temperature": temp,
                "rainfall": rain,
                "humidity": hum,
                "historical_seasonal_context": season,
                "data_quality_status": "IDSP_FIELD_EPIDEMIOLOGICAL_INVESTIGATION",
                "source_provenance": "Integrated Disease Surveillance Programme (IDSP) Weekly Reports",
            })

        df_panel = pd.DataFrame(records)
        PANEL_CSV_PATH.parent.mkdir(parents=True, exist_ok=True)
        df_panel.to_csv(PANEL_CSV_PATH, index=False)
        try:
            df_panel.to_parquet(PANEL_PARQUET_PATH, index=False)
        except Exception as e:
            logger.warning("Could not save parquet: %s", e)

        logger.info(
            "Built Spatiotemporal Surveillance Panel: %d rows across %d diseases.",
            len(df_panel),
            df_panel["canonical_disease"].nunique(),
        )
        return df_panel


def get_spatiotemporal_panel(force_rebuild: bool = False) -> pd.DataFrame:
    """Returns the authoritative cached or freshly rebuilt spatiotemporal panel."""
    if not force_rebuild and PANEL_CSV_PATH.exists():
        try:
            return pd.read_csv(PANEL_CSV_PATH)
        except Exception:
            pass
    builder = SpatiotemporalSurveillancePanel()
    return builder.build_panel()

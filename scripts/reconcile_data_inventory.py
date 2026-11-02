import pandas as pd
import json
from pathlib import Path

# 1. OpenDengue Spatial (Annual State-level)
spatial_path = Path("data/raw/opendengue_india_spatial.csv")
df_spatial = pd.read_csv(spatial_path)
print("=" * 80)
print(f"1. OPENDENGUE SPATIAL (ANNUAL)")
print(f"File: {spatial_path} ({spatial_path.stat().st_size:,} bytes)")
print(f"Total Rows: {len(df_spatial)}")
print(f"Columns: {list(df_spatial.columns)}")
print(f"Unique Adm 1 Names (States/UTs): {df_spatial['adm_1_name'].nunique()}")

years = sorted(df_spatial['Year'].unique())
print(f"Year Range: {years[0]} to {years[-1]} (Total calendar span: {years[-1] - years[0] + 1} years)")
print(f"Distinct Years in Data ({len(years)}): {years}")
all_expected_years = set(range(years[0], years[-1] + 1))
missing_years = sorted(list(all_expected_years - set(years)))
print(f"Missing Years Across Dataset: {missing_years}")

# Check 8 benchmark states
benchmark_states = ["DELHI", "KARNATAKA", "KERALA", "MAHARASHTRA", "TAMIL NADU", "GUJARAT", "RAJASTHAN", "WEST BENGAL"]
print("\nObservations per benchmark state:")
for state in benchmark_states:
    sub = df_spatial[df_spatial['adm_1_name'].str.upper() == state]
    st_years = sorted(sub['Year'].unique())
    st_missing = sorted(list(all_expected_years - set(st_years)))
    print(f"  {state:<15}: {len(sub)} rows | {len(st_years)} years ({st_years[0]}-{st_years[-1]}) | Missing: {st_missing}")

# Check duplicate rows
dup_spatial = df_spatial.duplicated(subset=['Year', 'adm_1_name']).sum()
print(f"Duplicate (Year, State) tuples: {dup_spatial}")

# 2. OpenDengue Temporal (Monthly National/State)
temporal_path = Path("data/raw/opendengue_india_temporal.csv")
df_temp = pd.read_csv(temporal_path)
print("\n" + "=" * 80)
print(f"2. OPENDENGUE TEMPORAL (MONTHLY)")
print(f"File: {temporal_path} ({temporal_path.stat().st_size:,} bytes)")
print(f"Total Rows: {len(df_temp)}")
print(f"Columns: {list(df_temp.columns)}")

df_temp['Year_num'] = pd.to_numeric(df_temp['Year'], errors='coerce')
df_temp['start_dt'] = pd.to_datetime(df_temp['calendar_start_date'], errors='coerce')

dates = sorted(df_temp['start_dt'].dropna().unique())
print(f"Date range: {dates[0]} to {dates[-1]}")
print(f"Total distinct monthly starts: {len(dates)}")

# Check 2024-2025 monthly series
sub_2024_2025 = df_temp[df_temp['start_dt'] >= '2024-01-01']
print(f"\nObservations between Jan 2024 and Jan 2025: {len(sub_2024_2025)} rows")
months_2024_2025 = sorted(sub_2024_2025['calendar_start_date'].unique())
print("Unique calendar_start_dates in 2024-2025 span:")
for m in months_2024_2025:
    print(f"  {m}")

# National vs Subnational rows in temporal CSV
print("\nUnique Admin Levels in Temporal CSV:")
print(f"  adm_0_name unique: {df_temp['adm_0_name'].unique()}")
print(f"  adm_1_name unique count: {df_temp['adm_1_name'].nunique()}")
print(f"  adm_2_name unique count: {df_temp['adm_2_name'].nunique()}")

# 3. IDSP Bulletin PDF
print("\n" + "=" * 80)
print(f"3. IDSP OFFICIAL BULLETIN (PDF)")
pdf_path = Path("data/raw/bulletins/idsp_2026_w1.pdf")
print(f"File: {pdf_path} ({pdf_path.stat().st_size:,} bytes)")
# Check extracted rows from IDSP in SQLite database
import sqlite3
conn = sqlite3.connect("data/surveillance_store.sqlite")
cur = conn.cursor()
idsp_docs = cur.execute("SELECT document_id, title, text, publication_timestamp FROM documents WHERE source_id LIKE '%idsp%'").fetchall()
print(f"IDSP Documents in SQLite: {len(idsp_docs)}")
for doc in idsp_docs[:3]:
    print(f"  Doc ID: {doc[0]} | Title: {doc[1][:60]}... | Pub: {doc[3]}")

# 4. Check disease coverage in SQLite fused_events
print("\n" + "=" * 80)
print("4. ALL 8 DISEASES IN SQLITE STORE")
diseases = [
    "dengue", "malaria", "chikungunya", "leptospirosis", 
    "cholera", "acute diarrheal disease", "japanese encephalitis", "scrub typhus"
]
for d in diseases:
    fused_cnt = cur.execute("SELECT COUNT(*) FROM fused_events WHERE LOWER(canonical_disease) LIKE ?", (f"%{d}%",)).fetchone()[0]
    bins_cnt = cur.execute("SELECT COUNT(*) FROM time_bins WHERE LOWER(series_key) LIKE ?", (f"%{d}%",)).fetchone()[0]
    alerts_cnt = cur.execute("SELECT COUNT(*) FROM alerts WHERE LOWER(disease_key) LIKE ?", (f"%{d}%",)).fetchone()[0]
    print(f"  {d:<26}: {fused_cnt} fused events | {bins_cnt} time bins | {alerts_cnt} alerts")

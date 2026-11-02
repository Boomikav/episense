import sqlite3
import json

db_path = "data/episense.db"
conn = sqlite3.connect(db_path)
conn.row_factory = sqlite3.Row
c = conn.cursor()

print("=== RAICHUR RECORDS ===")
c.execute("""
    SELECT observation_id, reporting_week, original_disease_label, canonical_disease, 
           state, district, location_raw, case_count, death_count, narrative, metadata_json
    FROM surveillance_observations
    WHERE district LIKE '%Raichur%'
""")
for r in c.fetchall():
    print(f"ID: {r['observation_id']}, Wk: {r['reporting_week']}, Orig: {r['original_disease_label']}, Canon: {r['canonical_disease']}")
    print(f"Location: {r['location_raw']}, Cases: {r['case_count']}, Deaths: {r['death_count']}")
    print(f"Narrative: {r['narrative']}")
    print(f"Metadata: {r['metadata_json']}")
    print("-" * 50)

print("\n=== KOTTAYAM MUMPS RECORDS ===")
c.execute("""
    SELECT observation_id, reporting_week, original_disease_label, canonical_disease, 
           state, district, location_raw, case_count, death_count, narrative, metadata_json
    FROM surveillance_observations
    WHERE district LIKE '%Kottayam%' AND (original_disease_label LIKE '%Mumps%' OR canonical_disease LIKE '%Mumps%')
""")
for r in c.fetchall():
    print(f"ID: {r['observation_id']}, Wk: {r['reporting_week']}, Orig: {r['original_disease_label']}, Canon: {r['canonical_disease']}")
    print(f"Location: {r['location_raw']}, Cases: {r['case_count']}, Deaths: {r['death_count']}")
    print(f"Narrative: {r['narrative']}")
    print(f"Metadata: {r['metadata_json']}")
    print("-" * 50)

print("\n=== KOZHIKODE MPOX RECORDS ===")
c.execute("""
    SELECT observation_id, reporting_week, original_disease_label, canonical_disease, 
           state, district, location_raw, case_count, death_count, narrative, metadata_json
    FROM surveillance_observations
    WHERE district LIKE '%Kozhikode%' AND (original_disease_label LIKE '%Mpox%' OR canonical_disease LIKE '%Mpox%')
""")
for r in c.fetchall():
    print(f"ID: {r['observation_id']}, Wk: {r['reporting_week']}, Orig: {r['original_disease_label']}, Canon: {r['canonical_disease']}")
    print(f"Location: {r['location_raw']}, Cases: {r['case_count']}, Deaths: {r['death_count']}")
    print(f"Narrative: {r['narrative']}")
    print(f"Metadata: {r['metadata_json']}")
    print("-" * 50)

print("\n=== FIROZEPUR LEPTOSPIROSIS RECORDS ===")
c.execute("""
    SELECT observation_id, reporting_week, original_disease_label, canonical_disease, 
           state, district, location_raw, case_count, death_count, narrative, metadata_json
    FROM surveillance_observations
    WHERE district LIKE '%Firozepur%' AND canonical_disease LIKE '%Leptospirosis%'
""")
for r in c.fetchall():
    print(f"ID: {r['observation_id']}, Wk: {r['reporting_week']}, Orig: {r['original_disease_label']}, Canon: {r['canonical_disease']}")
    print(f"Location: {r['location_raw']}, Cases: {r['case_count']}, Deaths: {r['death_count']}")
    print(f"Narrative: {r['narrative']}")
    print(f"Metadata: {r['metadata_json']}")
    print("-" * 50)

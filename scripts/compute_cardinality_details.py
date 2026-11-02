import sqlite3
import json
import sys
from collections import Counter

sys.path.insert(0, "src")
from episense.taxonomy.priority import PRIORITY_CANONICAL_NAMES, resolve_priority_disease

conn = sqlite3.connect("data/surveillance_store.sqlite")
cur = conn.cursor()

rows = cur.execute("""
    SELECT document_id, metadata_json, text
    FROM documents
    WHERE source_id = 'idsp_bulletin_feed'
""").fetchall()

priority_counts = Counter()
non_priority_counts = Counter()

priority_records = []
non_priority_records = []

for doc_id, meta_json, text in rows:
    meta = json.loads(meta_json) if meta_json else {}
    raw_dis = meta.get("disease", "").strip()
    c_meta = resolve_priority_disease(raw_dis) or resolve_priority_disease(meta.get("canonical_disease", ""))
    
    if c_meta:
        priority_counts[c_meta.canonical_name] += 1
        priority_records.append((doc_id, meta, text, c_meta.canonical_name))
    else:
        non_priority_counts[raw_dis] += 1
        non_priority_records.append((doc_id, meta, text, raw_dis))

print("=== PRIORITY DISEASE OBSERVATIONS ===")
total_prio = 0
for dis in PRIORITY_CANONICAL_NAMES:
    cnt = priority_counts[dis]
    total_prio += cnt
    print(f"  {dis}: {cnt}")
print(f"TOTAL PRIORITY OBSERVATIONS: {total_prio}")

print("\n=== NON-PRIORITY OBSERVATIONS ===")
total_non_prio = sum(non_priority_counts.values())
print(f"TOTAL NON-PRIORITY OBSERVATIONS: {total_non_prio}")
print("Top non-priority diseases:")
for dis, cnt in non_priority_counts.most_common(15):
    print(f"  {dis}: {cnt}")

print("\n=== TOTAL IDSP OBSERVATIONS ===")
print(f"Total: {total_prio + total_non_prio}")

# Leptospirosis inspection
lepto_recs = [r for r in priority_records if r[3] == "Leptospirosis"]
print(f"\nLeptospirosis observations count: {len(lepto_recs)}")
for doc_id, meta, text, cname in lepto_recs:
    print(f"  UID: {meta.get('unique_id')} | Wk: {meta.get('week')} | Loc: {meta.get('district')}, {meta.get('state')} | Subdist: {meta.get('sub_district')} | Cases: {meta.get('cases')}")

conn.close()

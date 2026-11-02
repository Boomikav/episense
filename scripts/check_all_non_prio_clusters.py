import sqlite3
import json
import sys
from collections import defaultdict

sys.path.insert(0, "src")
from episense.taxonomy.priority import resolve_priority_disease

conn = sqlite3.connect("data/surveillance_store.sqlite")
cur = conn.cursor()

rows = cur.execute("""
    SELECT document_id, metadata_json, text
    FROM documents
    WHERE source_id = 'idsp_bulletin_feed'
""").fetchall()

print(f"Total documents: {len(rows)}")

records = []
for doc_id, m_str, text in rows:
    meta = json.loads(m_str) if m_str else {}
    raw_dis = (meta.get("disease") or "").strip()
    c_meta = resolve_priority_disease(raw_dis) or resolve_priority_disease(meta.get("canonical_disease") or "")
    
    uid = meta.get("unique_id", "")
    parts = uid.split("/")
    week = int(parts[3]) if len(parts) >= 4 and parts[3].isdigit() else None
    
    records.append({
        "doc_id": doc_id,
        "uid": uid,
        "week": week,
        "state": (meta.get("state") or "").strip(),
        "district": (meta.get("district") or "").strip(),
        "sub_district": (meta.get("sub_district") or "").strip(),
        "raw_disease": raw_dis,
        "canonical_disease": c_meta.canonical_name if c_meta else raw_dis,
        "is_priority": c_meta is not None,
        "cases": meta.get("cases"),
        "deaths": meta.get("deaths"),
        "text": text or "",
    })

prio = [r for r in records if r["is_priority"]]
non_prio = [r for r in records if not r["is_priority"]]

print(f"Priority count: {len(prio)}")
print(f"Non-priority count: {len(non_prio)}")

# Check any groups sharing state, district, disease, sub_district/village
by_geo_dis = defaultdict(list)
for r in non_prio:
    k = (r["state"].lower(), r["district"].lower(), r["raw_disease"].lower())
    by_geo_dis[k].append(r)

print("\n--- Non-Priority Multi-Observation Buckets (state, district, disease) ---")
for k, recs in by_geo_dis.items():
    if len(recs) > 1:
        print(f"Group {k}: {len(recs)} records")
        for r in recs:
            print(f"   UID: {r['uid']}, Sub: {r['sub_district']}, Cases: {r['cases']}, Text snippet: {r['text'][:80]}")

conn.close()

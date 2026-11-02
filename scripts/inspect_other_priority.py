import sys
import json
import sqlite3
import re
from collections import defaultdict

sys.path.insert(0, "src")
from episense.taxonomy.priority import PRIORITY_CANONICAL_NAMES, resolve_priority_disease

conn = sqlite3.connect("data/surveillance_store.sqlite")
cur = conn.cursor()

rows = cur.execute("""
    SELECT metadata_json, text
    FROM documents
    WHERE source_id = 'idsp_bulletin_feed'
""").fetchall()

recs = []
for meta_json, text in rows:
    meta = json.loads(meta_json) if meta_json else {}
    raw_dis = meta.get("disease", "").strip()
    c_meta = resolve_priority_disease(raw_dis) or resolve_priority_disease(meta.get("canonical_disease", ""))
    if not c_meta:
        continue
    uid = meta.get("unique_id") or ""
    parts = uid.split("/")
    week = int(parts[3]) if len(parts) >= 4 and parts[3].isdigit() else None
    
    recs.append({
        "uid": uid,
        "week": week,
        "state": meta.get("state", "").strip(),
        "district": meta.get("district", "").strip(),
        "disease": c_meta.canonical_name,
        "cases": meta.get("cases"),
        "deaths": meta.get("deaths"),
        "text": text,
    })

for target_dis in ["Malaria", "Leptospirosis", "Cholera", "Chikungunya"]:
    dis_recs = [r for r in recs if r["disease"] == target_dis]
    print(f"\n=======================================================")
    print(f"{target_dis.upper()}: {len(dis_recs)} observations")
    print(f"=======================================================")
    by_geo = defaultdict(list)
    for r in dis_recs:
        by_geo[(r["state"].lower(), r["district"].lower())].append(r)
    multi_geo = {k: v for k, v in by_geo.items() if len(v) > 1}
    print(f"Districts with multiple observations: {len(multi_geo)}")
    for (st, dt), d_recs in multi_geo.items():
        print(f"  {dt.title()}, {st.title()}: {len(d_recs)} obs across weeks {[r['week'] for r in d_recs]}")
        for r in d_recs:
            print(f"    Wk {r['week']} | UID: {r['uid']} | Cases: {r['cases']} | Text snippet: {r['text'][:120]}...")

conn.close()

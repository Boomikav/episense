import sqlite3
import json
import re
from collections import defaultdict

conn = sqlite3.connect("data/surveillance_store.sqlite")
cur = conn.cursor()

rows = cur.execute("""
    SELECT document_id, metadata_json, text
    FROM documents
    WHERE source_id = 'idsp_bulletin_feed'
""").fetchall()

import sys
sys.path.insert(0, "src")
from episense.taxonomy.priority import resolve_priority_disease

records = []
for doc_id, meta_json, text in rows:
    meta = json.loads(meta_json) if meta_json else {}
    raw_dis = meta.get("disease", "").strip()
    c_meta = resolve_priority_disease(raw_dis) or resolve_priority_disease(meta.get("canonical_disease", ""))
    
    uid = meta.get("unique_id", "")
    parts = uid.split("/")
    week = int(parts[3]) if len(parts) >= 4 and parts[3].isdigit() else None
    
    raw_text = text or ""
    v_match = re.search(r"Village[:\s]+([^,\n]+)", raw_text, re.IGNORECASE)
    village = v_match.group(1).strip() if v_match else ""
    
    sd_match = re.search(r"Sub-?\s*District[:\s]+([^,\n]+)", raw_text, re.IGNORECASE)
    sub_dist = sd_match.group(1).strip() if sd_match else (meta.get("sub_district") or "")

    sd_date = meta.get("event_start")
    if not sd_date:
        d_match = re.search(r"Date of start of outbreak[:\s]+(\d{2}-\d{2}-\d{4})", raw_text, re.IGNORECASE)
        sd_date = d_match.group(1).strip() if d_match else None

    records.append({
        "doc_id": doc_id,
        "uid": uid,
        "week": week,
        "state": meta.get("state", "").strip(),
        "district": meta.get("district", "").strip(),
        "sub_district": sub_dist,
        "village": village,
        "start_date": sd_date,
        "raw_disease": raw_dis,
        "is_priority": c_meta is not None,
        "canonical_disease": c_meta.canonical_name if c_meta else raw_dis,
        "cases": meta.get("cases"),
        "deaths": meta.get("deaths"),
        "text": raw_text,
    })

non_prio_records = [r for r in records if not r["is_priority"]]
print(f"Total non-priority records: {len(non_prio_records)}")

# Group by (state, district, disease)
by_geo_dis = defaultdict(list)
for r in non_prio_records:
    st_k = r["state"].lower().strip()
    dt_k = r["district"].lower().strip()
    ds_k = r["raw_disease"].lower().strip()
    by_geo_dis[(st_k, dt_k, ds_k)].append(r)

multi_groups = {k: v for k, v in by_geo_dis.items() if len(v) > 1}
print(f"Total multi-record non-priority geo-disease buckets: {len(multi_groups)}")

# Inspect the candidate groups:
# 1. Chickenpox Shirishbani
# 2. Mumps Kottayam Nedumkunnam
# 3. Raichur Food Poisoning
# 4. Mpox Kozhikode
for k, v in multi_groups.items():
    if len(v) >= 2:
        # Check if same village or follow-up
        vils = [r["village"] for r in v if r["village"]]
        dates = [r["start_date"] for r in v if r["start_date"]]
        wks = [r["week"] for r in v]
        txt = " ".join(r["text"] for r in v)
        if "shirishbani" in txt.lower() or "nedumkunnam" in txt.lower() or "sindhnur" in txt.lower() or "mpox" in k[2]:
            print("\nCandidate Multi Group:", k, f"({len(v)} records)")
            for r in v:
                print(f"  UID: {r['uid']} | Wk: {r['week']} | Date: {r['start_date']} | Vil: {r['village']} | Sub: {r['sub_district']} | Cases: {r['cases']}")

conn.close()

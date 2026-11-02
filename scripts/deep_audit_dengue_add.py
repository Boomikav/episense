import sys
import json
import sqlite3
import re
from collections import defaultdict

conn = sqlite3.connect("data/surveillance_store.sqlite")
cur = conn.cursor()

rows = cur.execute("""
    SELECT metadata_json, text
    FROM documents
    WHERE source_id = 'idsp_bulletin_feed'
""").fetchall()

for dis_name in ["Dengue", "Acute Diarrhoeal Disease"]:
    print("=" * 80)
    print(f"DEEP AUDIT: {dis_name.upper()}")
    print("=" * 80)
    
    recs = []
    for meta_json, text in rows:
        meta = json.loads(meta_json) if meta_json else {}
        d = meta.get("disease", "").strip()
        c = meta.get("canonical_disease", "").strip()
        if dis_name.lower() in d.lower() or dis_name.lower() in c.lower():
            uid = meta.get("unique_id") or ""
            parts = uid.split("/")
            week = int(parts[3]) if len(parts) >= 4 and parts[3].isdigit() else None
            
            raw_text = text or ""
            v_match = re.search(r"Village[:\s]+([^,\n]+)", raw_text, re.IGNORECASE)
            village = v_match.group(1).strip() if v_match else ""
            
            sd_match = re.search(r"Sub-?\s*District[:\s]+([^,\n]+)", raw_text, re.IGNORECASE)
            sub_dist = sd_match.group(1).strip() if sd_match else (meta.get("sub_district") or "")
            
            d_match = re.search(r"Date of start of outbreak[:\s]+(\d{2}-\d{2}-\d{4})", raw_text, re.IGNORECASE)
            start_date = d_match.group(1).strip() if d_match else meta.get("event_start")
            
            recs.append({
                "uid": uid,
                "week": week,
                "state": meta.get("state", "").strip(),
                "district": meta.get("district", "").strip(),
                "sub_district": sub_dist,
                "village": village,
                "start_date": start_date,
                "cases": meta.get("cases"),
                "deaths": meta.get("deaths"),
                "status": meta.get("status", "").strip(),
                "text": raw_text,
            })
            
    print(f"Total records found: {len(recs)}")
    
    # Check for same village
    by_vil = defaultdict(list)
    for r in recs:
        v_norm = re.sub(r"[^a-z0-9]", "", r["village"].lower())
        st_norm = re.sub(r"[^a-z0-9]", "", r["state"].lower())
        dt_norm = re.sub(r"[^a-z0-9]", "", r["district"].lower())
        if len(v_norm) > 3:
            by_vil[(st_norm, dt_norm, v_norm)].append(r)
            
    multi_vil = {k: v for k, v in by_vil.items() if len(v) > 1}
    print(f"Village matches (same state, district, village): {len(multi_vil)}")
    for k, v_list in multi_vil.items():
        print(f"\n  Village key {k}: {len(v_list)} observations")
        for r in v_list:
            print(f"    Wk {r['week']:2d} | UID: {r['uid']} | Start: {r['start_date']} | Cases: {r['cases']} | Status: {r['status']}")
            print(f"      Text: {r['text'][:130]}...")

conn.close()

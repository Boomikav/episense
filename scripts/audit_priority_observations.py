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
    SELECT document_id, title, metadata_json, text, publication_timestamp
    FROM documents
    WHERE source_id = 'idsp_bulletin_feed'
""").fetchall()

priority_set = {p.lower() for p in PRIORITY_CANONICAL_NAMES}

priority_recs = []
for doc_id, title, meta_json, text, pub_ts in rows:
    meta = json.loads(meta_json) if meta_json else {}
    uid = meta.get("unique_id") or ""
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

    # Check priority
    raw_dis = meta.get("disease", "").strip()
    c_meta = resolve_priority_disease(raw_dis) or resolve_priority_disease(meta.get("canonical_disease", ""))
    if not c_meta:
        continue

    def parse_int_or_none(val):
        if val is None or val == "" or str(val).lower() in ("not reported", "none", "null"):
            return None
        try:
            return int(str(val).replace(",", "").strip())
        except ValueError:
            return None

    priority_recs.append({
        "doc_id": doc_id,
        "uid": uid,
        "week": week,
        "state": meta.get("state", "").strip(),
        "district": meta.get("district", "").strip(),
        "sub_district": sub_dist,
        "village": village,
        "start_date": sd_date,
        "raw_disease": raw_dis,
        "canonical_disease": c_meta.canonical_name,
        "cases": parse_int_or_none(meta.get("cases")),
        "deaths": parse_int_or_none(meta.get("deaths")),
        "status": meta.get("status", "Under Surveillance").strip(),
        "sample_count": parse_int_or_none(meta.get("sample_count")),
        "positive_sample_count": parse_int_or_none(meta.get("positive_sample_count")),
        "page_number": meta.get("page_number", 1),
        "pdf_sha256": meta.get("pdf_sha256", ""),
        "text": raw_text,
    })

print(f"Total Priority Records: {len(priority_recs)}")

# Group by canonical disease
by_dis = defaultdict(list)
for r in priority_recs:
    by_dis[r["canonical_disease"]].append(r)

for dis in PRIORITY_CANONICAL_NAMES:
    recs = by_dis.get(dis, [])
    print(f"\n=======================================================")
    print(f"DISEASE: {dis} ({len(recs)} observations)")
    print(f"=======================================================")
    
    # Group by (state, district)
    by_geo = defaultdict(list)
    for r in recs:
        by_geo[(r["state"].lower(), r["district"].lower())].append(r)
        
    multi_geo = {k: v for k, v in by_geo.items() if len(v) > 1}
    print(f"  Districts with multiple observations: {len(multi_geo)}")
    
    for (st, dt), geo_recs in multi_geo.items():
        print(f"\n  --- District: {dt.title()}, {st.title()} ({len(geo_recs)} records) ---")
        for gr in sorted(geo_recs, key=lambda x: (x["week"] or 0, x["start_date"] or "")):
            v_str = gr['village'] if gr['village'] else "No village stated"
            sd_str = gr['sub_district'] if gr['sub_district'] else "No subdist stated"
            print(f"    Wk {gr['week']:2d} | UID: {gr['uid']} | Start: {gr['start_date']} | Cases: {gr['cases']} | Deaths: {gr['deaths']} | Loc: {v_str} ({sd_str}) | Status: {gr['status']}")
            # snippet of comments
            lines = gr["text"].split("\n\n")
            if len(lines) > 1:
                print(f"      Comments: {lines[1][:120]}...")

conn.close()

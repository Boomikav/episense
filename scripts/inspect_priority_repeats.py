import sys
import json
import sqlite3
import re
from collections import defaultdict
from datetime import datetime

sys.path.insert(0, "src")
from episense.taxonomy.priority import PRIORITY_CANONICAL_NAMES, resolve_priority_disease

conn = sqlite3.connect("data/surveillance_store.sqlite")
cur = conn.cursor()

rows = cur.execute("""
    SELECT document_id, title, metadata_json, text
    FROM documents
    WHERE source_id = 'idsp_bulletin_feed'
""").fetchall()

recs = []
for doc_id, title, meta_json, text in rows:
    meta = json.loads(meta_json) if meta_json else {}
    raw_dis = meta.get("disease", "").strip()
    c_meta = resolve_priority_disease(raw_dis) or resolve_priority_disease(meta.get("canonical_disease", ""))
    if not c_meta:
        continue
        
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

    def parse_int_or_none(val):
        if val is None or val == "" or str(val).lower() in ("not reported", "none", "null"):
            return None
        try:
            return int(str(val).replace(",", "").strip())
        except ValueError:
            return None

    recs.append({
        "uid": uid,
        "week": week,
        "state": meta.get("state", "").strip(),
        "district": meta.get("district", "").strip(),
        "sub_district": sub_dist,
        "village": village,
        "start_date": sd_date,
        "disease": c_meta.canonical_name,
        "raw_disease": raw_dis,
        "cases": parse_int_or_none(meta.get("cases")),
        "deaths": parse_int_or_none(meta.get("deaths")),
        "status": meta.get("status", "Under Surveillance").strip(),
        "sample_count": parse_int_or_none(meta.get("sample_count")),
        "positive_sample_count": parse_int_or_none(meta.get("positive_sample_count")),
        "text": raw_text,
    })

print(f"Total priority records: {len(recs)}")

# Inspect by each of the 8 diseases
for target_dis in PRIORITY_CANONICAL_NAMES:
    dis_recs = [r for r in recs if r["disease"] == target_dis]
    print("\n" + "=" * 80)
    print(f"AUDITING PRIORITY DISEASE: {target_dis.upper()} ({len(dis_recs)} observations)")
    print("=" * 80)
    
    # Check pairwise within the same (state, district)
    by_dist = defaultdict(list)
    for r in dis_recs:
        by_dist[(r["state"].lower(), r["district"].lower())].append(r)
        
    candidates = []
    for (st, dt), d_recs in by_dist.items():
        if len(d_recs) < 2:
            continue
        # Compare all pairs
        for i in range(len(d_recs)):
            for j in range(i + 1, len(d_recs)):
                r1 = d_recs[i]
                r2 = d_recs[j]
                
                v1 = re.sub(r"[^a-z0-9]", "", r1["village"].lower())
                v2 = re.sub(r"[^a-z0-9]", "", r2["village"].lower())
                same_vil = bool(v1 and v2 and (v1 == v2 or v1 in v2 or v2 in v1))
                
                sd1 = re.sub(r"[^a-z0-9]", "", r1["sub_district"].lower())
                sd2 = re.sub(r"[^a-z0-9]", "", r2["sub_district"].lower())
                same_sd = bool(sd1 and sd2 and (sd1 == sd2 or sd1 in sd2 or sd2 in sd1))
                
                w1 = r1["week"] or 0
                w2 = r2["week"] or 0
                week_diff = abs(w1 - w2)
                
                same_date = bool(r1["start_date"] and r2["start_date"] and r1["start_date"] == r2["start_date"])
                
                has_fu = "follow" in (r1["text"] + r2["text"]).lower() or "previous week" in (r1["text"] + r2["text"]).lower()
                
                # If same village, or same start date with adjacent week, or explicit follow up
                if same_vil or (same_sd and week_diff <= 2) or same_date or has_fu:
                    candidates.append((r1, r2, same_vil, same_sd, same_date, week_diff, has_fu))
                    
    if not candidates:
        print(f"  --> NO candidate repeated events found for {target_dis}. All {len(dis_recs)} observations represent distinct geographical localities, separate epidemic periods, or unique institutional outbreaks.")
    else:
        print(f"  Found {len(candidates)} candidate pairs to evaluate:")
        for r1, r2, same_vil, same_sd, same_date, w_diff, has_fu in candidates:
            print(f"\n  Candidate Linkage in {r1['district'].title()}, {r1['state'].title()}:")
            print(f"    Obs 1: Wk {r1['week']:2d} | UID: {r1['uid']} | Start: {r1['start_date']} | Cases: {r1['cases']} | Vil: '{r1['village']}' | SubDist: '{r1['sub_district']}'")
            print(f"    Obs 2: Wk {r2['week']:2d} | UID: {r2['uid']} | Start: {r2['start_date']} | Cases: {r2['cases']} | Vil: '{r2['village']}' | SubDist: '{r2['sub_district']}'")
            print(f"    Evidence cues: same_village={same_vil}, same_subdistrict={same_sd}, same_start_date={same_date}, week_diff={w_diff}, follow_up_cue={has_fu}")
            print(f"    Obs 1 text: {r1['text'][:150]}...")
            print(f"    Obs 2 text: {r2['text'][:150]}...")

conn.close()

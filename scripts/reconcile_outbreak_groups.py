import sys
import json
import sqlite3
import re
from collections import defaultdict
from datetime import datetime

sys.path.insert(0, "src")
from episense.taxonomy.priority import PRIORITY_CANONICAL_NAMES, resolve_priority_disease
from episense.fusion.quantities import QuantityAggregator
from episense.schemas.event import EventObservation, EpidemiologicalQuantities
from episense.schemas.assertion import Assertion, AssertionStatus
from episense.schemas.location import Location, GeographicLevel
from episense.schemas.nlp import ResolvedLocation, ResolutionState

conn = sqlite3.connect("data/surveillance_store.sqlite")
cur = conn.cursor()

rows = cur.execute("""
    SELECT document_id, title, metadata_json, text, publication_timestamp
    FROM documents
    WHERE source_id = 'idsp_bulletin_feed'
""").fetchall()

manifest = json.loads(open("data/raw/ncdc_2026/manifest.json", encoding="utf-8").read())
manifest_by_week = {m.get("reporting_week") or m.get("week"): m for m in manifest}

records = []
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

    def parse_int_or_none(val):
        if val is None or val == "" or str(val).lower() in ("not reported", "none", "null"):
            return None
        try:
            return int(str(val).replace(",", "").strip())
        except ValueError:
            return None

    c_prio = resolve_priority_disease(meta.get("disease", "")) or resolve_priority_disease(meta.get("canonical_disease", ""))

    records.append({
        "doc_id": doc_id,
        "uid": uid,
        "week": week,
        "state": meta.get("state", "").strip(),
        "district": meta.get("district", "").strip(),
        "sub_district": sub_dist,
        "village": village,
        "start_date": sd_date,
        "disease": meta.get("disease", "").strip(),
        "canonical_disease": c_prio.canonical_name if c_prio else meta.get("disease", "").strip(),
        "is_priority": c_prio is not None,
        "priority_name": c_prio.canonical_name if c_prio else None,
        "cases": parse_int_or_none(meta.get("cases")),
        "deaths": parse_int_or_none(meta.get("deaths")),
        "status": meta.get("status", "Under Surveillance").strip(),
        "page_number": meta.get("page_number", 1),
        "pdf_sha256": meta.get("pdf_sha256", ""),
        "pub_ts": pub_ts,
        "text": raw_text,
    })

print(f"Total processed records: {len(records)}")

# 1. Clustering into candidate outbreak groups
# Linkage key: (state, district, canonical_disease)
by_geo_dis = defaultdict(list)
for r in records:
    st_k = r["state"].lower().strip()
    dt_k = r["district"].lower().strip()
    ds_k = r["canonical_disease"].lower().strip()
    by_geo_dis[(st_k, dt_k, ds_k)].append(r)

# Evaluate each geo-disease group
# If len == 1: singleton group
# If len > 1: check if records are genuinely repeated outbreak reports or distinct outbreaks
confirmed_linked_groups = []
unresolved_review_groups = []
distinct_outbreak_events = []

aggregator = QuantityAggregator()

for (st_k, dt_k, ds_k), group_recs in by_geo_dis.items():
    if len(group_recs) == 1:
        distinct_outbreak_events.append({
            "group_id": f"CANONICAL-{group_recs[0]['uid']}",
            "type": "SINGLETON",
            "records": group_recs,
            "canonical_disease": group_recs[0]["canonical_disease"],
            "state": group_recs[0]["state"],
            "district": group_recs[0]["district"],
            "resolved_cases": group_recs[0]["cases"],
            "resolved_deaths": group_recs[0]["deaths"],
            "has_conflict": False,
        })
        continue

    # Multi-record group: cluster by village & start date proximity
    # Sub-clustering
    sub_clusters = []
    visited = set()

    for i in range(len(group_recs)):
        if i in visited:
            continue
        cluster = [group_recs[i]]
        visited.add(i)
        
        for j in range(i + 1, len(group_recs)):
            if j in visited:
                continue
            r1 = group_recs[i]
            r2 = group_recs[j]
            
            # Check village match
            v1 = re.sub(r"[^a-z0-9]", "", r1["village"].lower())
            v2 = re.sub(r"[^a-z0-9]", "", r2["village"].lower())
            same_village = bool(v1 and v2 and (v1 == v2 or v1 in v2 or v2 in v1))
            
            # Check dates
            same_date = bool(r1["start_date"] and r2["start_date"] and r1["start_date"] == r2["start_date"])
            
            # Check text mention of follow-up
            has_followup = "follow-up" in r1["text"].lower() or "follow-up" in r2["text"].lower() or "follow up" in r1["text"].lower() or "follow up" in r2["text"].lower()
            
            # Strict linkage rule:
            # Must share exact village AND (same start date OR adjacent weeks <= 2)
            w1 = r1["week"] or 0
            w2 = r2["week"] or 0
            adj_weeks = abs(w1 - w2) <= 2 and abs(w1 - w2) > 0
            
            if same_village and (same_date or adj_weeks):
                cluster.append(r2)
                visited.add(j)
            elif has_followup and abs(w1 - w2) <= 3:
                cluster.append(r2)
                visited.add(j)

        sub_clusters.append(cluster)

    for cluster in sub_clusters:
        if len(cluster) == 1:
            distinct_outbreak_events.append({
                "group_id": f"CANONICAL-{cluster[0]['uid']}",
                "type": "DISTINCT_LOCAL_OUTBREAK",
                "records": cluster,
                "canonical_disease": cluster[0]["canonical_disease"],
                "state": cluster[0]["state"],
                "district": cluster[0]["district"],
                "resolved_cases": cluster[0]["cases"],
                "resolved_deaths": cluster[0]["deaths"],
                "has_conflict": False,
            })
        else:
            # Check if genuine repeated outbreak
            # Verify anti-inflation
            vils = set(r["village"] for r in cluster if r["village"])
            dates = set(r["start_date"] for r in cluster if r["start_date"])
            wks = [r["week"] for r in cluster]
            
            # Check if different institutions (like Raichur school vs girls hostel)
            insts = []
            for r in cluster:
                txt = r["text"].lower()
                if "hostel" in txt or "school" in txt or "college" in txt:
                    insts.append(txt[:100])
                    
            # If institutions are distinctly different, keep separate!
            if "hostel" in " ".join(insts) and "residential school" in " ".join(insts):
                # Separate!
                for r in cluster:
                    distinct_outbreak_events.append({
                        "group_id": f"CANONICAL-{r['uid']}",
                        "type": "DISTINCT_LOCAL_INSTITUTION",
                        "records": [r],
                        "canonical_disease": r["canonical_disease"],
                        "state": r["state"],
                        "district": r["district"],
                        "resolved_cases": r["cases"],
                        "resolved_deaths": r["deaths"],
                        "has_conflict": False,
                    })
                continue
                
            # Genuine linked continuing outbreak!
            # Sort cluster chronologically
            cluster.sort(key=lambda x: (x["week"] or 0, x["pub_ts"] or ""))
            
            # Convert to EventObservation to test QuantityAggregator
            obs_objs = []
            for r in cluster:
                obs_objs.append(
                    EventObservation(
                        document_id=r["doc_id"],
                        source_id="idsp_bulletin_feed",
                        canonical_disease=r["canonical_disease"],
                        raw_disease_span=r["disease"],
                        assertion=Assertion(assertion_status=AssertionStatus.CONFIRMED),
                        publication_time=datetime.fromisoformat(r["pub_ts"]) if r["pub_ts"] else datetime.now(),
                        quantities=EpidemiologicalQuantities(
                            case_count=r["cases"],
                            death_count=r["deaths"],
                        )
                    )
                )
            
            agg_q, has_conf, conf_sum = aggregator.aggregate(obs_objs)
            
            cases_sum = sum(r["cases"] for r in cluster if r["cases"] is not None)
            cases_latest = agg_q.case_count
            cases_max = agg_q.max_reported_estimate
            
            confirmed_linked_groups.append({
                "canonical_id": f"CANONICAL-OUTBREAK-{cluster[0]['uid']}",
                "disease": cluster[0]["canonical_disease"],
                "state": cluster[0]["state"],
                "district": cluster[0]["district"],
                "village": list(vils)[0] if vils else "Multiple/Unstated",
                "weeks": wks,
                "records": cluster,
                "cases_sum_inflated": cases_sum,
                "cases_latest_exposed": cases_latest,
                "cases_max_estimate": cases_max,
                "has_conflict": has_conf,
                "conflict_summary": conf_sum,
                "inflation_prevented": cases_sum - (cases_latest or 0),
            })
            
            distinct_outbreak_events.append({
                "group_id": f"CANONICAL-OUTBREAK-{cluster[0]['uid']}",
                "type": "LINKED_CONTINUING_OUTBREAK",
                "records": cluster,
                "canonical_disease": cluster[0]["canonical_disease"],
                "state": cluster[0]["state"],
                "district": cluster[0]["district"],
                "resolved_cases": cases_latest,
                "resolved_deaths": agg_q.death_count,
                "has_conflict": has_conf,
            })

print("\n" + "=" * 80)
print("OUTBREAK GROUP RECONCILIATION SUMMARY")
print("=" * 80)
print(f"Total source observations:           {len(records)}")
print(f"Confirmed linked outbreak groups:    {len(confirmed_linked_groups)}")
print(f"Total canonical outbreak events:     {len(distinct_outbreak_events)}")

print("\nConfirmed Linked Outbreak Groups Details:")
for grp in confirmed_linked_groups:
    print(f"\n* ID: {grp['canonical_id']}")
    print(f"  Disease: {grp['disease']} | Location: {grp['village']}, {grp['district']}, {grp['state']}")
    print(f"  Reporting Weeks: {grp['weeks']}")
    for r in grp['records']:
        fname = manifest_by_week.get(r['week'], {}).get('filename', f"week{r['week']}.pdf")
        print(f"    - Week {r['week']:2d} ({fname}): Cases={r['cases']}, Deaths={r['deaths']}, Status={r['status']}")
    print(f"  Anti-Inflation Check:")
    print(f"    - Blind Sum (INFLATED):         {grp['cases_sum_inflated']} cases")
    print(f"    - Latest Source-Reported Value: {grp['cases_latest_exposed']} cases")
    print(f"    - Max Reported Estimate:        {grp['cases_max_estimate']} cases")
    print(f"    - False Cases Deflated:         {grp['inflation_prevented']} cases prevented from double counting")
    print(f"  Conflict / Progression Log:       {grp['conflict_summary']}")

conn.close()

import sys
import json
import sqlite3
import re
from collections import Counter, defaultdict
from datetime import datetime

sys.path.insert(0, "src")
from episense.taxonomy.priority import PRIORITY_CANONICAL_NAMES, resolve_priority_disease

conn = sqlite3.connect("data/surveillance_store.sqlite")
cur = conn.cursor()

# 1. Fetch all IDSP documents
rows = cur.execute("""
    SELECT document_id, title, metadata_json, text, publication_timestamp, retrieval_timestamp
    FROM documents
    WHERE source_id = 'idsp_bulletin_feed'
""").fetchall()

print(f"Total IDSP documents in DB: {len(rows)}")

manifest = json.loads(open("data/raw/ncdc_2026/manifest.json", encoding="utf-8").read())

# Map manifest by week
manifest_by_week = {}
for m in manifest:
    w = m.get("reporting_week") or m.get("week")
    manifest_by_week[w] = m

observations = []
for doc_id, title, meta_json, text, pub_ts, ret_ts in rows:
    meta = json.loads(meta_json) if meta_json else {}
    uid = meta.get("unique_id") or ""
    parts = uid.split("/")
    week = int(parts[3]) if len(parts) >= 4 and parts[3].isdigit() else None
    
    def parse_int_or_none(val):
        if val is None or val == "" or str(val).lower() in ("not reported", "none", "null"):
            return None
        try:
            return int(str(val).replace(",", "").strip())
        except ValueError:
            return None

    raw_text = text or ""
    v_match = re.search(r"Village[:\s]+([^,\n]+)", raw_text, re.IGNORECASE)
    village = v_match.group(1).strip() if v_match else ""
    
    sd_match = re.search(r"Sub-?\s*District[:\s]+([^,\n]+)", raw_text, re.IGNORECASE)
    sub_dist = sd_match.group(1).strip() if sd_match else (meta.get("sub_district") or "")

    sd_date = meta.get("event_start")
    if not sd_date:
        d_match = re.search(r"Date of start of outbreak[:\s]+(\d{2}-\d{2}-\d{4})", raw_text, re.IGNORECASE)
        sd_date = d_match.group(1).strip() if d_match else None

    obs = {
        "doc_id": doc_id,
        "unique_id": uid,
        "week": week,
        "state": meta.get("state", "").strip(),
        "district": meta.get("district", "").strip(),
        "sub_district": sub_dist,
        "village": village,
        "start_date": sd_date,
        "raw_disease": meta.get("disease", "").strip(),
        "canonical_disease": meta.get("canonical_disease", "").strip(),
        "status": meta.get("status", "Under Surveillance").strip(),
        "cases": parse_int_or_none(meta.get("cases")),
        "deaths": parse_int_or_none(meta.get("deaths")),
        "sample_count": parse_int_or_none(meta.get("sample_count")),
        "positive_sample_count": parse_int_or_none(meta.get("positive_sample_count")),
        "pdf_sha256": meta.get("pdf_sha256"),
        "page_number": meta.get("page_number"),
        "pub_ts": pub_ts,
        "ret_ts": ret_ts,
        "text": raw_text,
    }
    observations.append(obs)

# 2. Priority classification
PRIORITY_SET = {p.lower() for p in PRIORITY_CANONICAL_NAMES}
for o in observations:
    raw = o["raw_disease"]
    canon = o["canonical_disease"]
    meta_prio = resolve_priority_disease(raw)
    if meta_prio:
        o["priority_disease"] = meta_prio.canonical_name
        o["priority_type"] = "EXACT_REGISTRY_MATCH" if meta_prio.canonical_name.lower() == raw.lower() else "VALIDATED_SYNONYM"
    else:
        # Check canonical
        c_prio = resolve_priority_disease(canon)
        if c_prio:
            o["priority_disease"] = c_prio.canonical_name
            o["priority_type"] = "VALIDATED_SYNONYM"
        else:
            o["priority_disease"] = None
            o["priority_type"] = "OUT_OF_SCOPE"

priority_obs = [o for o in observations if o["priority_disease"] is not None]
non_priority_obs = [o for o in observations if o["priority_disease"] is None]

print(f"Total observations: {len(observations)}")
print(f"Total priority: {len(priority_obs)}")
print(f"Total non-priority: {len(non_priority_obs)}")

# 3. Weekly breakdown
weekly_table = []
for w in range(1, 35):
    w_obs = [o for o in observations if o["week"] == w]
    w_prio = [o for o in w_obs if o["priority_disease"] is not None]
    m_info = manifest_by_week.get(w, {})
    cases_sum = sum(o["cases"] for o in w_obs if o["cases"] is not None)
    deaths_sum = sum(o["deaths"] for o in w_obs if o["deaths"] is not None)
    missing_cases = sum(1 for o in w_obs if o["cases"] is None)
    missing_deaths = sum(1 for o in w_obs if o["deaths"] is None)
    weekly_table.append({
        "week": w,
        "filename": m_info.get("filename", f"week{w}.pdf"),
        "sha256": m_info.get("sha256", "")[:12],
        "total_obs": len(w_obs),
        "priority_obs": len(w_prio),
        "reported_cases": cases_sum,
        "reported_deaths": deaths_sum,
        "missing_cases": missing_cases,
        "missing_deaths": missing_deaths,
    })

# 4. Eight-disease priority breakdown
prio_breakdown = {}
for dis in PRIORITY_CANONICAL_NAMES:
    dis_obs = [o for o in priority_obs if o["priority_disease"] == dis]
    exact_cnt = sum(1 for o in dis_obs if o["priority_type"] == "EXACT_REGISTRY_MATCH")
    syn_cnt = sum(1 for o in dis_obs if o["priority_type"] == "VALIDATED_SYNONYM")
    cases_cnt = sum(o["cases"] for o in dis_obs if o["cases"] is not None)
    deaths_cnt = sum(o["deaths"] for o in dis_obs if o["deaths"] is not None)
    missing_cases = sum(1 for o in dis_obs if o["cases"] is None)
    raw_labels = Counter(o["raw_disease"] for o in dis_obs)
    prio_breakdown[dis] = {
        "total_obs": len(dis_obs),
        "exact_matches": exact_cnt,
        "validated_synonyms": syn_cnt,
        "reported_cases": cases_cnt,
        "reported_deaths": deaths_cnt,
        "missing_cases": missing_cases,
        "raw_labels": dict(raw_labels),
    }

# 5. Out-of-scope non-priority breakdown
out_of_scope_counts = Counter(o["raw_disease"] for o in non_priority_obs)

# 6. Status breakdown
status_counts = Counter(o["status"] for o in observations)

# 7. Quantity missingness
total_cases_missing = sum(1 for o in observations if o["cases"] is None)
total_deaths_missing = sum(1 for o in observations if o["deaths"] is None)
total_samples_missing = sum(1 for o in observations if o["sample_count"] is None)

# Save audit results to JSON
results = {
    "summary": {
        "total_downloaded_pdfs": len(manifest),
        "unique_pdf_hashes": len(set(m.get("sha256") for m in manifest if m.get("sha256"))),
        "extracted_report_rows": 1414,
        "valid_source_observations": len(observations),
        "priority_disease_observations": len(priority_obs),
        "non_priority_observations": len(non_priority_obs),
        "total_reported_cases": sum(o["cases"] for o in observations if o["cases"] is not None),
        "total_reported_deaths": sum(o["deaths"] for o in observations if o["deaths"] is not None),
        "missing_cases_count": total_cases_missing,
        "missing_deaths_count": total_deaths_missing,
        "missing_samples_count": total_samples_missing,
    },
    "weekly_table": weekly_table,
    "priority_breakdown": prio_breakdown,
    "top_out_of_scope": dict(out_of_scope_counts.most_common(20)),
    "status_counts": dict(status_counts),
}

with open("data/ncdc_audit_metrics.json", "w", encoding="utf-8") as f:
    json.dump(results, f, indent=2)

print("\nAudit metrics calculated and saved to data/ncdc_audit_metrics.json.")
print("Summary:", results["summary"])
conn.close()

import sys
from pathlib import Path
from datetime import datetime, timezone
import json
import sqlite3

sys.path.insert(0, "src")
from episense.taxonomy.priority import PRIORITY_CANONICAL_NAMES, resolve_priority_disease

DB_PATH = Path("data/surveillance_store.sqlite")

def generate_audit():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    # Query all October documents
    start_iso = "2026-10-01T00:00:00+00:00"
    end_iso = "2026-10-31T23:59:59+00:00"

    rows = conn.execute(
        """
        SELECT document_id, source_id, title, text, publication_timestamp,
               retrieval_timestamp, content_hash_sha256, metadata_json
        FROM documents
        WHERE publication_timestamp >= ? AND publication_timestamp <= ?
        ORDER BY publication_timestamp ASC
        """,
        (start_iso, end_iso),
    ).fetchall()

    print(f"Total raw October documents retrieved: {len(rows)}")

    # Deduplicate by SHA-256
    unique_docs = {}
    duplicate_groups = {}

    for r in rows:
        h = r["content_hash_sha256"].lower()
        if h not in unique_docs:
            unique_docs[h] = r
            duplicate_groups[h] = [r]
        else:
            duplicate_groups[h].append(r)

    print(f"Unique documents by SHA-256: {len(unique_docs)}")
    print(f"Duplicate documents filtered: {len(rows) - len(unique_docs)}")

    # Load traces and fused events to map extracted observations and canonical events
    trace_rows = conn.execute("SELECT document_id, candidate_event_ids_json, fused_event_ids_json, overall_status FROM pipeline_traces").fetchall()
    doc_traces = {t["document_id"]: t for t in trace_rows}

    fe_rows = conn.execute("SELECT fused_event_id, canonical_disease, json_data FROM fused_events").fetchall()
    fused_events_map = {}
    for fer in fe_rows:
        fe_data = json.loads(fer["json_data"])
        for ref in fe_data.get("evidence_references", []):
            d_id = ref.get("document_id")
            if d_id:
                fused_events_map.setdefault(d_id, set()).add(fer["fused_event_id"])

    non_priority_pathogens = [
        "nipah", "ebola", "marburg", "mpox", "monkeypox", "zika", "yellow fever",
        "mers", "sars", "avian influenza", "h5n1", "h9n2", "anthrax", "plague",
        "diphtheria", "hantavirus", "polio", "rift valley fever", "lassa fever",
        "crimean-congo", "oropouche", "chandipura", "covid-19", "coronavirus"
    ]

    international_terms = [
        "bangladesh", "dhaka", "pakistan", "sri lanka", "nepal", "congo", "senegal",
        "ethiopia", "brazil", "nigeria", "sudan", "multi-country", "global", "italy",
        "russian federation", "saudi arabia", "cambodia", "thailand", "uganda"
    ]

    audited_records = []
    primary_counts = {
        "OUT_OF_SCOPE_PATHOGEN_OR_INTERNATIONAL": 0,
        "ADMINISTRATIVE_POLICY_OR_DISCOVERY_STUB": 0,
        "PRIORITY_DISEASE_NEGATIVE_RULEOUT": 0,
        "PRIORITY_DISEASE_ACTIONABLE_POSITIVE": 0,
    }
    secondary_counts = {
        "priority_disease_tagged": 0,
        "duplicate_instances": 0,
        "international_geography": 0,
        "media_discovery_stub": 0,
        "non_priority_pathogen": 0,
    }

    for h, r in unique_docs.items():
        doc_id = r["document_id"]
        title = r["title"] or ""
        text = r["text"] or ""
        source_id = r["source_id"]
        pub_ts = r["publication_timestamp"]
        title_lower = title.lower()
        text_lower = text.lower()
        meta = json.loads(r["metadata_json"] or "{}")

        # Detect priority disease mentions
        detected_priority = None
        for p in PRIORITY_CANONICAL_NAMES:
            if p.lower() in text_lower or p.lower() in title_lower:
                detected_priority = p
                break
        if not detected_priority and ("add" in text_lower.split() or "add" in title_lower.split()):
            detected_priority = "Acute Diarrhoeal Disease"

        # Check characteristics
        is_non_priority_pathogen = any(p in title_lower or p in text_lower for p in non_priority_pathogens)
        is_international = any(c in title_lower for c in international_terms) or meta.get("is_international") == "true" or meta.get("geographic_scope") == "Global/International"
        is_discovery_stub = (source_id == "gdelt_doc_discovery") or ("discovered media report" in text_lower and "no. of cases" not in text_lower)
        is_negated = any(
            phrase in text_lower or phrase in title_lower
            for phrase in [
                "rule out", "ruled out", "tested negative", "all samples tested negative",
                "zero active infections", "no cholera cases", "subsided with zero", "negative for"
            ]
        )
        has_clinical_cues = any(
            cue in text_lower or cue in title_lower
            for cue in ["outbreak", "cases reported", "confirmed cases", "cluster of cases", "surge in cases", "death toll", "fatalities", "no. of cases"]
        )

        # Secondary tags
        sec_tags = []
        if detected_priority:
            sec_tags.append(f"priority_disease:{detected_priority}")
            secondary_counts["priority_disease_tagged"] += 1
        if is_international:
            sec_tags.append("international_geography")
            secondary_counts["international_geography"] += 1
        if is_discovery_stub:
            sec_tags.append("media_discovery_stub")
            secondary_counts["media_discovery_stub"] += 1
        if is_non_priority_pathogen:
            sec_tags.append("non_priority_pathogen")
            secondary_counts["non_priority_pathogen"] += 1
        if len(duplicate_groups[h]) > 1:
            sec_tags.append(f"duplicate_count:{len(duplicate_groups[h]) - 1}")
            secondary_counts["duplicate_instances"] += (len(duplicate_groups[h]) - 1)

        # Single Mutually Exclusive Primary Classification
        if is_non_priority_pathogen or is_international:
            primary_disp = "OUT_OF_SCOPE_PATHOGEN_OR_INTERNATIONAL"
        elif is_negated and detected_priority:
            primary_disp = "PRIORITY_DISEASE_NEGATIVE_RULEOUT"
        elif detected_priority and has_clinical_cues and not is_discovery_stub and not is_international:
            # Genuine domestic clinical outbreak report
            primary_disp = "PRIORITY_DISEASE_ACTIONABLE_POSITIVE"
        else:
            # Administrative policy, guideline, routine communication, or unverified media stub
            primary_disp = "ADMINISTRATIVE_POLICY_OR_DISCOVERY_STUB"

        primary_counts[primary_disp] += 1

        # Trace / observation counts
        tr = doc_traces.get(doc_id)
        status = tr["overall_status"] if tr else "PROCESSED"
        cand_ids = json.loads(tr["candidate_event_ids_json"] or "[]") if tr else []
        fe_ids = list(fused_events_map.get(doc_id, []))

        audited_records.append({
            "document_id": doc_id,
            "sha256": h,
            "source_id": source_id,
            "publication_timestamp": pub_ts,
            "title": title[:70],
            "primary_classification": primary_disp,
            "secondary_tags": sec_tags,
            "priority_disease": detected_priority or "None",
            "extracted_observations_count": len(cand_ids),
            "canonical_events_count": len(fe_ids),
            "processing_status": status,
        })

    print("\n" + "=" * 80)
    print("PRIMARY CLASSIFICATION COUNTS (Mutually Exclusive Partition):")
    print("=" * 80)
    for k, v in primary_counts.items():
        print(f"  {k:45s}: {v}")
    total_primary = sum(primary_counts.values())
    print(f"  {'TOTAL UNIQUE DOCUMENTS':45s}: {total_primary}")
    print(f"  {'RAW INGESTED (Unique + Duplicates)':45s}: {total_primary + len(rows) - len(unique_docs)}")

    print("\n" + "=" * 80)
    print("SECONDARY OVERLAPPING TAGS:")
    print("=" * 80)
    for k, v in secondary_counts.items():
        print(f"  {k:45s}: {v}")

    # Output detailed audit to JSON
    audit_output_path = Path("docs/document_level_classification_audit.json")
    audit_output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(audit_output_path, "w", encoding="utf-8") as f:
        json.dump({
            "audit_window_start": start_iso,
            "audit_window_end": end_iso,
            "raw_ingested_count": len(rows),
            "unique_ingested_count": len(unique_docs),
            "duplicates_filtered_count": len(rows) - len(unique_docs),
            "primary_classification_summary": primary_counts,
            "secondary_tags_summary": secondary_counts,
            "documents": audited_records,
        }, f, indent=2)

    print(f"\nDocument audit saved to: {audit_output_path}")

if __name__ == "__main__":
    generate_audit()

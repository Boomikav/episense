import sqlite3
import json
import httpx

def trace_recent_report():
    print("=" * 80)
    print("END-TO-END TRACE OF A GENUINELY RECENT REPORT (OCTOBER 2026)")
    print("=" * 80)

    conn = sqlite3.connect("data/surveillance_store.sqlite")
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    # Search for the cholera document from October 2026
    row = c.execute("""
        SELECT document_id, source_id, origin, title, publication_timestamp, retrieval_timestamp, text, metadata_json
        FROM documents
        WHERE title LIKE '%cholera%' AND publication_timestamp >= '2026-10'
    """).fetchone()

    if not row:
        print("Cholera document not found, listing recent 2026 documents:")
        recent = c.execute("SELECT document_id, title, publication_timestamp FROM documents WHERE publication_timestamp >= '2026-10'").fetchall()
        for r in recent:
            print(f"  {r['publication_timestamp']}: {r['title']} ({r['document_id']})")
        return

    doc_id = row["document_id"]
    print(f"1. STORAGE (Document in SQLite 'documents' table):")
    print(f"   Document ID   : {doc_id}")
    print(f"   Source ID     : {row['source_id']}")
    print(f"   Origin        : {row['origin']}")
    print(f"   Title         : {row['title']}")
    print(f"   Published At  : {row['publication_timestamp']}")
    print(f"   Retrieved At  : {row['retrieval_timestamp']}")
    print(f"   Text Snippet  : {row['text'][:120]}...\n")

    # 2. NLP Pipeline Trace
    trace_row = c.execute("SELECT trace_id, nlp_output_json, overall_status FROM pipeline_traces WHERE document_id = ?", (doc_id,)).fetchone()
    if trace_row:
        print(f"2. NLP PIPELINE TRACE ('pipeline_traces' table):")
        print(f"   Trace ID       : {trace_row['trace_id']}")
        print(f"   Overall Status : {trace_row['overall_status']}")
        if trace_row["nlp_output_json"]:
            nlp = json.loads(trace_row["nlp_output_json"])
            entities = nlp.get("entities", [])
            print(f"   Extracted Entities ({len(entities)}):")
            for ent in entities[:5]:
                print(f"     - Type: {ent.get('entity_type')}, Text: '{ent.get('text')}' (span {ent.get('start_char')}:{ent.get('end_char')})")
        print()

    # 3. Event Resolution
    fe_rows = c.execute("""
        SELECT fused_event_id, canonical_disease, primary_origin, earliest_time, latest_time, total_cases, json_data
        FROM fused_events
        WHERE canonical_disease LIKE '%cholera%'
    """).fetchall()
    print(f"3. EVENT RESOLUTION ('fused_events' table):")
    print(f"   Matching Cholera Fused Events: {len(fe_rows)}")
    for fe in fe_rows[:3]:
        data = json.loads(fe["json_data"])
        print(f"   - Fused ID: {fe['fused_event_id']}")
        print(f"     Disease : {fe['canonical_disease']}")
        loc = data.get('canonical_location')
        loc_name = loc.get('normalized_name') if isinstance(loc, dict) else str(loc)
        print(f"     Location: {loc_name}")
        print(f"     Category: {data.get('decision_category')}")
        print(f"     Current : {data.get('currentness_status')}")
    print()

    # 4. Alert & Decision Category
    alert_rows = c.execute("""
        SELECT alert_id, disease_key, alert_tier, composite_score, origin, json_data
        FROM alerts
        WHERE disease_key LIKE '%cholera%'
    """).fetchall()
    print(f"4. ALERTS & DECISION CATEGORIES ('alerts' table):")
    print(f"   Matching Cholera Alerts: {len(alert_rows)}")
    for a in alert_rows[:3]:
        data = json.loads(a["json_data"])
        print(f"   - Alert ID : {a['alert_id']}")
        print(f"     Tier     : {a['alert_tier']}")
        print(f"     Category : {data.get('decision_category')}")
        print(f"     Action   : {data.get('recommended_action')}")
    print()

    # 5. Live API Verification
    try:
        r = httpx.get("http://127.0.0.1:8008/api/v1/metrics/overview", timeout=5.0)
        if r.status_code == 200:
            overview = r.json()
            findings = overview.get("most_important_new_findings", [])
            print(f"5. LIVE DASHBOARD API ('/api/v1/metrics/overview'):")
            print(f"   Total findings in overview: {len(findings)}")
            for f in findings:
                print(f"   - [{f.get('disease')}] {f.get('headline')} | Decision: {f.get('decision_category')} | Origin: {f.get('origin')}")
    except Exception as ex:
        print(f"   API check error: {ex}")

if __name__ == "__main__":
    trace_recent_report()

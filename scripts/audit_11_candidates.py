import sqlite3, json

con = sqlite3.connect("data/surveillance_store.sqlite")
cur = con.cursor()

# Get the 11 candidate alerts
candidate_ids = [
    "3f30f362-1ccc-5286-88c3-ff92c7837177",
    "9da644f9-ad9c-5c65-87cd-1230c65b9650",
    "d50680b7-2c21-5d1c-8eaf-3c89c959d591",
    "85197a1c-b518-55f0-b9bc-e9e193e31831",
    "855dcf6b-c821-5ee2-8b0c-2a5fa02d2217",
    "b2cfdb68-4852-5b06-9e66-b9e3602da969",
    "2154b6f8-440b-5f80-8306-19064991c101",
    "2cbd71bb-01da-50dd-acbe-34d5b77db254",
    "5cd8de88-28a3-554a-ac85-8a76b6517055",
    "1a966219-447d-5cd9-a5ed-c9c01f795a73",
    "7531ce57-c795-5fbd-acb2-6f9fe0906fc5",
]

print("=== AUDIT OF ALL 11 CANDIDATES ===")
for cid in candidate_ids:
    row = cur.execute("SELECT alert_id, disease_key, geo_key, alert_tier, composite_score, origin, period_start, json_data FROM alerts WHERE alert_id = ?", (cid,)).fetchone()
    if not row:
        print(f"Alert {cid} NOT FOUND!")
        continue
    data = json.loads(row[7])
    fe_ids = data.get("supporting_fused_event_ids", [])
    print(f"\n--- Candidate Alert: {cid} ---")
    print(f"Disease: {row[1]} | Location: {row[2]} | Tier: {row[3]} | Heuristic Score: {row[4]}")
    print(f"Period: {data.get('period_start')} to {data.get('period_end')} | Origin: {row[5]}")
    print(f"Supporting Fused Event IDs: {fe_ids}")
    for fe_id in fe_ids:
        fe_row = cur.execute("SELECT fused_event_id, canonical_disease, primary_origin, json_data FROM fused_events WHERE fused_event_id = ?", (fe_id,)).fetchone()
        if fe_row:
            fe_data = json.loads(fe_row[3])
            obs_ids = fe_data.get("contributing_observation_ids", [])
            print(f"  FusedEvent: {fe_id} | Disease: {fe_row[1]} | Origin: {fe_row[2]}")
            print(f"  Event Window: {fe_data.get('event_window_start')} to {fe_data.get('event_window_end')}")
            print(f"  Decision Cat: {fe_data.get('decision_category')} | Currentness: {fe_data.get('currentness_status')}")
            print(f"  Quantities: {fe_data.get('aggregated_quantities')}")
            print(f"  Contributing Obs IDs: {obs_ids}")
            for ev_ref in fe_data.get("evidence_references", []):
                doc_id = ev_ref.get("document_id")
                doc_row = cur.execute("SELECT title, source_id, publication_timestamp, text FROM documents WHERE document_id = ?", (doc_id,)).fetchone()
                if doc_row:
                    print(f"    Source Doc: {doc_id} | Title: '{doc_row[0]}' | Source: {doc_row[1]} | PubDate: {doc_row[2]}")
                    print(f"    Span: '{ev_ref.get('span_text')}'")

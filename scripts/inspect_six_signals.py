import sqlite3
import json

conn = sqlite3.connect("data/surveillance_store.sqlite")
cur = conn.cursor()
cur.execute("SELECT signal_id, disease_key, geo_key, json_data FROM signals")
rows = cur.fetchall()
for r in rows:
    data = json.loads(r[3])
    rel = data.get("reliability_status")
    level = data.get("signal_level")
    if rel == "stable_baseline" and level not in ("no_signal", "noise"):
        print(f"Signal ID: {r[0]} | Disease: {r[1]} | Geo: {r[2]} | Rel: {rel} | Level: {level} | Downgraded: {data.get('is_downgraded', data.get('downgraded_reason'))} | Gated: {data.get('is_gated')}")

conn.close()

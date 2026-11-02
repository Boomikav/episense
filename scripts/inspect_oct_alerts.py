import sqlite3, json
from datetime import datetime, timezone

con = sqlite3.connect("data/surveillance_store.sqlite")
cur = con.cursor()

rows = cur.execute("SELECT alert_id, disease_key, geo_key, alert_tier, composite_score, origin, period_start, json_data FROM alerts").fetchall()
print(f"Total alerts in DB: {len(rows)}")

# Check alerts with period_end in Oct 2026 or Nov 2026
oct_2026_start = datetime(2026, 10, 1, tzinfo=timezone.utc)
oct_2026_end = datetime(2026, 10, 31, 23, 59, 59, tzinfo=timezone.utc)
nov_2026_end = datetime(2026, 11, 30, 23, 59, 59, tzinfo=timezone.utc)

oct_alerts = []
for r in rows:
    data = json.loads(r[7])
    p_end_str = data.get("period_end")
    if p_end_str:
        p_end = datetime.fromisoformat(p_end_str.replace("Z", "+00:00"))
        if oct_2026_start <= p_end <= nov_2026_end:
            oct_alerts.append((r, data))

print(f"Alerts with period_end in Oct/Nov 2026: {len(oct_alerts)}")
for r, d in oct_alerts[:25]:
    print(f"ID: {r[0]} Disease: {r[1]} Geo: {r[2]} Tier: {r[3]} Score: {r[4]} Origin: {r[5]} Start: {r[6]} End: {d.get('period_end')} Curr: {d.get('currentness_status')} Cat: {d.get('decision_category')}")

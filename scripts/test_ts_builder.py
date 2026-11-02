import sys
sys.path.insert(0, "src")
import sqlite3, json
from episense.schemas.event import FusedEvent
from episense.baseline.timeseries import TimeSeriesBuilder

con = sqlite3.connect("data/surveillance_store.sqlite")
con.row_factory = sqlite3.Row
r = con.execute("SELECT * FROM fused_events WHERE fused_event_id = '1e404a20-bbf2-503e-b2a3-16e044736014'").fetchone()
fe = FusedEvent.model_validate_json(r["json_data"])
print("FE event_window_start:", fe.event_window_start)
print("FE is_event_time_estimated:", fe.is_event_time_estimated)
print("FE assertion_status:", fe.assertion_status)

ts = TimeSeriesBuilder()
bins = ts.build_weekly_bins([fe])
print(f"Generated {len(bins)} bins:")
for b in bins:
    print(b.bin_id, b.disease_key, b.geo_key, b.iso_year, b.iso_week, b.period_start, b.period_end)

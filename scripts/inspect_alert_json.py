import sqlite3, json
con = sqlite3.connect("data/surveillance_store.sqlite")
r = con.execute("SELECT json_data FROM alerts WHERE alert_id = '3f30f362-1ccc-5286-88c3-ff92c7837177'").fetchone()
if r:
    data = json.loads(r[0])
    print(json.dumps(data, indent=2))

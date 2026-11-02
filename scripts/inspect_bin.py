import sqlite3, json

con = sqlite3.connect("data/surveillance_store.sqlite")
con.row_factory = sqlite3.Row
r = con.execute("SELECT * FROM time_bins WHERE bin_id = '3b87c99e-6ee1-594f-af09-4a17cf94f54b'").fetchone()
data = json.loads(r["json_data"])
print(json.dumps(data, indent=2))

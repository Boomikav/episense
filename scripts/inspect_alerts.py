import requests

base = "http://127.0.0.1:8008"
r = requests.get(f"{base}/api/v1/alerts")
print("Alerts response status:", r.status_code)
alerts = r.json()
print("Alerts total:", len(alerts.get("items", [])) if isinstance(alerts, dict) else len(alerts))

if isinstance(alerts, dict) and "items" in alerts:
    items = alerts["items"]
elif isinstance(alerts, list):
    items = alerts
else:
    items = []

print(f"Number of alert items: {len(items)}")
for i, a in enumerate(items[:20]):
    print(f"[{i}] ID: {a.get('alert_id')} Disease: {a.get('canonical_disease')} Location: {a.get('location')} Tier: {a.get('alert_tier')} Origin: {a.get('origin')} Status: {a.get('currentness_status') or a.get('status')}")

r_geo = requests.get(f"{base}/api/v1/geo/alerts")
print("\nGeo alerts status:", r_geo.status_code)
geo_data = r_geo.json()
print("Geo alerts feature count:", len(geo_data.get("features", [])))
for f in geo_data.get("features", [])[:15]:
    props = f.get("properties", {})
    print("Geo Feature:", props.get("id"), props.get("canonical_disease"), props.get("location_name"), props.get("currentness_status"), props.get("alert_tier"))

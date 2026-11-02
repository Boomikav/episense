import urllib.request
import json

url = "http://127.0.0.1:8008/api/v1/sources/who_news_feed/poll"
req = urllib.request.Request(url, data=b"", headers={"Content-Type": "application/json"}, method="POST")

try:
    print(f"Triggering POST {url}...")
    with urllib.request.urlopen(req, timeout=30) as resp:
        data = json.loads(resp.read().decode("utf-8"))
        print("Poll response:")
        print(f"  Source ID: {data.get('source_id')}")
        print(f"  Status: {data.get('status')}")
        print(f"  HTTP Status: {data.get('http_status')}")
        print(f"  Documents found: {data.get('documents_found')}")
        print(f"  Documents ingested (new): {data.get('documents_ingested')}")
        print(f"  Duplicates skipped: {data.get('duplicates_skipped')}")
        print(f"  Items deferred: {data.get('items_deferred')}")
        print(f"  Duration: {data.get('duration_ms'):.1f} ms")
        print(f"  Details: {data.get('details')}")
except Exception as e:
    print(f"Polling failed: {e}")

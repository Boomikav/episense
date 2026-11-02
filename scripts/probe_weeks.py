import httpx
import json

headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
client = httpx.Client(timeout=15.0, follow_redirects=True, headers=headers, verify=False)

with open('data/raw/ncdc_2026/manifest.json') as f:
    manifest = json.load(f)

for w in [2, 3, 10, 20, 33]:
    item = next(m for m in manifest if m['reporting_week'] == w)
    try:
        r = client.get(item['url'])
        is_pdf = r.content.startswith(b"%PDF")
        print(f"Week {w}: status {r.status_code}, len {len(r.content)}, is_pdf {is_pdf}")
    except Exception as e:
        print(f"Week {w}: Error {e}")

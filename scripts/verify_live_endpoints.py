import urllib.request
import json

BASE_URL = "http://127.0.0.1:8008"

def test_endpoint(path):
    url = f"{BASE_URL}{path}"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "EpiSenseVerifier/1.0"})
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            print(f"[OK] {path} -> HTTP {resp.status}")
            return data
    except Exception as e:
        print(f"[FAIL] {path} -> {e}")
        return None

def main():
    print("Testing live EpiSense FastAPI endpoints...")
    health = test_endpoint("/health")
    taxonomy = test_endpoint("/api/v1/taxonomy/priority")
    metrics_live = test_endpoint("/api/v1/metrics/live")
    metrics_overview = test_endpoint("/api/v1/metrics/overview")
    sufficiency = test_endpoint("/api/v1/forecasting/sufficiency")
    sources_health = test_endpoint("/api/v1/sources/health")
    series = test_endpoint("/api/v1/forecasting/series")

    if metrics_overview:
        figs = metrics_overview.get("summary_figures", {})
        print("  Overview Summary Figures:")
        for k, v in figs.items():
            print(f"    - {v.get('label')}: {v.get('value')}")

    if health:
        print(f"  Health status: {health.get('status')}, version: {health.get('version')}")

    if taxonomy:
        print(f"  Taxonomy priority count: {len(taxonomy)}")
        print(f"  Pathogens: {[t['canonical_name'] for t in taxonomy]}")

    if metrics_live:
        acc = metrics_live.get("surveillance_accounting", {})
        print(f"  Surveillance accounting total docs: {acc.get('documents_ingested_total')}")
        print(f"  Surveillance accounting live docs: {acc.get('documents_ingested_live')}")
        print(f"  Surveillance accounting historical docs: {acc.get('documents_ingested_historical')}")
        print(f"  Priority disease active events: {acc.get('priority_diseases_accounting', {}).get('active_priority_events')}")
        print(f"  Signals baseline gated count: {acc.get('alerts_baseline_gated')}")

    if sufficiency:
        print(f"  Sufficiency profiled diseases count: {len(sufficiency)}")
        for d, p in sufficiency.items():
            print(f"    - {d}: consec={p.get('consecutive_observed_periods')}, forecast={p.get('forecast_eligibility')}, anomaly={p.get('statistical_anomaly_eligibility')}")

    if sources_health:
        print(f"  Sources total: {sources_health.get('total_sources')}, operational: {sources_health.get('operational_sources')}")

    if series:
        print(f"  Available series count: {len(series)}")

if __name__ == "__main__":
    main()

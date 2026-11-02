import urllib.request
import json

def check():
    url = 'http://127.0.0.1:8008/api/v1/forecasting/sufficiency'
    req = urllib.request.urlopen(url)
    data = json.loads(req.read().decode('utf-8'))
    print("Eight Disease Statuses:")
    for disease, prof in data.items():
        m_status = prof.get('modelling_status')
        f_elig = prof.get('forecast_eligibility')
        fresh = prof.get('operational_data_freshness')
        trend = prof.get('historical_trend')
        model = prof.get('best_candidate_model')
        print(f" - {disease:25s} | status={m_status:30s} | elig={f_elig:20s} | freshness={fresh} | trend={trend} | best_model={model}")

    print("\nCheck /panel endpoint:")
    req2 = urllib.request.urlopen('http://127.0.0.1:8008/api/v1/forecasting/panel?limit=5')
    panel_data = json.loads(req2.read().decode('utf-8'))
    print(f"Panel total rows: {panel_data.get('total_count')}, returned: {len(panel_data.get('records', []))}")

    print("\nCheck /evaluations endpoint:")
    req3 = urllib.request.urlopen('http://127.0.0.1:8008/api/v1/forecasting/evaluations')
    eval_data = json.loads(req3.read().decode('utf-8'))
    print(f"Evaluations models: {len(eval_data.get('evaluations', []))}, ablations: {len(eval_data.get('ablations', []))}")

if __name__ == "__main__":
    check()

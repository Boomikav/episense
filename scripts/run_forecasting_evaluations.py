"""
Comprehensive Chronological Forecasting Evaluation for EpiSense.
Executes rigorous, leakage-free evaluations:
1. Operational Monthly Forecasting:
   - Malaria National Series (NCVBDC MMIS 2024-2025, N=22 months)
   - Train: 2024-01 to 2025-04 (16 months) | Holdout: 2025-05 to 2025-10 (6 months, horizon h=1..6)
2. Retrospective Annual Analysis:
   - Dengue 7 Indian States (OpenDengue v1.3, 1997-2024, N=28 years)
   - Train: 2015-2022 (8 years) | Holdout: 2023-2024 (2 years, 14 predictions)
   - Malaria National Series (NCVBDC, 1995-2024, N=30 years)
   - Train: 1995-2020 (26 years) | Holdout: 2021-2024 (4 years, horizon h=1..4)
3. Suppression Accounting for Series with Inadequate Data:
   - Pathogens / frequencies with N < 12 consecutive observations strictly retained as SUPPRESSED_INSUFFICIENT_BASELINE.
"""

from pathlib import Path
import sys
sys.path.insert(0, "src")

import json
from datetime import datetime, timezone
import numpy as np
import pandas as pd

from episense.forecasting.models import (
    SeasonalNaiveForecaster,
    PoissonGLMForecaster,
    NegativeBinomialForecaster,
    EnsembleForecaster,
)
from episense.forecasting.evaluation import compute_interval_score

EVAL_OUTPUT_PATH = Path("data/benchmarks/forecasting_evaluation_results.json")
EVAL_OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)

models = {
    "Seasonal Naive / Persistence": lambda: SeasonalNaiveForecaster(),
    "Poisson GLM": lambda: PoissonGLMForecaster(autoregressive_lags=2, include_trend=True),
    "Negative Binomial GLM": lambda: NegativeBinomialForecaster(autoregressive_lags=2, include_trend=True),
    "Ensemble Forecaster": lambda: EnsembleForecaster(),
}

evaluation_summary = {
    "framework": "EpiSense Evidence-Aware Forecasting Evaluation",
    "evaluation_timestamp": datetime.now(timezone.utc).isoformat(),
    "gating_rule": "N >= 12 consecutive unbroken periodic observations strictly enforced for prospective operational forecasting",
    "frequency_breakdown": {
        "monthly_operational_forecasting": {},
        "annual_retrospective_analysis": {},
        "weekly_operational_forecasting": {
            "all_eight_diseases": {
                "eligibility": "SUPPRESSED_INSUFFICIENT_BASELINE",
                "max_consecutive_weeks": {
                    "Dengue": 11,
                    "Malaria": 1,
                    "Chikungunya": 2,
                    "Leptospirosis": 1,
                    "Cholera": 1,
                    "Acute Diarrhoeal Disease": 1,
                    "Japanese Encephalitis": 0,
                    "Scrub Typhus": 2,
                },
                "status": "All 8 priority diseases fail weekly continuity gate (< 12 unbroken weeks). Zero prospective weekly ML forecasts permitted."
            }
        }
    }
}

# =========================================================================
# 1. Monthly Malaria National Operational Forecasting Evaluation (N=22)
# =========================================================================
print("\n" + "="*80)
print("1. OPERATIONAL MONTHLY FORECASTING: MALARIA NATIONAL (NCVBDC MMIS 2024-2025)")
print("="*80)

malaria_monthly_file = Path("data/raw/official_historical_series/malaria_india_ncvbdc_monthly_2024_2025.csv")
df_mal_m = pd.read_csv(malaria_monthly_file)
y_mal_m = df_mal_m["reported_cases"].values.astype(float)
n_total = len(y_mal_m)
n_train = 16
n_holdout = 6

y_train_mal = y_mal_m[:n_train]
y_test_mal = y_mal_m[n_train:]
holdout_periods = [f"{df_mal_m['year'].iloc[i]}-{df_mal_m['month'].iloc[i]:02d}" for i in range(n_train, n_total)]

print(f"Total Observations: {n_total} months (2024-01 to 2025-10)")
print(f"Train Period: 2024-01 to 2025-04 ({n_train} months)")
print(f"Holdout Period: 2025-05 to 2025-10 ({n_holdout} months: {', '.join(holdout_periods)})")
print(f"Forecast Horizon: h = 1 to {n_holdout} months")

mal_results = {}
for m_name, m_cls in models.items():
    m = m_cls().fit(y_train_mal)
    preds = m.predict(horizon=n_holdout, last_year=2025, last_week=17, last_date=datetime(2025, 4, 30, tzinfo=timezone.utc))
    
    y_hat = np.array([p.point_estimate for p in preds])
    l95 = np.array([p.interval_95_lower for p in preds])
    u95 = np.array([p.interval_95_upper for p in preds])
    
    abs_err = np.abs(y_test_mal - y_hat)
    sq_err = (y_test_mal - y_hat) ** 2
    mape = np.mean(abs_err / np.maximum(y_test_mal, 1.0)) * 100.0
    
    cov95 = np.mean((l95 <= y_test_mal) & (y_test_mal <= u95)) * 100.0
    winklers = [compute_interval_score(yt, l, u, alpha=0.05) for yt, l, u in zip(y_test_mal, l95, u95)]
    
    mae = float(np.mean(abs_err))
    rmse = float(np.sqrt(np.mean(sq_err)))
    mean_w95 = float(np.mean(u95 - l95))
    mean_winkler = float(np.mean(winklers))
    
    mal_results[m_name] = {
        "mae": round(mae, 2),
        "rmse": round(rmse, 2),
        "mape_percent": round(mape, 2),
        "coverage_95_percent": round(cov95, 1),
        "mean_interval_width_95": round(mean_w95, 2),
        "mean_winkler_score": round(mean_winkler, 2),
        "predictions": [
            {
                "period": p_str,
                "y_true": int(yt),
                "y_pred": round(float(yh), 1),
                "lower_95": round(float(l), 1),
                "upper_95": round(float(u), 1),
                "covered_95": bool(l <= yt <= u),
                "abs_err": round(float(abs(yt - yh)), 1),
                "winkler": round(float(w), 1)
            }
            for p_str, yt, yh, l, u, w in zip(holdout_periods, y_test_mal, y_hat, l95, u95, winklers)
        ]
    }
    print(f"  {m_name:<30}: MAE = {mae:>8.2f} | RMSE = {rmse:>8.2f} | MAPE = {mape:>5.1f}% | 95% Cov = {cov95:>5.1f}% | Winkler = {mean_winkler:>9.2f}")

evaluation_summary["frequency_breakdown"]["monthly_operational_forecasting"]["malaria_national"] = {
    "series_id": "malaria:national:monthly:ncvbdc",
    "disease": "Malaria",
    "target_variable": "Total Positive Cases (TPC: BSE + RDT)",
    "target_unit": "cases",
    "geographic_level": "National (India)",
    "total_observations": n_total,
    "consecutive_unbroken_periods": n_total,
    "training_period": "2024-01 to 2025-04 (16 months)",
    "holdout_period": "2025-05 to 2025-10 (6 months)",
    "forecast_horizon": "6 months",
    "eligibility_decision": "GO",
    "evaluation_metrics": mal_results
}

# =========================================================================
# 2. Retrospective Annual Analysis: Dengue 7 Indian States (1997-2024, N=28)
# =========================================================================
print("\n" + "="*80)
print("2. RETROSPECTIVE ANNUAL ANALYSIS: DENGUE 7 STATES (OPENDENGUE V1.3)")
print("="*80)

states = ["Delhi", "Kerala", "Tamil Nadu", "Maharashtra", "Karnataka", "Gujarat", "Rajasthan"]
df_dengue_sp = pd.read_csv("data/raw/opendengue_india_spatial.csv")
df_dengue_sp["Year"] = pd.to_numeric(df_dengue_sp["Year"], errors="coerce")
df_dengue_sp["dengue_total"] = pd.to_numeric(df_dengue_sp["dengue_total"], errors="coerce").fillna(0.0)

dengue_holdout_records = []
dengue_state_metrics = {m: [] for m in models}

for state in states:
    sdf = df_dengue_sp[
        (df_dengue_sp["adm_1_name"].str.upper() == state.upper()) &
        (df_dengue_sp["Year"] >= 2015) &
        (df_dengue_sp["Year"] <= 2024)
    ].sort_values("Year")
    y = sdf["dengue_total"].values
    if len(y) < 10:
        continue
    y_tr = y[:8]   # 2015-2022
    y_te = y[8:]   # 2023-2024 (2 years)

    for m_name, m_cls in models.items():
        m = m_cls().fit(y_tr)
        preds = m.predict(horizon=2, last_year=2022, last_week=52, last_date=datetime(2022, 12, 31, tzinfo=timezone.utc))
        for step, (yr, yt, p) in enumerate(zip([2023, 2024], y_te, preds)):
            l95 = p.interval_95_lower
            u95 = p.interval_95_upper
            w = compute_interval_score(yt, l95, u95, alpha=0.05)
            dengue_holdout_records.append({
                "model": m_name,
                "state": state,
                "year": yr,
                "y_true": float(yt),
                "y_pred": float(p.point_estimate),
                "lower95": float(l95),
                "upper95": float(u95),
                "covered95": bool(l95 <= yt <= u95),
                "abs_err": float(abs(yt - p.point_estimate)),
                "sq_err": float((yt - p.point_estimate) ** 2),
                "winkler": float(w),
            })

df_dengue_eval = pd.DataFrame(dengue_holdout_records)
dengue_summary_metrics = {}
for m_name in models:
    sub = df_dengue_eval[df_dengue_eval["model"] == m_name]
    mae = float(sub["abs_err"].mean())
    rmse = float(np.sqrt(sub["sq_err"].mean()))
    cov95 = float(sub["covered95"].mean() * 100.0)
    winkler = float(sub["winkler"].mean())
    dengue_summary_metrics[m_name] = {
        "mae": round(mae, 2),
        "rmse": round(rmse, 2),
        "coverage_95_percent": round(cov95, 1),
        "mean_winkler_score": round(winkler, 2),
        "predictions_count": len(sub),
    }
    print(f"  {m_name:<30}: MAE = {mae:>10.2f} | Pooled RMSE = {rmse:>10.2f} | 95% Cov = {cov95:>5.1f}% | Winkler = {winkler:>11.2f}")

evaluation_summary["frequency_breakdown"]["annual_retrospective_analysis"]["dengue_seven_states"] = {
    "series_id": "dengue:seven_states:annual:opendengue",
    "disease": "Dengue",
    "states_evaluated": states,
    "target_variable": "Reported Dengue Total",
    "target_unit": "cases",
    "geographic_level": "State (7 Major Indian States)",
    "training_period": "2015-2022 (8 years per state)",
    "holdout_period": "2023-2024 (2 years per state = 14 predictions)",
    "forecast_horizon": "2 years",
    "eligibility_decision": "RETROSPECTIVE_EVALUATED_ONLY (Operational forecasting suppressed: 50% empirical coverage under post-COVID surge)",
    "evaluation_metrics": dengue_summary_metrics
}

# =========================================================================
# 3. Retrospective Annual Analysis: Malaria National (1995-2024, N=30)
# =========================================================================
print("\n" + "="*80)
print("3. RETROSPECTIVE ANNUAL ANALYSIS: MALARIA NATIONAL (NCVBDC 1995-2024)")
print("="*80)

malaria_annual_file = Path("data/raw/official_historical_series/malaria_india_ncvbdc_1995_2024.csv")
df_mal_a = pd.read_csv(malaria_annual_file)
y_mal_a = df_mal_a["reported_cases"].values.astype(float)
n_ann = len(y_mal_a)
n_tr_a = 26  # 1995-2020
n_te_a = 4   # 2021-2024

y_tr_mal_a = y_mal_a[:n_tr_a]
y_te_mal_a = y_mal_a[n_tr_a:]
holdout_years = list(df_mal_a["year"].iloc[n_tr_a:])

mal_a_results = {}
for m_name, m_cls in models.items():
    m = m_cls().fit(y_tr_mal_a)
    preds = m.predict(horizon=n_te_a, last_year=2020, last_week=52, last_date=datetime(2020, 12, 31, tzinfo=timezone.utc))
    
    y_hat = np.array([p.point_estimate for p in preds])
    l95 = np.array([p.interval_95_lower for p in preds])
    u95 = np.array([p.interval_95_upper for p in preds])
    
    abs_err = np.abs(y_te_mal_a - y_hat)
    sq_err = (y_te_mal_a - y_hat) ** 2
    cov95 = np.mean((l95 <= y_te_mal_a) & (y_te_mal_a <= u95)) * 100.0
    winklers = [compute_interval_score(yt, l, u, alpha=0.05) for yt, l, u in zip(y_te_mal_a, l95, u95)]
    
    mae = float(np.mean(abs_err))
    rmse = float(np.sqrt(np.mean(sq_err)))
    winkler = float(np.mean(winklers))
    
    mal_a_results[m_name] = {
        "mae": round(mae, 2),
        "rmse": round(rmse, 2),
        "coverage_95_percent": round(cov95, 1),
        "mean_winkler_score": round(winkler, 2),
    }
    print(f"  {m_name:<30}: MAE = {mae:>10.2f} | RMSE = {rmse:>10.2f} | 95% Cov = {cov95:>5.1f}% | Winkler = {winkler:>11.2f}")

evaluation_summary["frequency_breakdown"]["annual_retrospective_analysis"]["malaria_national"] = {
    "series_id": "malaria:national:annual:ncvbdc",
    "disease": "Malaria",
    "target_variable": "Total Reported Malaria Cases",
    "target_unit": "cases",
    "geographic_level": "National (India)",
    "training_period": "1995-2020 (26 years)",
    "holdout_period": "2021-2024 (4 years: 2021, 2022, 2023, 2024)",
    "forecast_horizon": "4 years",
    "eligibility_decision": "RETROSPECTIVE_EVALUATED_ONLY",
    "evaluation_metrics": mal_a_results
}

# Save results
with open(EVAL_OUTPUT_PATH, "w", encoding="utf-8") as f:
    json.dump(evaluation_summary, f, indent=2)

print(f"\nSaved comprehensive evaluation report to {EVAL_OUTPUT_PATH}")

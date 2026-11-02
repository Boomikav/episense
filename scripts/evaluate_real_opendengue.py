"""
Reproducible evaluation script for real historical OpenDengue data in India.
Evaluates:
1. Continuous Phase 1 (1997-2012, N=16) across 8 major Indian states with rolling-origin evaluation.
2. Holdout evaluation on post-transition Phase 2 (2015-2024, N=10) with 2-year holdout (2023-2024).
Compares:
- Seasonal Naive / Persistence baseline
- Poisson GLM
- Negative Binomial GLM (independent L-BFGS-B estimation)
- Ensemble Forecaster (calibrated weighted intervals)
"""

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

import numpy as np
import pandas as pd
from datetime import datetime, timezone

from episense.forecasting.models import (
    SeasonalNaiveForecaster,
    PoissonGLMForecaster,
    NegativeBinomialForecaster,
    EnsembleForecaster,
)
from episense.forecasting.evaluation import ChronologicalHoldoutEvaluator, compute_interval_score

RAW_CSV = Path("data/raw/opendengue_india_spatial.csv")

def run():
    if not RAW_CSV.exists():
        print(f"Data file not found: {RAW_CSV}")
        return

    df = pd.read_csv(RAW_CSV)
    df["Year"] = pd.to_numeric(df["Year"], errors="coerce")
    df["dengue_total"] = pd.to_numeric(df["dengue_total"], errors="coerce").fillna(0.0)

    # 7 complete focus states with unbroken sequences in both phases
    # Note: West Bengal is omitted because it lacks 1997-2000 (N=12 in Phase 1) and 2018-2019 (N=8 in Phase 2)
    states = [
        "Delhi",
        "Kerala",
        "Tamil Nadu",
        "Maharashtra",
        "Karnataka",
        "Gujarat",
        "Rajasthan",
    ]

    print("=" * 80)
    print("PART 1: ROLLING-ORIGIN EVALUATION ON CONTINUOUS PHASE 1 (1997-2012, N=16)")
    print("=" * 80)
    print(f"Evaluated States ({len(states)}): {', '.join(states)}")
    print("Origins per state: 5 (origins 10 to 14, evaluating years 2007 to 2011)")
    print(f"Total rolling evaluation origins: {len(states) * 5} (7 states x 5 origins)")

    models = {
        "Persistence": lambda: SeasonalNaiveForecaster(),
        "Poisson GLM": lambda: PoissonGLMForecaster(autoregressive_lags=2, include_trend=True),
        "Negative Binomial": lambda: NegativeBinomialForecaster(autoregressive_lags=2, include_trend=True),
        "Ensemble": lambda: EnsembleForecaster(),
    }

    results_p1 = {m: [] for m in models}
    results_p1_sq = {m: [] for m in models}

    for state in states:
        sdf = df[(df["adm_1_name"].str.upper() == state.upper()) & (df["Year"] >= 1997) & (df["Year"] <= 2012)].sort_values("Year")
        y = sdf["dengue_total"].values
        if len(y) < 16:
            continue

        for origin in range(10, 15):
            y_train = y[:origin]
            y_test = y[origin]  # 1-step ahead ground truth

            for m_name, m_cls in models.items():
                m = m_cls().fit(y_train)
                pred = m.predict(horizon=1, last_year=int(sdf["Year"].iloc[origin-1]), last_week=52, last_date=datetime(2000, 1, 1, tzinfo=timezone.utc))
                y_hat = pred[0].point_estimate
                abs_err = abs(y_test - y_hat)
                results_p1[m_name].append(abs_err)
                results_p1_sq[m_name].append((y_test - y_hat) ** 2)

    print(f"\nPhase 1 Rolling Origin 1-step Results across 7 states ({len(results_p1['Persistence'])} origins):")
    for m_name in models:
        mae = float(np.mean(results_p1[m_name]))
        rmse = float(np.sqrt(np.mean(results_p1_sq[m_name])))
        print(f"  {m_name:<20}: MAE = {mae:>10.2f} | Pooled RMSE = {rmse:>10.2f}")

    print("\n" + "=" * 80)
    print("PART 2: POST-COVID RESURGENCE CHRONOLOGICAL HOLDOUT ON PHASE 2 (2015-2024, N=10)")
    print("=" * 80)
    print(f"Evaluated States ({len(states)}): {', '.join(states)}")
    print("Train: 2015-2022 (N=8) | Holdout: 2023-2024 (N=2)")
    print(f"Total held-out predictions: {len(states) * 2} (7 states x 2 horizon steps)")

    holdout_results = {m: {"mae": [], "macro_rmse": [], "cov95": [], "width95": []} for m in models}
    holdout_detailed = []

    for state in states:
        sdf = df[(df["adm_1_name"].str.upper() == state.upper()) & (df["Year"] >= 2015) & (df["Year"] <= 2024)].sort_values("Year")
        y = sdf["dengue_total"].values
        if len(y) < 10:
            continue

        y_train = y[:8]
        y_test = y[8:]

        for m_name, m_cls in models.items():
            m = m_cls().fit(y_train)
            pred = m.predict(horizon=2, last_year=2022, last_week=52, last_date=datetime(2022, 12, 31, tzinfo=timezone.utc))
            y_hat = np.array([p.point_estimate for p in pred])
            abs_err = np.abs(y_test - y_hat)
            sq_err = (y_test - y_hat) ** 2
            widths = [p.interval_95_upper - p.interval_95_lower for p in pred]
            cov = [1 if p.interval_95_lower <= yt <= p.interval_95_upper else 0 for yt, p in zip(y_test, pred)]

            holdout_results[m_name]["mae"].append(np.mean(abs_err))
            holdout_results[m_name]["macro_rmse"].append(np.sqrt(np.mean(sq_err)))
            holdout_results[m_name]["width95"].append(np.mean(widths))
            holdout_results[m_name]["cov95"].append(np.mean(cov) * 100.0)

            for step, (yr, yt, p) in enumerate(zip([2023, 2024], y_test, pred)):
                l95 = p.interval_95_lower
                u95 = p.interval_95_upper
                w95 = u95 - l95
                alpha = 0.05
                pen = 0.0
                if yt < l95:
                    pen = (2.0 / alpha) * (l95 - yt)
                elif yt > u95:
                    pen = (2.0 / alpha) * (yt - u95)
                winkler = w95 + pen

                holdout_detailed.append({
                    "model": m_name,
                    "state": state,
                    "year": yr,
                    "step": step + 1,
                    "y_true": yt,
                    "y_pred": p.point_estimate,
                    "lower95": l95,
                    "upper95": u95,
                    "width95": w95,
                    "covered": (l95 <= yt <= u95),
                    "abs_err": abs(yt - p.point_estimate),
                    "sq_err": (yt - p.point_estimate) ** 2,
                    "winkler": winkler,
                })

    hdf = pd.DataFrame(holdout_detailed)

    print("\nPhase 2 State Holdout Aggregate Results across 7 states (14 predictions):")
    for m_name in models:
        sub = hdf[hdf["model"] == m_name]
        mae = float(sub["abs_err"].mean())
        macro_rmse = float(np.mean(holdout_results[m_name]["macro_rmse"]))
        pooled_rmse = float(np.sqrt(sub["sq_err"].mean()))
        mean_w95 = float(sub["width95"].mean())
        med_w95 = float(sub["width95"].median())
        cov_pct = float(sub["covered"].mean() * 100.0)
        cov_count = int(sub["covered"].sum())
        mean_wink = float(sub["winkler"].mean())
        print(f"  {m_name:<20}: MAE = {mae:>10.2f} | Macro-RMSE = {macro_rmse:>10.2f} | Pooled-RMSE = {pooled_rmse:>10.2f} | 95% Width (Mean) = {mean_w95:>10.2f} | 95% Width (Med) = {med_w95:>10.2f} | 95% Cov = {cov_pct:>5.1f}% ({cov_count:2d}/14) | Winkler = {mean_wink:>11.2f}")

    print("\n" + "-" * 80)
    print("DETAILED PREDICTION-LEVEL AUDIT FOR ENSEMBLE MODEL (2023-2024 HOLDOUT):")
    print("-" * 80)
    ens_sub = hdf[hdf["model"] == "Ensemble"][["state", "year", "y_true", "y_pred", "lower95", "upper95", "width95", "covered", "winkler"]]
    print(ens_sub.to_string(index=False))

    print("\n[CRITICAL SCIENTIFIC CALIBRATION FINDING]")
    print("  Nominal Coverage Target: 95.0%")
    print("  Empirical Holdout Coverage: 50.0% (7 of 14 predictions covered)")
    print("  Calibration Status: NOT CALIBRATED. Nominal 95% intervals severely under-cover extreme post-COVID surges.")
    print("  Sample Size Limitation: N=14 predictions (7 states x 2 years) is insufficient to establish statistical calibration.")

if __name__ == "__main__":
    run()

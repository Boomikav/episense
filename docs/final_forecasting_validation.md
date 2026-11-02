# EpiSense — Authoritative Forecasting Validation, Metric Reconciliation, and Interval Calibration Report

**Project Title:** EpiSense: An Evidence-Aware Framework for Multisource Disease Surveillance and Conditional Early Warning  
**Repository Path:** `C:\Users\ajaya\Desktop\NLP`  
**Date of Audit:** October 28, 2026  
**Auditor:** Senior Public-Health Data Scientist & Epidemiological Forecasting Lead  
**Governing Code & Evidence Artifacts:**
- Script: [`scripts/evaluate_real_opendengue.py`](file:///C:/Users/ajaya/Desktop/NLP/scripts/evaluate_real_opendengue.py)
- Consistency Checker: [`scripts/check_winkler_consistency.py`](file:///C:/Users/ajaya/Desktop/NLP/scripts/check_winkler_consistency.py)
- Primary Spatial Data: [`data/raw/opendengue_india_spatial.csv`](file:///C:/Users/ajaya/Desktop/NLP/data/raw/opendengue_india_spatial.csv) (`SHA-256: f52d72513d3c7132830b18732ef4779aef9641245e955d80c97f9098c733115a`)
- Prior Metric Reconciliation: [`docs/forecasting_metric_reconciliation.md`](file:///C:/Users/ajaya/Desktop/NLP/docs/forecasting_metric_reconciliation.md)

---

## 1. Executive Reconciliation & Numerical Discrepancy Resolution

Earlier draft reports cited conflicting metrics:
- **Discrepant / Draft Claim:** Ensemble MAE = 6,676, Baseline MAE = 10,000, Winkler = 17,998.4 on "eight Indian states."
- **Authoritative Verified Result:** Ensemble MAE = 10,752.21, Persistence MAE = 8,342.14, Mean Winkler = 224,985.61 on **seven Indian states** ($N=14$ predictions).

### Formal Resolution of the Discrepancy
1. **Origin of the 6,676 / 10,000 Figure:** The 6,676 vs 10,000 figure was generated in an early draft exploration that inverted comparison baselines and applied heuristic post-processing. It cannot be reproduced from the canonical OpenDengue source data and is **formally withdrawn**.
2. **State Selection ($K=7$, Not 8):** The analysis evaluated 8 focus states: Delhi, Kerala, Tamil Nadu, Maharashtra, Karnataka, Gujarat, Rajasthan, and West Bengal. However, **West Bengal contains missing observations for 2018–2019** ($N=8 < 10$ in Phase 2) and was dropped by the filter `if len(y) < 10: continue`. Exactly **7 states** meet the continuous sample requirement.
3. **Model Ranking During Resurgence:** During the severe post-COVID epidemic surge (2023–2024), the naive **Persistence Baseline achieved lower point error (MAE: 8,342.14)** than parametric GLMs (MAE: 11,380.03 to 11,412.90) and the Ensemble (MAE: 10,752.21). Persistence projects the elevated 2022 baseline directly, whereas count autoregressions trained on 2015–2022 underpredicted the magnitude of the 2023–2024 post-pandemic resurgence shock.
4. **Winkler Score Reconciliation:** The Mean Winkler score is **224,985.61** (Median: 31,364.66). The high mean score is directly driven by the large penalty ($40 \times (y - U_{95})$) on the 7 under-covered resurgence surge observations (e.g. Tamil Nadu 2024 with 27,378 observed vs 12,317 upper bound).

---

## 2. Authoritative Phase 2 Post-COVID Resurgence Holdout Table (2015–2024)

### Evaluation Protocol
- **Source Data:** `opendengue_india_spatial.csv` (`SHA-256: f52d72513d3c...`)
- **Evaluated States (7):** Delhi, Kerala, Tamil Nadu, Maharashtra, Karnataka, Gujarat, Rajasthan.
- **Training Window:** 2015–2022 ($N_{\text{train}} = 8$ annual observations per state).
- **Holdout Test Window:** 2023–2024 ($N_{\text{test}} = 2$ annual observations per state, horizon steps $h=1, 2$).
- **Total Predictions:** $7 \text{ states} \times 2 \text{ horizon steps} = \mathbf{14} \text{ predictions}$.
- **Zero Data Leakage:** Feature scaling, autoregressive lag creation, and model parameter optimization were conducted strictly on pre-2023 data. The holdout was not used to fit models, tune ensemble weights, or calibrate interval bounds.

### Authoritative 4-Model Comparative Master Table

| Model | Specification | Holdout MAE | Macro-RMSE | Pooled-RMSE | 95% Width (Mean) | 95% Width (Median) | Nominal Coverage | Empirical Coverage | Mean Interval Score (Winkler) | Median Interval Score (Winkler) |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Persistence (Naive)** | $\hat{y}_{t+h} = y_t$ | **8,342.14** | **9,181.63** | **11,243.96** | 28,500.90 | 28,525.85 | 95.0% | **100.0% (14/14)** | **28,500.90** | **28,525.85** |
| **Poisson GLM** | Lags=2, Trend=True | 11,412.90 | 12,114.68 | 13,654.48 | 276.86 | 246.00 | 95.0% | **0.0% (0/14)** | 451,239.71 | 433,526.48 |
| **Negative Binomial** | Lags=2, Trend=True, L-BFGS-B | 11,380.03 | 12,086.34 | 13,607.62 | 13,118.86 | 10,541.00 | 95.0% | **42.9% (6/14)** | 296,064.57 | 185,550.00 |
| **Ensemble** | 0.5 NB + 0.3 Poi + 0.2 Naive | **10,752.21** | **11,474.70** | **13,076.30** | **12,342.66** | **10,733.75** | **95.0%** | **50.0% (7/14)** | **224,985.61** | **31,364.66** |

---

## 3. Exact Prediction-Level Breakdown for Ensemble Model

$$\text{Winkler Score} = (U_{95} - L_{95}) + \frac{2}{\alpha}(L_{95} - y)\mathbb{I}(y < L_{95}) + \frac{2}{\alpha}(y - U_{95})\mathbb{I}(y > U_{95}), \quad \alpha = 0.05 \implies \frac{2}{\alpha} = 40.0$$

| State | Year | Step | Observed ($y$) | Forecast ($\hat{y}$) | 95% Lower | 95% Upper | 95% Width | Covered? | Winkler Score | Absolute Error |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Delhi** | 2023 | 1 | 16,866 | 2,617.26 | 266.00 | 5,840.84 | 5,574.84 | **False** | 446,581.24 | 14,248.74 |
| **Delhi** | 2024 | 2 | 10,585 | 5,104.94 | 1,452.80 | 11,816.67 | 10,363.87 | **True** | 10,363.87 | 5,480.06 |
| **Kerala** | 2023 | 1 | 17,426 | 2,374.66 | 946.10 | 6,162.61 | 5,216.51 | **False** | 455,752.11 | 15,051.34 |
| **Kerala** | 2024 | 2 | 20,674 | 2,398.31 | 975.50 | 7,443.58 | 6,468.08 | **False** | 535,684.88 | 18,275.69 |
| **Tamil Nadu** | 2023 | 1 | 9,121 | 3,448.27 | 1,214.90 | 9,227.07 | 8,012.17 | **True** | 8,012.17 | 5,672.73 |
| **Tamil Nadu** | 2024 | 2 | 27,378 | 4,242.81 | 1,682.90 | 12,317.91 | 10,635.01 | **False** | 613,038.61 | 23,135.19 |
| **Maharashtra** | 2023 | 1 | 19,034 | 8,925.32 | 3,396.20 | 18,467.04 | 15,070.84 | **False** | 37,749.24 | 10,108.68 |
| **Maharashtra** | 2024 | 2 | 19,385 | 9,070.30 | 3,464.20 | 19,758.73 | 16,294.53 | **True** | 16,294.53 | 10,314.70 |
| **Karnataka** | 2023 | 1 | 19,300 | 5,196.23 | 1,920.70 | 10,929.84 | 9,009.14 | **False** | 343,815.54 | 14,103.77 |
| **Karnataka** | 2024 | 2 | 32,886 | 8,625.83 | 3,975.60 | 17,977.15 | 14,001.55 | **False** | 610,355.55 | 24,260.17 |
| **Gujarat** | 2023 | 1 | 7,222 | 4,087.47 | 1,061.80 | 11,894.28 | 10,832.48 | **True** | 10,832.48 | 3,134.53 |
| **Gujarat** | 2024 | 2 | 7,891 | 7,859.92 | 2,518.60 | 23,175.54 | 20,656.94 | **True** | 20,656.94 | 31.08 |
| **Rajasthan** | 2023 | 1 | 13,924 | 9,080.32 | 3,043.00 | 18,724.27 | 15,681.27 | **True** | 15,681.27 | 4,843.68 |
| **Rajasthan** | 2024 | 2 | 12,514 | 14,384.58 | 5,591.60 | 30,571.68 | 24,980.08 | **True** | 24,980.08 | 1,870.58 |

---

## 4. Phase 1 Rolling-Origin Evaluation (1997–2012, $N=16$, Stable Endemic Period)

Across the stable endemic period prior to the 2013–2014 data hiatus, evaluated across 35 rolling forecast origins ($7 \text{ states} \times 5 \text{ origins}$):
- **Persistence (Naive)**: **MAE = 947.17** | Pooled RMSE = 1,520.11 (Lowest Error)
- **Poisson GLM**: MAE = 1,257.38 | Pooled RMSE = 1,870.42
- **Negative Binomial**: MAE = 1,925.07 | Pooled RMSE = 4,016.00
- **Ensemble**: MAE = 1,482.24 | Pooled RMSE = 2,420.35

In stable endemic regimes, simple persistence consistently outperforms parametric count models.

---

## 5. Critical Uncertainty Calibration Findings & Scientific Limitations

1. **Prediction Interval Calibration Failure:**
   - Empirical coverage on Phase 2 holdout is **50.0% (7 of 14 covered)** against a 95.0% nominal target.
   - **Status:** **CALIBRATION NOT DEMONSTRATED**. Intervals constructed from historical endemic baselines cannot accommodate extreme post-pandemic resurgence shocks. All 7 missed predictions failed at the upper bound.
2. **Equidispersion Failure of Poisson GLM:**
   - Yielded an artificially narrow mean interval width of only **276.86 cases** and **0.0% coverage (0/14)**, failing due to severe overdispersion ($\text{Var}(Y) \gg \mathbb{E}[Y]$).
3. **Sample Size Constraint:**
   - $N=14$ observations across 7 states is statistically insufficient to prove calibrated intervals.
   - Prospective warning effectiveness or generalizable resurgence calibration cannot be claimed from this retrospective evaluation.

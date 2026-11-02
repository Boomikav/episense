# EpiSense Forecasting Metric Reconciliation & Provenance Audit

**Audit Date:** 2026-10-27  
**Auditor:** Senior Public-Health Data Scientist & Epidemiological Forecasting Lead  
**Governing Standard:** Reproducible Computational Epidemiology & Peer Review Standards  
**Authoritative Evidence Artifacts:**
- [`scripts/evaluate_real_opendengue.py`](file:///C:/Users/ajaya/Desktop/NLP/scripts/evaluate_real_opendengue.py)
- [`scripts/verify_model_corrections.py`](file:///C:/Users/ajaya/Desktop/NLP/scripts/verify_model_corrections.py)
- [`data/raw/opendengue_india_spatial.csv`](file:///C:/Users/ajaya/Desktop/NLP/data/raw/opendengue_india_spatial.csv)
- [`data/raw/opendengue_india_temporal.csv`](file:///C:/Users/ajaya/Desktop/NLP/data/raw/opendengue_india_temporal.csv)

---

## 1. Executive Reconciliation Summary

Earlier reports recorded divergent forecasting metrics (e.g., persistence MAE of 1,449.32 vs 947.17; ensemble interval widths of 55,815 vs 12,342 vs 6,056; references to 40 rolling origins across 8 states vs 35 origins across 7 states; references to 16 holdout predictions vs 14 predictions). Rather than selecting whichever metric appears most favorable, this audit establishes the exact data origin, missing-year handling, sample partitioning, model configuration, and mathematical aggregation behind every reported figure.

### Key Forensic Findings:

1. **State Counts & Missing-Year Handling (Why 7 States, Not 8):**
   - The analysis selected 8 focus states: Delhi, Kerala, Tamil Nadu, Maharashtra, Karnataka, West Bengal, Gujarat, and Rajasthan.
   - Forensic inspection of `opendengue_india_spatial.csv` reveals that **7 states** (Delhi, Kerala, Tamil Nadu, Maharashtra, Karnataka, Gujarat, Rajasthan) have **exactly 26 annual observations spanning 1997–2024**, missing only `[2013, 2014]` due to the institutional transition between published literature compilations and the online NCVBDC portal.
   - **West Bengal** contains only 20 total observations: it is missing 1997–2000 (starts in 2001, $N=12$ in Phase 1) and missing 2018–2019 ($N=8$ in Phase 2).
   - In [`scripts/evaluate_real_opendengue.py`](file:///C:/Users/ajaya/Desktop/NLP/scripts/evaluate_real_opendengue.py), length filters `if len(y) < 16: continue` (Phase 1) and `if len(y) < 10: continue` (Phase 2) skipped West Bengal.
   - Consequently, **Phase 1 evaluated exactly 7 states across 5 rolling origins each ($7 \times 5 = 35$ origins)**, NOT 40 origins.
   - **Phase 2 evaluated exactly 7 states across 2 holdout horizon steps ($7 \times 2 = 14$ predictions)**, NOT 16 predictions.
   - The previous references to "40 evaluation origins" and "16 holdout points across 8 states" were hardcoded console print labels that assumed West Bengal had been included without checking the post-filter length. The computed metrics themselves were strictly calculated over the 35 origins and 14 holdout points.

2. **The 947.17 vs 1,449.32 Persistence MAE Discrepancy:**
   - **947.17 (Authoritative / Accepted):** Evaluated strictly on the continuous, unbroken Phase 1 period (1997–2012, $N=16$) across the 7 complete states over 35 rolling forecast origins ($t = 10, 11, 12, 13, 14$, predicting 2007, 2008, 2009, 2010, 2011).
   - **1,449.32 (Historical / Superseded):** Evaluated across an unsegmented 26-observation sequence that bridged the 2013–2014 data hiatus and included origins entering the volatile post-2015 resurgence period.

3. **The 12,342.66 vs 55,815 vs 6,056.26 Ensemble Interval Widths:**
   - **55,815 cases (Superseded Outer-Envelope Heuristic):** An earlier heuristic took the union outer envelope ($\min L_m, \max U_m$) across sub-models.
   - **12,342.66 cases (Authoritative Phase 2 Holdout Across 7 States):** The mixture quantile interval ($L_{95} = \sum w_m L_{95, m}, U_{95} = \sum w_m U_{95, m}$) evaluated on the Phase 2 holdout (2023–2024) across the 7 complete states ($N=14$).
   - **6,056.26 cases (Single-State Karnataka Benchmark):** Evaluated specifically in [`scripts/reproduce_ablations.py`](file:///C:/Users/ajaya/Desktop/NLP/scripts/reproduce_ablations.py) on Karnataka state series alone, where the mixture interval width was 6,056.26 cases compared to the outer-envelope width of 46,091.81 cases.

4. **Prediction Interval Calibration Assessment:**
   - The nominal target coverage is **95.0%**.
   - The empirical holdout coverage across the 14 predictions is **50.0% (7 of 14 covered)**.
   - **These intervals are NOT calibrated.** Nominal 95% intervals severely under-cover extreme post-COVID epidemic surges (in all 7 missed predictions, true case counts exceeded the 95% upper bound).
   - The holdout sample size ($N=14$ predictions across 7 states, 2 years) is far too small to establish statistical calibration.

5. **Ensemble Weighting & Holdout Independence:**
   - Ensemble weights are fixed a priori: $w_{\text{NB}} = 0.50, w_{\text{Poisson}} = 0.30, w_{\text{Naive}} = 0.20$.
   - **No holdout data were used to optimize ensemble weights or interval bounds.** Models were fit strictly on training observations ($y \le 2022$), preserving strict out-of-sample holdout integrity.

---

## 2. Phase 1 Rolling-Origin Evaluation (1997–2012, $N=16$)

### Dataset & Partitioning:
- **Source:** `opendengue_india_spatial.csv`
- **States Evaluated ($K=7$):** Delhi, Kerala, Tamil Nadu, Maharashtra, Karnataka, Gujarat, Rajasthan. (West Bengal excluded: $N=12 < 16$, missing 1997–2000).
- **Time Span:** 1997 to 2012 ($N=16$ consecutive annual observations per state).
- **Forecast Horizon:** $h = 1$ year ahead.
- **Rolling Origins per State:** 5 origins ($t = 10, 11, 12, 13, 14$):
  - Origin 10: Train on 1997–2006 ($N=10$), predict 2007 ($y_{\text{true}} = y_{10}$).
  - Origin 11: Train on 1997–2007 ($N=11$), predict 2008 ($y_{\text{true}} = y_{11}$).
  - Origin 12: Train on 1997–2008 ($N=12$), predict 2009 ($y_{\text{true}} = y_{12}$).
  - Origin 13: Train on 1997–2009 ($N=13$), predict 2010 ($y_{\text{true}} = y_{13}$).
  - Origin 14: Train on 1997–2010 ($N=14$), predict 2011 ($y_{\text{true}} = y_{14}$).
- **Total Evaluation Origins:** $7 \text{ states} \times 5 \text{ origins} = \mathbf{35} \text{ origins}$.

### Phase 1 Results:

$$\text{MAE} = \frac{1}{35} \sum_{i=1}^{35} |y_i - \hat{y}_i|, \quad \text{Pooled RMSE} = \sqrt{\frac{1}{35} \sum_{i=1}^{35} (y_i - \hat{y}_i)^2}$$

| Model | Specification | 1-Step Ahead MAE | Pooled RMSE | Scientific Takeaway |
| :--- | :--- | :---: | :---: | :--- |
| **Persistence (Seasonal Naive)** | $\hat{y}_{t+1} = y_t$ | **947.17** | **1,520.11** | **Lowest Error (Best)**. In stable endemic conditions, persistence outperforms complex count models. |
| **Poisson GLM** | Lags=2, Trend=True | **1,257.38** | **1,870.42** | Over-reacts to local fluctuations relative to persistence. |
| **Negative Binomial (NB2)** | Lags=2, Trend=True, L-BFGS-B | **1,925.07** | **4,016.00** | Over-dispersed variance causes wider parameter drift on small $N \le 14$ samples. |
| **Ensemble** | 0.5 NB + 0.3 Poi + 0.2 Naive | **1,482.24** | **2,420.35** | Blends GLMs with persistence, intermediate error. |

---

## 3. Phase 2 Post-COVID Resurgence Holdout (2015–2024, $N=10$)

### Dataset & Partitioning:
- **Source:** `opendengue_india_spatial.csv`
- **States Evaluated ($K=7$):** Delhi, Kerala, Tamil Nadu, Maharashtra, Karnataka, Gujarat, Rajasthan. (West Bengal excluded: $N=8 < 10$, missing 2018–2019).
- **Time Span:** 2015 to 2024 ($N=10$ consecutive annual observations per state).
- **Training Set:** 2015–2022 ($N_{\text{train}} = 8$ years per state).
- **Holdout Testing Set:** 2023 and 2024 ($N_{\text{test}} = 2$ years per state, horizon steps $h=1$ and $h=2$).
- **Total Held-Out Predictions:** $7 \text{ states} \times 2 \text{ horizon steps} = \mathbf{14} \text{ predictions}$.

### Exact Prediction-Level Results for Ensemble Forecaster:

$$\text{Winkler Score} = (U_{95} - L_{95}) + \frac{2}{\alpha}(L_{95} - y)\mathbb{I}(y < L_{95}) + \frac{2}{\alpha}(y - U_{95})\mathbb{I}(y > U_{95}), \quad \alpha = 0.05 \implies \frac{2}{\alpha} = 40$$

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

## 4. Phase 2 4-Model Comparative Master Table

Aggregation procedures:
- $\text{MAE} = \frac{1}{14} \sum_{i=1}^{14} |y_i - \hat{y}_i|$
- $\text{Macro-RMSE} = \frac{1}{7} \sum_{s=1}^7 \sqrt{\frac{1}{2} \sum_{h=1}^2 (y_{s, h} - \hat{y}_{s, h})^2}$
- $\text{Pooled-RMSE} = \sqrt{\frac{1}{14} \sum_{i=1}^{14} (y_i - \hat{y}_i)^2}$

| Model | MAE | Macro-RMSE | Pooled-RMSE | 95% Width (Mean) | 95% Width (Median) | Nominal Coverage | Empirical Coverage | Mean Interval Score (Winkler) | Median Interval Score (Winkler) |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Persistence** | **8,342.14** | **9,181.63** | **11,243.96** | 28,500.90 | 28,525.85 | 95.0% | **100.0% (14/14)** | **28,500.90** | **28,525.85** |
| **Poisson GLM** | 11,412.90 | 12,114.68 | 13,654.48 | 276.86 | 246.00 | 95.0% | **0.0% (0/14)** | 451,239.71 | 433,526.48 |
| **Negative Binomial** | 11,380.03 | 12,086.34 | 13,607.62 | 13,118.86 | 10,541.00 | 95.0% | **42.9% (6/14)** | 296,064.57 | 185,550.00 |
| **Ensemble** | **10,752.21** | **11,474.70** | **13,076.30** | **12,342.66** | **10,733.75** | **95.0%** | **50.0% (7/14)** | **224,985.61** | **31,364.66** |

---

## 5. Critical Scientific Calibration Assessment

1. **Empirical Coverage vs Nominal Target:**
   - Nominal Target: **95.0%**.
   - Empirical Holdout Coverage: **50.0% (7 of 14 predictions covered)**.
   - Status: **CALIBRATION NOT DEMONSTRATED**. The intervals must NOT be claimed as calibrated.
   - Rationale: In severe post-COVID epidemic surge conditions (2023–2024), true case counts surged well beyond the variance estimated from the quiescent 2015–2022 baseline. All 7 missed predictions failed at the upper bound.
   - Generalization Boundary: These retrospective holdout results reflect tested behavior on two held-out years in 7 Indian states; they cannot be assumed to generalize to other surge regimes, geographical areas, or pathogens.

2. **Equidispersion Failure of Poisson GLM:**
   - Poisson GLM yielded a mean interval width of only **276.86 cases** and **0.0% empirical coverage (0/14)**.
   - Under Poisson assumptions, $\text{Var}(Y) = \mu$. When empirical variance is hundreds of times the mean ($\alpha > 0$), Poisson bounds are artificially narrow and collapse completely.

3. **Sample Size Limitations & Exact Winkler Aggregation:**
   - $N=14$ predictions across 7 states is insufficient to establish asymptotic prediction interval calibration. Establishing formal empirical calibration for extreme quantiles ($\alpha = 0.05$) requires hundreds of observations across multiple epidemic seasons.
   - Exact Winkler aggregation verified:
     $$\text{Winkler Score} = (U_{95} - L_{95}) + \frac{2}{\alpha}(L_{95} - y)\mathbb{I}(y < L_{95}) + \frac{2}{\alpha}(y - U_{95})\mathbb{I}(y > U_{95})$$
     With $\alpha = 0.05 \implies \frac{2}{\alpha} = 40.0$.
     Sum across all 14 rows = $3,149,798.51$. Mean = $3,149,798.51 / 14 = \mathbf{224,985.61}$. Median = $\mathbf{31,364.66}$.
     Zero discrepancy was found between the row-level table and the reported aggregate metrics.

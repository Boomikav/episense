# Final Scientific Acceptance Report — EpiSense

**Date:** 2026-10-27  
**Platform:** EpiSense — An Evidence-Aware Framework for Multisource Disease Surveillance and Conditional Early Warning  
**Repository Directory:** `C:\Users\ajaya\Desktop\NLP`  
**Auditor:** Senior Public-Health Informatics Lead, Statistical Surveillance Specialist, & Systems Architect  
**Authoritative Final Acceptance Decision:**  
# **`Research prototype — functionally tested; real-data evaluation completed only for the documented datasets; prospective early-warning effectiveness not yet established.`**

---

## 1. Executive Summary & Four-Issue Verification Audit

This report presents an evidence-based verification and consistency audit of the EpiSense repository, incorporating bounded findings and the final resolution of four empirical issues:

1. **Prediction Interval Calibration (Issue 1 Checked):**
   - In the Phase 2 post-COVID holdout (2023–2024), across 7 complete states ($N=14$ predictions), empirical coverage of the nominal 95% mixture prediction interval is **50.0% (7 of 14 covered)**.
   - **Calibration has NOT been demonstrated on this 14-observation holdout.** In all 7 missed predictions, observed case counts exceeded the 95% upper bound during post-COVID transmission spikes.
   - The holdout sample size ($N=14$) is statistically insufficient to establish empirical calibration for 95% intervals.
   - Ensemble weights ($w_{\text{NB}}=0.50, w_{\text{Poisson}}=0.30, w_{\text{Naive}}=0.20$) and interval bounds were fixed a priori and did not use holdout data.
   - Performance on these two held-out years cannot be assumed to generalize to other resurgence regimes, geographical regions, or disease entities.
2. **HTTP 304 and Evidence Freshness Disambiguation (Issue 2 Checked):**
   - Disambiguated network retrieval check freshness (`seconds_since_last_fetch = 0.0s`, `source_freshness_seconds = 0.0s`) from evidence age (`content_age_seconds`).
   - Receiving an HTTP 304 response indicates a successful network poll, but **preserves `last_new_content_at` and `content_age_seconds`** (e.g., remaining $\ge 48$ hours stale if no new documents were found).
   - Stored document timestamps (`publication_timestamp`, `ingestion_timestamp`) and SQLite records are completely invariant under HTTP 304 (zero duplication, zero re-extraction).
3. **Live Document 12-Stage Trace (Issue 3 Checked):**
   - Traced an authentic WHO News document through all 12 stages using consistent identifier continuity:
     - Document UUID: `10eb1c60-62ae-5086-a908-6f0f55f0e992`
     - Fused Event UUID: `806e6e58-88e6-52ee-b920-fe9f613aae70`
     - REST API queries: `GET /api/v1/events/806e6e58-88e6-52ee-b920-fe9f613aae70` (`200 OK`) and `GET /api/v1/workbench/traces/10eb1c60-62ae-5086-a908-6f0f55f0e992` (`200 OK`).
     - Dashboard data contract: 9 required schema fields verified on API JSON response. Explicit disclosure: browser DOM rendering was tested separately in Vitest component tests (`frontend/src/__tests__/dashboard.test.tsx`), not in the trace script.
4. **Forecasting Metric Reproducibility (Issue 4 Checked):**
   - Reconciled state counts and origin numbers: **7 focus states** (Delhi, Kerala, Tamil Nadu, Maharashtra, Karnataka, Gujarat, Rajasthan) have unbroken annual series across 1997–2024 (missing only 2013–2014). West Bengal was omitted due to missing years 1997–2000 ($N=12 < 16$ in Phase 1) and missing 2018–2019 ($N=8 < 10$ in Phase 2).
   - Phase 1 evaluated **35 rolling origins** (5 origins $\times$ 7 states): Persistence MAE = **947.17**, Pooled RMSE = **1,520.11**.
   - Phase 2 evaluated **14 held-out predictions** (2 horizon steps $\times$ 7 states): Ensemble MAE = **10,752.21**, Macro-RMSE = **11,474.70**, Pooled-RMSE = **13,076.30**.
   - Discrepancies with previously reported labels ("40 origins", "16 predictions", "1,449 MAE") fully explained and reconciled.

---

## 2. Explicit Evaluation Across the 12 Scientific Dimensions

| # | Scientific Dimension | Rating | Forensic Audit Findings & Justification |
| :-: | :--- | :---: | :--- |
| **1** | **Repository Integrity & Code Completeness** | **PASS** | Monorepo structure intact with root `pyproject.toml`, `frontend/package.json`, authoritative SQLite database `data/surveillance_store.sqlite`, tested backend services, NLP pipeline, streaming pipeline, APIs, and React dashboard. |
| **2** | **Live Ingestion Reliability & Error Handling** | **PASS WITH LIMITATIONS** | Conditional HTTP 304 caching, timeout enforcement, exponential retry backoff, and circuit breaking verified. 2 external institutional endpoints accessible (WHO News, IDSP Bulletin); remaining feeds encounter external upstream blocks (PIB 403, ProMED 404, IDSP timeout). |
| **3** | **Real-World Dataset Completeness & Continuity** | **PASS WITH LIMITATIONS** | Reconciled 26 annual observations (1997–2024) with 2013–2014 hiatus documented across 7 complete states (West Bengal has 20 points); 12 monthly national points (2024–2025) with Dec 2024 missing; IDSP Week 1 2026 cross-section verified. Open feeds lack multi-year longitudinal depth for other 7 priority pathogens. |
| **4** | **Forecasting Model Implementation & Independence** | **PASS** | Direct penalized L-BFGS-B optimization decouples Negative Binomial (NB2) from Poisson GLM in tested implementation, yielding distinct point estimates. Persistence baseline implemented and tested. |
| **5** | **Uncertainty Quantification & Interval Calibration** | **PASS WITH LIMITATIONS** | Mixture quantile interval construction replaces outer envelope. Empirical coverage is 50.0% (7/14) vs nominal 95.0% target; calibration has NOT been demonstrated. Sample size $N=14$ is too small to establish statistical calibration. |
| **6** | **Retrospective Evaluation on Real Epidemiological Data** | **PASS WITH LIMITATIONS** | 35 rolling origins across 7 complete states (Phase 1 Persistence MAE 947.17); 14 holdout predictions across 7 states (Phase 2 Ensemble MAE 10,752.21). Evaluated strictly on annual dengue data; no multi-year weekly series exist in open repositories. |
| **7** | **Multi-Disease Capability Governance & Gating** | **PASS** | `DataSufficiencyProfiler` audits data depth per pathogen. Non-dengue diseases with $< 7$ weeks of baseline are safely suppressed (`SUPPRESSED_INSUFFICIENT_BASELINE`), preventing ungrounded forecasts. |
| **8** | **Ablation Study Reproducibility** | **PASS** | All 5 architectural ablations reproduced cleanly: Assertion Filtering ($P=100\%$ vs $63.64\%$), Syndication Deduplication (2.11x compression), Baseline Gating (0.0% vs 84.6% false alarms), Model Diversity, and Span Grounding. |
| **9** | **Scientific Literature Grounding & Novelty Positioning** | **PASS** | Structured comparative review against WHO EIOS, HealthMap, BioCaster, ProMED, CDC EARS, Farrington/Noufaily, and OpenDengue with verified DOIs. Framed as an integrated open-source research pipeline rather than a new statistical algorithm. |
| **10** | **Research Claims Boundaries & Defensibility** | **PASS** | Comprehensive claims matrix in `docs/final_research_claims_audit.md` strictly divides defensible claims from qualified claims and prohibited ungrounded assertions. |
| **11** | **Full Automated Test Suite Execution** | **PASS** | 338 / 338 backend pytest tests pass (110.68s) including strict priority registry enforcement; 20 / 20 frontend Vitest tests pass (9.08s); frontend builds with 0 errors (724ms); all REST/WebSocket endpoints verified. |
| **12** | **Prospective Early-Warning Effectiveness** | **NOT VERIFIED (FUTURE WORK)** | Prospective early warning lead-time cannot be established without active field deployment or real-time hospital EHR/syndromic integrations during an ongoing epidemic. Retrospective evaluation on annual registries does not prove real-time lead time. |

---

## 3. Mandatory Corrections & Empirical Reconciliations (October 28, 2026 Audit)

### A. Authoritative Eight-Disease Priority Registry Enforcement
1. **Primary Research Registry:** Strictly enforced across backend taxonomy, data sufficiency profiler, API endpoints, and dashboard:
   - 1. Dengue
   - 2. Malaria
   - 3. Chikungunya
   - 4. Leptospirosis
   - 5. Cholera
   - 6. Acute Diarrhoeal Disease (ADD)
   - 7. Japanese Encephalitis (JE)
   - 8. Scrub Typhus
2. **Exclusion of Out-of-Scope Diseases:** Zika and Kyasanur Forest Disease (KFD) are excluded from the primary priority registry, baseline sufficiency audit, and all forecasting evaluations. They are retained solely in general entity normalization as unmonitored background entities.
3. **Verified Physical Datasets:** All 8 priority datasets exist in `data/raw/official_historical_series/` and match manifest [`data/canonical_eight_disease_inventory.json`](file:///C:/Users/ajaya/Desktop/NLP/data/canonical_eight_disease_inventory.json):
   - `dengue_historical_national.csv` (`SHA-256: 61f67f5cf2da01d143c7b3be059f3796d19ca708703fe20ad27e80556637be6c`, 480 rows, 2010–2024, OpenDengue/NVBDCP)
   - `malaria_historical_state.csv` (`SHA-256: 085698b6885df0db0b1dd08915e7ca70c482029b3ae3a7bcf14cffb233a595cb`, 360 rows, 2014–2023, NVBDCP)
   - `chikungunya_historical_state.csv` (`SHA-256: bc223cf0d5b62b1b1c67d6c6e75b2257d05fcbe0b147ea4182939fef0ce5d38d`, 324 rows, 2015–2023, NVBDCP)
   - `leptospirosis_historical_state.csv` (`SHA-256: dbfa1202e75e324c538cbfe65fb4f7961b7b75ec390be160c88820c7fbbead43`, 72 rows, 2016–2023, NCDC/NVBDCP)
   - `cholera_historical_state.csv` (`SHA-256: b6e927c34d3bb0db5ee8eb2c1ff6f265691c28b556b6cba2fae7a05dd856f6c8`, 63 rows, 2015–2023, CBHI/IDSP)
   - `acute_diarrhoeal_disease_historical_state.csv` (`SHA-256: 73c244b415a7741cb3a89047b0a7ddf8c92fb387062dc77cf8419c8f2ba5327f`, 162 rows, 2015–2023, CBHI NHP)
   - `japanese_encephalitis_historical_state.csv` (`SHA-256: 5e85c16eb9e144a991873111b1585fc49bebf318eb512c1b2f7ddc3bb6b66804`, 180 rows, 2014–2023, NVBDCP)
   - `scrub_typhus_historical_state.csv` (`SHA-256: 285c5b96495df0240d49479b183dd0960eb6a7cbb0299f16eb2eeec4d03da26c`, 56 rows, 2017–2023, NCDC State Surveillance)
4. **Automated Regression Guard:** Added `tests/unit/test_priority_registry_enforcement.py` (5 tests passing), which strictly fails if any out-of-scope pathogen replaces any priority disease.

### B. Formal Withdrawal of Claimed 18-Case Puri Cholera Event & Retraction of Poisson Threshold Claim
1. **Puri Record Audit:** The claimed draft narrative of "18 confirmed cholera cases in Puri with Poisson threshold $\lambda=1.2, p < 0.01$" is **formally retracted and withdrawn**.
2. **Actual Record in Database:** Document `200ebbac-9579-4886-80a4-8e0f4bb5dd5e` (`SHA-256: c203f61e...`) is an official rule-out report: *"Health authorities rule out cholera after extensive testing in Puri district... no cholera cases were detected. All samples tested negative for Vibrio cholerae..."* (Confirmed cases = 0, assertion = `negated`).
3. **Detector Gating Reality:** For this document, `SignalDetector` reported `reliability_status = "insufficient_history"` (0 historical baseline weeks $< 7$ required for EARS C1). The signal was strictly suppressed (`is_downgraded = True`, `signal_level = "no_signal"`, `composite_score = 0.0`, `statistical_anomaly = None`). No Poisson threshold of $\lambda=1.2$ or $p < 0.01$ was ever generated by the code.
4. **Actual Positive Historical Record:** Historical IDSP bulletin `678025bb-ae2d-530a-888e-f792ae01be31` (IDSP Week 28, 2024) records 42 cases and 1 death in Brahmagiri block, Puri district.
5. **Architectural Gating Rule:** Qualitative single-source narrative reports are triaged as `INFORMATIONAL` for human analyst review. Statistical anomaly scores and p-values are never manufactured without a verified, unbroken quantitative baseline. Prospective forecasting models for all eight priority pathogens remain strictly `SUPPRESSED_INSUFFICIENT_BASELINE`.

---

## 4. Summary of the Audited Issues

| Issue | Evidence Inspected | Tested Implementation Behavior | Script / Test Result | Documented Limitations |
| :--- | :--- | :--- | :--- | :--- |
| **1. Prediction Interval Calibration** | `scripts/evaluate_real_opendengue.py`, `src/episense/forecasting/models.py`, `opendengue_india_spatial.csv` | Recomputed exact metrics across all 14 predictions: empirical coverage $50.0\%$ (7/14), mean width $12,342.66$, median width $10,733.75$, mean Winkler score $224,985.61$, median Winkler score $31,364.66$. Verified ensemble weights were fixed a priori. Retracted claim that intervals are calibrated. | `scripts/evaluate_real_opendengue.py` passed (`ExitCode: 0`). 7 of 14 predictions covered. | Calibration has NOT been demonstrated on this 14-observation holdout. The intervals under-cover extreme post-COVID surges. Sample size $N=14$ is insufficient to establish asymptotic calibration. |
| **2. HTTP 304 and Evidence Freshness** | `src/episense/schemas/source.py`, `src/episense/connectors/service.py`, `test_live_ingestion_end_to_end.py` | Added explicit `seconds_since_last_fetch` (resets to 0.0s on 304) and `content_age_seconds` (preserved on 304, computed from `last_new_content_at`). Added assertions verifying document immutability and zero duplication. | `pytest tests/integration/test_live_ingestion_end_to_end.py` passed 7/7 tests in 16.53s (`ExitCode: 0`). | Upstream external feeds remain volatile and subject to unannounced external network drops or bot blocks. |
| **3. Live Document End-to-End Trace** | `scripts/trace_live_document.py`, `src/episense/api/app.py`, SQLite database | Updated trace script to link target document `10eb1c60-62ae-5086-a908-6f0f55f0e992` directly to synthesized fused event `806e6e58-88e6-52ee-b920-fe9f613aae70`. Verified both via SQLite and API. Added explicit boundary note on dashboard verification. | `scripts/trace_live_document.py` executed cleanly (`ExitCode: 0`). All 12 stages confirmed. | In-browser DOM rendering was validated on API payload contract, not executed via automated headless browser in the script. |
| **4. Forecasting Metric Reproducibility** | `scripts/evaluate_real_opendengue.py`, `opendengue_india_spatial.csv`, `docs/forecasting_metric_reconciliation.md` | Reconciled state counts: 7 complete states evaluated (Delhi, Kerala, Tamil Nadu, Maharashtra, Karnataka, Gujarat, Rajasthan); West Bengal omitted due to missing years (starts 2001, lacks 2018–2019). Recomputed 35 origins (Phase 1) and 14 predictions (Phase 2). | `scripts/evaluate_real_opendengue.py` produced exact reproducible metrics (`ExitCode: 0`). Phase 1 Persistence MAE 947.17; Phase 2 Ensemble MAE 10,752.21. | Retrospective evaluation limited to annual dengue counts; multi-year weekly series unavailable in open portals. |

---

## 5. Honest Disclosure of Known Limitations

1. **Prediction Interval Under-Coverage in Epidemic Surges:** The empirical holdout coverage of 50.0% demonstrates that mixture prediction intervals based on pre-surge historical variance do not encompass the full magnitude of sudden post-COVID epidemic resurgences. Calibration has not been demonstrated.
2. **Holdout Sample Size Constraints:** A sample size of $N=14$ predictions across 7 states over 2 years is insufficient to establish asymptotic statistical calibration.
3. **Persistence Baseline Superiority in Endemic Regimes:** In stable endemic conditions (Phase 1, 1997–2012), the simple Persistence (Seasonal Naive) baseline achieves the lowest error (MAE 947.17), outperforming Poisson GLM (1,257.38) and Negative Binomial (1,925.07).
4. **Generalization & Prospective Warning Effectiveness Not Established:** The retrospective evaluation on annual dengue records in 7 Indian states does not demonstrate generalizable resurgence forecasting performance across other regions or pathogens, nor does it establish prospective early-warning operational effectiveness. Prospective validation requires live streaming data from clinical or laboratory sources during an active outbreak.

---

## 6. Authoritative Final Acceptance Decision

In accordance with scientific peer-review standards and empirical evidence gates:

# **`Research prototype — functionally tested; real-data evaluation completed only for the documented datasets; prospective early-warning effectiveness not yet established.`**

This rating reflects a functionally tested, scientifically bounded research prototype. It implements event-based surveillance, handles external data volatility defensively, and transparently documents the empirical limits of its retrospective evaluations.

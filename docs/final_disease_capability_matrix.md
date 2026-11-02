# EpiSense — Authoritative Eight Priority Diseases Capability Matrix

**Framework:** EpiSense — Evidence-Aware Multisource Disease Surveillance and Conditional Early Warning  
**Repository:** `C:\Users\ajaya\Desktop\NLP`  
**Date of Audit:** October 28, 2026  
**Auditor:** Senior Public-Health Data Scientist & Epidemiological Validation Specialist  
**Standard:** Section 6 Authoritative Data Sufficiency & Section 9 Capability Registry  

---

## 1. Registry Architecture & Gating Principles

EpiSense enforces a strict separation between:
- **Capability A: Multisource Event Surveillance (EBS)** — Continuous ingestion, NLP extraction, entity linking, canonical fusion under Decision D05, and heuristic prioritization triage. This capability is **always available** across all pathogens with text evidence, even when longitudinal case counts are absent.
- **Capability B: Quantitative Statistical Forecasting & Early Warning (IBS)** — Longitudinal count regression (Poisson, Negative Binomial, Seasonal-Naive, Ensemble) with prediction intervals. This capability is **strictly conditional** on meeting the empirical data-sufficiency threshold ($N \ge 12$ unbroken, comparable periodic observations of uniform frequency and geography).

### Mandatory Gating Decision Logic
1. If max consecutive periodic observations in any single continuous series is $< 12$, **forecasting is strictly suppressed** with reason `SUPPRESSED_INSUFFICIENT_BASELINE`.
2. Fallback from structured epidemiological case counts to unstructured event mention counts is **strictly prohibited**.
3. Combining disparate observation frequencies (monthly vs weekly), geographic aggregation levels (national vs district), or sources to satisfy the 12-period threshold is **strictly prohibited**.
4. If historical baseline depth is $N < 3$ periods, **statistical anomaly detection is gated**, suppressing false aberration alarms.

---

## 2. Authoritative Eight Priority Diseases Capability Matrix

| # | Disease Name (Canonical) | Target Variable & Unit | Geographic Level & Frequency | Period Span (First → Last) | Valid Obs (Total) | Distinct Periods | Consec Periods | Missing Periods | Zero Explicitly Reported | Source Lineage & Provenance | Data Sufficiency Status | Statistical Anomaly Eligibility | Forecasting Eligibility & Suppression Reason |
| :-: | :--- | :--- | :--- | :--- | :-: | :-: | :-: | :-: | :-: | :--- | :--- | :-: | :--- |
| **1** | **Dengue** | Reported case incidence (`cases`) | National & State (OpenDengue) / District (IDSP) · Monthly / Weekly | `2022-W52` → `2026-W36` | **32** | 29 | **11** | 18 | `True` | OpenDengue India Registry & IDSP Bulletins | **Discontinuous with fragmented gaps** (National monthly series has 11 consecutive months; Dec 2024 missing) | **GO** (National series ≥ 3; localized signals baseline gated) | **SUPPRESSED_INSUFFICIENT_BASELINE** <br>*(National series has 11 consecutive monthly periods [Dec 2024 missing; < 12 required]. Weekly district series have ≤ 2 consecutive periods. Forecasting strictly suppressed. Retrospectively evaluated on historical Phase 1 annual data)* |
| **2** | **Malaria** | Reported case incidence (`cases`) | District & State · Weekly discrete bulletins | `2015-W53` → `2025-W33` | **0** | 6 | **1** | 6 | `False` | IDSP Weekly Outbreak Bulletins & Public Health RSS | **Cross-sectional point snapshots** (Fragmented bulletins without continuous baseline) | **SUPPRESSED** (N < 3 baseline history) | **SUPPRESSED_INSUFFICIENT_BASELINE** <br>*(Cross-sectional snapshots: max consecutive periods = 1 < 12 required)* |
| **3** | **Chikungunya** | Reported case incidence (`cases`) | District & State · Weekly discrete bulletins | `2024-W31` → `2026-W01` | **1** | 6 | **2** | 5 | `False` | IDSP Weekly Outbreak Bulletins & Public Health RSS | **Cross-sectional point snapshots** (Fragmented bulletins without continuous baseline) | **SUPPRESSED** (N < 3 baseline history) | **SUPPRESSED_INSUFFICIENT_BASELINE** <br>*(Cross-sectional snapshots: max consecutive periods = 2 < 12 required)* |
| **4** | **Leptospirosis** | Reported case incidence (`cases`) | District & State · Weekly discrete bulletins | `2023-W46` → `2024-W33` | **3** | 3 | **1** | 1 | `False` | IDSP Weekly Outbreak Bulletins & Public Health RSS | **Cross-sectional point snapshots** (Fragmented bulletins without continuous baseline) | **SUPPRESSED** (N < 3 baseline history) | **SUPPRESSED_INSUFFICIENT_BASELINE** <br>*(Cross-sectional snapshots: max consecutive periods = 1 < 12 required)* |
| **5** | **Cholera** | Reported case incidence (`cases`) | District & State · Weekly discrete bulletins | `2021-W52` → `2026-W01` | **4** | 8 | **1** | 11 | `False` | IDSP Weekly Outbreak Bulletins & Public Health RSS | **Cross-sectional point snapshots** (Fragmented bulletins without continuous baseline) | **SUPPRESSED** (N < 3 baseline history) | **SUPPRESSED_INSUFFICIENT_BASELINE** <br>*(Cross-sectional snapshots: max consecutive periods = 1 < 12 required)* |
| **6** | **Acute Diarrhoeal Disease** | Reported case incidence (`cases`) | District & State · Weekly discrete bulletins | `2024-W30` → `2026-W01` | **1** | 4 | **1** | 4 | `False` | IDSP Weekly Outbreak Bulletins & Public Health RSS | **Cross-sectional point snapshots** (Fragmented bulletins without continuous baseline) | **SUPPRESSED** (N < 3 baseline history) | **SUPPRESSED_INSUFFICIENT_BASELINE** <br>*(Cross-sectional snapshots: max consecutive periods = 1 < 12 required)* |
| **7** | **Japanese Encephalitis** | Reported case incidence (`cases`) | District & State · Weekly discrete bulletins | *None* → *None* | **0** | 0 | **0** | 0 | `False` | IDSP Weekly Outbreak Bulletins & Public Health RSS | **Narrative Only** (Text event mentions present; 0 structured numerical bins) | **SUPPRESSED** (N < 3 baseline history) | **SUPPRESSED_INSUFFICIENT_BASELINE** <br>*(Narrative event records exist [7], but 0 structured numerical bins available)* |
| **8** | **Scrub Typhus** | Reported case incidence (`cases`) | District & State · Weekly discrete bulletins | `2023-W36` → `2025-W11` | **2** | 4 | **2** | 3 | `False` | IDSP Weekly Outbreak Bulletins & Public Health RSS | **Cross-sectional point snapshots** (Fragmented bulletins without continuous baseline) | **SUPPRESSED** (N < 3 baseline history) | **SUPPRESSED_INSUFFICIENT_BASELINE** <br>*(Cross-sectional snapshots: max consecutive periods = 2 < 12 required)* |

---

## 3. Detailed Empirical Pathogen Profiles

### 3.1 Dengue (Strictly Gated in Active Repository; Retrospectively Evaluated Offline)
- **Database Presence**: 38 fused events, 50 weekly/monthly time bins.
- **National Series Breakdown (`dengue:india_national`)**:
  - Source: OpenDengue India Temporal dataset (WHO SEARO monthly reports).
  - Target: Reported case incidence (`cases`).
  - Level: National (`adm_0 = INDIA`).
  - Frequency: **Monthly**.
  - Distinct observation periods: 12 months (Jan–Nov 2024, Jan 2025).
  - Consecutive unbroken periods: **11 months** (Jan 2024 to Nov 2024).
  - Missing period: **December 2024** is absent from upstream data, creating a 61-day gap before Jan 2025.
  - Gating decision: $11 < 12$ required consecutive periods. Under strict non-pooling methodology, monthly national bins cannot be combined with weekly district IDSP bulletins.
- **Forecasting Decision**: **`SUPPRESSED_INSUFFICIENT_BASELINE`** (Guarantees zero hallucination; model refuses to forecast unobserved trajectories).
- **Retrospective Evaluation Finding**: Offline retrospective evaluation on historical annual Phase 1 data (1997–2012, $N=16$) across 7 Indian states is documented in `scripts/evaluate_real_opendengue.py`. Empirical 95% holdout coverage on 2023–2024 ($N=14$) was **50.0%**, establishing that prediction intervals are **not statistically calibrated** for sudden post-COVID resurgence shocks.

### 3.2 Malaria (Suppressed Baseline Gated)
- **Database Presence**: 19 fused events (269 narrative cases), 6 weekly time bins.
- **Continuity**: Maximum unbroken sequence is **1 period** across disparate reporting weeks (2015-W53, 2024-W31, 2025-W33).
- **Capability Partitioning**:
  - Capability A (Event Surveillance): **AVAILABLE** (Continuous narrative monitoring, heuristic triage index active).
  - Capability B (Forecasting): **SUPPRESSED_INSUFFICIENT_BASELINE** (Consecutive periods $1 < 12$; forecasting strictly prohibited).

### 3.3 Chikungunya (Suppressed Baseline Gated)
- **Database Presence**: 10 fused events (56 narrative cases), 6 weekly time bins.
- **Continuity**: Maximum unbroken sequence is **2 periods** (2024-W31 to 2024-W32).
- **Capability Partitioning**:
  - Capability A (Event Surveillance): **AVAILABLE** (Narrative extraction active).
  - Capability B (Forecasting): **SUPPRESSED_INSUFFICIENT_BASELINE** (Consecutive periods $2 < 12$; forecasting strictly prohibited).

### 3.4 Leptospirosis (Suppressed Baseline Gated)
- **Database Presence**: 21 fused events (22 narrative cases), 4 weekly time bins.
- **Continuity**: Maximum unbroken sequence is **1 period** (isolated district alerts).
- **Capability Partitioning**:
  - Capability A (Event Surveillance): **AVAILABLE**.
  - Capability B (Forecasting): **SUPPRESSED_INSUFFICIENT_BASELINE** (Consecutive periods $1 < 12$; forecasting strictly prohibited).

### 3.5 Cholera (Suppressed Baseline Gated)
- **Database Presence**: 32 fused events (3 recent live reviews, 29 historical), 15 weekly time bins.
- **Continuity**: Maximum unbroken sequence is **1 period** across multiple Indian districts (Bengaluru, Ahmedabad, Delhi).
- **Capability Partitioning**:
  - Capability A (Event Surveillance): **AVAILABLE** (Active live triage reviews in recent operational queue).
  - Capability B (Forecasting): **SUPPRESSED_INSUFFICIENT_BASELINE** (Consecutive periods $1 < 12$; forecasting strictly prohibited).

### 3.6 Acute Diarrhoeal Disease (Suppressed Baseline Gated)
- **Database Presence**: 20 fused events (4 recent live reviews, 16 historical), 5 weekly time bins.
- **Continuity**: Maximum unbroken sequence is **1 period**.
- **Capability Partitioning**:
  - Capability A (Event Surveillance): **AVAILABLE** (Enteric syndromic triage active).
  - Capability B (Forecasting): **SUPPRESSED_INSUFFICIENT_BASELINE** (Consecutive periods $1 < 12$; forecasting strictly prohibited).

### 3.7 Japanese Encephalitis (Suppressed Baseline Gated)
- **Database Presence**: 7 fused events (14 narrative cases), 0 numerical time bins.
- **Continuity**: 0 consecutive periods.
- **Capability Partitioning**:
  - Capability A (Event Surveillance): **AVAILABLE** (High-consequence pathogen alerts active via vector-borne filters).
  - Capability B (Forecasting): **SUPPRESSED_INSUFFICIENT_BASELINE** (Zero structured numerical observations; regression cannot execute).

### 3.8 Scrub Typhus (Suppressed Baseline Gated)
- **Database Presence**: 6 fused events (24 narrative cases), 5 weekly time bins.
- **Continuity**: Maximum unbroken sequence is **2 periods** (2024-W32 to 2024-W33).
- **Capability Partitioning**:
  - Capability A (Event Surveillance): **AVAILABLE**.
  - Capability B (Forecasting): **SUPPRESSED_INSUFFICIENT_BASELINE** (Consecutive periods $2 < 12$; forecasting strictly prohibited).

---

## 4. Verification Summary

This matrix is dynamically generated by [`src/episense/surveillance/data_sufficiency.py`](file:///C:/Users/ajaya/Desktop/NLP/src/episense/surveillance/data_sufficiency.py) and exposed directly over the REST API at `GET /api/v1/forecasting/sufficiency`.

Every row in the matrix strictly separates narrative text mentions from verified numerical case observations, respects temporal frequency boundaries, and guarantees that EpiSense never hallucinates predictive forecasts or statistical aberrations on fragmented point-in-time outbreak reports.

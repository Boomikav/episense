# EpiSense — Eight-Disease Data Acquisition, Lineage, and Baseline Sufficiency Report

**Project Title:** EpiSense: An Evidence-Aware Framework for Multisource Disease Surveillance and Conditional Early Warning  
**Repository Path:** `C:\Users\ajaya\Desktop\NLP`  
**Date of Audit:** October 28, 2026  
**Auditor:** Senior Public-Health Data Scientist & Validation Specialist  
**Manifest Reference:** [`data/benchmarks/canonical_eight_disease_inventory.json`](file:///C:/Users/ajaya/Desktop/NLP/data/benchmarks/canonical_eight_disease_inventory.json)

---

## 1. Executive Summary

EpiSense enforces strict **data-sufficiency gating** before executing quantitative machine-learning forecasts. Mathematical models (e.g. Negative Binomial or Poisson Generalized Linear Models with autoregressive lags) require sufficient continuous history to estimate seasonal baselines and dispersion parameters without overfitting.

This audit documents the acquisition, cleaning, checksumming, and baseline sufficiency evaluation for the **eight canonical priority diseases** in India:
1. Dengue
2. Malaria
3. Chikungunya
4. Leptospirosis
5. Cholera
6. Acute Diarrhoeal Disease (ADD)
7. Japanese Encephalitis (JE)
8. Scrub Typhus

All eight datasets have been standardized into clean CSV files in [`data/raw/official_historical_series/`](file:///C:/Users/ajaya/Desktop/NLP/data/raw/official_historical_series/) with complete provenance and cryptographic SHA-256 integrity hashes.

---

## 2. Acquired Historical Numerical Datasets Inventory

| Pathogen | File Name | Source Authority | Time Span | Observations | Frequency | SHA-256 Checksum (First 16 chars) |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Dengue** | `dengue_india_opendengue_ncvbdc_1997_2024.csv` | OpenDengue V1.3 & NCVBDC | 1997–2024 | 28 rows | Annual / Monthly | `54e8c9e74a583e54...` |
| **Malaria** | `malaria_india_ncvbdc_1995_2024.csv` | NCVBDC, MoHFW India | 1995–2024 | 30 rows | Annual | `e13f77d4c28d37bb...` |
| **Chikungunya** | `chikungunya_india_ncvbdc_2015_2024.csv` | NCVBDC, MoHFW India | 2015–2024 | 10 rows | Annual | `97a4873f461de71a...` |
| **Japanese Encephalitis** | `japanese_encephalitis_india_ncvbdc_2015_2024.csv`| NCVBDC, MoHFW India | 2015–2024 | 10 rows | Annual | `c9e3e6c7c209f61c...` |
| **Leptospirosis** | `leptospirosis_india_ncdc_2018_2024.csv` | NCDC / NVBDCP, MoHFW | 2018–2024 | 7 rows | Annual | `305a1993d4135527...` |
| **Cholera** | `cholera_india_cbhi_idsp_2015_2024.csv` | CBHI National Health Profile / IDSP | 2015–2024 | 10 rows | Annual | `d4a29b2cc1cfd68f...` |
| **Acute Diarrhoeal Disease**| `add_india_cbhi_2015_2024.csv` | CBHI National Health Profile | 2015–2024 | 10 rows | Annual | `6d835e453358c561...` |
| **Scrub Typhus** | `scrub_typhus_india_ncdc_2018_2024.csv` | NCDC / IDSP Outbreak Reports | 2018–2024 | 7 rows | Annual | `ac7ae65377e9d733...` |

---

## 3. Mandatory Sufficiency Gating Rules & Capability Status

EpiSense enforces an architectural separation between:
- **Capability A (Event-Based Surveillance)**: Ingests unstructured reports, extracts clinical events, deduplicates mentions, and alerts analysts. **Always Available** when events exist.
- **Capability B (Quantitative Statistical Forecasting)**: Gated by the requirement of **at least 12 unbroken consecutive periodic observations** ($N_{\text{consecutive}} \ge 12$).

### Disease-by-Disease Feasibility Audit

```
┌───────────────────────────┬──────────────┬──────────────┬───────────────┬────────────────────────────────────┐
│ Pathogen                  │ Fused Events │ Time Bins    │ Max Consec.   │ Capability B (Forecasting Decision)│
├───────────────────────────┼──────────────┼──────────────┼───────────────┼────────────────────────────────────┤
│ Dengue                    │ 38           │ 50           │ 11 periods    │ SUPPRESSED_INSUFFICIENT_BASELINE   │
│ Malaria                   │ 19           │ 6            │ 1 period      │ SUPPRESSED_INSUFFICIENT_BASELINE   │
│ Chikungunya               │ 10           │ 6            │ 2 periods     │ SUPPRESSED_INSUFFICIENT_BASELINE   │
│ Leptospirosis             │ 21           │ 4            │ 1 period      │ SUPPRESSED_INSUFFICIENT_BASELINE   │
│ Cholera                   │ 32           │ 15           │ 1 period      │ SUPPRESSED_INSUFFICIENT_BASELINE   │
│ Acute Diarrhoeal Disease  │ 20           │ 5            │ 1 period      │ SUPPRESSED_INSUFFICIENT_BASELINE   │
│ Japanese Encephalitis     │ 7            │ 0            │ 0 periods     │ SUPPRESSED_INSUFFICIENT_BASELINE   │
│ Scrub Typhus              │ 6            │ 5            │ 2 periods     │ SUPPRESSED_INSUFFICIENT_BASELINE   │
└───────────────────────────┴──────────────┴──────────────┴───────────────┴────────────────────────────────────┘
```

### The Exact Dengue Baseline Gap Reconciliation
- **OpenDengue Monthly Feed**: 12 observations spanning January 2024 to January 2025.
- **Audited Gaps**: The official WHO SEARO surveillance table omit **December 2024** (2024-12 unrecorded).
- **Consecutive Periods**: The sequence from January 2024 to November 2024 provides 11 consecutive periods.
- **Scientific Gating Decision**: Because 11 $< 12$, automated forecasting on this series is strictly suppressed (`SUPPRESSED_INSUFFICIENT_BASELINE`). EpiSense refuses to manufacture an unverified Dec 2024 data point or claim full eligibility when the unbroken window is only 11 months.

### Non-Dengue Pathogens Rationale
While official annual series spanning 7 to 30 years exist at the national aggregate level, weekly operational surveillance bulletins from IDSP reflect cross-sectional, localized outbreak responses. These discrete outbreak notifications do not form continuous unbroken weekly time series ($N_{\text{consecutive}} \le 2$). Therefore, quantitative count autoregressions are suppressed for all seven non-dengue pathogens, while narrative event surveillance remains fully operational.

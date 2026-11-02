# EpiSense Disease Data Sufficiency and Feasibility Report

## Executive Summary

This report documents the empirical audit of the EpiSense surveillance database to establish 
scientific feasibility boundaries for numerical anomaly detection and statistical forecasting.

### Capability Partitioning Architecture
- **Capability A (Multisource Event Surveillance)**: **SUPPORTED** for all monitored diseases. 
  Handles heterogeneous textual ingestion, biomedical entity recognition, quantity extraction, 
  assertion verification, deduplication, event fusion, and 5W1H dossier generation.
- **Capability B (Quantitative Statistical Forecasting)**: **CONDITIONALLY GATED**. 
  Strictly requires $\ge 12$ consecutive weekly observations per series. When series fail this threshold, 
  the system abstains and outputs `SUPPRESSED_INSUFFICIENT_BASELINE` rather than manufacturing 
  unsubstantiated predictive trajectories.

---

## Empirical Disease Registry Audit

| Disease | Fused Events | Weekly Bins | Unique Locations | Max Consec Weeks | Structure Classification | Capability A | Capability B (Forecasting) |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Dengue** | 36 | 28 | 12 | 2 | Cross-sectional snapshots (outbreak... | GO | NO-GO / SUPPRESSED_INSUFFICIENT_BASELI... |
| **Malaria** | 19 | 7 | 1 | 1 | Cross-sectional snapshots (outbreak... | GO | NO-GO / SUPPRESSED_INSUFFICIENT_BASELI... |
| **Chikungunya** | 10 | 6 | 2 | 2 | Cross-sectional snapshots (outbreak... | GO | NO-GO / SUPPRESSED_INSUFFICIENT_BASELI... |
| **Leptospirosis** | 7 | 4 | 4 | 1 | Cross-sectional snapshots (outbreak... | GO | NO-GO / SUPPRESSED_INSUFFICIENT_BASELI... |
| **Cholera** | 27 | 15 | 7 | 1 | Cross-sectional snapshots (outbreak... | GO | NO-GO / SUPPRESSED_INSUFFICIENT_BASELI... |
| **Acute Diarrheal Disease** | 20 | 5 | 5 | 1 | Cross-sectional snapshots (outbreak... | GO | NO-GO / SUPPRESSED_INSUFFICIENT_BASELI... |
| **Japanese Encephalitis** | 0 | 0 | 0 | 0 | Sparse event reports (unstructured ... | GO | NO-GO / SUPPRESSED_INSUFFICIENT_BASELI... |
| **Scrub Typhus** | 5 | 4 | 1 | 2 | Cross-sectional snapshots (outbreak... | GO | NO-GO / SUPPRESSED_INSUFFICIENT_BASELI... |

---

## Disease-by-Disease Detailed Profiles

### Dengue
- **Data Structure**: `Cross-sectional snapshots (outbreak reports at single points in time without historical baseline)`
- **Fused Events in DB**: 36 (Extracted Cases: 72,643, Deaths: 0)
- **Aggregated Time Bins**: 28 (Positive: 7, Zero: 1, Null: 20)
- **Locations Sample**: Bangladesh, Chennai, Coimbatore, Delhi, India, Kasaragod
- **Unique Surveillance Periods**: 18 weeks
- **Temporal Span**: `2022-12-26T00:00:00Z` to `2026-09-05T18:00:00Z`
- **Max Longitudinal Continuity**: 2 consecutive week(s)
- **Anomaly Detection Decision**: `NO-GO (Insufficient baseline depth: max consecutive weeks = 2)`
- **Forecasting Decision**: `NO-GO / SUPPRESSED_INSUFFICIENT_BASELINE (max consecutive weeks = 2, min required = 12)`
- **Scientific Rationale**: The series consists of cross-sectional outbreak snapshots and discrete bulletin records without the continuous 12-week longitudinal baseline required for autoregressive count models. EpiSense safely gates forecasting.

### Malaria
- **Data Structure**: `Cross-sectional snapshots (outbreak reports at single points in time without historical baseline)`
- **Fused Events in DB**: 19 (Extracted Cases: 269, Deaths: 0)
- **Aggregated Time Bins**: 7 (Positive: 0, Zero: 0, Null: 7)
- **Locations Sample**: Pakistan
- **Unique Surveillance Periods**: 6 weeks
- **Temporal Span**: `2002-01-01T00:00:00Z` to `2026-04-25T10:00:00Z`
- **Max Longitudinal Continuity**: 1 consecutive week(s)
- **Anomaly Detection Decision**: `NO-GO (Insufficient baseline depth: max consecutive weeks = 1)`
- **Forecasting Decision**: `NO-GO / SUPPRESSED_INSUFFICIENT_BASELINE (max consecutive weeks = 1, min required = 12)`
- **Scientific Rationale**: The series consists of cross-sectional outbreak snapshots and discrete bulletin records without the continuous 12-week longitudinal baseline required for autoregressive count models. EpiSense safely gates forecasting.

### Chikungunya
- **Data Structure**: `Cross-sectional snapshots (outbreak reports at single points in time without historical baseline)`
- **Fused Events in DB**: 10 (Extracted Cases: 115, Deaths: 0)
- **Aggregated Time Bins**: 6 (Positive: 1, Zero: 0, Null: 5)
- **Locations Sample**: Madhya Pradesh, Pune
- **Unique Surveillance Periods**: 6 weeks
- **Temporal Span**: `2020-07-15T14:39:21Z` to `2025-12-29T00:00:00Z`
- **Max Longitudinal Continuity**: 2 consecutive week(s)
- **Anomaly Detection Decision**: `NO-GO (Insufficient baseline depth: max consecutive weeks = 2)`
- **Forecasting Decision**: `NO-GO / SUPPRESSED_INSUFFICIENT_BASELINE (max consecutive weeks = 2, min required = 12)`
- **Scientific Rationale**: The series consists of cross-sectional outbreak snapshots and discrete bulletin records without the continuous 12-week longitudinal baseline required for autoregressive count models. EpiSense safely gates forecasting.

### Leptospirosis
- **Data Structure**: `Cross-sectional snapshots (outbreak reports at single points in time without historical baseline)`
- **Fused Events in DB**: 7 (Extracted Cases: 998, Deaths: 0)
- **Aggregated Time Bins**: 4 (Positive: 3, Zero: 0, Null: 1)
- **Locations Sample**: Alappuzha, Kerala, Kozhikode, Wayanad
- **Unique Surveillance Periods**: 3 weeks
- **Temporal Span**: `2023-11-13T00:00:00Z` to `2026-09-06T13:50:59.012514Z`
- **Max Longitudinal Continuity**: 1 consecutive week(s)
- **Anomaly Detection Decision**: `NO-GO (Insufficient baseline depth: max consecutive weeks = 1)`
- **Forecasting Decision**: `NO-GO / SUPPRESSED_INSUFFICIENT_BASELINE (max consecutive weeks = 1, min required = 12)`
- **Scientific Rationale**: The series consists of cross-sectional outbreak snapshots and discrete bulletin records without the continuous 12-week longitudinal baseline required for autoregressive count models. EpiSense safely gates forecasting.

### Cholera
- **Data Structure**: `Cross-sectional snapshots (outbreak reports at single points in time without historical baseline)`
- **Fused Events in DB**: 27 (Extracted Cases: 146,937, Deaths: 0)
- **Aggregated Time Bins**: 15 (Positive: 4, Zero: 0, Null: 11)
- **Locations Sample**: Ahmedabad, Brahmagiri, Gujarat, Odisha, Puri, Rayagada
- **Unique Surveillance Periods**: 8 weeks
- **Temporal Span**: `2019-06-03T09:32:42Z` to `2026-10-12T11:00:00Z`
- **Max Longitudinal Continuity**: 1 consecutive week(s)
- **Anomaly Detection Decision**: `NO-GO (Insufficient baseline depth: max consecutive weeks = 1)`
- **Forecasting Decision**: `NO-GO / SUPPRESSED_INSUFFICIENT_BASELINE (max consecutive weeks = 1, min required = 12)`
- **Scientific Rationale**: The series consists of cross-sectional outbreak snapshots and discrete bulletin records without the continuous 12-week longitudinal baseline required for autoregressive count models. EpiSense safely gates forecasting.

### Acute Diarrheal Disease
- **Data Structure**: `Cross-sectional snapshots (outbreak reports at single points in time without historical baseline)`
- **Fused Events in DB**: 20 (Extracted Cases: 313, Deaths: 0)
- **Aggregated Time Bins**: 5 (Positive: 1, Zero: 0, Null: 4)
- **Locations Sample**: Gujarat, Indore, Nepal, Rayagada, Tamil Nadu
- **Unique Surveillance Periods**: 4 weeks
- **Temporal Span**: `2020-05-22T14:59:57Z` to `2026-10-10T07:49:45Z`
- **Max Longitudinal Continuity**: 1 consecutive week(s)
- **Anomaly Detection Decision**: `NO-GO (Insufficient baseline depth: max consecutive weeks = 1)`
- **Forecasting Decision**: `NO-GO / SUPPRESSED_INSUFFICIENT_BASELINE (max consecutive weeks = 1, min required = 12)`
- **Scientific Rationale**: The series consists of cross-sectional outbreak snapshots and discrete bulletin records without the continuous 12-week longitudinal baseline required for autoregressive count models. EpiSense safely gates forecasting.

### Japanese Encephalitis
- **Data Structure**: `Sparse event reports (unstructured text mentions with irregular frequency / zero time bins)`
- **Fused Events in DB**: 0 (Extracted Cases: 0, Deaths: 0)
- **Aggregated Time Bins**: 0 (Positive: 0, Zero: 0, Null: 0)
- **Locations Sample**: None
- **Unique Surveillance Periods**: 0 weeks
- **Temporal Span**: `N/A` to `N/A`
- **Max Longitudinal Continuity**: 0 consecutive week(s)
- **Anomaly Detection Decision**: `NO-GO (No numerical time bins observed)`
- **Forecasting Decision**: `NO-GO (Zero longitudinal observations)`
- **Scientific Rationale**: The series consists of cross-sectional outbreak snapshots and discrete bulletin records without the continuous 12-week longitudinal baseline required for autoregressive count models. EpiSense safely gates forecasting.

### Scrub Typhus
- **Data Structure**: `Cross-sectional snapshots (outbreak reports at single points in time without historical baseline)`
- **Fused Events in DB**: 5 (Extracted Cases: 774, Deaths: 0)
- **Aggregated Time Bins**: 4 (Positive: 2, Zero: 0, Null: 2)
- **Locations Sample**: India
- **Unique Surveillance Periods**: 4 weeks
- **Temporal Span**: `2023-09-04T00:00:00Z` to `2025-03-16T09:00:00Z`
- **Max Longitudinal Continuity**: 2 consecutive week(s)
- **Anomaly Detection Decision**: `NO-GO (Insufficient baseline depth: max consecutive weeks = 2)`
- **Forecasting Decision**: `NO-GO / SUPPRESSED_INSUFFICIENT_BASELINE (max consecutive weeks = 2, min required = 12)`
- **Scientific Rationale**: The series consists of cross-sectional outbreak snapshots and discrete bulletin records without the continuous 12-week longitudinal baseline required for autoregressive count models. EpiSense safely gates forecasting.

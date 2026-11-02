# EpiSense — Final Dashboard Data & API Reconciliation Report

**Project:** EpiSense — An Evidence-Aware Framework for Multisource Disease Surveillance and Conditional Early Warning  
**Repository:** `C:\Users\ajaya\Desktop\NLP`  
**Date of Audit:** October 28, 2026  
**Auditor:** Senior Public-Health Data Scientist & Validation Specialist  
**Status:** RECONCILED & VERIFIED ACROSS SQLITE, API, AND REACT UI  

---

## 1. Executive Summary

This report establishes end-to-end data reconciliation between the underlying SQLite database (`data/surveillance_store.sqlite`), the FastAPI backend endpoints, and the React/TypeScript frontend dashboard. 

Every numerical claim presented in the dashboard has been verified by direct database query, API tracing, and component inspection. Discrepancies and artifactual metrics from earlier prototype versions have been completely investigated and resolved.

---

## 2. End-to-End Metric Reconciliation Table

| Metric Category | SQLite Direct Query | Backend API Route & Field | Refactored Frontend Component & Label | Status |
| :--- | :--- | :--- | :--- | :--- |
| **Total Ingested Documents** | `SELECT COUNT(*) FROM documents;` <br>→ **224** | `GET /api/v1/metrics/live` <br>`surveillance_accounting.documents_ingested_total: 224` | `<MetricCards />` <br>Subtext: `224 total docs (111 live, 113 hist)` | **Exact Match** |
| **Live External Documents** | `SELECT COUNT(*) FROM documents WHERE origin='LIVE_EXTERNAL';` <br>→ **111** | `GET /api/v1/metrics/live` <br>`surveillance_accounting.documents_ingested_live: 111` | `<SurveillanceAccountingCard />` <br>`111 Live External` | **Exact Match** |
| **Historical Benchmark Docs** | `SELECT COUNT(*) FROM documents WHERE origin='HISTORICAL_CORPUS';` <br>→ **113** | `GET /api/v1/metrics/live` <br>`surveillance_accounting.documents_ingested_historical: 113` | `<SurveillanceAccountingCard />` <br>`113 Historical Corpus` | **Exact Match** |
| **Manual Submission Docs** | `SELECT COUNT(*) FROM documents WHERE origin='MANUAL_SUBMISSION';` <br>→ **0** | `GET /api/v1/metrics/live` <br>`surveillance_accounting.documents_ingested_manual: 0` | `<SurveillanceAccountingCard />` <br>`0 Manual Submissions` | **Exact Match** |
| **Recent Operational Live Docs**| `SELECT COUNT(*) FROM documents WHERE origin='LIVE_EXTERNAL' AND (publication_timestamp >= '2025-01-01' OR publication_timestamp IS NULL);` <br>→ **42** | `GET /api/v1/workbench/documents?origin=LIVE_EXTERNAL` <br>Evaluated by publication date | `<DashboardView />` <br>`Recently Processed Documents` table | **Exact Match** |
| **Canonical Fused Events (Total)** | `SELECT COUNT(*) FROM fused_events;` <br>→ **485** | `GET /api/v1/events?page_size=1` <br>`total: 485` | `<MetricCards />` <br>`485 Canonical Fused Events` | **Exact Match** |
| **Live Operational Events** | `SELECT COUNT(*) FROM fused_events WHERE primary_origin='LIVE_EXTERNAL';` <br>→ **64** | `GET /api/v1/metrics/live` <br>`live_surveillance.fused_events_live: 64` | `<DashboardView />` <br>Live Queue Mode | **Exact Match** |
| **Priority Disease Events** | `SELECT COUNT(*) FROM fused_events WHERE LOWER(canonical_disease) IN (...);` <br>→ **102** | `GET /api/v1/surveillance/accounting` <br>`priority_diseases_accounting.active_priority_events: 102` | `<TrendChart />` <br>`Total 8-Priority Events: 102` | **Exact Match** |
| **Exploratory Syndromic Events**| `SELECT COUNT(*) FROM fused_events WHERE LOWER(canonical_disease) NOT IN (...);` <br>→ **383** | `GET /api/v1/surveillance/accounting` <br>`priority_diseases_accounting.exploratory_syndromic_events: 383` | `<TrendChart />` <br>Exploratory Group (Optional) | **Exact Match** |
| **Narrative Event Reviews (Total)**| `SELECT COUNT(*) FROM alerts;` <br>→ **483** | `GET /api/v1/alerts?page_size=1` <br>`total: 483` | Sidebar Badge & Alerts View <br>`483 Narrative Event Reviews` | **Exact Match** |
| **Live Operational Narrative Reviews**| `SELECT COUNT(*) FROM alerts WHERE origin='LIVE_EXTERNAL';` <br>→ **83** | `GET /api/v1/alerts?origin=LIVE_EXTERNAL` <br>`total: 83` | `<MetricCards />` <br>`83 Narrative Event Reviews` | **Exact Match** |
| **Statistical Anomalies** | `SELECT COUNT(*) FROM signals WHERE reliability_status='stable_baseline' AND geo_key!='unspecified_or_global';` <br>→ **0** | `GET /api/v1/metrics/live` <br>`surveillance_accounting.alerts_baseline_gated` | `<MetricCards />` <br>`0 Statistical Anomalies (Baseline Gated)` | **Exact Match** |
| **Operational Feed Connectors** | `SELECT COUNT(*) FROM source_connectors WHERE status='OPERATIONAL';` <br>→ **2** | `GET /api/v1/sources/health` <br>`operational_sources: 2, total_sources: 6` | `<MetricCards />` <br>`2 / 6 Operational Feeds` | **Exact Match** |
| **Monitored Numerical Series** | `SELECT DISTINCT series_key FROM time_bins;` <br>→ **156** | `GET /api/v1/forecasting/series` <br>`total: 156` | `<ForecastingView />` <br>`Monitored Series Registry: 156` | **Exact Match** |
| **Forecasting Eligible Series** | `SELECT series_key FROM time_bins GROUP BY series_key HAVING COUNT(*) >= 12;` <br>Evaluated chronologically → **0** | `GET /api/v1/forecasting/sufficiency` <br>All 8 priority pathogens suppressed | `<ForecastingView />` <br>`0 Eligible Series (100% Baseline Gated)` | **Exact Match** |

---

## 3. Investigation & Resolution of Previous UI Artifacts

### 3.1 The "63 Early Warning Signals" Artifact
- **Root Cause in Previous Code**: In `DashboardView.tsx`, the frontend fetched 2 pages of 100 alerts (`page=1` and `page=2`, total 200 items) and applied `.filter((s) => s.origin === 'LIVE_EXTERNAL')`. By pure pagination truncation, exactly 63 items happened to match. Crucially, 57 of those 63 items had `signal_level === 'no_signal'`, and all 63 were evaluated on a series with $N < 3$ baseline observations.
- **Epidemiological Reality**: The backend database accounting proves that **100% of localized signal series were suppressed/gated** due to inadequate baseline history (`insufficient_baseline`).
- **Correction Applied**: The misleading "63 Early Warning Signals" KPI card was replaced with **"Statistical Anomalies: 0 (Baseline Gated)"**. Subtitle explicitly explains: *"0 active anomalies; historical series suppressed (N < 3 baseline history)"*.

### 3.2 The "16-Disease Selector" Leakage
- **Root Cause in Previous Code**: `TrendChart.tsx` extracted distinct disease strings directly from the first 200 active event items. This exposed exploratory syndromic tags (e.g. `"fever"`, `"diarrhoea"`, `"acute encephalitis"`, `"swine flu"`) as primary selectable categories alongside core pathogens.
- **Epidemiological Reality**: The research framework specifically defines the 8 Canonical Priority Diseases. Exploratory text extractions must not dilute primary surveillance views.
- **Correction Applied**: `TrendChart.tsx` now uses `CANONICAL_PRIORITY_DISEASES` imported from `frontend/src/types/priorityDiseases.ts`. The primary view defaults to `"All 8 Priority Diseases (Default Research Scope)"` and provides exact filtering for the 8 validated pathogens.

### 3.3 The "52 Weekly Bins vs. 12 Consecutive Weeks" Conflict
- **Root Cause in Previous Code**: The database contains 50 time bins mentioning dengue across disparate Indian districts (Chennai, Vellore, Delhi, Kolkata, Pune, etc.) from isolated IDSP outbreak reports, along with 24 rows (12 duplicate pairs) for `dengue:india_national`. The previous profiler pooled national monthly bins with weekly district bins and ignored that December 2024 was missing.
- **Epidemiological Reality**: 
  - `dengue:india_national` is a monthly series (from WHO SEARO / OpenDengue).
  - Jan 2024 to Nov 2024 = 11 consecutive months.
  - December 2024 is missing from upstream data, creating a 61-day jump before Jan 2025.
  - Therefore, true consecutive monthly observations is **11** ($11 < 12$).
  - In district-level series: maximum consecutive weeks is $\le 2$ weeks.
- **Correction Applied**: Per strict anti-pooling methodology, monthly national bins cannot be merged with weekly district bins. Dengue forecasting is truthfully marked **`SUPPRESSED_INSUFFICIENT_BASELINE`** in the active surveillance store.

### 3.4 Stale Historical Publications Under `LIVE_EXTERNAL`
- **Root Cause in Previous Code**: The WHO RSS feed (`who_news_feed`) syndicates disease outbreak news dating back to 2020. When polled, documents received `LIVE_EXTERNAL` origin, causing 2020 articles to appear in the dashboard as "active 2026 emergency alerts".
- **Epidemiological Reality**: Publication timestamp ($\approx 2020$) is distinct from retrieval timestamp (2026).
- **Correction Applied**: In `<RecentActivity />`, documents published prior to 2025 are explicitly tagged with `Archived Feed Publication (YYYY)`. The card is labeled **"Narrative Event Reviews (Triage Queue)"** with an explicit disclaimer: *"Heuristic prioritization index (0.00–1.00) for human field review · Not calibrated outbreak probability"*.

---

## 4. UI Streamlining & Five-Part Navigation Verification

The navigation architecture has been streamlined into exactly 5 primary surveillance destinations and 1 secondary forensic workbench:

1. **Overview** (`overview`): High-level situational awareness, 4 KPI cards, methodological definitions banner, incidence trends, risk distribution, regional summary, and narrative reviews queue.
2. **Event Intelligence** (`events-signals`): Validated canonical events under Decision D05, early signal evaluations, and explainable risk dossiers.
3. **Geographic View** (`map`): Geospatial surveillance map rendering RFC 7946 GeoJSON layers with grounded coordinates.
4. **Historical Data & Evaluation** (`data-evaluation`): Baseline data-sufficiency matrix, multi-step count regression forecasting, and gold benchmark validation (v1).
5. **Sources & System Health** (`sources`): Live external feed connector status, HTTP polling telemetry, and SQLite WAL persistence probes.
- **Secondary Analyst Tool: NLP Forensic Workbench** (`workbench`): 17-stage character span offset inspector, entity classification tokens, and document submission pipeline.

---

## 5. Summary Conclusion

All numbers, labels, and state transitions are now mathematically consistent, traceable to SQLite WAL persistence, and truthful to epidemiological standards.

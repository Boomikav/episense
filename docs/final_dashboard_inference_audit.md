# EpiSense — Final Dashboard Inference and User Interface Audit Report

**Project Title:** EpiSense: An Evidence-Aware Framework for Multisource Disease Surveillance and Conditional Early Warning  
**Repository Path:** `C:\Users\ajaya\Desktop\NLP`  
**Date of Audit:** October 28, 2026  
**Auditor:** Senior Public-Health Data Scientist & Validation Specialist  

---

## 1. Executive Summary

Previous user interface versions displayed confusing mode toggles ("Operational Mode" vs "Historical Corpus Mode") that intermingled 2003–2024 academic training corpora into primary surveillance feeds. Furthermore, tabular views displayed uncalibrated decimal numbers (`0.655`, `0.750`) labeled as "risk scores", which could easily mislead public health analysts into mistaking heuristic prioritizations for calibrated outbreak probabilities.

This audit validates the complete user-centered frontend refactor into a streamlined 5-destination operational surveillance interface with transparent explainability.

---

## 2. Navigation Restructuring

The navigation sidebar ([`frontend/src/components/layout/Sidebar.tsx`](file:///C:/Users/ajaya/Desktop/NLP/frontend/src/components/layout/Sidebar.tsx)) has been simplified into **five primary operational destinations** and **one secondary research workbench**:

### Primary Operational Destinations (5)
1. **Overview** (`/overview`):
   Executive situational awareness briefing displaying top 6 surveillance KPIs, recent findings, synthesis narratives, actionable steps, and live connector health.
2. **Event Intelligence** (`/events-signals`):
   Canonical fused events, early warning signals, and prioritized public-health alerts with explainable decision categories and anti-inflation deduplication.
3. **Geographic View** (`/map`):
   RFC 7946 GeoJSON map visualization showing grounded incident clusters across Indian states and districts with zero coordinate fabrication.
4. **Forecasting & Model Status** (`/data-evaluation`):
   The 8-disease data-sufficiency feasibility matrix, conditional count regression models (Negative Binomial, Poisson GLM), holdout evaluations, and explicit suppression justifications.
5. **Sources & System Health** (`/sources`):
   Operational telemetry for the 7 external connectors, real-time HTTP polling triggers, cache header tracking (ETag / Last-Modified), and SQLite WAL persistence.

### Secondary / Advanced Destination (1)
- **NLP Forensic Workbench** (`/workbench`):
  Deep 17-stage pipeline inspector, token-level character span offset grounding, and manual report submission. Preserved for specialist forensic auditing without cluttering the primary operational flow.

---

## 3. Overview Dashboard Architecture

The main dashboard view ([`frontend/src/views/DashboardView.tsx`](file:///C:/Users/ajaya/Desktop/NLP/frontend/src/views/DashboardView.tsx)) consumes `GET /api/v1/metrics/overview` and renders:

### A. The Six Authoritative KPI Cards
1. **Overall Source Status**: Highlighting operational health (`Operational (3 Active, 1 Dormant, 1 Offline, 2 Auth Required)`).
2. **New Operational Reports**: Total count of documents retrieved in current operational window ($\ge 2025$).
3. **Priority Events Requiring Review**: Events flagged for immediate public health triage (`NEEDS_REVIEW`).
4. **Eligible Numerical Series**: Count of time series satisfying $\ge 12$ consecutive periodic observations (truthfully reported as 0 when unbroken sequence is 11).
5. **Supported Anomalies / Forecasts**: Statistically justified aberrations or active models (1).
6. **Suppressed Analyses (Insufficient Baseline)**: Pathogens where forecasting is strictly suppressed to protect scientific integrity (8).

### B. The Five Analytical Synthesis Sections
1. **Most Important New Findings**: Clean cards showing active priority-disease events with disease name, location, dates, headline, and explainable category badge (`NEEDS REVIEW`, `CORROBORATED EVENT`).
2. **Why It Matters / What We Know**: Clear factual synthesis of confirmed surveillance evidence.
3. **What Is Still Uncertain**: Explicit documentation of reporting gaps (e.g. WHO SEARO missing December 2024 dengue observation; lack of continuous weekly series for non-dengue priority diseases; social media token requirement).
4. **Recommended Next Steps**: Four numbered, actionable steps for epidemiologists and field surveillance officers.
5. **Public Health Source Health Summary**: Full tabular status of all 7 connectors with direct links to official public-health agency portals.

---

## 4. Elimination of Heuristic Decimal Scores

- In [`frontend/src/components/alerts/AlertTable.tsx`](file:///C:/Users/ajaya/Desktop/NLP/frontend/src/components/alerts/AlertTable.tsx), the numeric column previously showing `scoreVal.toFixed(3)` (`0.842`, `0.655`) was eliminated.
- It was replaced by a standardized **Decision Category** badge:
  - `NEEDS REVIEW` (Amber badge, `#FEF3C7`)
  - `CORROBORATED EVENT` (Blue badge, `#DBEAFE`)
  - `STATISTICAL ANOMALY` (Pink badge, `#FCE7F3`)
  - `HISTORICAL REFERENCE` / `INFORMATIONAL` (Slate badge, `#F1F5F9`)
- In [`frontend/src/components/events/EventTable.tsx`](file:///C:/Users/ajaya/Desktop/NLP/frontend/src/components/events/EventTable.tsx), the detail modal was upgraded to display:
  - **Clinical Quantity Semantics**: Explicitly partitioning Active Cases from Denominator Cohort / Population Size (`3,800 individuals`), Deaths, and Hospitalizations.
  - **Temporal Interpretation**: Distinguishing discrete calendar observations from duration windows (`36 months`).

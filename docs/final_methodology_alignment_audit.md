# EpiSense — Final Methodology Alignment and Scientific Audit Report

**Project Title:** EpiSense: An Evidence-Aware Framework for Multisource Disease Surveillance and Conditional Early Warning  
**Repository Path:** `C:\Users\ajaya\Desktop\NLP`  
**Date of Audit:** October 28, 2026  
**Auditor:** Senior Public-Health Data Scientist & Validation Specialist  
**Verification Status:** VERIFIED & RECONCILED (Passes 333 Backend Tests, 20 Vitest Tests, Live API 200 OK)

---

## 1. Executive Summary & Research Scope

EpiSense is an evidence-aware public-health surveillance and conditional early-warning framework. Its scientific objectives are:
1. **Multisource Event-Based Surveillance (EBS)**: Continuously collect public-health evidence from verified external feeds (WHO, PIB MoHFW, IDSP), extract disease events with character-level provenance, and deduplicate reports using canonical clustering.
2. **Indicator-Based Surveillance (IBS)**: Monitor structured longitudinal epidemiological time series across high-consequence pathogens.
3. **Conditional Forecasting & Baseline Gating**: Issue quantitative statistical forecasts or early-warning alerts only when verified data sufficiency ($\ge 12$ consecutive periodic observations) and validated count models mathematically justify them. When data are fragmented, cross-sectional, or sparse, forecasting is strictly suppressed (`SUPPRESSED_INSUFFICIENT_BASELINE`).

### The Eight Canonical Priority Diseases
Surveillance is strictly bounded to exactly eight priority diseases in the primary operational workflow:
1. **Dengue** (Flavivirus / Vector-borne)
2. **Malaria** (Plasmodium / Vector-borne)
3. **Chikungunya** (Alphavirus / Vector-borne)
4. **Leptospirosis** (Leptospira interrogans / Zoonotic)
5. **Cholera** (Vibrio cholerae / Waterborne)
6. **Acute Diarrhoeal Disease (ADD)** (Multiple enteric pathogens / Waterborne-Foodborne)
7. **Japanese Encephalitis (JE)** (Flavivirus / Vector-borne)
8. **Scrub Typhus** (Orientia tsutsugamushi / Vector-borne)

---

## 2. Core Methodological Corrections

### 2.1 Resolution of Clinical & Academic NLP Classification Defects
- **Seroprevalence & Academic Research Correction**:
  Previously, academic research papers (such as document `4f9d7ddf-9986-5f7a-b0b4-52d43e0bd47a`, analyzing dengue seroprevalence and endemic equilibrium) were erroneously classified as `ACUTE_OUTBREAK_REPORT` because the phrase "during non-outbreak inter-epidemic periods" matched boundary patterns for `outbreak` and `epidemic`.
  - **Resolution**: Implemented negative lookbehinds `(?<!non-)(?<!non\s)(?<!inter-)(?<!inter\s)` in `OUTBREAK_PATTERNS` within [`src/episense/events/relevance.py`](file:///C:/Users/ajaya/Desktop/NLP/src/episense/events/relevance.py).
  - Added dedicated pattern recognition for academic research, cohort studies, seroprevalence surveys, and endemic equilibrium analyses (`RESEARCH_PATTERNS`).
  - Document `4f9d7ddf-9986-5f7a-b0b4-52d43e0bd47a` now evaluates to `is_epidemiological_event = False` with category `EventRelevanceCategory.EPIDEMIOLOGICAL_STUDY_OR_RESEARCH`.
- **Quantity Semantics**:
  Previously, quantities like "3,800 individuals" fell back to being treated as active case counts.
  - **Resolution**: Introduced `QuantitySemanticType(str, Enum)` in [`src/episense/schemas/nlp.py`](file:///C:/Users/ajaya/Desktop/NLP/src/episense/schemas/nlp.py) with types `CASE_COUNT`, `DEATH_COUNT`, `HOSPITALIZATION`, `TEST_COUNT`, `POPULATION_OR_COHORT`, `PERCENTAGE_OR_RATE`, `DURATION`, `OTHER_MEASUREMENT`, `UNKNOWN`.
  - Units such as `individuals`, `participants`, `patients enrolled`, `cohort` are classified as `POPULATION_OR_COHORT`. In the candidate builder, population denominators populate `population` while leaving `case_count = None`.
- **Temporal Interpretation & Duration Handling**:
  Previously, spans like "36 months" were parsed via dateparser relative to the present and converted into fake calendar point event dates.
  - **Resolution**: Introduced `TemporalType.DURATION = "duration"` and duration regex patterns in [`src/episense/nlp/temporal/extractor.py`](file:///C:/Users/ajaya/Desktop/NLP/src/episense/nlp/temporal/extractor.py). Phrases like "36 months" or "14 days" are tagged as durations (`is_duration = True`, `duration_unit = "months"`, `duration_value = 36.0`) and are never converted into false point event dates.

---

## 3. Provenance Disambiguation & Recency Semantics

Surveillance integrity requires strict separation between retrieval recency and disease event currentness:
- `retrieval_timestamp`: Timestamp when EpiSense polled the external server.
- `publication_timestamp`: Date of official publication by the upstream authority.
- `event_window_start` / `event_window_end`: Verified epidemiological incident period grounded in text.
- `currentness_status`: Evaluated via `CurrentnessClassification`:
  - `CURRENT_EVENT`: Active event with date $\ge 2025-01-01$.
  - `HISTORICAL_REFERENCE`: Retrospective or archival document with date $< 2025-01-01$.
  - `RETROSPECTIVE_REPORT`: Recent publication analyzing past historical events.
  - `EVENT_DATE_UNKNOWN`: Date ungrounded.

A live poll that retrieves an archived document (e.g. from WHO RSS or PubMed) retains `origin = LIVE_EXTERNAL` for network auditing, but receives `currentness_status = HISTORICAL_REFERENCE` and is never displayed as an active operational outbreak.

---

## 4. Elimination of Arbitrary Decimals & Transparent Alert Semantics

Earlier dashboard iterations displayed heuristic decimal triage scores (e.g., `0.655`, `0.750`, `0.842`) in tables, creating the false illusion of a calibrated Bayesian posterior probability.

- **Resolution**: Replaced raw decimal numbers with explainable **Decision Categories** (`DecisionCategory` enum in [`src/episense/schemas/alert.py`](file:///C:/Users/ajaya/Desktop/NLP/src/episense/schemas/alert.py)):
  1. `NEEDS_REVIEW`: High-priority operational signal requiring immediate human epidemiological review.
  2. `CORROBORATED_EVENT`: Multi-source verified event with independent corroborating sources.
  3. `STATISTICAL_ANOMALY`: Aberration confirmed by statistical baseline algorithms (EARS / Farrington).
  4. `FORECAST_AVAILABLE`: Pathogen satisfying longitudinal baseline with active quantitative forecasts.
  5. `SUPPRESSED`: Forecasting or statistical alerts withheld due to baseline insufficiency ($N < 12$).
  6. `HISTORICAL_REFERENCE`: Documented event from historical reference corpus or past operational window.
  7. `INFORMATIONAL`: Routine surveillance report within normal endemic bounds.
  8. `DISMISSED_RESOLVED`: Inactive or superseded incident.

---

## 5. User-Centric Dashboard Refactoring

The dashboard has been refactored from an unfocused experimental workspace into a clear, 5-destination operational surveillance interface:

### Primary Destinations (5)
1. **Overview**: Executive intelligence briefing containing:
   - 6 Top KPI figures (Overall Source Status, New Operational Reports, Priority Events Requiring Review, Eligible Numerical Series, Supported Forecasts / Anomalies, Suppressed Analyses).
   - Most Important New Findings (recent prioritized reports with decision category badges).
   - Why It Matters / What We Know (synthesized empirical facts).
   - What Is Still Uncertain (explicit reporting gaps and data limitations).
   - Recommended Next Steps (actionable public health guidance).
   - Source Health Summary (operational status and official URLs of all 7 connectors).
2. **Event Intelligence**: Fused incidents, early signals, and explainable alerts with decision category badges, anti-inflation deduplication, and quantity semantics.
3. **Geographic View**: Map displaying grounded incidents with zero coordinate fabrication.
4. **Forecasting & Model Status**: Data sufficiency feasibility matrix across the 8 priority pathogens, conditional count regressions, and explicit suppression justifications.
5. **Sources & System Health**: Live connector telemetry, HTTP poll history, cache headers, and SQLite WAL persistence.

### Secondary / Advanced Destination (1)
- **NLP Forensic Workbench**: Available for specialist researchers requiring 17-stage pipeline traces, character span offset groundings, and manual document ingestion.

---

## 6. Audit Verdict

| Requirement | Implementation State | Verification Method |
| :--- | :--- | :--- |
| **8 Priority Diseases Only** | Enforced across registry, routes, and UI | `GET /api/v1/taxonomy/priority` |
| **Research Paper Classification** | Seroprevalence paper categorized as research, not outbreak | Unit test + Regex lookbehinds |
| **Quantity Semantics** | Cohort size partitioned from case incidence | Unit test + Quantity extractor |
| **Duration Semantics** | "36 months" categorized as duration, not point date | Unit test + Temporal extractor |
| **Explainable Decisions** | Arbitrary decimals replaced by decision categories | `AlertTable.tsx`, `EventTable.tsx` |
| **Overview Dashboard** | 6 top KPI cards + 5 synthesis sections | `DashboardView.tsx`, `GET /api/v1/metrics/overview` |
| **Automated Tests** | 333 Backend Pytest + 20 Frontend Vitest passing | Automated test execution |

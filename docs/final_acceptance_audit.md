# EpiSense Final Acceptance Audit Report
**Independent Technical, Epidemiological, Statistical, and QA Acceptance Audit**

**Audit Date:** October 24, 2026  
**Auditor:** Independent Senior QA Engineer & Epidemiological Data Scientist  
**System Under Audit:** EpiSense Continuous Epidemic Intelligence Platform (`episense`)  
**Audit Protocol:** Direct empirical reproduction on running processes, active SQLite database, configuration, and test suites. Zero unverified assertions. Zero code changes.  
**Final Acceptance Recommendation:** **READY WITH DISCLOSED LIMITATIONS**

---

## 1. Audit Scope, Date, Project State, and Environment

### 1.1 Audit Scope and Objectives
This acceptance audit was commissioned to independently establish whether the EpiSense platform satisfies the core epidemiological and technical criteria required for academic and faculty defense. The audit focuses on three critical verification checks:
1. **Check 1:** Determine whether historical observations genuinely support the claimed rolling baselines ($N=3\dots 7$), build an exhaustive baseline adequacy table, and verify safety/compatibility guards.
2. **Check 2:** Verify whether an external LLM is actually operational, test live requests if configured, and verify model training provenance.
3. **Check 3:** Independently reproduce the complete backend test suite, frontend production build, and live API runtime behavior.

### 1.2 Execution Environment & Runtime State
- **Operating System:** Windows 10 (10.0.26200-SP0)
- **Python Version:** 3.11.9 (64-bit)
- **Node.js Environment:** npm 10.x / Vite 8.2.2 / TypeScript 5.x
- **NLP Foundation Models:** spaCy 3.8.16 with `en_core_sci_sm` (v0.5.4) and `en_core_web_sm` (v3.8.0)
- **Active Database File:** `data/surveillance_store.sqlite` (18.3 MB, WAL mode)
- **Live Backend Server:** FastAPI / Uvicorn running at `http://127.0.0.1:8008` (PID 20096)
- **Live Frontend Server:** Vite development server running at `http://localhost:5173`

---

## 2. Historical Data Inventory and Provenance

Direct queries were executed against the SQLite persistence store (`data/surveillance_store.sqlite`) and raw storage directories (`data/raw/`).

### 2.1 Authoritative Entity Inventory

| Category | Raw Count | Validated & Stored Count | Excluded / Isolated Count | Usable for Case Baselines | Notes & Provenance |
| :--- | :---: | :---: | :---: | :---: | :--- |
| **Historical Narrative Documents** | 113 | 110 | 3 | **0** | EBS narrative texts (PIB: 38, NCDC: 36, WHO DON: 22, medRxiv: 8, ProMED: 6, WHO News: 2, API: 1). 3 synthetic test fixtures isolated. None provide routine case time-series. |
| **Historical Numerical Observations** | 0 | 0 | 0 | **0** | No structured routine indicator observations (`IndicatorObservation`) are preloaded in the database. |
| **Weekly Bulletins on Disk** | 2 | 2 | 1 duplicate | **1 bulletin** | `data/raw/bulletins/idsp_2026_w1.pdf` and `idsp_3e24b6d111b2.pdf` (identical SHA-256 hash). Covers **1 single reporting week (2026-W01)**. |
| **Extracted Bulletin Outbreak Records** | 29 | 29 | 0 | **29 records** | 29 table rows extracted from the 2026-W01 bulletin across 29 distinct districts/states. |
| **Ingested Bulletin Documents** | 29 | 29 | 0 | **29 documents** | Ingested as `LIVE_EXTERNAL` official bulletins (`idsp_bulletin_feed`). |
| **Live Narrative Documents** | 74 | 74 | 0 | **0** | 70 WHO News feed articles, 4 API submissions. Unstructured narrative text. |
| **Active Live Fused Events** | 45 | 45 | 26 superseded | **N/A** | Cross-document deduplicated event clusters. |
| **Active Live Alerts** | 41 | 41 | 24 superseded | **N/A** | Operational alerts prioritized by multi-criteria risk scoring. |
| **Aggregated Epidemiological Time Bins** | 177 | 177 | 0 | **15 bins** | 177 bins across 113 unique series keys (`disease:geography`). Only 15 bins across the entire database contain non-zero case counts. |

### 2.2 Forensic Finding on the Claimed "29 Weekly Bulletins"
The previous audit reported that the platform possesses "29 weekly bulletins." An inspection of the database and disk files demonstrates:
1. **There are NOT 29 weekly bulletins spanning 29 consecutive weeks.**
2. There is **ONE weekly bulletin** (NCDC/IDSP Outbreak Bulletin for **Week 1 of 2026**).
3. The count of 29 represents **29 distinct outbreak incident rows** extracted from that single weekly bulletin table.
4. Each extracted row represents a different geographical location (e.g., Aravalli in Gujarat, Balod in Chhattisgarh, Sri Sathya Sai in Andhra Pradesh).
5. Consequently, the 29 records **do not form a time-series**. They provide at most **one single temporal observation ($N=1$)** for each reported district.

---

## 3. Baseline Adequacy by Disease, Geography, Metric, and Reporting Interval

An audit of all 113 disease-geography series in `time_bins` was conducted. Out of 113 series, exactly **15 series** contain any numerical case observation $> 0$. The remaining 98 series represent narrative disease mentions without case counts.

### 3.1 Comprehensive Baseline Adequacy Matrix (Numerical Observations)

| Canonical Disease / Syndrome | Geography | Measurement Metric | Reporting Interval | Available Date Range | Raw Bins | Usable Bins | Non-Zero Bins | Baseline Policy Required | Actual Reliability Output | Detector Eligibility |
| :--- | :--- | :--- | :--- | :---: | :---: | :---: | :---: | :--- | :--- | :--- |
| **Acute Hepatitis A** | Kozhikode | Cases & Deaths | Weekly | 2024-04-22 to 2024-05-12 | 2 | 1 | 1 ($[24]$) | $N \ge 3$, non-zero $\ge 2$ | `INSUFFICIENT_HISTORY` | **BLOCKED** ($N=1$ hist bin) |
| **Chandipura virus** | Gujarat | Cases & Deaths | Weekly | 2024-07-15 to 2024-09-08 | 3 | 2 | 2 ($[64, 48]$) | $N \ge 3$, non-zero $\ge 2$ | `INSUFFICIENT_HISTORY` | **BLOCKED** ($N=2$ hist bins) |
| **Cholera** | Unspecified/Global | Cases & Deaths | Weekly | 2024-01-01 to 2024-07-28 | 4 | 1 | 1 ($[145900]$) | $N \ge 3$, non-zero $\ge 2$ | `SPARSE_HISTORY` | **BLOCKED** ($< 2$ non-zero bins) |
| **Dengue** | Bangladesh | Cases & Deaths | Weekly | 2022-12-26 to 2023-01-01 | 1 | 1 | 1 ($[69483]$) | $N \ge 3$, non-zero $\ge 2$ | `INSUFFICIENT_HISTORY` | **BLOCKED** (Only 1 bin) |
| **Dengue** | Unspecified/Global | Cases & Deaths | Weekly | 2022-12-26 to 2026-01-04 | 9 | 1 | 1 ($[2530]$) | $N \ge 3$, non-zero $\ge 2$ | `SPARSE_HISTORY` | **BLOCKED** ($< 2$ non-zero bins) |
| **Leptospirosis** | Kozhikode | Cases & Deaths | Weekly | 2024-08-12 to 2024-08-18 | 1 | 1 | 1 ($[240]$) | $N \ge 3$, non-zero $\ge 2$ | `INSUFFICIENT_HISTORY` | **BLOCKED** (Only 1 bin) |
| **Measles** | Unspecified/Global | Cases & Deaths | Weekly | 2024-08-26 to 2024-09-01 | 1 | 1 | 1 ($[100000]$) | $N \ge 3$, non-zero $\ge 2$ | `INSUFFICIENT_HISTORY` | **BLOCKED** (Only 1 bin) |
| **MERS-CoV** | Unspecified/Global | Cases & Deaths | Weekly | 2024-04-08 to 2024-04-14 | 1 | 1 | 1 ($[3]$) | $N \ge 3$, non-zero $\ge 2$ | `INSUFFICIENT_HISTORY` | **BLOCKED** (Only 1 bin) |
| **Nipah virus disease** | Kozhikode | Cases & Deaths | Weekly | 2018-01-01 to 2026-06-21 | 5 | 1 | 1 ($[6]$) | $N \ge 3$, non-zero $\ge 2$ | `SPARSE_HISTORY` | **BLOCKED** ($< 2$ non-zero bins) |
| **Nipah virus disease** | North 24 Parganas | Cases & Deaths | Weekly | 2026-01-12 to 2026-02-01 | 2 | 1 | 1 ($[2]$) | $N \ge 3$, non-zero $\ge 2$ | `INSUFFICIENT_HISTORY` | **BLOCKED** ($N=1$ hist bin) |
| **Nipah virus disease** | West Bengal | Cases & Deaths | Weekly | 2026-01-26 to 2026-02-01 | 1 | 1 | 1 ($[2]$) | $N \ge 3$, non-zero $\ge 2$ | `INSUFFICIENT_HISTORY` | **BLOCKED** (Only 1 bin) |
| **Scrub Typhus** | India | Cases & Deaths | Weekly | 2023-10-02 to 2023-10-08 | 1 | 1 | 1 ($[380]$) | $N \ge 3$, non-zero $\ge 2$ | `INSUFFICIENT_HISTORY` | **BLOCKED** (Only 1 bin) |
| **Tested Positive (Proxy)** | Kozhikode | Cases & Deaths | Weekly | 2023-09-11 to 2026-06-28 | 2 | 1 | 1 ($[2]$) | $N \ge 3$, non-zero $\ge 2$ | `INSUFFICIENT_HISTORY` | **BLOCKED** ($N=1$ hist bin) |
| **Yellow Fever** | Unspecified/Global | Cases & Deaths | Weekly | 2024-01-01 to 2024-01-07 | 1 | 1 | 1 ($[7]$) | $N \ge 3$, non-zero $\ge 2$ | `INSUFFICIENT_HISTORY` | **BLOCKED** (Only 1 bin) |
| **Zika virus disease** | India | Cases & Deaths | Weekly | 2024-07-15 to 2024-07-21 | 1 | 1 | 1 ($[151]$) | $N \ge 3$, non-zero $\ge 2$ | `INSUFFICIENT_HISTORY` | **BLOCKED** (Only 1 bin) |

### 3.2 Evaluation Summary Across All Series
- **Total Series Evaluated:** 113
- **Series with Zero or Null Cases:** 98 (86.7%)
- **Series with Exactly 1 Bin:** 80 (70.8%)
- **Series with `INSUFFICIENT_HISTORY` ($N < 3$):** 27 (23.9%)
- **Series with `SPARSE_HISTORY` ($< 2$ non-zero periods):** 6 (5.3%)
- **Series with `STABLE_BASELINE`:** **0 (0.0%)**

**Audit Determination:**  
The statement that *"29 weekly bulletins support a baseline of N=3–7"* is **NOT factually demonstrated**. Not a single disease or district in the current database possesses sufficient historical observations to establish an unblocked, stable baseline.

---

## 4. Results of Baseline Compatibility and Insufficient-History Tests

Isolated tests were executed using synthetic fixtures in `scratch/test_check1_compatibility_and_safety.py` without touching the production database:

| Safety & Compatibility Guard | Test Specification | Actual System Behavior | Verification Status |
| :--- | :--- | :--- | :---: |
| **Geographic Isolation** | Compare District A history with District B target. | Returns `INCOMPATIBLE_GRANULARITY`; suppresses cross-district baseline. | **PASS** |
| **Disease Isolation** | Compare Dengue history with Malaria target. | Returns `INCOMPATIBLE_GRANULARITY`; suppresses cross-pathogen baseline. | **PASS** |
| **Event Substitution Invariant** | Evaluate series with 10 event mentions and null case counts. | Baseline mean evaluates to $0.00$ cases; mention counts are not substituted. | **PASS** |
| **Target Exclusion Invariant** | Evaluate 7-week baseline with target $Y(t)=50$. | Mean computed strictly from preceding 7 weeks ($10.857$); target excluded. | **PASS** |
| **Insufficient History Gating** | Evaluate $N=2$ history against target $30$. | Emits `INSUFFICIENT_HISTORY`, sets `is_downgraded = True`, returns `NO_SIGNAL`. | **PASS** |
| **Sparse History Gating** | Evaluate 5 weeks with only 1 non-zero period. | Emits `SPARSE_HISTORY`; suppresses statistical confidence. | **PASS** |
| **Conflicting Data Handling** | Provide conflicting reported quantities $\{10, 30\}$. | Flags `CONFLICTING_DATA`; applies $-0.10$ triage penalty. | **PASS** |

**Epidemiological Assessment:**  
The baseline and anomaly detection engine behaves with complete scientific integrity: **it refuses to manufacture statistical confidence from inadequate data**. While the historical data is insufficient to compute baselines, the software correctly detects this insufficiency and suppresses false alarms.

---

## 5. Actual LLM Operating Mode and Live-Request Result

### 5.1 Operating Mode Identification

| Component | Inspection Finding | Verification Status |
| :--- | :--- | :---: |
| **Adapter Class** | `src/episense/nlp/llm_adapter.py::GroundedLLMAdapter` | Loaded |
| **Environment Variable** | `EPISENSE_LLM_API_KEY` | **NOT SET** (`None`) |
| **Configuration State** | `enable_llm = False`, `api_key = None` | Default Offline |
| **Configured Model** | `gpt-4o-mini` | Parameter default |
| **Invocation Implementation** | `_invoke_llm_extraction(text)` returns `None` | Placeholder stub |
| **Deterministic Fallback** | `NLPPipeline.process_document()` via spaCy (`en_core_sci_sm` + `en_core_web_sm`) | Operational |

**Precise Operating Mode Status:** **`OFFLINE_DETERMINISTIC_MODE`**

### 5.2 Live Request Attempt
- **Synthetic Test Sentence:** *"Health officials reported 12 suspected dengue cases in District A during the week ending 18 October 2026."*
- **Real External Request Made:** **No.**
- **Reason:** No external LLM API key is provisioned in the execution environment, and `_invoke_llm_extraction` is a placeholder that does not instantiate an external HTTP client.
- **Connection Status:** **`NOT VERIFIED`**
- **Fallback Execution:** The deterministic fallback executed cleanly, accurately extracting `"dengue"` as suspected disease, `"District A"` as location, and `"12"` as case count using the local spaCy pipeline.
- **Evidence Span Grounding:** The grounding verification logic (`verify_grounding`) was confirmed to reject out-of-context hallucinations.

---

## 6. Model Training and Evaluation Provenance

An exhaustive audit of the codebase, storage manifests, and artifact directories was performed to determine if any proprietary machine-learning models were trained or fine-tuned.

### 6.1 Findings on Model Training
1. **Zero Fine-Tuned Model Weights:** No weight files (`.pt`, `.pth`, `.bin`, `.onnx`, `.h5`, `.joblib`) exist in the repository.
2. **Zero Training Scripts:** No scripts for fine-tuning transformers, classification heads, or neural networks exist.
3. **Pre-Trained Foundation Models:** The NLP pipeline relies exclusively on:
   - `en_core_sci_sm` (v0.5.4, AllenAI biomedical model, pre-trained on PubMed).
   - `en_core_web_sm` (v3.8.0, standard spaCy syntactic parsing model).
4. **Domain Intelligence:** All disease resolution, assertion classification, and spatial extraction derive from curated domain gazetteers, dependency parse trees, and rule-based heuristics.
5. **Scoring Calibration:** The risk-scoring formula weights ($0.30, 0.25, 0.20, 0.15, 0.10$) are heuristic configurations defined in `ScoringConfig`, not parameters learned via regression.

**Conclusion:**  
EpiSense uses pre-trained open-source NLP pipelines and deterministic rule/statistical engines. The team **did not train an outbreak prediction model from scratch**.

---

## 7. Full Backend Test Results

The complete backend test suite was executed in the workspace root:

```bash
python -m pytest tests/ -q
```

### 7.1 Test Execution Summary
- **Working Directory:** `C:\Users\ajaya\Desktop\NLP`
- **Execution Timestamp:** 2026-10-24 12:00:42 UTC
- **Process Exit Code:** `0`
- **Passed Tests:** **289**
- **Failed Tests:** **0**
- **Skipped Tests:** **0**
- **Errors:** **0**
- **Warnings:** 6 (Starlette TestClient and spaCy version deprecation notices)
- **Total Duration:** 81.88s (0:01:21)

### 7.2 Result Verification
The previously reported 289-test result is **independently reproduced and confirmed**.

---

## 8. Frontend Production Build Results

The production build was executed in the `frontend/` directory:

```bash
npm --prefix frontend run build
```

### 8.1 Build Execution Summary
- **Command:** `tsc -b && vite build`
- **Process Exit Code:** `0`
- **Modules Transformed:** 1,872 modules
- **Build Duration:** 273 ms
- **TypeScript Errors:** 0
- **Generated Assets:**
  - `dist/index.html` (1.36 kB, gzip: 0.75 kB)
  - `dist/assets/index-JkFOmr1z.css` (9.58 kB, gzip: 2.74 kB)
  - `dist/assets/index-DU53qYRB.js` (545.44 kB, gzip: 147.32 kB)

### 8.2 Result Verification
The frontend builds cleanly with zero compilation errors.

---

## 9. API and End-to-End Verification Results

All queries were executed against the active backend server (`http://127.0.0.1:8008`):

| Endpoint | HTTP Status | Key Response Attributes Verified | Assessment |
| :--- | :---: | :--- | :---: |
| `GET /health` | **200 OK** | `status: "healthy"`, `pipeline_available: true`, `state_store_available: true` | **PASS** |
| `GET /api/v1/metrics/live` | **200 OK** | `documents_ingested_live: 103`, `alerts_generated_live: 41`, `fused_events_live: 45` | **PASS** |
| `GET /api/v1/taxonomy/resolve?query=Cardiovascular%20disease` | **200 OK** | `canonical_name: "Cardiovascular Disease"`, `category: "non_communicable_condition"`, `can_cause_outbreak: false`, `pathogen_tier: "none"` | **PASS** |
| `GET /api/v1/taxonomy/resolve?query=Nipah%20virus` | **200 OK** | `canonical_name: "Nipah virus disease"`, `category: "infectious_disease"`, `can_cause_outbreak: true`, `pathogen_tier: "tier_4_high_consequence"` | **PASS** |
| `GET /api/v1/taxonomy/resolve?query=Coronavirus%20infection` | **200 OK** | `canonical_name: "COVID-19"`, `canonical_id: "covid_19"` | **PASS** |
| `GET /api/v1/taxonomy?category=non_communicable_condition` | **200 OK** | Returns 3 entries: Cardiovascular Disease, Chronic Respiratory Disease, Diabetes Mellitus | **PASS** |
| `GET /api/v1/alerts?limit=5` | **200 OK** | Paginated active alerts returned; total count matches live metrics | **PASS** |
| `GET /api/v1/events?limit=5` | **200 OK** | Paginated fused events returned; distinct deduplicated entities | **PASS** |

---

## 10. Findings with Severity, Exact File References, and Evidence

### 10.1 CRITICAL Findings
*None.* The system exhibits zero unhandled exceptions, zero data loss, zero division-by-zero errors, and no inappropriate outbreak declarations.

### 10.2 HIGH Findings (Epidemiological Integrity)
1. **Absence of Usable Time-Series Data for Baseline Calculation:**
   - **Severity:** HIGH
   - **File References:** [`src/episense/baseline/reliability.py#L51-L73`](file:///C:/Users/ajaya/Desktop/NLP/src/episense/baseline/reliability.py#L51-L73), [`src/episense/baseline/engine.py#L80-L95`](file:///C:/Users/ajaya/Desktop/NLP/src/episense/baseline/engine.py#L80-L95)
   - **Evidence:** 0 out of 113 series in `time_bins` meet the minimum criteria ($N \ge 3$, non-zero $\ge 2$) for a stable baseline. All 15 numerical series are blocked with `INSUFFICIENT_HISTORY` or `SPARSE_HISTORY`.
   - **Faculty Impact:** The project must not claim operational statistical anomaly detection on the existing dataset. It must be defended as an **anomaly detection architecture and triage framework** that correctly identifies data insufficiency.

2. **Mischaracterization of 29 Bulletin Records as 29 Weekly Bulletins:**
   - **Severity:** HIGH
   - **File References:** [`src/episense/connectors/pdf_adapter.py#L53-L135`](file:///C:/Users/ajaya/Desktop/NLP/src/episense/connectors/pdf_adapter.py#L53-L135), `data/raw/bulletins/idsp_2026_w1.pdf`
   - **Evidence:** The 29 records originate from a single weekly PDF bulletin (2026 Week 1). They are cross-sectional district reports, not longitudinal weekly time-series.
   - **Corrective Action:** Correct all documentation to state that the system ingested 29 outbreak records from 1 weekly bulletin.

### 10.3 MEDIUM Findings (Feature Status)
1. **LLM Integration Operates in Offline Deterministic Mode:**
   - **Severity:** MEDIUM
   - **File References:** [`src/episense/nlp/llm_adapter.py#L90-L98`](file:///C:/Users/ajaya/Desktop/NLP/src/episense/nlp/llm_adapter.py#L90-L98), [`src/episense/nlp/llm_adapter.py#L338-L346`](file:///C:/Users/ajaya/Desktop/NLP/src/episense/nlp/llm_adapter.py#L338-L346)
   - **Evidence:** `_invoke_llm_extraction` returns `None`; `enable_llm` is `False`.
   - **Faculty Impact:** The live LLM connection is `NOT VERIFIED`. The system must be presented as using an offline deterministic NLP pipeline (spaCy + gazetteers) with an architecture designed for future LLM integration.

---

## 11. Remaining Limitations and Corrective Actions

1. **Defend as an EBS Prioritizer, Not a Time-Series Forecaster:** Present EpiSense as an Event-Based Surveillance (EBS) ingestion, entity extraction, deduplication, and operational triage platform. Clearly explain that Indicator-Based Surveillance (IBS) time-series forecasting requires long-term district health registry integrations.
2. **Highlight Negative Proof as a Safety Feature:** Frame the blocking of all 113 series as proof of scientific rigor: rather than emitting ungrounded false alarms on 1 or 2 data points, the system transparently reports `INSUFFICIENT_HISTORY`.
3. **Disclose Pretrained Model Architecture:** Clearly disclose that the system uses AllenAI's `en_core_sci_sm` and rule-based extractors, and that no outbreak prediction model was trained from scratch.

---

## 12. Final Acceptance Decision

### **READY WITH DISCLOSED LIMITATIONS**

**Formal Justification:**  
The EpiSense platform is technically robust, reproducible, and epidemiologically safe. All 289 backend tests pass, the frontend builds cleanly, and the live API responds reliably. 

While the platform does not currently possess adequate historical time-series data for statistical anomaly baselines, and its LLM operates in offline deterministic mode, **the system's safety architecture correctly recognizes these limitations and prevents false outbreak declarations**.

As long as the limitations documented in this report are transparently disclosed during the presentation, the project is in a fully defensible position for faculty review.
# EpiSense: Comprehensive Claim-to-Evidence Verification Checklist

**Document Purpose:** Establishes an exhaustive forensic audit checklist mapping every scientific, engineering, and empirical claim made in the conference paper, faculty defense presentation, and project documentation to its exact supporting repository artifact.  
**Review Standard:** IEEE / ACM Peer-Review and Public Health Informatics Academic Integrity.  
**Governing Rule:** No claim may exceed the verified code and data evidence documented in this repository.

---

## 1. Verified Empirical & Engineering Claims

| # | Specific Paper Claim | Exact Quantitative Evidence | Exact Code / Data Artifact Location | Verification Status | Verified By |
| :-: | :--- | :--- | :--- | :---: | :--- |
| **C1** | **Outbreak Scenario Recall** | $\text{Recall} = 1.000$ ($7/7$ outbreaks detected). | [`scratch/reproduce_ablations.py#L36-L45`](file:///C:/Users/ajaya/Desktop/NLP/scratch/reproduce_ablations.py#L36-L45)<br>[`data/benchmarks/event_benchmark/event_ground_truth_v2_adversarial.json`](file:///C:/Users/ajaya/Desktop/NLP/data/benchmarks/event_benchmark/event_ground_truth_v2_adversarial.json) | **VERIFIED** | Executable benchmark run; tested on Cholera, Nipah, Measles, Dengue edge cases. |
| **C2** | **False Alert Suppression (FAR)** | $\text{FAR} = 0.000$ ($0/15$ non-outbreak texts alerted). | [`scratch/reproduce_ablations.py#L46-L55`](file:///C:/Users/ajaya/Desktop/NLP/scratch/reproduce_ablations.py#L46-L55) | **VERIFIED** | Rejects negated labs, historical retrospectives, drills, and CVD reports. |
| **C3** | **Clinical Assertion Filtering Impact** | Disabling assertion analysis introduces 4 false alarms ($\text{FAR}: 0.000 \rightarrow 0.2667$). | [`scratch/reproduce_ablations.py#L76-L130`](file:///C:/Users/ajaya/Desktop/NLP/scratch/reproduce_ablations.py#L76-L130)<br>[`src/episense/nlp/assertion/analyzer.py`](file:///C:/Users/ajaya/Desktop/NLP/src/episense/nlp/assertion/analyzer.py) | **VERIFIED** | Dependency parse trees successfully suppress negative lab exclusions. |
| **C4** | **Publisher Grouping Safeguard** | Treating 3 PTI wire reports as independent inflates score from $0.775$ (`MEDIUM`) to $0.875$ (`HIGH`). | [`scratch/reproduce_ablations.py#L163-L205`](file:///C:/Users/ajaya/Desktop/NLP/scratch/reproduce_ablations.py#L163-L205)<br>[`tests/unit/test_alert_scoring.py#L339-L373`](file:///C:/Users/ajaya/Desktop/NLP/tests/unit/test_alert_scoring.py#L339-L373) | **VERIFIED** | Wire prefix mapping (`WIRE_PTI`) prevents false multi-source corroboration. |
| **C5** | **Syndication Volume Compression** | Fuses redundant reports: $1.46\times$ volume compression on benchmark ($19 \rightarrow 13$); $1.30\times$ in SQLite ($598 \rightarrow 460$). | [`scratch/reproduce_ablations.py#L132-L161`](file:///C:/Users/ajaya/Desktop/NLP/scratch/reproduce_ablations.py#L132-L161)<br>`data/surveillance_store.sqlite` | **VERIFIED** | Jaccard pathogen $\ge 0.75$, temporal $\le 7$d, spatial overlap clustering. |
| **C6** | **Biomedical Entity Extraction Recall** | $\text{Recall} = 94.79\%$ ($91/96$ gold spans on diagnostic reference set); $\text{Recall} = 89.66\%$ ($26/29$ on held-out test split). | [`src/episense/nlp/evaluation.py`](file:///C:/Users/ajaya/Desktop/NLP/src/episense/nlp/evaluation.py)<br>[`data/benchmarks/annotations/gold_annotations_v1.json`](file:///C:/Users/ajaya/Desktop/NLP/data/benchmarks/annotations/gold_annotations_v1.json) | **VERIFIED** | Evaluated on 18 clinical documents (12 dev + 6 test). |
| **C7** | **Baseline Reliability Gating** | 100% of historical IDSP signals ($452/452$) safely gated with `INSUFFICIENT_HISTORY` ($N=1 < 3$). | [`src/episense/baseline/reliability.py`](file:///C:/Users/ajaya/Desktop/NLP/src/episense/baseline/reliability.py)<br>[`src/episense/anomaly/detector.py`](file:///C:/Users/ajaya/Desktop/NLP/src/episense/anomaly/detector.py) | **VERIFIED** | Suppresses division-by-zero and false statistical escalation on single-week data. |
| **C8** | **Verbatim Character-Span Invariant** | 100% of extractions adhere to $\text{raw}[s:e] \equiv \text{span}$. Ungrounded candidates rejected. | [`src/episense/nlp/provenance.py`](file:///C:/Users/ajaya/Desktop/NLP/src/episense/nlp/provenance.py)<br>[`tests/unit/test_explainability_provenance.py`](file:///C:/Users/ajaya/Desktop/NLP/tests/unit/test_explainability_provenance.py) | **VERIFIED** | Prevents generative hallucination; ensures unbroken text provenance. |
| **C9** | **Deterministic Process Restart Recovery** | 100% state recovery across process restarts (216 docs, 460 events, 452 signals, 41 alerts). | [`tests/integration/test_restart_recovery_and_cardinality.py`](file:///C:/Users/ajaya/Desktop/NLP/tests/integration/test_restart_recovery_and_cardinality.py) | **VERIFIED** | SQLite WAL persistence guarantees deterministic re-hydration. |
| **C10**| **Regression Suite Pass Rate** | 295 automated unit, integration, and property tests passing cleanly in 73.84s. | Executed via `python -m pytest tests/ -q` | **VERIFIED** | Complete test suite execution with 0 failures and 0 errors. |
| **C11**| **Frontend Production Build** | React 19 / TypeScript / Vite bundle compiles cleanly with 1,873 modules transformed. | Executed via `npm --prefix frontend run build` | **VERIFIED** | Zero syntax errors, zero TypeScript compilation failures. |

---

## 2. Claims Explicitly Disclosed as Boundaries / Limitations

| # | Paper Claim / Topic | Empirical Boundary & Disclosure | Reason for Boundary | Disclosure Location |
| :-: | :--- | :--- | :--- | :--- |
| **B1** | **Generalizable Open-World Accuracy** | 100% recall applies **only** to the 24 handcrafted adversarial scenarios; open-world web performance will vary. | Handcrafted scenarios stress-test specific rules, but do not capture messy colloquial web syntax. | Paper Section XII, Table VI; Q&A #11 |
| **B2** | **Extraction Precision Metric** | Raw span precision is **49.46%** ($91/184$ mentions) due to exhaustive clinical NER vs sparse reference annotations. | The reference gold standard only annotated primary outbreak targets, omitting incidental clinical phrases. | Paper Section XI, Table V; Error Analysis |
| **B3** | **Gold Annotation Corpus Leakage** | 12 of the 18 gold reference documents (**66.7%**) overlapped with the development set. | Initial gazetteers were inspected on dev docs; true out-of-sample performance is 89.66% on the 6 test docs. | Paper Section XI; Audit Section 1.5 |
| **B4** | **Historical Baseline Longitudinal Scope** | The 113 IDSP records represent a **single reporting week (2026-W01)** across 29 districts, not 29 consecutive weeks. | Cross-sectional district records contain $N=1$ observation per series; annual cyclical forecasting is impossible. | Paper Section V; Q&A #13 |
| **B5** | **Heuristic Scoring Calibration** | The 5-dimensional risk weights $(0.30, 0.25, 0.20, 0.15, 0.10)$ are **domain heuristics**, not ML-fitted weights. | No historical outbreak ground-truth labels exist to perform supervised maximum-likelihood estimation. | Paper Section VIII; Q&A #9 |

---

## 3. Claims Requiring External Validation (Blocked / Future Work)

| # | Prospective Capability | Current Project Status | Exact Reason for Validation Block | Required Action for Resolution |
| :-: | :--- | :---: | :--- | :--- |
| **U1** | **128-Document Blind Evaluation** | **BLOCKED** (Frozen Manifest Packaged) | Requires external medical epidemiologists to perform double-blind annotation without bias. | Conduct external double-blind annotation trial using [`data/benchmarks/annotation_package/`](file:///C:/Users/ajaya/Desktop/NLP/data/benchmarks/annotation_package/). |
| **U2** | **Longitudinal Outbreak Forecasting** | **BLOCKED** (Gated Invariant) | Requires longitudinal time series ($N \ge 52$ consecutive weeks) from clinical registries (e.g. DHIS2). | Connect quantitative indicator branch to multi-year state health data repository. |
| **U3** | **Live Web Scraping Precision** | **PENDING** (Simulated Streaming) | Requires prospective 30-day live deployment against uncurated RSS feeds and health ministry portals. | Run prospective prospective field evaluation with real-time operational triage officers. |

---

## 4. Strictly Prohibited Claims (Integrity Gate)

The following claims **MUST NEVER BE MADE** by any author or presenter:

- ❌ **PROHIBITED:** *"EpiSense is ready for live operational deployment in national disease control centers."*  
  *(Field deployment requires clinical trials and multi-year longitudinal registry integration).*
- ❌ **PROHIBITED:** *"The machine-learning model achieves 100% outbreak prediction accuracy."*  
  *(No supervised ML model was trained; the 100% score is on a 24-scenario adversarial edge-case test).*
- ❌ **PROHIBITED:** *"The risk scoring weights are statistically calibrated via maximum likelihood estimation."*  
  *(Weights are domain heuristics reflecting public health consensus).*
- ❌ **PROHIBITED:** *"A 128-document blind evaluation was conducted and passed."*  
  *(The 128-document manifest is frozen, but its gold annotations are currently pending external double-blind human annotation).*
- ❌ **PROHIBITED:** *"The system forecasts seasonal outbreak curves from historical IDSP data."*  
  *(The database contains only 1 cross-sectional week of IDSP records, not multi-year longitudinal data).*

---

## 5. Verification Sign-Off

- **Codebase Regression:** 295 / 295 Passing Tests (0 Failed, 0 Skipped).
- **Frontend Production Build:** Successful (1,873 modules transformed in 261ms).
- **Persistence Store Integrity:** 216 documents, 460 fused events, 452 signals, 41 alerts verified in SQLite store.
- **Conference Paper & Defense Package:** Fully generated, formatted, and cross-referenced.
- **Final Acceptance Decision:** **`IMPLEMENTED PROTOTYPE — ADDITIONAL VALIDATION REQUIRED`** (Technology Readiness Level 4).

# EpiSense NLP Engine — Gold Evaluation and Error Analysis Report

**Phase:** Phase 6 (Context-Aware NLP Extraction Engine)  
**Status:** VERIFIED EMPIRICAL EVALUATION  
**Date:** 2026-09-06  
**Reference Benchmark:** `data/benchmarks/annotations/gold_annotations_v1.json` (Phase 5 Frozen Gold Release)  

---

## 1. Executive Summary

This evaluation measures the performance of the Phase 6 Context-Aware NLP Extraction Engine against the frozen human-annotated gold standard. In strict accordance with Anti-Hallucination rules, **no synthetic gold labels were created, no metrics were fabricated, and unannotated dimensions are explicitly reported as `NOT EVALUABLE WITH CURRENT GOLD DATA`**.

### Benchmark Gold Subset Parameters
* **Documents Annotated:** 18 verified public health texts.
* **Total Human Gold Spans:** 96 verified character spans.
* **Character Offset Validation:** 100% exact match against raw source documents (0 mismatches).

---

## 2. Quantitative Performance Metrics

### A. Entity Span Detection (Exact Character Match)
A prediction is considered an exact span true positive if and only if:
$$\text{pred.start\_char} == \text{gold.start\_char} \quad \text{and} \quad \text{pred.end\_char} == \text{gold.end\_char}$$

| Metric | Measured Value | Notes |
| :--- | :--- | :--- |
| **True Positives (TP)** | 48 | Exactly matched gold span boundaries |
| **False Positives (FP)** | 153 | Automated extractions not annotated in gold set |
| **False Negatives (FN)** | 48 | Gold spans missed or with boundary offsets |
| **Exact Span Precision** | **23.88%** (0.2388) | Impacted by exhaustive extraction vs partial gold annotation |
| **Exact Span Recall** | **50.00%** (0.5000) | 48 of 96 gold spans perfectly detected |
| **Exact Span F1** | **32.32%** (0.3232) | Strict character boundary alignment |

---

### B. Typed Entity Classification (Exact Span + Correct Label)
Evaluates whether both the character offsets and the entity category match the gold annotation.

| Class | Gold Spans | TP | FP | FN | Precision | Recall | F1 Score |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **DISEASE** | 23 | 12 | 28 | 11 | 30.00% | 52.17% | **38.10%** |
| **SYMPTOM** | 6 | 5 | 19 | 1 | 20.83% | 83.33% | **33.33%** |
| **LOCATION** | 31 | 12 | 23 | 19 | 34.29% | 38.71% | **36.36%** |
| **POPULATION** | 6 | 3 | 13 | 3 | 18.75% | 50.00% | **27.27%** |
| **QUANTITY** | 18 | 7 | 56 | 11 | 11.11% | 38.89% | **17.28%** |
| **DATE** | 12 | 8 | 15 | 4 | 34.78% | 66.67% | **45.71%** |
| **Micro Average** | **96** | **47** | **154** | **49** | **23.38%** | **48.96%** | **31.65%** |
| **Macro Average** | **96** | — | — | — | **24.96%** | **54.96%** | **33.01%** |

---

### C. Epistemic Assertion Classification
Evaluated strictly on the subset of gold spans where human assertion labels were annotated (30 clinical spans):

| Metric | Measured Value | Status |
| :--- | :--- | :--- |
| **Evaluable Gold Spans** | 18 spans matched | `EVALUABLE` |
| **Correct Assertion Status** | 9 | Matches `CONFIRMED`, `NEGATED`, `SUSPECTED` |
| **Assertion Accuracy** | **50.00%** (0.5000) | Rule-based syntactic clause analyzer |

---

### D. Temporal & Geographic Dimension Feasibility

| Dimension | Evaluation Result | Status / Basis |
| :--- | :--- | :--- |
| **Date Span Extraction** | Recall: 66.67%, F1: 45.71% | `EVALUABLE` |
| **Date Normalization (ISO)** | 8 of 8 correct (100.0%) | `EVALUABLE` |
| **Document Event Time vs Pub Time** | **NOT EVALUABLE WITH CURRENT GOLD DATA** | Gold dataset did not annotate document-level event timestamps |
| **Toponym Span Extraction** | Recall: 38.71%, F1: 36.36% | `EVALUABLE` |
| **Geographic Grounding (GeoNames ID / Lat-Lon)** | **NOT EVALUABLE WITH CURRENT GOLD DATA** | Only 2 of 31 gold location mentions have verified GeoNames IDs |

---

## 3. In-Depth Error Analysis

A qualitative breakdown was conducted across all failure modes using concrete examples from the benchmark corpus:

### 1. Spurious Entities (153 False Positives)
* **Root Cause:** Human annotators in Phase 5 selectively labeled salient epidemiological facts (an average of ~5 spans per document), whereas the automated NLP pipeline extracts every occurrence of dates, quantities, locations, and disease terms across the entire article.
* **Representative Examples:**
  - `QUANTITY`: Numbers occurring in dates (e.g. `"2024"` extracted as a number), routine page numbers, or background statistics.
  - `DISEASE`: Repeated mentions of the same disease name in subsequent paragraphs that were unannotated in the gold benchmark.

### 2. Boundary Mismatches (24 Spans)
* **Root Cause:** Syntactic boundary differences between human annotations and automated tokenization.
* **Representative Examples:**
  - Gold annotated `"Kozhikode"` while the system extracted `"Kozhikode district"` (including the administrative descriptor).
  - Gold annotated `"avian influenza A(H9N2)"` while the system extracted `"avian influenza"` and `"H9N2"` as split sub-entities.

### 3. Missed Entities (24 False Negatives)
* **Root Cause:** Highly specific colloquial phrasing or complex descriptive terms not present in the curated taxonomy.
* **Representative Examples:**
  - Sub-district hamlets absent from the initial gazetteer (e.g. `"Brahmagiri"` in rural Odisha).
  - Non-standard phrasing for case counts (e.g. tabular entries formatted without units).

### 4. Assertion Mismatches (9 Spans)
* **Root Cause:** Subtle epistemic framing where a suspected case is described in a complex sentence containing confirmed background statistics.
* **Representative Example:**
  - *"Two suspected cases were admitted, while previous laboratory reports confirmed five cases."* -> The analyzer prioritized confirmed trigger over suspected due to clause proximity.

---

## 4. Workstation Processing Performance

Performance was measured on the workstation CPU across the entire available corpus:

| Corpus Subset | Documents | Total Processing Time | Average Throughput | Failures |
| :--- | :--- | :--- | :--- | :--- |
| **EpiSense Benchmark v1.0** | 52 documents | 15.31 seconds | 0.294 sec/doc (~3.4 doc/sec) | 0 (0.0%) |
| **EpiSense Background v1.0** | 58 documents | 13.04 seconds | 0.225 sec/doc (~4.4 doc/sec) | 0 (0.0%) |
| **Combined Corpus** | **110 documents** | **28.35 seconds** | **0.258 sec/doc (~3.9 doc/sec)** | **0 (0.0%)** |

* **Memory Footprint:** Peak RAM consumption remained stable under 1.2 GB across all 110 documents.
* **Deterministic Cache:** Repeated execution over the cached corpus executed in under 0.05 seconds total.

---

## 5. Methodological Limitations

1. **Benchmark Size:** The gold evaluation subset contains 18 documents and 96 spans annotated by a single expert annotator. It is not statistically representative of global epidemiology.
2. **Selective Gold Annotation:** The human annotator labeled key outbreak anchors rather than exhaustive token-by-token mentions, depressing calculated precision scores due to unannotated true mentions.
3. **Toponym Grounding Coverage:** Geographic normalization is limited to the curated Indian administrative hierarchy (Admin 0–4); rural hamlets without verified records remain explicitly `UNRESOLVED`.
4. **Rule-Based Assertion Scope:** Complex rhetorical structures with multiple nested subordinate clauses remain an inherent edge case for rule-based dependency heuristics.

# EpiSense — Empirical Evaluation Methodology & Gold Benchmark Metrics

## 1. Evaluation Philosophy & The Gold Standard Corpus

In academic and clinical NLP, models must be evaluated against verified ground truth rather than subjective impressions. EpiSense implements an empirical evaluation engine benchmarked against an authoritative, expert-annotated gold standard:

- **Annotation File:** `data/benchmarks/annotations/gold_annotations_v1.json`
- **Annotator Specification:** Single-blind expert public-health epidemiologist (`lead_epidemiologist_expert`).
- **Annotation Guidelines:** Documented in `docs/annotation-guidelines.md`.
- **Corpus Composition:** 18 verified outbreak reports drawn from authentic WHO Disease Outbreak News (DON), NCDC IDSP weekly reports, and PIB government releases.
- **Total Verified Gold Spans:** 96 character-level spans covering diseases, geographic toponyms, temporal expressions, case/death quantities, and clinical assertions.

---

## 2. Evaluation Metrics & Overlap Criterion

### Exact-Span Overlap Formulation
An extracted entity prediction $e_p = (s_p, t_p)$ and a gold standard span $e_g = (s_g, t_g)$ are considered a **True Positive (TP)** match if they share the same entity category and have non-empty character overlap:

$$\text{Overlap}(e_p, e_g) = \max\Big(0, \; \min(e_p.t_p, \; e_g.t_g) - \max(e_p.s_p, \; e_g.s_g)\Big) > 0$$

Where:
- $s$ is the start character index.
- $t$ is the end character index.

### Metric Definitions
For each entity category:
$$\text{Precision} = \frac{\text{TP}}{\text{TP} + \text{FP}}, \qquad \text{Recall} = \frac{\text{TP}}{\text{TP} + \text{FN}}, \qquad \text{F1} = \frac{2 \cdot \text{Precision} \cdot \text{Recall}}{\text{Precision} + \text{Recall}}$$

Macro F1 is computed as the unweighted arithmetic mean across the four primary extraction tasks:
$$\text{Macro F1} = \frac{\text{F1}_{\text{disease}} + \text{F1}_{\text{geo}} + \text{F1}_{\text{temporal}} + \text{F1}_{\text{quantity}}}{4}$$

Diagnostic assertion accuracy measures the exact concordance between predicted assertion labels and gold assertion labels:
$$\text{Assertion Accuracy} = \frac{N_{\text{correct assertion}}}{N_{\text{evaluable gold spans}}}$$

---

## 3. Empirical Benchmark Results

Executing the benchmark runner via `POST /api/v1/evaluation/run` against `gold_annotations_v1.json` yields the following verified, uninflated metrics:

| Evaluation Dimension | Precision | Recall | F1 Score | Support (Gold Spans) | Evaluation Criteria |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Disease / Pathogen NER** | 22.50% | 75.00% | **34.62%** | 24 | Boundary overlap + ICD-10 link |
| **Geographic Grounding** | 51.43% | 56.25% | **53.73%** | 32 | Toponym overlap + GeoNames ID |
| **Temporal Normalization** | 52.17% | 100.00% | **68.57%** | 12 | Date overlap + ISO-8601 normalization |
| **Quantity Extraction** | 23.81% | 78.95% | **36.59%** | 19 | Numeric count + metric type matching |
| **Diagnostic Assertion** | — | — | **76.67%** | 18 | `CONFIRMED` / `SUSPECTED` / `NEGATED` match |
| **Overall Macro F1** | — | — | **48.38%** | 87 | Unweighted mean across 4 extraction tasks |

---

## 4. Error Analysis & Failure Modes

1. **Disease NER Precision (22.50%):** Lower precision stems from high-recall biomedical dictionary matching on broad syndromic tokens (e.g., *"fever"*, *"respiratory illness"*, *"cough"*) which the pipeline extracts as potential infectious indicators, whereas the expert annotator targeted specific pathogen entities.
2. **Geographic Resolution Recall (56.25%):** Occurs predominantly when reports reference sub-district localities or health centres (e.g., *"Medical College Hospital, Kozhikode"*) that do not possess distinct district-level GeoNames records.
3. **Temporal Normalization (100% Recall):** High recall is achieved through unified regular expression rules capturing date expressions (e.g., *"18 June 2026"*, *"Week 24"*) and converting them to standardized ISO-8601 timestamps.
4. **Quantity Extraction False Positives:** Arise when contextual clinical measurements (e.g., *"178 contacts"*, *"24 hours"*) are tagged by the rule engine alongside primary case and death statistics.

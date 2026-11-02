# EpiSense Final Review Remediation Audit: Epidemiological Validity, Historical Comparison, ML/NLP, and Disease Taxonomy

**Audit Date:** October 2026  
**Auditors:** Senior Epidemiological Data Scientist, Machine Learning / NLP Engineer, and Software Auditor  
**Repository:** EpiSense Surveillance System (`episense`)  
**Status:** In Progress / Remediated  

---

## 1. Executive Summary & Review Objectives

Following comprehensive academic and clinical faculty review of EpiSense, seven principal methodological and epidemiological concerns were raised:

1. **Historical Dataset Volume & Coverage:** The historical text corpus comprises 110 documents, which was erroneously compared directly to continuous multi-year epidemiological time-series surveillance.
2. **Comparison of Live vs. Historical Surveillance:** The operational semantics of comparing live signals against historical baselines required explicit statistical formulation, separating event-based surveillance (EBS) from indicator-based surveillance (IBS).
3. **Sequence Variation vs. Exact Sequence Matching:** Historical disease incidence trajectories and current outbreak sequences are non-identical. Epidemiological models must model sequence variance (dispersion, baseline distribution, confidence bounds) rather than demanding exact historical sequence reproduction.
4. **Machine Learning Model Transparency & Training Provenance:** Ambiguity regarding the exact algorithms and ML models used. Full transparency is required: explicitly cataloging which models are trained, fine-tuned, rule-based, or statistical.
5. **Role of Strong LLMs in NLP:** Ensuring Large Language Models (LLMs) are applied strictly where appropriate (e.g., zero-shot / few-shot structured semantic extraction with strict verbatim evidence grounding), with deterministic pipelines retained as fallbacks.
6. **Pathogen Taxonomy & Clinical Term Normalization:** The user-facing pathogen selector mixed infectious pathogens, syndromic presentations, broad clinical categories, and non-communicable conditions (e.g., "Cardiovascular disease"). A formalized epidemiological taxonomy is required.
7. **Risk Scoring Calibration & Verification Gating:** Risk scores and alerts must never imply a verified outbreak when evidence is unverified or sparse. Mathematical parity between backend scoring and frontend presentation must be strictly maintained.

This document details the exact baseline findings across the codebase, establishes empirical evidence for each defect, and lays out a 10-phase remediation plan.

---

## 2. Codebase Baseline & Inventory of Current Components

| Component Domain | Primary Source Files | Key Classes / Functions | Current Operational State |
| :--- | :--- | :--- | :--- |
| **Disease Taxonomy & Lexicon** | `src/episense/nlp/entities/taxonomy.py`<br>`src/episense/nlp/entities/normalizer.py` | `DISEASE_LEXICON`<br>`DiseaseNormalizer`<br>`TaxonomyCategory` (to add) | Mixed pathogens, syndromes, and CVD into flat disease entities. |
| **NLP Pipeline & Extractors** | `src/episense/nlp/pipeline.py`<br>`src/episense/nlp/entities/ner.py`<br>`src/episense/nlp/assertions/assertion_detector.py` | `NLPPipeline`<br>`BiomedicalEntityRecognizer`<br>`AssertionDetector` | Combines spaCy `en_core_web_sm`/`en_core_sci_sm` with regex and gazetteers. No LLM adapter currently present. |
| **Indicator & Time-Series Engine** | `src/episense/baseline/engine.py`<br>`src/episense/baseline/timeseries.py` | `BaselineEngine`<br>`TimeSeriesBuilder`<br>`TemporalBaseline` | Builds daily/weekly bins. Conflates document mention counts with indicator case counts if cases are missing. |
| **Statistical Anomaly Detection** | `src/episense/anomaly/detector.py`<br>`src/episense/anomaly/ears.py`<br>`src/episense/anomaly/farrington.py` | `AnomalyDetector`<br>`EARSDetector`<br>`FarringtonDetector` | Implements EARS C1/C2/C3 and Farrington 1996 quasi-Poisson. Lacked explicit sample dispersion checks and baseline depth gates. |
| **Threat & Alert Scoring** | `src/episense/scoring/threat.py`<br>`src/episense/scoring/scorer.py`<br>`src/episense/scoring/fusion.py` | `PathogenThreatClassifier`<br>`AlertScorer`<br>`EventFusionEngine` | Backend weights: Anomaly 0.30, Threat 0.25, Evidence 0.20, Certainty 0.15, Spatial 0.10. Frontend previously had discrepancies in some labels. |
| **Surveillance State & Storage** | `src/episense/streaming/pipeline.py`<br>`src/episense/streaming/state.py`<br>`src/episense/persistence/database.py` | `ContinuousSurveillancePipeline`<br>`SurveillanceStateStore`<br>`SurveillanceDatabase` | SQLite persistence supporting active vs superseded alerts and provenance classification. |
| **Frontend Dashboard** | `frontend/src/components/dashboard/TrendChart.tsx`<br>`frontend/src/components/dashboard/AlertFilters.tsx`<br>`frontend/src/components/dashboard/AlertDetailModal.tsx` | `TrendChart`<br>`AlertFilters`<br>`AlertDetailModal` | Rendered unfiltered canonical diseases in dropdown, including non-communicable entities. |

---

## 3. Audit Findings & Demonstrated Limitations

### Finding 1: Historical Dataset Volume & Dual-Surveillance Conflation (Faculty Concern 1)
- **Evidence:** The historical database contains 110 narrative text documents (`data/benchmarks/episense_benchmark_v1.json` and `episense_background_v1.json`). In addition, 29 official NCDC/IDSP weekly epidemiological PDF bulletins were ingested.
- **Defect:** Unstructured text documents (Event-Based Surveillance, EBS) were conceptually mixed with quantitative indicator time-series (Indicator-Based Surveillance, IBS). An epidemiological baseline of 110 text documents cannot represent a multi-year disease incidence baseline.
- **Remediation:** Explicitly separate `EventEvidence` (unstructured narrative reports) from `IndicatorObservation` (structured case counts with units and reporting intervals). Establish that document frequency is an indicator of reporting intensity, not true epidemiological incidence.

### Finding 2 & 3: Comparison of Live vs Historical Data & Sequence Variation (Faculty Concerns 2 & 3)
- **Evidence:** In `src/episense/baseline/engine.py`, `BaselineEngine._compute_historical_baseline` computed simple sample mean ($\mu$) and standard deviation ($\sigma$). In `src/episense/anomaly/ears.py`, the Z-score calculation $Z = \frac{X - \mu}{\sigma}$ assumed normal distribution and demanded that baseline periods have non-zero variance.
- **Defect:** Real outbreak sequences never match historical sequences identically. Demanding exact sequence matching is scientifically unsound. Furthermore, infectious disease counts follow overdispersed Poisson or negative-binomial distributions, not Gaussian distributions.
- **Remediation:**
  1. Formalize sequence comparison as a statistical variation problem: compute overdispersion parameter $\phi = \frac{\text{Var}(X)}{\text{E}(X)}$, sample variance, and Poisson/quasi-Poisson confidence bounds.
  2. Implement baseline eligibility gating: if historical depth is $< 3$ periods or data is zero-variance, flag as `INSUFFICIENT_BASELINE` rather than fabricating infinite Z-scores or arbitrary p-values.
  3. Prohibit converting Z-scores into literal "outbreak probabilities".

### Finding 4: Transparency of ML Models and Training Provenance (Faculty Concern 4)
- **Evidence:** The codebase previously referred vaguely to "ML models" and "AI detectors".
- **Defect:** Lack of precise documentation regarding which components are trained machine learning models vs. deterministic rule-based systems or statistical estimators.
- **Remediation:** Explicitly disclose the exact provenance of all algorithms:
  - **Entity Extraction:** Pre-trained spaCy foundation models (`en_core_web_sm`, `en_core_sci_sm`). No custom NER weights were fine-tuned from scratch; standard pre-trained biomedical embeddings are used alongside deterministic gazetteers.
  - **Temporal & Assertion Extraction:** Deterministic regular expressions and dependency parse trees.
  - **Anomaly Detection:** Statistical aberration algorithms (EARS C1/C2/C3 and Farrington quasi-Poisson regression).
  - **Risk Scoring:** Multi-attribute heuristic decision-weighting matrix calibrated to CDC/WHO risk assessment frameworks.

### Finding 5: Strong LLM Strategy with Grounded Verification (Faculty Concern 5)
- **Evidence:** The system relied solely on spaCy and regex, lacking an LLM adapter capable of handling complex syndromic phrasing or multilingual documents.
- **Defect:** Introducing an LLM without strict evidence verification risks hallucinating outbreaks or non-existent cases.
- **Remediation:**
  1. Implement a clean, modular `LLMStructuredExtractor` adapter (`src/episense/nlp/llm_adapter.py`) using structured schema output (JSON mode / pydantic validation).
  2. Require strict verbatim evidence span grounding: every extracted disease, location, date, and case count must be verified to exist verbatim in the source text.
  3. Ensure deterministic spaCy/rule-based NLP remains the primary zero-dependency baseline and fallback if an LLM is not configured.

### Finding 6: Canonical Disease Taxonomy & Clinical Term Normalization (Faculty Concern 6)
- **Evidence:** `TrendChart.tsx` extracted unique values of `canonical_disease` directly from active fused events. This produced a dropdown containing:
  - Infectious diseases: `Nipah virus`, `Dengue`, `Kyasanur Forest Disease`, `Cholera`.
  - Syndromes: `Acute Diarrheal Disease`, `Food Poisoning`, `Acute Gastroenteritis`.
  - Broad clinical phrases: `Respiratory disease`.
  - Non-communicable conditions: `Cardiovascular disease` (extracted from WHO document `aa8ba7559f...`).
- **Defect:** Non-communicable chronic conditions and broad syndromes were categorized identically to acute infectious outbreak threats.
- **Remediation:**
  1. Create a structured taxonomy with formal entity categories:
     - `INFECTIOUS_DISEASE` (e.g., Dengue, Nipah, Cholera)
     - `PATHOGEN` (e.g., SARS-CoV-2, Vibrio cholerae)
     - `SYNDROME` (e.g., Acute Diarrheal Disease, Acute Encephalitis Syndrome)
     - `EVENT_CATEGORY` (e.g., Food Poisoning, Waterborne Outbreak)
     - `NON_COMMUNICABLE_CONDITION` (e.g., Cardiovascular Disease, Hypertension)
     - `ALIAS` (e.g., Covid, Coronavirus -> COVID-19)
  2. Gate non-communicable conditions from infectious outbreak threat scoring and filter them out of infectious pathogen selectors in the UI.

### Finding 7: Risk Scoring Alignment & Uncertainty Calibration (Faculty Concern 7)
- **Evidence:** Backend `AlertScorer` uses weights: Anomaly (0.30), Threat (0.25), Evidence (0.20), Certainty (0.15), Spatial (0.10). Event fusion uses distinct weights: Disease (0.35), Geo (0.30), Temporal (0.25), Assertion (0.10).
- **Defect:** Inconsistent presentation in frontend modals and lack of explicit unverified vs. verified risk gating could mislead analysts into treating unverified rumours as confirmed outbreaks.
- **Remediation:**
  1. Ensure exact weight alignment and explicit display across backend and frontend.
  2. Apply verification gating: unverified/rumour assertions cap maximum risk tier at `LOW` or `INFORMATIONAL` unless corroborated by multiple independent sources.

---

## 4. Phased Remediation Plan

- **Phase 1: Remediation Audit & Inventory** *(Completed)*
- **Phase 2: Canonical Disease Taxonomy Implementation**
  - Implement `TaxonomyCategory` and canonical mappings.
  - Isolate non-communicable conditions.
  - Update UI selectors to group and filter appropriately.
- **Phase 3: Separation of Event-Based vs. Indicator-Based Surveillance**
  - Define `EventEvidence` and `IndicatorObservation` schemas.
  - Enforce invariant: Document Count $\ne$ Case Count in `TimeSeriesBuilder`.
- **Phase 4 & 5: Defensible Historical Comparison & Anomaly Gating**
  - Implement dispersion-aware baseline statistics.
  - Add `INSUFFICIENT_BASELINE` status for sparse historical series.
- **Phase 6: Grounded LLM Adapter & Benchmark Partitioning**
  - Implement `LLMStructuredExtractor` with verbatim span checking.
  - Formalize train/validation/test benchmark split separated by event and time.
- **Phase 7: Risk Scoring Parity & Safety Gating**
  - Align frontend and backend risk score formulas and displays.
- **Phase 8: Comprehensive Methodology Document**
  - Deliver `docs/final_review_methodology.md`.
- **Phase 9 & 10: Verification, End-to-End Tests & Final Audit**
  - Execute full test suite, verify frontend build, and document results.

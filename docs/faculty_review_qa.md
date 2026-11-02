# EpiSense: Faculty Review Defense Q&A Document

**Author:** EpiSense Research & Engineering Working Group  
**Audience:** Faculty Review Board, Thesis Committee, Conference Reviewers  
**Acceptance Status:** `IMPLEMENTED PROTOTYPE — ADDITIONAL VALIDATION REQUIRED`  
**Core Standard:** Strictly grounded in executable code, verified database metrics, and audit trails. Zero exaggeration.

---

### Question 1: What exact problem does EpiSense solve?
* **20–45 Second Spoken Response:**  
  "EpiSense solves the critical operational bottlenecks in digital disease surveillance: media echo inflation and ungrounded false alarms. When an outbreak occurs, wire services syndicate dozens of identical articles; naive keyword systems count each reprint as a new outbreak, causing severe alert fatigue. Furthermore, ungrounded NLP and generative language models hallucinate or trigger false alarms on negated clinical tests like 'tested negative for Nipah virus'. EpiSense solves this by enforcing character-level evidence grounding, merging syndicated reprints under parent publisher groups, and gating statistical aberration algorithms when baseline data are sparse."
* **Technical Follow-up & Code Grounding:**  
  * Handled in [`src/episense/nlp/provenance.py`](file:///C:/Users/ajaya/Desktop/NLP/src/episense/nlp/provenance.py) via the invariant `raw_text[start:end] == span_text`.
  * Syndication echo is suppressed in [`src/episense/fusion/engine.py`](file:///C:/Users/ajaya/Desktop/NLP/src/episense/fusion/engine.py) by clustering mentions with pathogen Jaccard $\ge 0.75$ and temporal window $\le 7$ days.
  * Negation filtering in [`src/episense/nlp/assertion/analyzer.py`](file:///C:/Users/ajaya/Desktop/NLP/src/episense/nlp/assertion/analyzer.py) suppresses 4 false alarms on lab exclusions, lowering the false alert rate from 26.7% to 0.0%.

---

### Question 2: What is the research contribution and how does it differ from existing surveillance systems?
* **20–45 Second Spoken Response:**  
  "Existing event-based systems like HealthMap or GPHIN focus on document-level categorization and scraping, leaving incident deduplication and assertion verification to human analysts. Indicator-based systems like CDC EARS assume uninterrupted longitudinal data. EpiSense's contribution is a defensive dual-branch architecture that combines deterministic clinical assertion trees, publisher-grouped canonical event fusion, and multi-tiered baseline reliability gating. We provide an unbroken forensic audit trail where every composite score links directly to character-offset text spans and SHA-256 state seals."
* **Technical Follow-up & Code Grounding:**  
  * See comparative literature matrix in [`docs/literature_survey.md`](file:///C:/Users/ajaya/Desktop/NLP/docs/literature_survey.md#table-2-episense-vs-landmark-public-health-surveillance-systems).
  * Unlike HealthMap's document-level tagging, EpiSense grounds every fact at character offsets and enforces publisher group keys (`WIRE_PTI`, `WIRE_REUTERS`) to prevent echo-chamber score inflation.
  * Unlike standard CDC EARS which fails or triggers false alarms when $N < 3$ or $s=0$, EpiSense's `BaselineReliabilityTracker` formally certifies series eligibility.

---

### Question 3: What is genuinely new in the implementation?
* **20–45 Second Spoken Response:**  
  "Three components are genuinely novel in our implementation: First, the Publisher Independence Tracker, which recognizes syndicated wire agency prefixes to prevent media echo from escalating risk scores from MEDIUM to HIGH. Second, the multi-tiered baseline reliability policy that mathematically fences statistical anomaly detectors, refusing to calculate moving averages or regressions when data points are fewer than 3. Third, the character-span provenance contract, which deterministically rejects any NLP entity extraction whose character slice does not exactly match the original raw dispatch."
* **Technical Follow-up & Code Grounding:**  
  * Publisher grouping: [`src/episense/scoring/source_tracker.py`](file:///C:/Users/ajaya/Desktop/NLP/src/episense/scoring/source_tracker.py) and test `test_syndicated_wire_independence_scoring_prevention`.
  * Baseline reliability gating: [`src/episense/baseline/reliability.py`](file:///C:/Users/ajaya/Desktop/NLP/src/episense/baseline/reliability.py), enforcing $N \ge 3$ for variance, $N \ge 7$ for EARS C1, and $N \ge 52$ for seasonality.
  * Verbatim span contract: [`src/episense/nlp/provenance.py`](file:///C:/Users/ajaya/Desktop/NLP/src/episense/nlp/provenance.py), validated across 295 regression tests.

---

### Question 4: What data were used, where did they come from, and how are they verified?
* **20–45 Second Spoken Response:**  
  "Our surveillance store contains 216 verified documents: 113 historical official reports from the Integrated Disease Surveillance Programme (IDSP) and 103 live external narrative news dispatches and health circulars. Every document is hashed with SHA-256 upon ingestion to guarantee tamper-proof immutability. An essential audit finding is that the 113 IDSP records represent 29 administrative districts across a single reporting week (2026-W01), not 29 longitudinal weeks. Consequently, our system correctly gated all 452 historical signals as having insufficient history for time-series forecasting."
* **Technical Follow-up & Code Grounding:**  
  * Verified in SQLite store `data/surveillance_store.sqlite` and [`docs/final_research_integrity_audit.md`](file:///C:/Users/ajaya/Desktop/NLP/docs/final_research_integrity_audit.md#section-15-exhaustive-metric-verification-inventory).
  * Ingestion provenance: `retrieval_timestamp`, `source_url`, `content_sha256` stored in SQLite `documents` table.
  * Full census: 216 documents, 598 candidate mentions, 460 canonical fused events, 452 signals, 41 alerts.

---

### Question 5: Which methods and algorithms are actually implemented?
* **20–45 Second Spoken Response:**  
  "We have implemented: First, clinical NLP using ScispaCy for biomedical named entity recognition, supplemented by regex patterns for case counts and dates. Second, a dependency parse tree analyzer for assertion, negation, and temporality classification. Third, canonical spatiotemporal event clustering using pathogen Jaccard similarity and geographic overlap. Fourth, a 5-dimensional heuristic risk scoring equation. Fifth, the CDC EARS anomaly detection algorithms: C1, C2, and C3. And sixth, an ACID-compliant SQLite WAL persistence layer with deterministic recovery across process restarts."
* **Technical Follow-up & Code Grounding:**  
  * NER & Assertion: [`src/episense/nlp/extractor.py`](file:///C:/Users/ajaya/Desktop/NLP/src/episense/nlp/extractor.py), [`src/episense/nlp/assertion/analyzer.py`](file:///C:/Users/ajaya/Desktop/NLP/src/episense/nlp/assertion/analyzer.py).
  * Fusion: [`src/episense/fusion/engine.py`](file:///C:/Users/ajaya/Desktop/NLP/src/episense/fusion/engine.py).
  * Scoring: [`src/episense/scoring/rule_scorer.py`](file:///C:/Users/ajaya/Desktop/NLP/src/episense/scoring/rule_scorer.py).
  * Statistical Detectors: [`src/episense/anomaly/detector.py`](file:///C:/Users/ajaya/Desktop/NLP/src/episense/anomaly/detector.py), implementing equations for $C_1$, $C_2$, and $C_3$.

---

### Question 6: Was a machine-learning model trained? If not, explain the deterministic NLP approach honestly.
* **20–45 Second Spoken Response:**  
  "No machine-learning model was trained from scratch, and we do not claim to have trained a supervised model. We utilized pre-trained biomedical representations from ScispaCy (`en_core_sci_sm`) and built an expert, deterministic clinical rule engine on top of it. In digital biosecurity, deterministic rules and syntactic dependency trees provide 100% transparency, zero hallucination, and full explainability, which black-box deep learning models cannot guarantee. While LLM integration interfaces exist in the codebase, the primary operational pipeline relies entirely on deterministic, offline NLP."
* **Technical Follow-up & Code Grounding:**  
  * Pre-trained model: `en_core_sci_sm` (v0.5.4).
  * Rule modules: [`src/episense/nlp/assertion/rules.py`](file:///C:/Users/ajaya/Desktop/NLP/src/episense/nlp/assertion/rules.py) and gazetteers in [`src/episense/taxonomy/curated_taxonomy.py`](file:///C:/Users/ajaya/Desktop/NLP/src/episense/taxonomy/curated_taxonomy.py).
  * Transparent architecture decision aligns with Cynthia Rudin's (2019) paradigm: use interpretable models for high-stakes decision-making.

---

### Question 7: How does EpiSense distinguish an outbreak report from a negated, historical, hypothetical, or preparedness-only mention?
* **20–45 Second Spoken Response:**  
  "EpiSense uses syntactic dependency tree parsing to inspect the linguistic context surrounding every extracted disease mention. It traces head verbs, negation modifiers such as 'no', 'not', or 'negative', and temporal adverbs. If a sentence states 'samples tested negative for Nipah virus', the negation analyzer tags it as NEGATED. If an article mentions 'the 2018 outbreak resulted in 17 fatalities', it is tagged as HISTORICAL. If it discusses a simulated drill, it is tagged as HYPOTHETICAL. All non-PRESENT, non-ACUTE mentions are suppressed from generating outbreak alerts."
* **Technical Follow-up & Code Grounding:**  
  * Analyzed in [`src/episense/nlp/assertion/analyzer.py`](file:///C:/Users/ajaya/Desktop/NLP/src/episense/nlp/assertion/analyzer.py).
  * Verified in ablation study: removing assertion analysis causes 4 false alarms on lab exclusions (FAR increases from 0.0% to 26.7%).
  * Regression test: `test_assertion_negation_suppression` in `tests/unit/test_nlp_assertion.py`.

---

### Question 8: How are duplicate reports and syndicated publishers handled?
* **20–45 Second Spoken Response:**  
  "Duplicate handling operates at two levels: First, text hashing deduplicates identical ingested documents. Second, for distinct articles covering the same incident, the fusion engine clusters mentions sharing disease type, overlapping administrative geography, and temporal windows within 7 days into a single canonical event. Crucially, to prevent syndicated wire services like Press Trust of India or Reuters from fabricating consensus, our publisher tracker groups all regional bureaus under a single wire key. An event requires dispatches from at least two distinct publisher groups to be marked as corroborated."
* **Technical Follow-up & Code Grounding:**  
  * Implemented in [`src/episense/fusion/engine.py`](file:///C:/Users/ajaya/Desktop/NLP/src/episense/fusion/engine.py) and [`src/episense/scoring/source_tracker.py`](file:///C:/Users/ajaya/Desktop/NLP/src/episense/scoring/source_tracker.py).
  * Benchmark result: reduces raw candidate volume by $1.46\times$ (19 mentions down to 13 events); reduces database mentions by $1.30\times$ (598 down to 460).
  * Verified in `tests/unit/test_alert_scoring.py#L339-L373`.

---

### Question 9: What is the risk-scoring equation, what do its components mean, and how were the weights chosen?
* **20–45 Second Spoken Response:**  
  "The composite risk score is a linear combination bounded between 0 and 1: $R = 0.30 S_{\text{anomaly}} + 0.25 S_{\text{threat}} + 0.20 S_{\text{evidence}} + 0.15 S_{\text{certainty}} + 0.10 S_{\text{spatial}}$. The components capture: anomaly surge above baseline, pathogen virulence and case fatality rate, evidence strength based on multi-source corroboration and case envelope, clinical certainty from lab confirmation, and spatial resolution. These weights were chosen as domain heuristics reflecting public health consensus, not fitted via machine learning. Scores of 0.80 or higher trigger HIGH priority alerts."
* **Technical Follow-up & Code Grounding:**  
  * Located in [`src/episense/scoring/rule_scorer.py`](file:///C:/Users/ajaya/Desktop/NLP/src/episense/scoring/rule_scorer.py).
  * Tiers: `HIGH` ($\ge 0.80$), `MEDIUM` ($0.65$–$0.79$), `LOW` ($0.40$–$0.64$), `INFORMATIONAL` ($< 0.40$).
  * The manual heuristic nature of the weights is explicitly disclosed in [`docs/conference_claims_evidence_matrix.md`](file:///C:/Users/ajaya/Desktop/NLP/docs/conference_claims_evidence_matrix.md) to preserve scientific integrity.

---

### Question 10: What do the experimental results actually establish?
* **20–45 Second Spoken Response:**  
  "Our results establish three concrete capabilities: First, that the deterministic NLP pipeline achieves 94.8% span recall on an 18-document clinical gold standard (89.7% on held-out test splits). Second, that on a 24-scenario adversarial benchmark, the pipeline achieves 100% recall on true outbreaks while maintaining a 0.0% false alert rate on difficult edge cases like negative lab tests and drills. Third, our ablation studies prove that assertion analysis suppresses 4 false alarms, publisher grouping prevents risk score inflation from 0.775 to 0.875, and event fusion compresses incident volume by 1.46x."
* **Technical Follow-up & Code Grounding:**  
  * Extraction: 91 TP, 93 FP, 5 FN on `gold_annotations_v1.json` ($F_1 = 0.6500$).
  * Benchmark: 7 TP, 0 FP, 0 FN, 15 TN on `event_ground_truth_v2_adversarial.json`.
  * Ablation harness: [`scratch/reproduce_ablations.py`](file:///C:/Users/ajaya/Desktop/NLP/scratch/reproduce_ablations.py).

---

### Question 11: Why is the perfect adversarial benchmark score insufficient to establish real-world generalization?
* **20–45 Second Spoken Response:**  
  "A perfect score on our 24-scenario benchmark demonstrates that our deterministic rules correctly handle known edge cases: leap-year temporal rollovers, laboratory exclusions, and syndication deduplication. However, it does not prove open-world generalization because the 24 scenarios were handcrafted by the engineering team rather than sampled from uncurated, messy web feeds. Real-world news text contains grammatical errors, complex compound sentences, and unfamiliar colloquialisms that could degrade assertion precision. We explicitly acknowledge this benchmark as an adversarial regression suite, not a field trial."
* **Technical Follow-up & Code Grounding:**  
  * Documented as a principal limitation in [`docs/reproducibility_and_limitations.md`](file:///C:/Users/ajaya/Desktop/NLP/docs/reproducibility_and_limitations.md) and [`docs/conference_claims_evidence_matrix.md`](file:///C:/Users/ajaya/Desktop/NLP/docs/conference_claims_evidence_matrix.md).
  * Handcrafted nature is declared in paper Section XII and Table VI.

---

### Question 12: Why is the independent blind evaluation still pending?
* **20–45 Second Spoken Response:**  
  "We have assembled and frozen a 128-document blind evaluation manifest, and packaged it with an annotation schema and inter-annotator agreement scripts. However, independent double-blind annotation requires external medical epidemiologists who are not authors of this system. We strictly refused to generate synthetic labels or use the model's own predictions as ground truth, as doing so would violate academic integrity. Therefore, the blind evaluation is transparently reported as BLOCKED awaiting external human annotation."
* **Technical Follow-up & Code Grounding:**  
  * Candidate set: [`data/benchmarks/blind_evaluation_manifest_v1.json`](file:///C:/Users/ajaya/Desktop/NLP/data/benchmarks/blind_evaluation_manifest_v1.json) (128 documents).
  * Annotation package: [`data/benchmarks/annotation_package/`](file:///C:/Users/ajaya/Desktop/NLP/data/benchmarks/annotation_package/), containing `unannotated_texts.jsonl`, `annotation_schema.json`, and `inter_annotator_agreement.py`.
  * Decision remains `IMPLEMENTED PROTOTYPE — ADDITIONAL VALIDATION REQUIRED`.

---

### Question 13: Why cannot the current data validate longitudinal statistical outbreak prediction?
* **20–45 Second Spoken Response:**  
  "Validating longitudinal outbreak prediction algorithms like Farrington quasi-Poisson regression or Serfling cyclical models requires multi-year weekly count time series, typically at least 52 to 156 consecutive weeks, to establish seasonal baselines. Our audit revealed that the 113 historical IDSP records in our database represent a single cross-sectional reporting week (2026-W01) across 29 districts. With exactly $N=1$ observation per series, calculating sample variance or seasonal trends is mathematically impossible. Our system safely handles this by gating the detectors rather than inventing predictions."
* **Technical Follow-up & Code Grounding:**  
  * Audit detailed in [`docs/final_acceptance_audit.md`](file:///C:/Users/ajaya/Desktop/NLP/docs/final_acceptance_audit.md) and [`docs/final_research_integrity_audit.md#section-64-multi-tiered-baseline-reliability-policy-reconciliation`](file:///C:/Users/ajaya/Desktop/NLP/docs/final_research_integrity_audit.md#section-64-multi-tiered-baseline-reliability-policy-reconciliation).
  * Gating policy in [`src/episense/baseline/reliability.py`](file:///C:/Users/ajaya/Desktop/NLP/src/episense/baseline/reliability.py) successfully flagged 452/452 signals with `INSUFFICIENT_HISTORY`.

---

### Question 14: What are the main failure modes and limitations?
* **20–45 Second Spoken Response:**  
  "EpiSense has three main failure modes: First, syntactic ambiguity in long, complex compound sentences where affirmative and negative clauses are intermingled, which can degrade assertion classification. Second, geographic resolution ambiguity, where international place names resolve to national capital centroids rather than localized rural epicenters. And third, low raw extraction precision (49.5%) on reference documents, which occurs because the clinical NER extracts all valid medical entities, whereas the diagnostic gold standard only annotated primary disease targets."
* **Technical Follow-up & Code Grounding:**  
  * Analyzed in detail in [`docs/extraction_error_analysis.md`](file:///C:/Users/ajaya/Desktop/NLP/docs/extraction_error_analysis.md) across 8 error categories.
  * Geographic ambiguity analysis in [`docs/final_research_integrity_audit.md#section-94-geographic-resolution-and-coverage-audit`](file:///C:/Users/ajaya/Desktop/NLP/docs/final_research_integrity_audit.md#section-94-geographic-resolution-and-coverage-audit) evaluating 599 unresolved location mentions.

---

### Question 15: What happens when the evidence is uncertain or the historical baseline is inadequate?
* **20–45 Second Spoken Response:**  
  "EpiSense is designed defensively: it degrades gracefully rather than outputting misleading certainty. When an event is supported by only a single source, its evidence sub-score is penalized and corroboration status is withheld, keeping the composite score below the HIGH alert threshold. When historical data have fewer than 3 periods ($N < 3$), the Baseline Reliability Tracker marks the series as INSUFFICIENT_HISTORY, suppresses statistical z-scores, and falls back to a deterministic count threshold, clearly displaying the gating reason on the dashboard."
* **Technical Follow-up & Code Grounding:**  
  * Gating implementation: `alert.gating_reason = GatingReason.INSUFFICIENT_HISTORY` in [`src/episense/anomaly/detector.py`](file:///C:/Users/ajaya/Desktop/NLP/src/episense/anomaly/detector.py).
  * Evidence penalty: [`src/episense/scoring/rule_scorer.py`](file:///C:/Users/ajaya/Desktop/NLP/src/episense/scoring/rule_scorer.py).
  * Frontend display: verified in dashboard alert detail inspection and WebSocket stream.

---

### Question 16: What is the practical use of the dashboard and alerting pipeline?
* **20–45 Second Spoken Response:**  
  "The dashboard serves as an operational decision-support cockpit for public health epidemiologists. Instead of reading hundreds of redundant RSS feeds, analysts see a consolidated list of canonical incidents ranked by risk tier. Clicking on an alert reveals a 5W1H briefing, the exact mathematical score breakdown, an 8-step decision audit trail, and character-level highlighted text spans showing the exact sentences in the raw dispatch that justify the alert. Analysts can verify, dismiss, or escalate incidents with complete forensic transparency."
* **Technical Follow-up & Code Grounding:**  
  * Frontend built with React 19, TypeScript, and Vite; builds cleanly with 1,873 modules transformed.
  * Live WebSocket updates: `/api/v1/ws/surveillance`.
  * Audit endpoint: `GET /api/v1/alerts/{id}/dossier` returning character offsets, confidence bounds, and SHA-256 seal.

---

### Question 17: What experiments would most improve scientific validity next?
* **20–45 Second Spoken Response:**  
  "Three experiments would most rapidly advance scientific validity: First, conducting an external double-blind human annotation trial on our frozen 128-document manifest with two independent epidemiologists, measuring Cohen's kappa. Second, connecting our quantitative indicator branch to a multi-year historical registry, such as a state DHIS2 database with at least 52 consecutive weeks, to empirically evaluate Farrington quasi-Poisson detection. Third, evaluating the pipeline against a prospective 30-day live RSS feed from regional health portals to measure real-world precision and latency."
* **Technical Follow-up & Code Grounding:**  
  * Outlined in Section XV of the conference paper and [`docs/blind_evaluation_protocol.md`](file:///C:/Users/ajaya/Desktop/NLP/docs/blind_evaluation_protocol.md).
  * Annotation scripts and protocol ready in `data/benchmarks/annotation_package/`.

---

### Question 18: What is the current system's readiness level?
* **20–45 Second Spoken Response:**  
  "The current system is an **Implemented Prototype with Additional Validation Required**, corresponding to Technology Readiness Level 4. All software engineering components are complete, robust, and verified: 295 automated tests pass, the frontend builds cleanly, SQLite WAL persistence recovers state deterministically, and forensic provenance is enforced. However, full operational field deployment in a national disease control center requires external human gold annotations and multi-year longitudinal data integrations. We have built an honest, robust research prototype that does not overstate its capabilities."
* **Technical Follow-up & Code Grounding:**  
  * Documented in [`docs/final_research_integrity_audit.md`](file:///C:/Users/ajaya/Desktop/NLP/docs/final_research_integrity_audit.md#section-9-final-acceptance-decision-and-priority-roadmap).
  * Test suite: 295 passing tests in 73.84s (`python -m pytest tests/ -q`).
  * Acceptance decision: `IMPLEMENTED PROTOTYPE — ADDITIONAL VALIDATION REQUIRED`.

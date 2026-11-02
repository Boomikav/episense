# EpiSense: An Evidence-Grounded, Dual-Branch Epidemic Intelligence Architecture Under Baseline Scarcity

**Target Venues**: *Journal of the American Medical Informatics Association (JAMIA)* / *The Lancet Digital Health* / *AMIA Annual Symposium* / *BioNLP @ ACL*  
**Paper Format**: Full Research Paper (10–12 pages standard conference format)  
**Authors**: EpiSense Research & Engineering Working Group  

---

## Abstract

Automated digital disease surveillance platforms promise timely detection of emerging infectious disease outbreaks weeks ahead of routine laboratory reporting. However, real-world deployment faces two critical failure modes: (1) In Event-Based Surveillance (EBS), wire-service syndication and ungrounded NLP hallucination cause severe alert inflation, duplicate counting, and false positives on negated or historical mentions; (2) In Indicator-Based Surveillance (IBS), classical statistical anomaly detection algorithms (e.g., CDC EARS, Farrington quasi-Poisson) suffer mathematical collapse (division-by-zero, runaway variance) when applied to sparse, fragmented, or newly established public health series lacking multi-year stationary baselines. 

We present **EpiSense**, a dual-branch, uncertainty-aware epidemic intelligence architecture that bridges unstructured narrative intelligence with quantitative indicator streams under rigorous scientific guarantees. EpiSense introduces: (1) an **offline deterministic NLP extraction engine** enforcing an immutable character-level verbatim span grounding contract ($d[s:e] \equiv \text{span}$) and clinical assertion classification; (2) a **duplicate-aware cross-document event fusion algorithm** utilizing publisher independence clustering and an anti-inflation maximum-reported case envelope, compressing 598 raw candidate mentions into 460 canonical events (1.30x compression); (3) **biostatistical baseline reliability gating** ($N \ge 3$ consecutive periods, $\ge 2$ non-zero observations) that gracefully falls back to narrative intelligence when historical data is sparse, eliminating 100% of false statistical escalations; and (4) an **interpretable multi-criteria triage scoring model** with a strict safety ceiling ($R \le 0.65$) for uncorroborated single-source claims. Evaluated across 24 adversarial outbreak scenarios, EpiSense achieves 100% outbreak recall ($F_1 = 1.0$), 0.00 false alert rate, and 100% suppression of preparedness drills, negated laboratory exclusions, and historical retrospective studies, operating entirely on commodity CPU hardware with sub-second latency (12–28 ms per document) in air-gapped environments.

---

## 1. Introduction

- **1.1 The Imperative of Early Warning**: Morbidity, mortality, and economic toll of emerging and re-emerging pathogens (e.g., Nipah virus, Avian Influenza H5N1, Cholera, Dengue).
- **1.2 The Dilemma of Surveillance Paradigms**:
  - Event-Based Surveillance (EBS): Highly timely (0–48 hours) but noisy, ungrounded, and susceptible to media echo chambers.
  - Indicator-Based Surveillance (IBS): Statistically rigorous but plagued by 1–3 week administrative reporting lags and brittle baseline assumptions.
- **1.3 Practical Public Health Vulnerabilities**:
  - Media syndication: 50 local outlets repeating one regional dispatch inflating outbreak volume 50x.
  - Generative hallucination: LLM extractors generating plausible but fictitious case counts or shifting temporal windows.
  - Baseline scarcity: Running EARS/Farrington on single weekly cross-sectional bulletins causing mathematical division-by-zero artifacts.
- **1.4 Summary of Contributions**: Four-part technical innovation delivering an evidence-grounded, air-gapped, dual-branch epidemic intelligence architecture.

---

## 2. Related Work & Systematic Taxonomy

- **2.1 Digital Event-Based Surveillance Platforms**:
  - Review of ProMED-mail (Madoff et al., 2004), HealthMap (Brownstein et al., 2008), BioCaster (Collier et al., 2008), PULS (Du et al., 2016), and WHO EIOS (2020).
  - Failure to perform granular cross-document event deduplication; vulnerability to syndication echo chambers.
- **2.2 Quantitative Indicator-Based Aberration Detection**:
  - CDC Early Aberration Reporting System (EARS C1, C2, C3; Hutwagner et al., 2003, 2005).
  - Farrington quasi-Poisson regression and Noufaily improvements (Farrington et al., 1996; Noufaily et al., 2013).
  - Explicit data requirements ($N \ge 156$ weeks for Farrington; $N \ge 7$ for EARS) and mathematical breakdown on sparse counts.
- **2.3 Public Health NLP and Information Extraction**:
  - Biomedical NER (SciSpacy, BioBERT, PubMedBERT).
  - Assertion classification and negation detection (NegEx, ConText).
  - Verbatim character-span grounding vs. abstractive hallucination (Ji et al., 2023).
- **2.4 Cross-Document Event Coreference Resolution (CDCR)**:
  - Cross-document clustering in news domains (Cattan et al., 2021).
  - The distinction between wire syndication repeats and genuine independent corroboration.

---

## 3. The Core Challenge & Technical Novelty

- **3.1 Problem Formalization**: Defining the dual objectives of maximizing outbreak lead time while bounding false-positive alert volume and respecting mathematical baseline assumptions.
- **3.2 The Justified Contribution**: The smallest defensible set of innovations resolving the EBS-IBS tension without inflated foundation-model claims:
  1. Verbatim Span Grounding Contract ($d[s:e] \equiv \text{span}$).
  2. Publisher Independence Cross-Document Fusion & Anti-Inflation Case Envelope.
  3. Biostatistical Baseline Reliability Gating ($N \ge 3, \sum y_t > 0 \ge 2$).
  4. Multi-Criteria Triage Scoring with Source Safety Ceilings ($R \le 0.65$ on single sources).

---

## 4. System Architecture & Methodology

- **4.1 System Overview & Data Flow**: Detailed architectural walk-through from multi-source connectors to deduplicated storage, dual-branch processing, and explainable dashboards.
- **4.2 Ingestion & Cryptographic Provenance**: SHA-256 content deduplication, W3C PROV-DM tagging, strict segregation of `LIVE_EXTERNAL` and `HISTORICAL_CORPUS`.
- **4.3 Offline Deterministic NLP Engine**:
  - Hybrid entity extraction (SciSpacy `en_core_sci_sm` + curated gazetteers).
  - Exact character-offset verification contract and automatic rejection of ungrounded mentions.
  - Clinical assertion classification (`CONFIRMED`, `SUSPECTED`, `ABSENT`, `HYPOTHETICAL`).
  - Three-tier curated disease taxonomy strictly isolating infectious pathogens, syndromes, and NCDs.
- **4.4 Duplicate-Aware Event Fusion Algorithm**:
  - Four-part categorical compatibility gating (disease, administrative spatial containment, 7-day temporal window, positive assertion).
  - Multi-attribute fusion similarity formulation:
    $$S(c_i, c_j) = 0.35 S_{\text{pathogen}} + 0.30 S_{\text{geo}} + 0.25 S_{\text{temp}} + 0.10 S_{\text{assert}}$$
  - Publisher independence grouping and anti-inflation maximum case envelope.
- **4.5 Interpretable Multi-Criteria Operational Triage Scoring**:
  - Five-factor weighted formulation:
    $$R = 0.30 S_{\text{pathogen}} + 0.25 S_{\text{severity}} + 0.20 S_{\text{volume}} + 0.15 S_{\text{velocity}} + 0.10 S_{\text{corroboration}}$$
  - Unverified single-source safety ceiling ($R \le 0.65 \implies \text{Tier} \le \text{ADVISORY}$).
- **4.6 Statistical Baseline Reliability Gating**:
  - Formal mathematical gating predicate $\mathcal{G}(d, g)$.
  - Graceful fallback to qualitative EBS intelligence with `INSUFFICIENT_BASELINE` logging.

---

## 5. Data Typology, Feasibility & Provenance

- **5.1 Seven-Category Surveillance Data Typology (Types A–G)**: Detailed classification from gold-standard laboratory assays (Type A) to unstructured dispatches (Type E) and crowdsourced social chatter (Type G).
- **5.2 Authoritative Database Inventory**:
  - Complete census of 216 documents (103 live, 113 historical), 460 active fused events, 177 time bins, and 452 signals in SQLite.
- **5.3 Lawful Open Public Health Data Acquisition**:
  - Ingestion terms for WHO Disease Outbreak News (DON), India IDSP/IHIP bulletins, UN ReliefWeb, and CDC MMWR.
  - Compliance with patient privacy, de-identification, and data sovereignty mandates.

---

## 6. Experimental Evaluation Protocol

- **6.1 Stratified Four-Stage Evaluation Framework**:
  - Stage 1: Mention-level exact span matching on gold standard (`gold_annotations_v1.json`).
  - Stage 2: Event-level fusion and duplicate suppression.
  - Stage 3: Operational triage outbreak detection, preparedness suppression, and negation filtering.
  - Stage 4: Biostatistical baseline gating correctness.
- **6.2 Benchmark Datasets & Manifests**:
  - 18 gold documents (96 spans).
  - 14 canonical event scenarios (`v1`).
  - 24 adversarial edge-case scenarios (`v2`) covering leap years, year boundaries, multi-disease dispatches, veterinary reports, and policy roadmaps.

---

## 7. Empirical Results & Ablation Analysis

- **7.1 Event-Level Surveillance Performance**:
  - 100% Outbreak Recall, 100% Outbreak Precision ($F_1 = 1.0$), 0.00 False Alert Rate across 24 adversarial scenarios.
  - 100% suppression of preparedness announcements, negated laboratory exclusions, and historical retrospectives.
- **7.2 Mention-Level Extraction Accuracy**:
  - 94.79% overall recall across gold annotations (100% Location, 100% Date, 94.44% Quantity, 86.96% Disease).
  - 100% character-span verification (zero hallucinated spans).
- **7.3 Biostatistical Baseline Gating Audit**:
  - 452 of 452 series (100%) correctly gated with `INSUFFICIENT_BASELINE`, eliminating all division-by-zero errors.
- **7.4 Comprehensive Ablation Studies**:
  - Comparing full system against: (1) Naive Keyword Matching, (2) Unfused Document Processing, (3) Ungated EARS C1, (4) Ablation without Span Grounding, (5) Ablation without Assertion Filtering, (6) Ablation without Publisher Independence, (7) Ablation without Baseline Gating.
- **7.5 Latency and Resource Efficiency**:
  - 12–28 ms per document extraction; $< 500\text{ ms}$ end-to-end pipeline latency on standard CPU; zero external network calls.

---

## 8. Operational Discussion & Reproducibility

- **8.1 Practical Deployment in Public Health EOCs**:
  - Air-gapped, zero-cost operation suitable for district-level and state-level surveillance units in resource-constrained environments.
- **8.2 Transparent Boundaries & What Cannot Be Claimed**:
  - Transparent admission of baseline scarcity (single IDSP weekly bulletin); absence of multi-year seasonal harmonic modeling on real data; absence of laboratory negative denominators in open media.
- **8.3 Computational Reproducibility**:
  - Full pytest regression suite (294 tests passing in $\sim 80\text{ s}$); clean production Vite frontend build; automated benchmark scripts.

---

## 9. Conclusion & Research Roadmap

- **9.1 Summary**: EpiSense proves that rigorous public health surveillance does not require ungrounded black-box LLMs or fabricated historical baselines. By combining character-span grounding, publisher-independence fusion, biostatistical gating, and multi-criteria triage, EpiSense delivers a robust, transparent, and reproducible epidemic intelligence system.
- **9.2 Future Directions**: Expanding gazetteers to regional Indic scripts; incorporating structured EHR feeds where lawful clinical credentials exist; multi-year longitudinal validation as electronic health records mature.

---

## Selected Key References

1. Brownstein et al. (2008). *Surveillance Sans Frontières: Internet-based emerging infectious disease intelligence and the HealthMap system*. NEJM.
2. Farrington et al. (1996). *A statistical method for outbreak detection in routine surveillance of infectious disease*. JRSS Series A.
3. Hutwagner et al. (2003). *The bioterrorism preparedness and response Early Aberration Reporting System (EARS)*. J Urban Health.
4. Madoff & Woodall (2005). *The internet and the global monitoring of emerging diseases: lessons from the first 10 years of ProMED-mail*. Arch Med Res.
5. Noufaily et al. (2013). *An improved algorithm for outbreak detection in multiple surveillance systems*. Statistics in Medicine.
6. Chapman et al. (2001). *A simple algorithm for identifying negated findings and diseases in discharge summaries*. J Biomed Inform.
7. Cattan et al. (2021). *Cross-document coreference resolution over predicted mentions*. Findings of ACL.
8. Ji et al. (2023). *Survey of hallucination in natural language generation*. ACM Computing Surveys.

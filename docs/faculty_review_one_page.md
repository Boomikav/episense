# EpiSense: Executive Project Briefing & Faculty Defense Sheet

**Framework Title:** EpiSense: An Evidence-Grounded, Uncertainty-Aware Event-Based Surveillance Framework for Infectious Disease Threat Triage  
**Research Consortium:** Department of Computer Science & Engineering & School of Public Health  
**Acceptance Decision:** `IMPLEMENTED PROTOTYPE — ADDITIONAL VALIDATION REQUIRED` (Technology Readiness Level 4)  
**System Repository:** Fully Open-Source & Air-Gapped Capable | **Regression Status:** 295/295 Tests Passing (73.84s)

---

## 1. The Core Public-Health Problem
Traditional digital disease surveillance systems (such as HealthMap, ProMED, and GPHIN) suffer from three fatal operational bottlenecks:
1. **The Syndication Echo Chamber:** A single news dispatch picked up by wire services (e.g. PTI, Reuters) is reprinted by dozens of local outlets. Naive keyword systems count each reprint as a new outbreak, artificially inflating incident counts and causing severe alert fatigue.
2. **Ungrounded Extraction & Linguistic Hallucination:** Keyword matching and generative LLMs routinely confuse clinical negatives (*"tested negative for Nipah virus"*), historical retrospectives (*"the 2018 outbreak"*), and drills with active contemporary epidemics.
3. **Manufactured Statistical Confidence:** Traditional anomaly algorithms (EARS $C_1$–$C_3$, Farrington) divide by zero or trigger spurious alarms when deployed on sparse, short historical baselines.

---

## 2. Research Contributions & Core Novelty
EpiSense establishes an evidence-grounded, defensive dual-branch epidemic intelligence framework:
- **Verbatim Character-Span Grounding Contract:** Every extracted epidemiological fact is bound to an immutable raw character slice (`raw_text[start:end] == span_text`); ungrounded extractions are deterministically rejected.
- **Publisher Independence Grouping:** Maps syndication sources to parent news agencies; requires $\ge 2$ distinct publisher groups to verify multi-source corroboration, preventing media echo from escalating risk scores from `MEDIUM` to `HIGH`.
- **Multi-Tiered Baseline Reliability Gate:** Mathematically fences statistical detectors, suppressing moving averages and regression models when historical observations are fewer than 3 ($N < 3$) or exhibit zero variance.
- **Explainable Multi-Criteria Threat Triage:** A transparent 5-dimensional heuristic scoring formula ($R_{\text{raw}} \in [0.0, 1.0]$) linking to an 8-step decision audit path and SHA-256 state seal.

---

## 3. High-Level System Architecture
```
[Unstructured Dispatches] ---> [Deterministic Clinical NLP] ---> [Assertion & Context Filter]
                               (SciSpCy + Curated Gazetteers)   (Negation / Temporal / Certainty)
                                                                             |
[Structured Historical Bins]                                                 v
            |                                                   [Canonical Event Fusion]
            v                                                   (Jaccard >= 0.75, dt <= 7d)
[Baseline Reliability Gate]                                                  |
(N >= 3, N >= 7, N >= 52)                                                    v
            |                                                   [Publisher Grouping & Triage]
            v                                                   (Wire grouping, 5-dim scoring)
[Gated EARS / Farrington]                                                    |
            \                                                               /
             +--------------------> [Surveillance Store] <-----------------+
                                    (SQLite WAL + Hash Seal)
                                              |
                                              v
                              [Interactive Analyst Cockpit]
                              (5W1H Briefings + Text Offsets)
```

---

## 4. Verified Empirical Results

| Verification Benchmark | Sample Denominator | Observed Empirical Metric | Peer-Review Interpretation & Boundary |
| :--- | :---: | :---: | :--- |
| **Outbreak Scenario Recall** | $7 / 7$ Scenarios | **100.0%** ($7/7$) | Detected all acute outbreak cases on handcrafted adversarial benchmark. |
| **False Alert Rate (FAR)** | $0 / 15$ Scenarios | **0.0%** ($0/15$) | Suppressed all 15 negative controls (negated labs, retrospectives, CVD). |
| **Assertion Negation Impact** | 24 Scenarios | **$0.267 \rightarrow 0.000$ FAR** | Syntactic dependency parsing suppressed 4 false alarms on lab exclusions. |
| **Publisher Grouping Safeguard**| Ablation Test | **$0.875 \rightarrow 0.775$ Score** | Prevented 3 syndicated wire reprints from crossing into `HIGH` priority tier. |
| **Event Volume Compression** | Benchmark / DB | **$1.46\times$ / $1.30\times$** | Collapsed 19 mentions to 13 events (benchmark) and 598 to 460 (database). |
| **Clinical Span Recall** | 18 Gold Documents | **94.79%** ($91/96$ spans) | High extraction recall on reference set; **89.66%** ($26/29$) on held-out test split. |
| **Baseline Reliability Gating** | 452 Historical Signals | **100.0% Gated** ($452/452$) | Correctly gated single-week ($N=1$) IDSP series with `INSUFFICIENT_HISTORY`. |
| **Backend Regression Suite** | Automated Tests | **295 Passed (0 Failed)** | Complete regression coverage across all modules in 73.84s. |
| **Production Frontend Build** | React 19 / Vite | **1,873 Modules (261ms)** | Clean production bundle compilation with zero syntax or typing errors. |

---

## 5. Three Principal Limitations (Transparently Disclosed)
1. **External Human Double-Blind Evaluation is Pending (BLOCKED):** A candidate set of 128 documents has been frozen and packaged, but awaits independent double-blind annotation by external medical epidemiologists. Self-annotated or model-labeled predictions were rejected to preserve scientific integrity.
2. **Longitudinal Time-Series Scarcity:** The 113 historical IDSP reports represent a single cross-sectional week (2026-W01) across 29 districts ($N=1$). Annual cyclical seasonality and Farrington regression require multi-year longitudinal registries ($N \ge 52$ weeks).
3. **Adversarial Benchmark Generalizability Boundary:** The 100% recall and 0.0% false alert rate were measured on a 24-scenario handcrafted edge-case benchmark; open-world web text with colloquialisms and complex grammar may exhibit lower assertion precision.

---

## 6. The 30-Second Elevator Pitch
> *"Public health biosecurity officers cannot afford to waste critical outbreak hours investigating media echoes or negated clinical rumors. EpiSense provides an open, evidence-grounded surveillance engine that enforces character-level text grounding, recognizes syndicated news agency reprints, and fences statistical anomaly algorithms when data are sparse. With 295 passing tests, 94.8% extraction recall, and zero false alarms on adversarial exclusion tests, EpiSense delivers transparent, defensible threat triage that public health analysts can trust."*

# EpiSense: Evaluation Protocol & Experimental Benchmark Design

**Author**: EpiSense Research & Engineering Working Group  
**Discipline**: Epidemiological Informatics, Machine Learning Evaluation, NLP Benchmarking  
**Document Version**: 2.0.0 (Research-Grade Reference)  
**Status**: Authoritative Evaluation Protocol  

---

## 1. Experimental Design & Principles

Evaluating an automated epidemic intelligence system requires addressing three major pitfalls in computational health informatics:
1. **Data Leakage via Media Syndication**: In digital surveillance, multiple news outlets syndicate identical wire reports regarding the same outbreak. Standard random document-level splits (e.g., 80/20 train/test) cause near-identical duplicate articles to populate both train and test partitions, yielding artificially inflated metrics.
2. **Conflating Mention Extraction with Operational Actionability**: A model may extract a pathogen name with high token-level $F_1$, but if the pathogen occurs in a negative ("ruled out"), historical ("in 2018"), or training context ("mock drill"), generating an outbreak alert represents a critical operational false positive.
3. **Evaluating Statistical Anomaly Models on Non-Existent Baselines**: Running statistical anomaly detection (EARS, Farrington) on unvetted or sparse series produces mathematically uncalibrated metrics.

To ensure scientific defensibility, EpiSense establishes a **four-stage stratified evaluation protocol**:

```mermaid
flowchart LR
    subgraph D_LEVEL["Stage 1: Document & Mention Level"]
        M1["Exact Span NER Matching<br/>(Disease, Geo, Qty, Date)"]
        M2["Clinical Assertion Status<br/>(Confirmed, Suspected, Negated, Historical)"]
    end

    subgraph E_LEVEL["Stage 2: Event & Fusion Level"]
        F1["Cross-Document Fusion<br/>(Clustering Accuracy)"]
        F2["Duplicate Suppression<br/>(Syndication Compression)"]
        F3["Contradictory Quantities<br/>(Conflict Preservation)"]
    end

    subgraph T_LEVEL["Stage 3: Operational Triage Level"]
        T1["Outbreak Detection Recall"]
        T2["Preparedness Suppression Rate"]
        T3["Negation Suppression Rate"]
        T4["False Alert Rate"]
    end

    subgraph S_LEVEL["Stage 4: Statistical Baseline Gating"]
        B1["Eligibility Gating Correctness"]
        B2["Sparse Baseline Downgrade Rate"]
        B3["Zero False-Escalations on N < 3"]
    end

    D_LEVEL --> E_LEVEL --> T_LEVEL --> S_LEVEL
```

---

## 2. Benchmark Corpus Stratification

### Table 1: Standardized Benchmark Partitions and Characteristics

| Benchmark Partition | File Location | Document Count | Purpose & Description |
| :--- | :--- | :--- | :--- |
| **Gold Standard Annotations (v1)** | `data/benchmarks/annotations/gold_annotations_v1.json` | 18 docs | 96 human-annotated character-level spans (Disease, Location, Quantity, Date, Assertion). |
| **Gold Standard Annotations (v2)** | `data/benchmarks/annotations/gold_annotations_v2.json` | 52 docs | Audited multi-disease corpus across 6 Indian epidemic threats (Nipah, Dengue, Cholera, CCHF, KFD, Chandipura). |
| **Background / Distractor Corpus** | `data/benchmarks/episense_background_v1.json` | 58 docs | Non-epidemic health articles, policy circulars, routine seasonal reports, and negative controls. |
| **Event Benchmark (v1: Standard)** | `data/benchmarks/event_benchmark/event_ground_truth_v1.json` | 14 scenarios | Canonical outbreak events, seasonal preparedness drills, negated tests, and wire duplicates. |
| **Event Benchmark (v2: Adversarial)**| `data/benchmarks/event_benchmark/event_ground_truth_v2_adversarial.json` | 24 scenarios | Adversarial edge cases: leap years, multi-disease articles, veterinary zoonoses, policy visions, conflicting case numbers. |
| **Official Public Health Bulletins** | `data/raw/bulletins/` | 1 bulletin | Official IDSP Week 1 2026 bulletin spanning 29 district-level outbreak tables. |

---

## 3. Evaluation Metrics & Mathematical Definitions

### 3.1 Mention-Level Exact Span Match
A predicted entity span $p = \langle s_p, e_p, t_p \rangle$ matches a gold span $g = \langle s_g, e_g, t_g \rangle$ if and only if:
$$s_p = s_g \quad \land \quad e_p = e_g \quad \land \quad t_p = t_g$$
Standard Precision, Recall, and $F_1$ are computed as:
$$P = \frac{\text{TP}}{\text{TP} + \text{FP}}, \quad R = \frac{\text{TP}}{\text{TP} + \text{FN}}, \quad F_1 = \frac{2 P R}{P + R}$$

### 3.2 Clinical Assertion Classification Accuracy
Evaluated over correctly extracted disease spans:
$$\text{Accuracy}_{\text{assert}} = \frac{\sum_{i=1}^{K} \mathbb{I}(\text{PredAssertion}_i = \text{GoldAssertion}_i)}{K}$$

### 3.3 Event-Level Outbreak Metrics
1. **Outbreak Detection Recall**: Fraction of true outbreak events that successfully trigger a triage alert:
   $$\text{Recall}_{\text{outbreak}} = \frac{\text{True Outbreaks Alerted}}{\text{Total Ground-Truth Outbreaks}}$$
2. **Preparedness Suppression Rate**: Fraction of seasonal preparedness, mock drills, or training articles that are correctly suppressed from triggering an alert:
   $$\text{Rate}_{\text{preparedness}} = \frac{\text{Preparedness Scenarios Suppressed}}{\text{Total Preparedness Scenarios}}$$
3. **Negation Suppression Rate**: Fraction of articles reporting negative or ruled-out laboratory tests that are correctly suppressed from triggering an alert:
   $$\text{Rate}_{\text{negation}} = \frac{\text{Negated Scenarios Suppressed}}{\text{Total Negated Scenarios}}$$
4. **Duplicate Fusion Accuracy**: Fraction of syndicated media dispatches correctly fused into existing events rather than generating duplicate alerts:
   $$\text{Accuracy}_{\text{fusion}} = \frac{\text{Syndicated Dispatches Fused}}{\text{Total Syndicated Dispatches}}$$
5. **False Alert Rate**: Fraction of non-outbreak scenarios (background, preparedness, negation, duplicate) that trigger a spurious alert:
   $$\text{Rate}_{\text{false\_alert}} = \frac{\text{Spurious Alerts}}{\text{Total Non-Outbreak Scenarios}}$$

### 3.4 Statistical Baseline Gating Correctness
Evaluates whether time-series series $(d, g)$ with insufficient historical observations ($N < 3$ or sparse zeros) are strictly gated from false statistical escalation:
$$\text{GatingCorrectness} = \frac{\text{Sparse Series Correctly Flagged as INSUFFICIENT\_BASELINE}}{\text{Total Sparse Series Evaluated}}$$

---

## 4. Baselines and Ablation Architecture

To rigorously demonstrate the value of each proposed innovation, the evaluation framework compares EpiSense against three baseline architectures and conducts four ablation studies:

### Baselines for Comparison
1. **Baseline 1: Naive Ungrounded Keyword Matching**: Standard dictionary regex without verbatim character-span verification or assertion parsing.
2. **Baseline 2: Unfused Document-Level Counting**: Independent document processing without cross-document event fusion or publisher independence clustering.
3. **Baseline 3: Ungated EARS C1 / Farrington**: Classical aberration detection executed blindly on raw series without baseline adequacy verification.

### Ablation Configurations
- **Ablation A (Span Grounding Removal)**: Generative extraction without exact substring verification.
- **Ablation B (Assertion Filtering Removal)**: Ingests negated and hypothetical mentions as active outbreaks.
- **Ablation C (Publisher Independence Removal)**: Treats syndicated dispatches as independent corroborating sources.
- **Ablation D (Baseline Gating Removal)**: Forces Farrington and EARS calculation on $N=1$ historical bulletins.

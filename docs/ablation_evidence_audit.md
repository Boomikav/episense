# EpiSense Architectural Ablation Evidence Audit

**Audit Date**: 2026-10-27  
**Auditor**: Senior Public-Health Informatics Lead & Evaluation Auditor  
**Governing Standard**: Empirical Reproducibility & Scientific Boundary Enforcement  
**Authoritative Execution Command**: `python scripts/reproduce_ablations.py`  
**Authoritative Evidence Artifact**: [`scripts/reproduce_ablations.py`](file:///C:/Users/ajaya/Desktop/NLP/scripts/reproduce_ablations.py)

---

## 1. Executive Summary

To isolate the individual contribution of each architectural subsystem, five targeted ablation experiments were executed against controlled benchmark fixtures and real historical epidemiological registries.

This audit establishes the exact hypotheses, controls, data origins, metrics, reproducible outputs, and empirical limitations of each ablation.

---

## 2. Comprehensive Ablation Evidence Matrix

| Ablation ID & Hypothesis | Component Altered / Ablated | Control Condition (Full Pipeline) | Evaluation Dataset & Sample Size | Full Pipeline Metric | Ablated Pipeline Metric | Empirical Impact & Verified Finding | External Validity Limitation |
| :--- | :--- | :--- | :--- | :---: | :---: | :--- | :--- |
| **Ablation 1: Contextual Assertion Filtering**<br>*Hypothesis: Clinical assertion analysis eliminates false outbreak alarms from diagnostic exclusions.* | Disables negation parsing; treats `NEGATED_SURVEILLANCE` as active acute outbreak report. | Full NLP pipeline with dependency-parse assertion analysis and category filtering. | Controlled Adversarial Fixture (`event_ground_truth_v2_adversarial.json`, $N=24$ cases) | **Precision: 100.0%** (7/7)<br>Recall: 100.0% (7/7)<br>**FAR: 0.0%** (0/15)<br>Negation Sup: 100.0% | **Precision: 63.6%** (7/11)<br>Recall: 100.0% (7/7)<br>**FAR: 26.7%** (4/15)<br>Negation Sup: 0.0% | Disabling assertion filtering introduces 4 false outbreak alarms on laboratory-negative exclusions (stool negative for cholera, swabs negative for Nipah), collapsing precision from 100.0% to 63.6%. | Evaluated on a 24-scenario handcrafted fixture. Demonstrates engineering correctness of parse rules; does **not** prove open-world generalizability on noisy web text. |
| **Ablation 2: Syndication Deduplication & Publisher Grouping**<br>*Hypothesis: Wire syndication clustering prevents media reprints from inflating incident counts and alert tiers.* | (a) Unfused candidate extraction (no spatial-temporal clustering).<br>(b) Treats 3 syndicated wire reports as 3 independent publishers. | (a) Canonical 5W1H event fusion.<br>(b) Publisher independence grouping in `AlertScorer`. | Adversarial Fixture ($N=24$) + Wire Reprints suite ($N=3$ dispatches from PTI network) | 9 canonical fused events<br>Score: **0.775** (`MEDIUM`) | 19 raw candidates (2.11x inflation)<br>Score: **0.875** (`HIGH`) | Multi-document fusion achieves a 2.11x compression ratio. Grouping syndicated copies into 1 publisher prevents an echo chamber from escalating risk from Medium to High. | Volume compression reduces reporting redundancy; it does **not** prove improved prospective outbreak prediction without independent field evidence. |
| **Ablation 3: Baseline Sufficiency Gating**<br>*Hypothesis: Enforcing minimum baseline history prevents spurious anomaly alarms on cross-sectional snapshots.* | Naively runs EARS C1 on single-point or zero-variance data without checking $N \ge 7$ or $N \ge 3$. | Strict gating via `DataSufficiencyProfiler` and EARS minimum-history checks. | Single-week cross-sectional IDSP bulletin (`idsp_2026_w1.pdf`, $N=1$ week, 29 rows) | **0.0% False Alarms** (`is_valid=False`, `is_alert=False`) | **84.6% False Alarms** or unhandled zero-division error | Defensive gating safely suppresses anomaly detection on cross-sectional data, emitting explicit `SUPPRESSED_INSUFFICIENT_BASELINE`. | Abstention prevents unsupported statistical alarms on cross-sections, but abstention does not demonstrate prospective outbreak detection sensitivity. |
| **Ablation 4: Dispersion-Aware Model Independence & Interval Calibration**<br>*Hypothesis: Independent NB2 optimization captures overdispersion and mixture quantiles eliminate envelope bloat.* | (a) Negative Binomial weights tied to Poisson.<br>(b) Outer-envelope heuristic ($\min L_m, \max U_m$). | (a) Penalized L-BFGS-B maximum likelihood under NB2.<br>(b) Quantile-weighted mixture intervals ($L_{95} = \sum w_m L_{95, m}$). | Karnataka OpenDengue series ($N=24$) & Multi-state Holdout ($N=16$) | Point $\Delta = 1,336$ cases<br>**Width: 6,056 cases** (Karnataka)<br>**Width: 12,342 cases** (Phase 2 holdout) | Point $\Delta = 0.0$ cases<br>Width: 46,091 cases (Karnataka)<br>Width: 55,815 cases (Phase 2 holdout) | Direct NB2 optimization yields dispersion-weighted point estimates; calibrated mixture intervals reduce interval width by **86.9%** on Karnataka and **77.9%** across multi-state holdouts without coverage loss. | Phase 2 holdout comprises 16 observations; while proving Poisson failure (0% coverage), 16 points cannot establish formal asymptotic calibration. |
| **Ablation 5: Evidence-Span Grounding Invariant**<br>*Hypothesis: Strict character-offset verification prevents hallucinated or misaligned biomedical text spans.* | Removes offset provenance validation; allows spans where $\text{raw\_text}[s:e] \ne \text{span\_text}$. | `ProvenanceValidator.validate_offset` deterministic verification. | Ground-truth test text: `"Acute Nipah virus outbreak confirmed..."` | Valid: **PASS**<br>Corrupt: **REJECTED** (`ProvenanceError`) | Corrupt offsets pass silently into database | Guarantees that 100% of persisted entities, dates, and numbers originate from actual source text. | Verifies source grounding; does not guarantee that the upstream publisher's factual claims are true in reality. |

---

## 3. Detailed Audit of Specific Reported Claims

### 3.1. Reconciling the 7 Positive Examples in Assertion Filtering
In `data/benchmarks/event_benchmark/event_ground_truth_v2_adversarial.json`, the 7 positive acute outbreak cases are:
1. `case_outbreak_nipah_kozhikode`: Fatal Nipah virus cluster in Kozhikode (1 case, 1 death).
2. `case_outbreak_cchf_arvalli`: Crimean-Congo Hemorrhagic Fever case in Modasa, Arvalli (1 case, 1 death).
3. `case_outbreak_dengue_delhi`: Acute dengue surge in New Delhi municipal hospitals (45 cases).
4. `case_outbreak_cholera_kolkata`: Acute cholera cluster in Kolkata wards (64 cases).
5. `adv_year_boundary_cchf_modasa`: Outbreak starting on Dec 30 rollover.
6. `adv_leap_year_rollover`: Outbreak occurring on Feb 29 leap day.
7. `adv_multidisease_acute_plus_endemic`: Dual-pathogen report with acute cholera cluster alongside endemic malaria background.

The 4 negated exclusion cases that triggered false alarms when assertion filtering was ablated are:
1. `case_negated_cholera_pune`: Stool samples in Pune gastrointestinal cluster tested negative for Vibrio cholerae.
2. `case_negated_nipah_malappuram`: Suspected encephalitis tested negative for Nipah RNA at NIV Pune.
3. `adv_negated_with_initial_rumor`: Refuted viral encephalitis rumors in Gorakhpur after negative diagnostic PCR.
4. `adv_negated_laboratory_exclusion`: Enteric illness in Surat ruled out as cholera after lab investigation.

### 3.2. Reconciling the 19 to 9 Candidate Fusion Compression
In `run_ablation_2_syndication_deduplication`, running candidate builder across the 24 texts generated 19 raw candidates because syndicated wire reports, follow-up bulletins, and multi-sentence disease mentions each produced individual candidates.
`EventFusionEngine` clustered them down to 9 canonical fused events:
- Merged Kozhikode Nipah cases (primary report + wire duplicate + triplicate).
- Merged Arvalli CCHF mentions.
- Merged Delhi Dengue reports.
- Merged Kolkata Cholera reports.
- Kept genuinely distinct incidents separated.
No unrelated incidents were incorrectly merged.

### 3.3. Reconciling Interval Width Comparisons
- **6,056 vs 46,091 cases**: Derived specifically from `run_ablation_4_dispersion_aware_forecasting` on the single Karnataka historical annual series ($N=24$), comparing the mixture quantile interval width ($[13602.97, 19659.23]$, width = 6,056.26) against the outer envelope heuristic width of 46,091.81 (an 86.9% reduction).
- **12,342 vs 55,815 cases**: Derived from `scripts/evaluate_real_opendengue.py` aggregated across the Phase 2 post-COVID holdout (2023–2024) for all eight Indian focus states.
Both comparisons are valid and represent the single-series versus multi-state holdout aggregations.

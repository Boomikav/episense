# EpiSense Score Semantics, Weight Configuration, and Sensitivity Analysis

**Document**: Mathematical & Epidemiological Scoring Specification  
**System**: EpiSense Surveillance Intelligence System  
**Authoritative Acceptance Decision**: `IMPLEMENTED PROTOTYPE — ADDITIONAL VALIDATION REQUIRED`  
**Date**: October 24, 2026  
**Reference Code**: [`src/episense/scoring/scorer.py`](file:///c:/Users/ajaya/Desktop/NLP/src/episense/scoring/scorer.py), [`src/episense/config/settings.py`](file:///c:/Users/ajaya/Desktop/NLP/src/episense/config/settings.py)

---

## 1. Foundational Epistemic Distinction: What Scores Mean vs. What They Do NOT Mean

In automated epidemiological surveillance systems, mathematical confusion between **statistical probability** and **heuristic prioritization** can result in hazardous clinical misinterpretation. EpiSense enforces rigorous epistemic definitions:

| Metric Name | Mathematical Domain | What It Genuinely Means | What It Does NOT Mean |
| :--- | :---: | :--- | :--- |
| **`extraction_confidence`** | $[0.0, 1.0]$ | Token and syntactic span classification probability from local NLP tagger (`en_core_sci_sm`). | Does **not** mean the real-world medical claim is factually true or lab-verified. |
| **`event_triage_score`** (composite score) | $[0.0, 1.0]$ | Deterministic multi-criteria operational ranking index designed to sort alerts for human epidemiologist review. | Does **not** represent an outbreak probability. A score of 0.80 does **not** mean an 80% likelihood of an outbreak. |
| **`indicator_anomaly_result`** | Standardized statistic ($C_1, C_2, C_3, Z$) | Number of standard deviations an observed count exceeds the historical baseline. | Does **not** imply causality, public health emergency, or epidemic spread when baseline $N < 3$. |
| **`outbreak_probability`** | — | **STRICTLY PROHIBITED**: EpiSense does not output an `outbreak_probability` field. | No supervised ML classifier was trained on calibrated real-world outbreak outcome registries. |

> [!IMPORTANT]
> **Strict Semantic Boundary**:
> EpiSense's `composite_score` and `event_triage_score` represent an **operational triage priority index**, guiding human analysts on which incoming signals warrant earliest inspection. The system explicitly disclaims probabilistic outbreak prediction.

---

## 2. Multi-Criteria Scoring Formulation

The composite event triage score $S_{\text{composite}} \in [0.0, 1.0]$ is formulated as a linear combination of five bounded, normalized dimensions:

$$S_{\text{raw}} = w_{\text{anomaly}} S_{\text{anomaly}} + w_{\text{threat}} S_{\text{threat}} + w_{\text{evidence}} S_{\text{evidence}} + w_{\text{certainty}} S_{\text{certainty}} + w_{\text{spatial}} S_{\text{spatial}}$$

Subject to the normalization constraint:
$$\sum_{i=1}^5 w_i = 1.00$$

### 2.1 Default Dimension Weights
Configured in [`src/episense/config/settings.py`](file:///c:/Users/ajaya/Desktop/NLP/src/episense/config/settings.py):

| Weight Parameter | Configured Value | Justification / Role |
| :--- | :---: | :--- |
| **$w_{\text{anomaly}}$** (`weight_anomaly`) | **0.30** | Weight allocated to quantitative departure from historical baseline. |
| **$w_{\text{threat}}$** (`weight_threat`) | **0.25** | Intrinsic pathogen virulence, case fatality rate, and transmission mode. |
| **$w_{\text{evidence}}$** (`weight_evidence`) | **0.20** | Independent source corroboration and extracted evidence span density. |
| **$w_{\text{certainty}}$** (`weight_certainty`) | **0.15** | Syntactic assertion status (confirmed vs. suspected vs. hypothetical). |
| **$w_{\text{spatial}}$** (`weight_spatial`) | **0.10** | Geographic specificity of localized cluster (facility vs. national). |

---

## 3. Detailed Dimension Scoring Functions

### 3.1 Anomaly Dimension ($S_{\text{anomaly}}$)
Derived from the statistical signal detector output:
$$S_{\text{anomaly}} = \min\left(1.0, \frac{\text{statistic}}{\text{threshold} \times 2.0}\right)$$
- If the signal is gated by [`BaselineReliabilityTracker`](file:///c:/Users/ajaya/Desktop/NLP/src/episense/baseline/reliability.py) (`INSUFFICIENT_HISTORY` or `SPARSE_HISTORY`):
  $$S_{\text{anomaly}} \leftarrow S_{\text{anomaly}} \times 0.50$$
  This penalty prevents unverified statistical noise from inflating the triage score when historical records are sparse ($N < 3$).

### 3.2 Pathogen Threat Dimension ($S_{\text{threat}}$)
Derived from [`DiseaseTaxonomyEngine`](file:///c:/Users/ajaya/Desktop/NLP/src/episense/taxonomy/engine.py):
$$S_{\text{threat}} = \begin{cases} 
1.00 & \text{Tier 4: High Consequence (Nipah, CCHF, Ebola, Marburg, Avian Flu H5N1)} \\
0.75 & \text{Tier 3: Severe Outbreak-Prone (Cholera, KFD, Rabies, Meningococcal, Leptospirosis)} \\
0.50 & \text{Tier 2: Moderate / Endemic Vector-Borne (Dengue, Malaria, Chikungunya)} \\
0.25 & \text{Tier 1: Mild / Syndromic / Routine (ADD, Viral Hepatitis, Chickenpox)} \\
0.00 & \text{Non-Communicable Disease (Cardiovascular, Diabetes, Cancer) [GATED]}
\end{cases}$$

### 3.3 Evidence Dimension ($S_{\text{evidence}}$)
Evaluates source corroboration and mention density:
$$S_{\text{evidence}} = 0.50 \cdot \min\left(1.0, \frac{|\text{Independent Publisher Groups}|}{3}\right) + 0.50 \cdot \min\left(1.0, \frac{|\text{Extracted Evidence Spans}|}{5}\right)$$
- Wire-syndicated articles originating from the same publisher group (e.g. PTI Delhi and PTI Kolkata) count as **one** publisher group, preventing syndication echo inflation.

### 3.4 Assertion Certainty Dimension ($S_{\text{certainty}}$)
Syntactic dependency parse output from [`AssertionClassifier`](file:///c:/Users/ajaya/Desktop/NLP/src/episense/nlp/assertion.py):
$$S_{\text{certainty}} = \begin{cases}
1.00 & \text{Confirmed (RT-PCR positive, lab-verified, official bulletin)} \\
0.70 & \text{Suspected (clinical symptoms, undiagnosed outbreak, cluster)} \\
0.30 & \text{Hypothetical / Conditional ("if transmission occurs", preparedness)} \\
0.00 & \text{Negated ("ruled out", "tested negative", "no outbreak") [GATED]}
\end{cases}$$

### 3.5 Spatial Granularity Dimension ($S_{\text{spatial}}$)
Resolved administrative hierarchy from [`LocationNormalizer`](file:///c:/Users/ajaya/Desktop/NLP/src/episense/taxonomy/location_normalizer.py):
$$S_{\text{spatial}} = \begin{cases}
1.00 & \text{Facility / Hospital / Village level} \\
0.80 & \text{Subdistrict / Taluk / Tehsil level} \\
0.60 & \text{District level} \\
0.40 & \text{State level} \\
0.20 & \text{National / Supranational level}
\end{cases}$$

---

## 4. Hard Safeguards and Alert Tiers

To prevent false alarms and ungrounded high alerts, four hard constraints are enforced in [`AlertScorer.score_signal()`](file:///c:/Users/ajaya/Desktop/NLP/src/episense/scoring/scorer.py#L90-L160):

1. **Non-Communicable Disease (NCD) Rule**: If the mention is classified as an NCD (e.g. hypertension, myocardial infarction), $S_{\text{final}} = 0.00$, tier = `informational`, action = `DISCARD`.
2. **Negation Rule**: If the assertion is `negated`, $S_{\text{final}} = 0.00$, tier = `informational`, action = `DISCARD`.
3. **High-Alert Corroboration Gate**: An alert can achieve the `high` alert tier **if and only if**:
   $$S_{\text{composite}} \ge 0.80 \quad \mathbf{AND} \quad |\text{Independent Publisher Groups}| \ge 2 \quad \mathbf{AND} \quad \neg \text{is\_gated}$$
   Single-source reports and gated baseline signals are mathematically capped at `medium` or `low`.
4. **Alert Tier Mapping**:
   $$\text{Tier} = \begin{cases}
   \text{HIGH} & S_{\text{composite}} \ge 0.80 \text{ and Corroborated } (\ge 2 \text{ sources}) \text{ and Ungated} \\
   \text{MEDIUM} & S_{\text{composite}} \ge 0.65 \\
   \text{LOW} & S_{\text{composite}} \ge 0.40 \\
   \text{INFORMATIONAL} & S_{\text{composite}} < 0.40 \text{ or Gated}
   \end{cases}$$

---

## 5. Operational Action Mapping

Each alert is assigned a standardized [`RecommendedReviewAction`](file:///c:/Users/ajaya/Desktop/NLP/src/episense/schemas/alert.py):

| Recommended Action | Triggering Conditions | Required Public Health Action |
| :--- | :--- | :--- |
| **`INVESTIGATE`** | `HIGH` alert tier OR Tier 4 pathogen (Nipah, CCHF) with confirmed status. | Immediate manual triage by epidemiologist; notify District Surveillance Officer (DSO). |
| **`MONITOR`** | `LOW` or `MEDIUM` alert tier with active community transmission. | Add to active surveillance watchlist; track spatial-temporal progression across adjacent weeks. |
| **`INFORMATIONAL`** | Baseline-gated records ($N < 3$), routine endemic conditions, or mild syndromes. | Logged in background repository for passive retrospective query; no immediate operational action. |
| **`DISCARD`** | Negated assertions, historical retrospectives, or non-communicable mentions. | Archived with zero priority; suppressed from active operational dashboards. |

---

## 6. Sensitivity Analysis Across 436 Active Surveillance Alerts

To prove that alert prioritization is not brittle or overfitted to arbitrary heuristic weights, an empirical sensitivity audit was conducted across all 436 active alerts in [`data/surveillance_store.sqlite`](file:///c:/Users/ajaya/Desktop/NLP/data/surveillance_store.sqlite) using [`scratch/scoring_sensitivity_analysis.py`](file:///c:/Users/ajaya/Desktop/NLP/scratch/scoring_sensitivity_analysis.py).

Five diverse weight perturbation regimes were evaluated:
1. **Default Baseline**: $w = [0.30, 0.25, 0.20, 0.15, 0.10]$
2. **Threat Heavy**: $w = [0.20, 0.35, 0.20, 0.15, 0.10]$ (Biosecurity / CFR focus)
3. **Anomaly Heavy**: $w = [0.40, 0.20, 0.15, 0.15, 0.10]$ (Statistical outbreak focus)
4. **Evidence Heavy**: $w = [0.25, 0.20, 0.30, 0.15, 0.10]$ (Multi-source corroboration focus)
5. **Equal Weights**: $w = [0.20, 0.20, 0.20, 0.20, 0.20]$ (Unweighted multi-criteria baseline)
6. **Spatial Relaxed**: $w = [0.35, 0.25, 0.25, 0.15, 0.00]$ (No penalty for regional resolution)

### Sensitivity Results

| Configuration | Weight Vector $[w_{\text{anom}}, w_{\text{threat}}, w_{\text{evid}}, w_{\text{cert}}, w_{\text{spat}}]$ | Spearman Rank Correlation ($\rho$) | Alert Tier Agreement | Top-10 Rank Overlap |
| :--- | :---: | :---: | :---: | :---: |
| **Default Baseline** | $[0.30, 0.25, 0.20, 0.15, 0.10]$ | $1.0000$ | $100.00\%$ | $10/10$ ($100\%$) |
| **Threat Heavy** | $[0.20, 0.35, 0.20, 0.15, 0.10]$ | $\mathbf{0.9877}$ | $90.83\%$ | $10/10$ ($100\%$) |
| **Anomaly Heavy** | $[0.40, 0.20, 0.15, 0.15, 0.10]$ | $\mathbf{0.9956}$ | $84.40\%$ | $10/10$ ($100\%$) |
| **Evidence Heavy** | $[0.25, 0.20, 0.30, 0.15, 0.10]$ | $\mathbf{0.9981}$ | $96.33\%$ | $10/10$ ($100\%$) |
| **Equal Weights** | $[0.20, 0.20, 0.20, 0.20, 0.20]$ | $\mathbf{0.9749}$ | $75.69\%$ | $9/10$ ($90\%$) |
| **Spatial Relaxed** | $[0.35, 0.25, 0.25, 0.15, 0.00]$ | $\mathbf{0.9789}$ | $95.18\%$ | $10/10$ ($100\%$) |

### Interpretation of Sensitivity Findings
1. **Rank Order Invariance ($\rho \ge 0.9749$)**: The rank ordering of prioritized alerts is extraordinarily stable across all configurations. An alert ranked in the top triage queue under the baseline remains in the top queue regardless of weight shifts.
2. **Top-10 Priority Stability**: 9 to 10 out of the top 10 most urgent incidents remain strictly identical across all regimes.
3. **Safe Fall-Out**: Because the high-alert corroboration safeguard and negation suppression operate upstream as hard constraints, parameter variations never promote ungrounded noise or negated mentions into high alerts.
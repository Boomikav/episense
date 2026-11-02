# EpiSense Epidemiological Alert Scoring & Risk Assessment Engine — Architectural Specification

**Document Version:** 1.0.0  
**Phase:** Phase 9 (Epidemiological Alert Scoring & Risk Assessment Engine)  
**Status:** IMPLEMENTED & VERIFIED  
**Target Scope:** Multi-Criteria Risk Scoring, Pathogen Clinical Threat Classification, Data-Reliability Safety Ceilings, Explainability Audit Dossiers, and Deterministic Public Health Alert Prioritization  

---

## 1. Architectural Philosophy & Objectives

In Phase 8, the Statistical Baselines & Early Signal Detection Engine transformed canonical `FusedEvent` streams into weekly time-series bins and detected statistical aberrations (`SignalObservation`).

However, **a statistical aberration is not an epidemiological risk assessment**:
* A statistical spike ($Z = 2.5$) in an endemic, self-limiting condition like seasonal viral fever or common cold carries vastly different public health implications than 2 suspected cases of an extremely lethal pathogen like Nipah virus, Marburg virus, or Avian Influenza.
* Uncorroborated reports from single open-source news blogs must not trigger emergency alerts without verification.
* Conflicting numerical reports (`CONFLICTING_DATA`) or ungrounded short historical series (`INSUFFICIENT_HISTORY`) must not manufacture artificial statistical confidence.
* Public health teams cannot triage hundreds of raw statistical deviations; they require a multi-criteria composite risk score that ranks events into calibrated operational tiers (`INFORMATIONAL`, `LOW`, `MEDIUM`, `HIGH`) with complete audit trails.
* **Core Public Health Invariant:** An epidemiological alert represents an operational triage prioritization for human review, **never** an automated clinical diagnosis or official outbreak declaration.

Phase 9 introduces the **Epidemiological Alert Scoring & Risk Assessment Engine**. It synthesizes Phase 8 statistical signals, Phase 7 fused event characteristics, pathogen clinical severity, and source diversity into explainable, provenance-preserving risk assessments (`EpidemiologicalAlert`).

```text
Phase 8 SignalObservation + Phase 7 FusedEvents + Phase 8 TimeBins
                          ↓
              Multi-Criteria Risk Scorer (src/episense/scoring/scorer.py)
  ├── Statistical Anomaly Deviation & Consensus (S_anomaly)
  ├── Pathogen Clinical Consequence Tiering (S_threat: Tier 1 to 4)
  ├── Source Independence & Authority Corroboration (S_evidence)
  ├── Clinical Assertion & Mortality Confirmation (S_certainty)
  └── Geospatial Locus & Granularity (S_spatial)
                          ↓
              Reliability-Aware Safety Gating & Ceilings
  ├── Negated Mention Suppression -> Tier: INFORMATIONAL (Score: 0.0)
  ├── Conflicting Quantities Across Sources -> Penalty (-0.10) & Cap at MEDIUM (0.79)
  ├── Insufficient Historical Baseline (N < 3) -> Cap at LOW (0.64) or MEDIUM (0.79)
  └── Single-Source Isolation -> Cap at MEDIUM (0.79, cannot reach HIGH)
                          ↓
              Explainability Generator (src/episense/scoring/explainer.py)
  ├── Dimension score breakdown (weights, raw composite, penalties, final score)
  ├── Ordered key driving risk factors
  ├── Structured gating rationale
  └── Full provenance graph (alert -> signal -> fused events -> evidence spans)
                          ↓
            Deterministic EpidemiologicalAlert Records
       (UUID5 IDs, Created At anchored to period_end, AlertTier assigned)
```

---

## 2. Core Domain Schemas (`src/episense/schemas/alert.py`)

Phase 9 defines strongly typed Pydantic models for alert scoring:

| Schema / Enum | Role | Definition & Values |
| :--- | :--- | :--- |
| `AlertTier` | Operational public health triage tier. | `INFORMATIONAL` ($[0.0, 0.40)$), `LOW` ($[0.40, 0.65)$), `MEDIUM` ($[0.65, 0.80)$), `HIGH` ($[0.80, 1.00]$). |
| `PathogenThreatTier`| Inherent clinical consequence tier. | `TIER_1_MILD` ($0.25$), `TIER_2_MODERATE` ($0.50$), `TIER_3_SEVERE` ($0.75$), `TIER_4_HIGH_CONSEQUENCE` ($1.00$). |
| `RiskScoreBreakdown`| Granular dimensional score audit. | `anomaly_score`, `threat_score`, `evidence_score`, `certainty_score`, `spatial_score`, `raw_composite_score`, `penalty_applied`, `final_score`, `applied_weights`. |
| `AlertExplanation` | Human-readable audit narrative. | `summary`, `driving_factors`, `gating_rationale`, `detailed_narrative`. |
| `EpidemiologicalAlert` | Canonical prioritized alert entity. | `alert_id` (UUID5), `signal_id`, `disease_key`, `geo_key`, `pathogen_threat_tier`, `period_start`, `period_end`, `composite_score`, `alert_tier`, `is_gated`, `gating_reason`, `score_breakdown`, `explanation`, `supporting_fused_event_ids`, `supporting_source_count`, `provenance_references`, `created_at`. |

---

## 3. Five-Dimensional Risk Scoring Methodology

Phase 9 evaluates five distinct epidemiological dimensions, each normalized to $[0.0, 1.0]$:

### 1. Statistical Anomaly Score ($S_{\text{anomaly}} \in [0.0, 1.0]$)
Measures the magnitude and consensus of statistical deviation from Phase 8:
* If `signal_level == NO_SIGNAL`: $S_{\text{anomaly}} = 0.0$.
* Scaled deviation based on standardized $Z$-score:
  $$S_Z = \min\left(1.0, \max\left(0.0, \frac{Z - 1.0}{3.0}\right)\right)$$
* Multi-detector boost: $+0.15$ bonus if multi-detector consensus was achieved (`DetectionMethod.MULTI_DETECTOR`).
* Bounded by Phase 8 signal level:
  - `STRONG_SIGNAL`: $S_{\text{anomaly}} \ge 0.85$
  - `SIGNAL`: $S_{\text{anomaly}} \ge 0.65$
  - `WATCH`: $0.25 \le S_{\text{anomaly}} \le 0.60$

### 2. Pathogen Clinical Threat Score ($S_{\text{threat}} \in [0.0, 1.0]$)
Classified deterministically via `PathogenThreatClassifier`:
* **Tier 4 ($1.00$ - High Consequence / Extreme CFR / Emerging Zoonotic):**
  Nipah virus, Marburg virus, Ebola, Avian Influenza (H5N1), Chandipura virus, MERS-CoV, Yellow Fever, CCHF.
* **Tier 3 ($0.75$ - Severe Epidemic / High Morbidity-Mortality):**
  Cholera, Kyasanur Forest Disease (KFD), Rabies, Japanese Encephalitis, Leptospirosis, Meningococcal disease, Anthrax, Plague.
* **Tier 2 ($0.50$ - Endemic Outbreak-Prone / Vector-Borne):**
  Dengue, Malaria, Chikungunya, Scrub Typhus, Measles, Zika, Mpox, Typhoid fever, Hepatitis A/E.
* **Tier 1 ($0.25$ - Mild / Syndromic / Generic Endemic):**
  Generic "disease/illness", "infection", viral fever, respiratory syncytial virus (RSV), gastroenteritis.

### 3. Source Evidence & Diversity Score ($S_{\text{evidence}} \in [0.0, 1.0]$)
Evaluates independent verification and reporting authority:
* Base score by independent source count $N_{\text{sources}}$:
  - $N_{\text{sources}} = 1$: $0.35$ (isolated report; cannot reach high certainty alone)
  - $N_{\text{sources}} = 2$: $0.70$ (independently corroborated)
  - $N_{\text{sources}} \ge 3$: $1.00$ (strong multi-source consensus)
* Official Agency Authority Boost: $+0.15$ boost (capped at $1.0$) if any source represents an official public health agency (e.g. PIB MOHFW, WHO, CDC, state IDSP).

### 4. Clinical Certainty & Mortality Score ($S_{\text{certainty}} \in [0.0, 1.0]$)
Reflects diagnostic assertion and severity:
* Assertion Status:
  - `CONFIRMED`: $1.00$ (laboratory or agency confirmed)
  - `SUSPECTED`: $0.70$ (clinical presentation pending lab confirmation)
  - `HISTORICAL`: $0.20$ (retrospective surveillance)
  - `NEGATED`: $0.00$ (ruled out)
* Mortality Boost: $+0.20$ boost (capped at $1.0$) if verified fatalities are reported.

### 5. Geospatial Granularity Score ($S_{\text{spatial}} \in [0.0, 1.0]$)
Evaluates spatial focus and actionable administrative resolution:
* District / City / Sub-district (Admin 2–4, actionable local locus): $1.00$
* State / Province (Admin 1): $0.75$
* Country / National (Admin 0): $0.50$
* Unspecified / Global: $0.30$

---

## 4. Mathematical Composite Formula & Safety Ceilings

### Composite Formula
$$\text{RawComposite} = w_{\text{anomaly}} S_{\text{anomaly}} + w_{\text{threat}} S_{\text{threat}} + w_{\text{evidence}} S_{\text{evidence}} + w_{\text{certainty}} S_{\text{certainty}} + w_{\text{spatial}} S_{\text{spatial}}$$

Default calibrated weights (configured via `ScoringConfig`):
$$w_{\text{anomaly}} = 0.30, \quad w_{\text{threat}} = 0.25, \quad w_{\text{evidence}} = 0.20, \quad w_{\text{certainty}} = 0.15, \quad w_{\text{spatial}} = 0.10$$
*(Sum strictly equals $1.00$)*.

### Reliability-Aware Safety Ceilings
1. **Explicit Negation Suppression:**
   If all underlying events are marked `AssertionStatus.NEGATED`:
   $$\text{FinalScore} = 0.0, \quad \text{AlertTier} = \text{INFORMATIONAL}$$
2. **Conflicting Data Penalty & Ceiling:**
   If target period contains conflicting quantity reports (`CONFLICTING_DATA` or `has_conflicts=True`):
   $$\text{Penalty} = 0.10, \quad \text{CandidateScore} = \max(0.0, \text{RawComposite} - 0.10)$$
   $$\text{FinalScore} = \min(\text{CandidateScore}, 0.79) \quad (\text{Strictly capped at MEDIUM})$$
3. **Insufficient Baseline History Ceiling:**
   If the historical baseline has $< 3$ historical weeks (`INSUFFICIENT_HISTORY`):
   - Tier 4 High-Consequence pathogen with $\ge 2$ independent sources: Capped at $0.79$ (`MEDIUM`).
   - All other conditions: Capped at $0.64$ (`LOW`).
4. **Single-Source Isolation Ceiling:**
   If reported by only a single source group ($N_{\text{sources}} = 1$):
   $$\text{FinalScore} = \min(\text{FinalScore}, 0.79) \quad (\text{Strictly barred from HIGH})$$

---

## 5. Operational Alert Tiers & Actionability

| Alert Tier | Final Score Range | Public Health Operational Meaning | Recommended Action |
| :--- | :--- | :--- | :--- |
| `INFORMATIONAL` | $[0.00, 0.40)$ | Routine surveillance, background noise, or negated events. | Log in background database; no alert raised. |
| `LOW` | $[0.40, 0.65)$ | Mild statistical elevation or uncorroborated single-source report for endemic disease. | Scheduled routine monitoring; review during weekly report. |
| `MEDIUM` | $[0.65, 0.80)$ | Corroborated notable aberration or unconfirmed report of high-threat pathogen. | Active verification; assign epidemiologist for 24-hour review. |
| `HIGH` | $[0.80, 1.00]$ | Multi-source corroborated aberration of high-consequence pathogen on stable baseline. | Immediate emergency triage; cross-agency verification and rapid response. |

---

## 6. Explainability Audit Dossier & Provenance Preservation

Every `EpidemiologicalAlert` compiles an `AlertExplanation` consisting of:
1. **Executive Summary:** One-sentence overview of alert level, pathogen, location, score, and observed vs expected counts.
2. **Driving Factors:** Ranked list of the primary factors contributing to the score (threat tier, anomaly $Z$-score, source count, mortality confirmation, spatial locus).
3. **Gating Rationale:** Transparent explanation of all applied penalties and ceilings (e.g. *"Conflicting quantity reports detected across sources: -0.10 penalty applied; alert capped at MEDIUM"*).
4. **Detailed Narrative Audit Trail:** Complete structured audit dossier documenting dimension scores, applied weights, and data-quality checks.
5. **Full Provenance Preservation:** Every alert preserves pointers to:
   - Associated Phase 8 `signal_id`.
   - Associated Phase 7 `supporting_fused_event_ids`.
   - Underlying raw document character spans in `EvidenceReference` (`[start_char:end_char]`, attribute role, extraction method).

---

## 7. Determinism & Serialization Invariants

* **Deterministic UUID5 Identifiers:**
  ```python
  seed = f"{disease_key}:{geo_key}:{period_start.isoformat()}:{signal_id}:alert"
  alert_id = uuid5(NAMESPACE_DNS, seed)
  ```
* **Deterministic Timestamp:** `created_at` is anchored to `period_end` rather than variable system clocks.
* **Deterministic Sorting:** Alerts are sorted in strict priority order:
  $$\text{key} = (-\text{composite\_score}, -\text{period\_start.timestamp}(), \text{disease\_key}, \text{geo\_key})$$
* **Reproducibility:** Two independent executions over identical Phase 8 outputs produce 100% byte-for-byte identical output files (`alerts.json` and `alert_summary.json`).

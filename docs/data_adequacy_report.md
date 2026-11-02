# EpiSense Data Adequacy and Historical Baseline Report

**Project**: EpiSense Surveillance Intelligence System  
**Evaluation Standard**: Public Health Informatics & Epidemiological Validity  
**Authoritative Acceptance Decision**: `IMPLEMENTED PROTOTYPE — ADDITIONAL VALIDATION REQUIRED`  
**Date**: October 24, 2026  
**Canonical Inventory**: [`canonical_data_inventory.json`](file:///c:/Users/ajaya/Desktop/NLP/data/benchmarks/canonical_data_inventory.json)

---

## 1. Executive Summary & Epidemiological Baseline Reality

A foundational critique raised during faculty evaluation was that the historical dataset contained too few documents to support longitudinal statistical anomaly detection, and that live signals were being compared against an inadequate baseline.

This audit report establishes the precise empirical reality of the surveillance database ([`data/surveillance_store.sqlite`](file:///c:/Users/ajaya/Desktop/NLP/data/surveillance_store.sqlite)), clarifies the distinction between cross-sectional and longitudinal data structures, and documents how EpiSense's safeguards prevent spurious alerts.

### Key Epidemiological Findings

1. **Cross-Sectional vs. Longitudinal Structure**:
   The 113 historical documents ingested from the Integrated Disease Surveillance Programme (IDSP) originate from **a single epidemiological bulletin representing Week 1 of 2026 (`2026-W01`)**. This bulletin contains cross-sectional reports across 29 administrative districts. It does **not** represent 29 consecutive longitudinal weeks.
2. **Longitudinal Sample Size ($N=1$)**:
   Because each district-pathogen pair appears at most once in this single bulletin, the historical series length is $N=1$. Under standard surveillance biostatistics (CDC EARS C1/C2/C3, Farrington algorithm), reliable estimation of expected counts ($\mu_t$) and variance ($\sigma_t^2$ or overdispersion $\phi$) requires a minimum historical baseline of $N \ge 3$ (and ideally $N \ge 7$ to $N \ge 156$ for multi-year seasonal models).
3. **Automated Safety Gating**:
   Rather than manufacturing false statistical confidence, EpiSense's [`BaselineReliabilityTracker`](file:///c:/Users/ajaya/Desktop/NLP/src/episense/baseline/reliability.py) automatically identifies that $N=1 < 3$ and designates 100% of historical signals as `INSUFFICIENT_HISTORY`. As a result, statistical anomaly detection is safely suppressed, and alerts default to informational triage priority based solely on narrative threat characteristics and verified lab confirmation.

---

## 2. Comprehensive Database Telemetry & Inventory

Direct census executed against the active SQLite persistence store ([`data/surveillance_store.sqlite`](file:///c:/Users/ajaya/Desktop/NLP/data/surveillance_store.sqlite)):

| Entity Layer | Total Census | Breakdown / Status | Epidemiological Role |
| :--- | :---: | :--- | :--- |
| **Ingested Documents** | **216** | 113 `HISTORICAL_CORPUS`<br>103 `LIVE_EXTERNAL` | Raw unstructured reports, dispatches, and weekly bulletin entries |
| **Candidate Mentions** | **598** | Extracted via deterministic NLP pipeline (`en_core_sci_sm`) | Raw entity and assertion tuples prior to deduplication |
| **Fused Events** | **486** | 460 active, 26 superseded<br>(415 historical, 45 live) | Deduplicated canonical outbreak incidents clustered across documents |
| **Corroboration Status** | **486** | 2 multi-source corroborated<br>484 single source group | Tracks publisher independence to stop syndicate wire duplicates |
| **Epidemiological Bins** | **177** | 16 numerical ($\ge 1$ verified cases)<br>161 zero or unquantified | Disease-geography-time weekly aggregate bins |
| **Early Warning Signals** | **452** | 452 gated (`INSUFFICIENT_HISTORY`)<br>0 ungated reliable | Statistical aberration signals evaluated via EARS / Farrington |
| **Operational Alerts** | **460** | 436 active, 24 superseded<br>(395 historical, 41 live) | Prioritized triage alerts for human public-health review |
| **Alert Tiers (Active)** | **436** | 227 Informational, 206 Low,<br>3 Medium, 0 High | 0 ungrounded high alerts generated; safety safeguards active |

---

## 3. Dissecting the Historical Dataset

### 3.1 Source Provenance
- **Source**: Integrated Disease Surveillance Programme (IDSP), National Centre for Disease Control (NCDC), Directorate General of Health Services, Ministry of Health and Family Welfare, Government of India.
- **Document Title**: *Weekly Outbreak Bulletin — Week 1, 2026 (Ending 4th January 2026)*.
- **Coverage**: 29 administrative districts across Indian States (including Kerala, Gujarat, West Bengal, Maharashtra, Tamil Nadu, and Assam).
- **Structure**: Tabular records containing State, District, Disease/Illness, Cases, Deaths, Date of Start, and Control Status.

### 3.2 The Single-Week Constraint Explained
In early project iterations, the 113 records were casually described as "historical data", leading to the misconception that EpiSense had 113 historical time points for longitudinal trend analysis. 

The audit confirms:
$$\text{Longitudinal Time Horizon} = 1 \text{ week } (2026\text{-W}01)$$
$$\text{Spatial Units} = 29 \text{ districts}$$
$$\text{Total District-Disease Outbreak Entries} = 113$$

Because all 113 entries occur within the exact same ISO calendar week, **there is zero historical longitudinal depth**. One cannot compute a 7-week moving average (EARS C1), a 2-week guard band (EARS C2), or seasonal regression (Farrington) across multiple weeks from a single weekly bulletin.

### 3.3 The Gating Mechanism in Action
When `SignalDetector.detect_anomalies()` processes a historical bin, it passes the historical stream to `BaselineReliabilityTracker.evaluate_reliability()`:
```python
if len(historical_bins) < self.min_sample_size:  # min_sample_size = 3
    return BaselineReliability.INSUFFICIENT_HISTORY, (
        f"Insufficient historical data: {len(historical_bins)} historical bins available "
        f"(minimum required is {self.min_sample_size})"
    )
```
Because `len(historical_bins) == 1`, the signal is tagged:
- `is_gated = True`
- `gating_reason = "INSUFFICIENT_HISTORY: Insufficient historical data: 1 historical bins available (minimum required is 3)"`
- `downgrade_factor = 0.50` applied to anomaly component.

This demonstrates that EpiSense **does not hallucinate historical trends** or pretend that cross-sectional records are longitudinal time series.

---

## 4. Live Data Pipeline & Ingestion Sources

EpiSense ingests live, streaming, heterogeneous health information to support Event-Based Surveillance (EBS):

1. **Promed-mail RSS Dispatches**: International Society for Infectious Diseases (ISID) moderated posts covering emerging zoonoses, undiagnosed fevers, and vector-borne outbreaks.
2. **WHO Disease Outbreak News (DON)**: Official global health emergency reports.
3. **MoHFW Press Information Bureau (PIB)**: Press releases and seasonal advisories from the Union Health Ministry.
4. **State Health Bulletins**: Surveillance bulletins from state health directorates (Kerala DHS, Gujarat HFW, Bengal Health).

### Live vs. Historical Event Reconciliation
- Live reports are processed through the exact same NLP extraction pipeline as historical records.
- When a live report arrives, `EventCandidateBuilder` extracts entities, assertions, and spatiotemporal anchors.
- `EventFusionEngine` compares the new candidate against all active fused events within a configurable temporal window ($\pm 7$ days).
- If the pathogen matches (via taxonomy key), the location matches (via normalized administrative hierarchy), and the time window overlaps, the report is fused into the existing incident rather than generating a duplicate alert.
- If the report originates from a new publisher domain outside the existing source group, `independent_source_count` increments, elevating the event's corroboration status.

---

## 5. Benchmark Corpora & Annotation Assets

To support reproducible evaluation without gold-standard leakage, datasets are segregated into distinct assets:

| Corpus Asset | Path | Size | Status / Role |
| :--- | :--- | :---: | :--- |
| **Reference Gold Standard** | [`data/benchmarks/annotations/gold_standard_v2.json`](file:///c:/Users/ajaya/Desktop/NLP/data/benchmarks/annotations/gold_standard_v2.json) | 18 docs (96 spans) | Dev benchmark for NLP extraction recall and precision tuning |
| **Frozen Blind Candidate Pool** | [`data/gold_standard/eval_frozen_128/`](file:///c:/Users/ajaya/Desktop/NLP/data/gold_standard/eval_frozen_128/) | 128 documents | Frozen, deduplicated candidate pool awaiting independent double-annotation |
| **Blind Provenance Manifest** | [`data/benchmarks/blind_evaluation_manifest_v1.json`](file:///c:/Users/ajaya/Desktop/NLP/data/benchmarks/blind_evaluation_manifest_v1.json) | 128 records | Detailed source provenance, publication timestamps, and SHA-256 hashes |
| **Adversarial Event Benchmark** | [`data/benchmarks/event_benchmark/event_ground_truth_v2_adversarial.json`](file:///c:/Users/ajaya/Desktop/NLP/data/benchmarks/event_benchmark/event_ground_truth_v2_adversarial.json) | 24 scenarios | 7 Outbreaks, 15 Controls, 2 Duplicates for end-to-end evaluation |

---

## 6. Scientific Roadmap for Complete Data Adequacy

To advance EpiSense from `IMPLEMENTED PROTOTYPE — ADDITIONAL VALIDATION REQUIRED` to full clinical/epidemiological acceptance, the following data acquisition roadmap is required:

1. **Multi-Year Longitudinal Ingestion**:
   - Ingest 52 consecutive weekly IDSP outbreak bulletins across 5 full years (260 longitudinal weeks).
   - This provides sufficient depth to ungate EARS C1/C2/C3 ($N \ge 7$) and train seasonal Farrington GLMs ($N \ge 156$ with 3-year baseline).
2. **Double-Blind Human Annotation**:
   - Complete independent human double-annotation of the 128 frozen documents in [`data/gold_standard/eval_frozen_128/`](file:///c:/Users/ajaya/Desktop/NLP/data/gold_standard/eval_frozen_128/) with trained epidemiologists calculating Inter-Annotator Agreement (Cohen's $\kappa$).
3. **Calibrated Outcome Registry**:
   - Partner with state surveillance units to link historical alerts to verified field-investigation outcomes (Rapid Response Team deployment logs) to train and calibrate a true probabilistic outbreak model.
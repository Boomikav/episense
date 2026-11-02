# EpiSense Statistical Baselines & Early Signal Detection Engine — Architectural Specification

**Document Version:** 1.0.0  
**Phase:** Phase 8 (Statistical Baselines & Early Signal Detection Engine)  
**Status:** IMPLEMENTED & VERIFIED  
**Target Scope:** Deterministic Epidemiological Time-Bin Aggregation, Historical Baseline Modeling, Statistical Aberration Detection (EARS C1/C2/C3 & Bounded Farrington), and Explainable Early-Warning Signal Generation  

---

## 1. Architectural Philosophy & Objectives

EpiSense is an explainable early epidemic intelligence framework for public health surveillance from open-source text. In Phase 7, the Event Fusion Engine synthesized multi-source NLP extractions into canonical, deduplicated `FusedEvent` entities.

However, raw event counts alone do not constitute public health intelligence:
* An event report of *10 dengue cases in week 36* may represent expected seasonal endemicity in an endemic state, whereas *2 cases of Nipah virus in an unexpected district* constitutes an urgent anomaly.
* Simple threshold alerts (e.g. fixed count > 5) produce intolerable false-positive rates during high-transmission seasons and severe false negatives during low-transmission periods.
* In media-based surveillance, bursts of redundant syndicated reporting can create illusory spikes if baselines operate directly on document counts rather than deduplicated epidemiological events.
* Crucially, a statistical aberration is **never** a confirmed outbreak; it is an early-warning signal that warrants public health verification and epidemiological triage.

Phase 8 introduces the **Statistical Baselines & Early Signal Detection Engine**. It aggregates canonical `FusedEvent` records into structured weekly time-series bins, estimates rolling historical baselines with rigorous reliability gating, evaluates statistical aberrations using established public health surveillance algorithms (CDC EARS and bounded Farrington-style quasi-Poisson models), and emits deterministic, explainable `SignalObservation` alerts backed by full character-level provenance.

```text
Canonical FusedEvents (Phase 7 Output: Deduplicated, Provenance-Preserving)
        ↓
TimeSeriesBuilder (src/episense/baseline/timeseries.py)
  ├── Input deduplication (seen_fused_ids)
  ├── Assertion status filtering (excludes NEGATED and generic HISTORICAL from positive incidence)
  ├── ISO epidemiological week aggregation (Monday 00:00 to Sunday 23:59 UTC)
  ├── Spatio-temporal stratification (disease_key × geo_key)
  └── Anti-inflation quantity synthesis (preserves conflicts & source independence)
        ↓
EpidemiologicalTimeBins (Deterministic UUID5 IDs, Evidence References)
        ↓
BaselineEngine & BaselineReliabilityTracker (src/episense/baseline/)
  ├── Rolling historical window selection (preceding chronological bins)
  ├── Summary statistics (Mean, Median, Sample Variance N-1, Std Dev, Dispersion)
  └── Data reliability gating (INSUFFICIENT_HISTORY, SPARSE_HISTORY, HIGH_VARIANCE, STABLE_BASELINE)
        ↓
BaselineEstimate Records (Deterministic UUID5 IDs, bounds, reliability status)
        ↓
Anomaly Detectors (src/episense/anomaly/)
  ├── EARSDetector (C1 standard, C2 with 2-period guard band, C3 accumulated persistence)
  └── BoundedFarringtonDetector (Quasi-Poisson overdispersion, Anscombe 2/3 transform)
        ↓
SignalDetector (src/episense/anomaly/detector.py)
  ├── Multi-detector consensus evaluation
  ├── Safety downgrading (insufficient baseline, conflicting reports, single-source variance)
  ├── Signal severity assignment (NO_SIGNAL, WATCH, SIGNAL, STRONG_SIGNAL)
  └── Explainable rationale generation (7-point deterministic audit trail)
        ↓
SignalObservation Records (Deterministic UUID5 IDs, Provenance References)
```

---

## 2. Core Domain Schemas (`src/episense/schemas/signal.py`)

Phase 8 introduces strongly typed Pydantic models designed for epidemiological integrity and strict determinism:

| Schema / Enum | Role | Key Fields |
| :--- | :--- | :--- |
| `BaselineReliability` | Statistical validity state of historical data. | `INSUFFICIENT_HISTORY`, `SPARSE_HISTORY`, `HIGH_VARIANCE`, `CONFLICTING_DATA`, `STABLE_BASELINE` |
| `SignalLevel` | Hierarchical severity of early warning alert. | `NO_SIGNAL`, `WATCH`, `SIGNAL`, `STRONG_SIGNAL` |
| `DetectionMethod` | Statistical aberration detection method applied. | `EARS_C1`, `EARS_C2`, `EARS_C3`, `FARRINGTON_BOUNDED`, `MULTI_DETECTOR` |
| `EpidemiologicalTimeBin` | Spatio-temporal aggregation bin (ISO calendar week). | `bin_id`, `disease_key`, `geo_key`, `period_start`, `period_end`, `iso_year`, `iso_week`, `observed_case_count`, `observed_death_count`, `fused_event_count`, `independent_source_count`, `has_conflicts`, `conflicting_quantities`, `provenance_references` |
| `BaselineEstimate` | Expected epidemiological baseline for a target period. | `baseline_id`, `disease_key`, `geo_key`, `target_period_start`, `target_period_end`, `baseline_window_weeks`, `baseline_mean`, `baseline_median`, `baseline_std`, `baseline_variance`, `dispersion_metric`, `reliability_status`, `rationale` |
| `SignalObservation` | Structured, explainable early-warning signal. | `signal_id`, `disease_key`, `geo_key`, `target_period_start`, `target_period_end`, `observed_value`, `expected_value`, `deviation`, `standardized_score`, `threshold`, `detection_method`, `signal_level`, `reliability_status`, `is_downgraded`, `downgrade_reason`, `explainable_rationale`, `provenance_references` |

---

## 3. Time-Series Aggregation & Anti-Inflation

The `TimeSeriesBuilder` aggregates canonical `FusedEvent` entities into weekly surveillance bins under strict public health constraints:

1. **Input Deduplication:** Every input event is checked against `seen_fused_ids` to eliminate any accidental double-processing.
2. **Assertion Scoping:**
   - Mentions marked `AssertionStatus.NEGATED` (e.g. *"no cases detected"*) are barred from contributing to positive observed case/death counts.
   - Generic historical commentary marked `AssertionStatus.HISTORICAL` with estimated dates is segregated into a distinct historical reference bin (ISO year 1970) to prevent publication dates from polluting active contemporary surveillance weeks.
3. **Calendar Alignment:** Aggregates strictly to ISO calendar weeks (Monday 00:00:00.000000 UTC to Sunday 23:59:59.999999 UTC).
4. **Stratification:** Bins are segregated strictly by `(disease_key, geo_key)`. Unresolved or cross-national locations are categorized under `unspecified_or_global` to prevent spurious cross-regional merging.
5. **Anti-Inflation Preservation:** Observed cases and deaths are aggregated from Phase 7 canonical fused events, which already synthesized duplicate news syndications. Conflicting quantities across merged reports are preserved in `conflicting_quantities`.
6. **Deterministic UUID5 Identifiers:**
   ```python
   bin_seed = f"{disease_key}:{geo_key}:{iso_year}:{iso_week}:{'hist' if is_generic else 'obs'}"
   bin_id = uuid5(NAMESPACE_DNS, bin_seed)
   ```

---

## 4. Historical Baseline Engine & Reliability Gating

The `BaselineEngine` and `BaselineReliabilityTracker` compute rolling historical baselines over preceding chronological bins:

### Statistical Formulations
* **Sample Mean:** $\bar{x} = \frac{1}{N} \sum_{i=1}^N x_i$
* **Sample Median:** Midpoint of sorted historical values (interpolated average for even $N$).
* **Sample Variance (Bessel's correction):** $s^2 = \frac{1}{N-1} \sum_{i=1}^N (x_i - \bar{x})^2$ for $N > 1$ (and $0.0$ for $N \le 1$).
* **Sample Standard Deviation:** $s = \sqrt{s^2}$
* **Dispersion Metric (Variance-to-Mean Ratio):** $D = \frac{s^2}{\max(\bar{x}, \epsilon)}$ to identify Poisson overdispersion ($D > 1.0$).
* **Expected Bounds:** $[\max(0, \bar{x} - 2s), \bar{x} + 2s]$.

### Reliability States
Rather than blindly applying statistical tests to insufficient data, EpiSense categorizes baseline reliability:
1. `INSUFFICIENT_HISTORY`: Fewer than `min_sample_size` (default: 3) historical weeks available. No statistical confidence manufactured.
2. `SPARSE_HISTORY`: Historical weeks $\ge 3$, but fewer than 2 non-zero periods. Extreme zero-inflation.
3. `HIGH_VARIANCE`: Coefficient of variation $CV = \frac{s}{\bar{x}} > 1.5$. High volatility in historical reporting.
4. `CONFLICTING_DATA`: Unresolved conflicting quantities reported in the target period.
5. `STABLE_BASELINE`: Sufficient sample size, adequate non-zero reporting, bounded variance, and unconflicted target data.

---

## 5. Statistical Anomaly Detection Algorithms

EpiSense integrates two proven, complementary public health surveillance algorithms:

### 1. CDC Early Aberration Reporting System (EARS)
Implemented in `src/episense/anomaly/ears.py`:
* **EARS C1 (Mild Sensitivity, Baseline $t-7$ to $t-1$):**
  $$C_1(t) = \frac{Y(t) - \bar{Y}_{1}(t)}{S_1(t) + \epsilon}$$
  Evaluates the immediate 7-period historical window. Alert triggered when $C_1(t) \ge 2.0$.
* **EARS C2 (Medium Sensitivity, 2-Period Guard Band, Baseline $t-9$ to $t-3$):**
  $$C_2(t) = \frac{Y(t) - \bar{Y}_{2}(t)}{S_2(t) + \epsilon}$$
  Enforces a 2-period guard band between the baseline window and the target period. This prevents a budding outbreak in week $t-1$ from artificially inflating the baseline and masking the continuing outbreak at week $t$.
* **EARS C3 (High Sensitivity, Persistent Elevation Accumulation):**
  $$C_3(t) = \sum_{i=0}^2 \max\left(0, C_2(t-i) - 1\right)$$
  Accumulates excess standardized scores over three consecutive weeks, detecting insidious, slow-rising outbreaks that do not cross the single-week $C_1$ or $C_2$ threshold.

### 2. Bounded Farrington Surveillance Algorithm
Implemented in `src/episense/anomaly/farrington.py`:
* Developed for count data that violate standard Gaussian assumptions (overdispersed Poisson distributions common in infectious disease surveillance).
* **Quasi-Poisson Overdispersion Estimation:**
  $$\phi = \max\left(1.0, \frac{1}{N-1} \sum_{i=1}^N \frac{(y_i - \hat{\mu})^2}{\max(\hat{\mu}, \epsilon)}\right)$$
* **Anscombe 2/3 Power Transformation:**
  Transforms raw counts $y$ to normalize variance:
  $$y^* = y^{2/3}, \quad \mu^* = \hat{\mu}^{2/3}$$
  Standard error in transformed space:
  $$\sigma^* = \frac{2}{3} \hat{\mu}^{-1/3} \sqrt{\phi \cdot \hat{\mu}}$$
* **Threshold & Alert:**
  Upper bound calculated in transformed space and inverted back to count space:
  $$U^* = \mu^* + Z_{\alpha} \sigma^*, \quad \text{Threshold} = (U^*)^{3/2}$$
  Alert triggered if $Y(t) > \text{Threshold}$.
* **Insufficient Data Gate:** Strictly enforces $N \ge 3$; returns no alert when history is inadequate.

---

## 6. Signal Synthesis, Safety Downgrades & Explainability

The `SignalDetector` (`src/episense/anomaly/detector.py`) synthesizes multi-detector results into actionable, explainable signals:

### Classification Rules & Safety Downgrading
1. **`STRONG_SIGNAL`:** Multi-detector consensus ($\ge 2$ algorithms alert) **AND** `STABLE_BASELINE` **AND** $\ge 2$ independent reporting source groups.
2. **`SIGNAL`:** Statistical alert triggered ($C_1/C_2/C_3 \ge 2.0$ or Farrington alert or $Z \ge 2.0$) with a defensible baseline.
3. **Safety Downgrading to `WATCH`:**
   - If an alert triggers but baseline is `INSUFFICIENT_HISTORY`, it is automatically downgraded to `WATCH` (*"Downgraded due to insufficient historical baseline observations"*).
   - If target period contains `CONFLICTING_DATA`, it is downgraded to `WATCH` (*"Downgraded due to conflicting quantity reports"*).
   - If reported by only a single source group under `HIGH_VARIANCE`, it is downgraded to `WATCH`.
4. **`WATCH`:** Mild elevation ($1.5 \le Z < 2.0$ or newly emerging non-zero reports against zero baseline).
5. **`NO_SIGNAL`:** Normal expected baseline variation ($Z < 1.5$, no detector alerts).

### 7-Point Explainable Audit Trail
Every emitted `SignalObservation` includes a deterministic, human-readable rationale:
```text
1. Observed: 2.0 cases across 1 fused events (1 independent sources).
2. Expected: 1.00 cases (baseline median: 1.00, std: 0.00).
3. Deviation: +1.00 (Z-score: +1.00).
4. Detectors Triggered: ['ears_c1'].
5. Historical Support: 8 historical weeks (8 non-zero periods), status: stable_baseline.
6. Source Support: 1 independent source groups (1 total articles).
7. Classification: SIGNAL (Criterion satisfied under baseline parameters).
```

### Full Provenance Preservation
Every `SignalObservation` preserves pointers to:
- Contributing canonical `supporting_fused_event_ids`.
- Supporting independent source count.
- Underlying raw document `EvidenceReference` spans `[start_char:end_char]`, attribute roles, and extraction methods.

---

## 7. Determinism & Reproducibility Guarantees

Phase 8 enforces strict bit-for-bit determinism:
* **Stable UUID5 Generation:** All `bin_id`, `baseline_id`, and `signal_id` fields use namespace UUID5 hashes derived from deterministic strings (e.g. disease, location, ISO year/week).
* **Deterministic Timestamps:** The `created_at` field in `SignalObservation` is anchored to `target_bin.period_end` rather than non-deterministic system clock calls.
* **Deterministic Ordering:** Bins, series keys, and conflict lists are strictly sorted prior to processing and serialization.
* **Verification:** Tested and verified with 100% byte-for-byte identity across repeated batch executions.

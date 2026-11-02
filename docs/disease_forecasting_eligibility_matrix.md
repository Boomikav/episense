# EpiSense — Disease-by-Disease Surveillance and Forecasting Eligibility Matrix

## 1. Executive Overview and Scientific Purpose

Epidemiological surveillance systems frequently ingest diverse health intelligence ranging from real-time unstructured news reports and social alerts to institutional weekly outbreak bulletins and multi-decade disease registries. A recurring failure mode in automated surveillance pipelines is **methodological overreach**: attempting to fit complex statistical forecasting models (such as autoregressive count regressions, seasonal decompositions, or neural sequence models) to cross-sectional outbreak snapshots or fragmented surveillance snippets where the underlying assumptions of continuous time-series modeling are fundamentally violated.

This document establishes the official **Epidemiological Capability Matrix** and **Data Eligibility Boundaries** for the EpiSense surveillance platform across the eight priority monsoon and post-monsoon outbreak pathogens in India:
1. **Dengue** (*Flavivirus* / *Aedes aegypti*)
2. **Malaria** (*Plasmodium vivax* / *P. falciparum*)
3. **Chikungunya** (*Alphavirus* / *Aedes albopictus*)
4. **Leptospirosis** (*Leptospira interrogans*)
5. **Cholera** (*Vibrio cholerae* O1/O139)
6. **Acute Diarrhoeal Disease (ADD)** (Polymicrobial / Enteropathogenic)
7. **Japanese Encephalitis (JE)** (*Flavivirus* / *Culex tritaeniorhynchus*)
8. **Scrub Typhus** (*Orientia tsutsugamushi*)

EpiSense enforces a strict scientific boundary between four operational modalities:
- **Modality 1: Event-Based Surveillance (EBS)** — Unstructured text ingestion, biomedical NER, quantity/temporal/spatial extraction, assertion verification, and multi-source event fusion into 5W1H dossiers.
- **Modality 2: Historical Outbreak Analysis** — Cross-sectional investigation of discrete outbreak clusters from official weekly health bulletins (e.g., Integrated Disease Surveillance Programme - IDSP).
- **Modality 3: Numerical Anomaly Detection** — Statistical aberration detection using CDC EARS (C1/C2/C3 algorithms) and Farrington quasi-Poisson regression against moving baseline windows.
- **Modality 4: Quantitative Statistical Forecasting** — Multi-step predictive trajectory and prediction interval modeling using count-data models (Seasonal-Naive, Poisson GLM, Negative Binomial GLM, and Variance-Weighted Ensemble).

---

## 2. Mathematical Requirements by Forecasting Model

Quantitative forecasting models rely on distinct structural assumptions. Gating criteria must reflect the specific mathematical requirements of each model class rather than an arbitrary static threshold.

| Forecasting Model | Mathematical Formulation | Minimum History Requirement ($N$) | Underlying Statistical Assumptions | Failure Mode on Inadequate Data |
| :--- | :--- | :--- | :--- | :--- |
| **Seasonal Naive** | $\hat{y}_{t+h} = y_{t+h-s} + \epsilon_t$<br>where $s$ is the seasonal period (e.g., $s=52$ weeks or $s=12$ months) | **$N \ge 2 \times s$**<br>(Weekly monsoon cycle: $N \ge 104$ weeks;<br>Annual state cycle: $N \ge 3$ years) | Stationary seasonal cycle where the epidemic curve in year $k$ closely mimics year $k-1$. | Index out-of-bounds error or silent fallback to non-seasonal random walk if $N < s$. Inability to compute residual standard deviation $\sigma$. |
| **Poisson GLM** (Autoregressive Count) | $\log(\mu_t) = \beta_0 + \sum_{i=1}^p \beta_i \log(y_{t-i} + 1) + \gamma \cdot t$<br>$Y_t \sim \text{Poisson}(\mu_t)$ | **$N \ge p + 3$**<br>(Configured minimum in EpiSense: **$N \ge 12$** observations) | Equidispersion ($\mathbb{E}[Y] = \text{Var}(Y)$). Linear log-relationship between recent lags and expected count. Non-degenerate Hessian in penalized maximum likelihood estimation (L-BFGS-B). | Complete separation when counts are all zero; singular information matrix when $N$ is small; severe underestimation of prediction interval width under overdispersion (0% coverage on epidemic data). |
| **Negative Binomial GLM** (Overdispersed) | $\log(\mu_t) = \mathbf{x}_t^T \boldsymbol{\beta}$<br>$Y_t \sim \text{NB}(\mu_t, \alpha)$<br>$\text{Var}(Y_t) = \mu_t + \alpha \mu_t^2$ | **$N \ge p + 4$**<br>(Configured minimum in EpiSense: **$N \ge 12$** observations) | Overdispersion ($\text{Var}(Y) > \mathbb{E}[Y]$). Pearson residual moment estimation $\hat{\alpha} = \frac{\chi^2 / (N - p) - 1}{\bar{y}}$ must yield $\hat{\alpha} > 0$. Uses Poisson mean parameterization. | Dispersion parameter $\hat{\alpha} \le 0$ on small or underdispersed samples; method collapses to Poisson GLM. Parameter variance explodes when $N < 10$. |
| **Variance-Weighted Ensemble** | $\hat{y}_{\text{ens}, t+h} = \sum_{m} w_m \hat{y}_{m, t+h}$<br>$w_m$ fixed ($0.50$ NB, $0.30$ Poi, $0.20$ Naive) | Minimum requirement of all constituent models | Constituent models produce finite predictions. Shrinks extreme trend projections toward the persistence baseline. | Taking the outer envelope of prediction intervals produces excessively wide bounds ($\bar{W} \approx 55,815$ cases), yielding nominal 100% coverage with low tactical utility. |

---

## 3. The IDSP Bulletin Structure vs Longitudinal Time Series

A central finding of the EpiSense scientific audit is the **temporal structure distinction** between cross-sectional surveillance bulletins and continuous longitudinal registries:

### The Single-Week Bulletin Reality
The official IDSP weekly outbreak bulletin (`data/raw/bulletins/idsp_2026_w1.pdf`) contains **29 documented disease outbreak records**. 
Crucially:
- All 29 records originate from **Reporting Week 1 of 2026 (`2026-W01`)**.
- Each record corresponds to a distinct administrative district across 14 different Indian states (e.g., Alappuzha, Kozhikode, Wayanad in Kerala; Coimbatore, Chennai in Tamil Nadu; Pune in Maharashtra).
- It represents a **spatial cross-sectional snapshot**, NOT a 29-week longitudinal series.

### The Naive Prototype Fallacy
Earlier naive prototypes treated the 29 rows in the database table as 29 consecutive weekly observations ($t = 1, 2, \dots, 29$) for a single temporal series. This produced:
1. **False Continuity**: The model treated an outbreak in Alappuzha in row 1 as the temporal antecedent of an outbreak in Coimbatore in row 2.
2. **Manufactured Predictive Confidence**: The system generated multi-week future forecasts and narrow confidence intervals based on non-existent temporal momentum.
3. **Violated Epidemiological Validity**: An outbreak in district A during week 1 does not constitute a "baseline" for district B during week 1.

### EpiSense Architectural Safeguard
EpiSense's `DataSufficiencyProfiler` rigorously tracks `(iso_year, iso_week)` continuity per unique `(disease_key, geo_key)` series. When analyzing single-week bulletin extractions:
- `max_consecutive_weeks = 1`
- `data_structure_classification = CROSS_SECTIONAL_SNAPSHOTS`
- The `ForecastingEngine` and `DataSufficiencyProfiler` automatically assign:
  `capability_b_quantitative_forecasting = "NO-GO / SUPPRESSED_INSUFFICIENT_BASELINE (Consecutive weeks 1 < 12)"`
- Rather than rendering an ungrounded forecast, the dashboard renders an explicit audit warning explaining the suppression.

---

## 4. Comprehensive Disease-by-Disease Eligibility Matrix

The following matrix defines the operational eligibility of the eight target pathogens across all four surveillance modalities based on real-world Indian public health data availability.

| Disease | Primary Public Health Data Source in India | Available Longitudinal Structure | Modality 1: Event Surveillance (EBS) | Modality 2: Historical Outbreak Analysis | Modality 3: Anomaly Detection (EARS / Farrington) | Modality 4: Quantitative Statistical Forecasting | Operational Gating Status & Rationale |
| :--- | :--- | :--- | :---: | :---: | :---: | :---: | :--- |
| **Dengue** | OpenDengue V1.3 Global Database; National Centre for Vector Borne Diseases Control (NCVBDC); IDSP Bulletins; WHO SEARO | **Multi-year longitudinal series available**: State annual counts (1997–2024, $N=26$ observations with 2013–2014 hiatus) for 13 states; National monthly counts (2024–2025, $N=12$ months, Dec 2024 missing); Weekly outbreak bulletins. | **ELIGIBLE** (Full NLP pipeline, spatial-temporal geocoding, deduplication, triage) | **ELIGIBLE** (Cluster extraction, district mapping, fatality audits) | **ELIGIBLE** (On longitudinal series; requires $\ge 3$ baseline bins for EARS, $\ge 3$ seasonal cycles for Farrington) | **ELIGIBLE** (On OpenDengue longitudinal state annual/national monthly series; **SUPPRESSED** on isolated IDSP single-bulletin cross-sections) | **GO / CONDITIONAL GO**<br>Forecasting evaluated on multi-decade state annual series ($N=26$) for macro planning. Single-bulletin extractions suppressed. Prospective weekly warning remains future work. |
| **Malaria** | NCVBDC Annual Reports (1995–2024); World Malaria Report; IDSP Bulletins | State-level annual API/case counts available from NCVBDC; IDSP provides sporadic localized outbreak investigation reports. | **ELIGIBLE** | **ELIGIBLE** | **ELIGIBLE** (When coupled to historical NCVBDC annual registries) | **CONDITIONAL GO** (On state annual registries; **SUPPRESSED** on live bulletin stream due to $N < 12$) | **SUPPRESSED ON LIVE STREAM**<br>No continuous open weekly sub-district malaria registry in real-time feeds. Historical annual forecasting feasible. |
| **Chikungunya** | NCVBDC (2006–2024 State Annual Series); IDSP Weekly Bulletins | Annual state-level surveillance since 2006 re-emergence; periodic local outbreak clusters in IDSP. | **ELIGIBLE** | **ELIGIBLE** | **ELIGIBLE** (On annual state series) | **CONDITIONAL GO** (Annual series $N=18$; **SUPPRESSED** on live weekly bulletin extractions) | **SUPPRESSED ON LIVE STREAM**<br>Requires multi-year annual baseline. Live extractions yield $N \le 2$ consecutive weeks. |
| **Leptospirosis** | IDSP Weekly Outbreak Bulletins; State Surveillance Units (Kerala, Maharashtra, Gujarat, Tamil Nadu) | Sporadic post-flood seasonal outbreaks; localized hospital admissions series (usually non-public / fragmented). | **ELIGIBLE** | **ELIGIBLE** (High clinical relevance for post-monsoon flood clusters) | **NO-GO / CONDITIONAL** (Insufficient historical baseline in open repositories) | **NO-GO / SUPPRESSED** (Zero continuous multi-year longitudinal public series available) | **SUPPRESSED_INSUFFICIENT_BASELINE**<br>Highly effective under Event Surveillance and Outbreak Analysis; quantitative forecasting strictly suppressed to prevent scientific hallucination. |
| **Cholera** | IDSP Outbreak Bulletins; State Public Health Laboratories; Literature case series | Point-source outbreak clusters; institutional line-lists. No continuous national public weekly routine incidence series. | **ELIGIBLE** | **ELIGIBLE** (Attack rate, water contamination source attribution, 5W1H dossiers) | **NO-GO** (Point-source epidemics violate baseline stationarity) | **NO-GO / SUPPRESSED** (Baseline data absent; point-source outbreaks behave non-linearly) | **SUPPRESSED_INSUFFICIENT_BASELINE**<br>Outbreak investigations prioritized in EBS. Time-series forecasting mathematically inappropriate for episodic point-source events. |
| **Acute Diarrhoeal Disease (ADD)** | IDSP Weekly Outbreak Bulletins; State Health Directorate Portals | Weekly outbreak notifications during monsoon; syndicated institutional summaries. | **ELIGIBLE** | **ELIGIBLE** | **CONDITIONAL** (Seasonal monsoon threshold monitoring) | **NO-GO / SUPPRESSED** (Absence of open continuous district-level weekly series) | **SUPPRESSED_INSUFFICIENT_BASELINE**<br>EBS operational. Quantitative forecasting gated pending continuous syndromic time series. |
| **Japanese Encephalitis (JE)** | NCVBDC Vector Borne Disease Surveillance; IDSP Bulletins; AES Registry (Gorakhpur, Assam) | Annual state-level summaries; specialized hospital-based AES/JE registries. | **ELIGIBLE** | **ELIGIBLE** | **CONDITIONAL** (Annual state counts) | **CONDITIONAL GO** (Annual state series; **SUPPRESSED** on weekly stream) | **SUPPRESSED ON LIVE STREAM**<br>Live weekly feed provides sparse isolated mentions ($N < 3$). Event intelligence active. |
| **Scrub Typhus** | IDSP Weekly Bulletins; Regional Tertiary Care Hospital Reports (Shimla, Vellore, Gorakhpur) | Seasonal post-monsoon winter peaks; discrete cluster reports without unified national continuous weekly registry. | **ELIGIBLE** | **ELIGIBLE** | **NO-GO** | **NO-GO / SUPPRESSED** (Insufficient longitudinal time bins) | **SUPPRESSED_INSUFFICIENT_BASELINE**<br>Event-based early warning active. Forecasting gated with audit reason displayed. |

---

## 5. Summary of Longitudinal Data Sources & Reconciled Provenance

To eliminate the empirical validation gap without resorting to fabricated synthetic series, EpiSense integrates official, peer-reviewed, open-access longitudinal datasets:

1. **OpenDengue Database V1.3** (*Nature Scientific Data*, 2024; DOI: 10.1038/s41597-024-02996-0; CC-BY 4.0):
   - **Indian Spatial Extract**: 692 official government and literature dengue surveillance records.
   - **State-Level Annual Longitudinal Series**: $N = 26$ observations across 13 major Indian states (Delhi, Maharashtra, Kerala, Tamil Nadu, Karnataka, Rajasthan, Gujarat, Punjab, Uttar Pradesh, Andhra Pradesh, Haryana, Chandigarh, Goa).
     * *Hiatus Audit*: Years 2013 and 2014 are absent due to the source boundary between published literature (ending 2012) and the MoHFW/NCVBDC online portal (beginning 2015).
   - **National Monthly Longitudinal Series**: $N = 12$ monthly observations (January 2024 – January 2025) from WHO SEARO (`WHO-ALL-2025-Y01-00`).
     * *Monthly Audit*: December 2024 is missing in the primary source feed.
2. **Integrated Disease Surveillance Programme (IDSP) Official Bulletins**:
   - `idsp_2026_w1.pdf` (Week 1, 2026): 29 confirmed/investigated outbreak clusters across 14 states, demonstrating multi-source event extraction, geocoding, and automated triage.

---

## 6. Scientific Governance and Audit Policy

1. **Zero Silent Fallback**: The platform must never substitute a missing temporal baseline with fabricated zeros, interpolated trends, or synthetic observations without explicit user-facing provenance labels.
2. **Explicit Abstention over Erroneous Precision**: When $N < 12$ for autoregressive count models or $N < 2 \times s$ for seasonal naive models, EpiSense explicitly abstains from forecasting, returns `status: "SUPPRESSED_INSUFFICIENT_BASELINE"`, and communicates the exact deficit (e.g., `observed_history = 1, required = 12`) to public health decision-makers.
3. **Auditable Lineage**: Every forecasted point must expose the model name, parameter estimates, training horizon cutoff, in-sample residual standard deviation, and empirical coverage intervals.
4. **Prohibition of False Warning Claims**: Multi-year annual forecasting must never be conflated with or claimed as near-term weekly outbreak early warning.

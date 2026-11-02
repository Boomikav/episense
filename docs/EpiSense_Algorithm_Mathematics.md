# EpiSense — Mathematical Specifications, Algorithm Formulations, and Worked Numerical Traces

**Document Purpose:** Rigorous mathematical audit and formal specification of statistical algorithms, event fusion metrics, anomaly estimators, and multi-criteria risk scoring implemented in the EpiSense codebase.  
**Authoritative Source Files:**
- `src/episense/fusion/matcher.py`
- `src/episense/fusion/quantities.py`
- `src/episense/anomaly/ears.py`
- `src/episense/anomaly/farrington.py`
- `src/episense/anomaly/detector.py`
- `src/episense/scoring/threat.py`
- `src/episense/scoring/scorer.py`
- `src/episense/explainability/auditor.py`

---

## 1. Multi-Source Event Matching Metric

In `src/episense/fusion/matcher.py` (lines 104–112), two event candidates $C_A$ and $C_B$ are compared across four orthogonal dimensions to determine whether they represent the same underlying epidemiological incident.

### Compatibility Formula
The composite match score $S_{\text{match}} \in [0.0, 1.0]$ is computed as:

$$S_{\text{match}} = \text{round}\Big(0.35 \cdot S_{\text{disease}} + 0.30 \cdot S_{\text{geo}} + 0.25 \cdot S_{\text{temporal}} + 0.10 \cdot S_{\text{assertion}}, \; 3\Big)$$

### Component Dimension Specifications

1. **Disease Compatibility ($S_{\text{disease}}$) — `src/episense/fusion/disease_linker.py`**
   - If canonical names or ICD-10 codes match exactly: $S_{\text{disease}} = 1.00$.
   - If one is a subtype or synonym in `DISEASE_LEXICON`: $S_{\text{disease}} = 0.90$.
   - If pathogens contradict: $S_{\text{disease}} = 0.00$, and candidate pair immediately short-circuits to `NO_MATCH`.

2. **Geographical Compatibility ($S_{\text{geo}}$) — `src/episense/fusion/geo_linker.py`**
   - If both locations are identical: $S_{\text{geo}} = 1.00$.
   - If one location is the administrative parent of the other (e.g., Kozhikode district within Kerala state): $S_{\text{geo}} = 0.85$.
   - If one or both locations are unlocated (`UNRESOLVED`): $S_{\text{geo}} = 0.60$ (neutral compatibility; does not force false merge).
   - If locations are conflicting sibling districts (e.g., Kozhikode vs. Malda): $S_{\text{geo}} = 0.00$, short-circuiting to `NO_MATCH`.

3. **Temporal Compatibility ($S_{\text{temporal}}$) — `src/episense/fusion/temporal_linker.py`**
   - Let $\Delta t = |t_A - t_B|$ be the difference in days between the event window centers.
   - For an operational fusion window $W = 7$ days:
     $$S_{\text{temporal}} = \max\left(0.0, \; 1.0 - \frac{\Delta t}{W}\right)$$
   - If $\Delta t > W$: $S_{\text{temporal}} = 0.00$, short-circuiting to `NO_MATCH`.

4. **Assertion Compatibility ($S_{\text{assertion}}$) — `src/episense/fusion/matcher.py:124-148`**
   - Identical status (`CONFIRMED` & `CONFIRMED`): $S_{\text{assertion}} = 1.00$.
   - Compatible investigation (`CONFIRMED` & `SUSPECTED`): $S_{\text{assertion}} = 0.85$.
   - Incompatible statuses (`NEGATED` vs. `CONFIRMED`, `HISTORICAL` vs. `CONFIRMED`): $S_{\text{assertion}} = 0.00$, short-circuiting to `NO_MATCH`.

### Decision Thresholds
$$\text{Decision} = \begin{cases} 
\text{MATCH} & \text{if } S_{\text{match}} \ge 0.78 \;\land\; S_{\text{disease}} \ge 0.90 \;\land\; S_{\text{geo}} \ge 0.80 \;\land\; S_{\text{temporal}} \ge 0.60 \\
\text{POSSIBLE\_MATCH} & \text{if } 0.50 \le S_{\text{match}} < 0.78 \\
\text{NO\_MATCH} & \text{if } S_{\text{match}} < 0.50 \;\lor\; \text{any dimension incompatible}
\end{cases}$$

---

## 2. Quantity Aggregation & Anti-Inflation Invariant

In `src/episense/fusion/quantities.py` (lines 53–92), epidemiological quantities (cases, deaths, hospitalizations, contacts) from merged observations are combined.

Given $k$ observations reporting counts $C = \{c_1, c_2, \dots, c_k\}$ for the same fused incident:
1. The set of distinct reported values $U = \text{unique}(C)$ is computed.
2. **Anti-Inflation Rule:** The system NEVER sums counts:
   $$\text{Estimated Count} = \begin{cases}
   c_1 & \text{if } |U| = 1 \\
   \max(U) & \text{if } |U| > 1 \quad (\text{with } \texttt{has\_conflicts} = \text{True})
   \end{cases}$$
3. When $|U| > 1$, the discrepancy is logged to `reported_values` and sets a state-wide conflict flag:
   $$\texttt{conflict\_summary} = \text{"Conflicting cases counts reported: } [c_{(1)}, c_{(2)}, \dots]"$$

---

## 3. Statistical Baseline Modeling & Anomaly Detection

In `src/episense/anomaly/`, EpiSense implements deterministic weekly time-series aberration algorithms.

### A. Time Binning & Standardized Z-Score Formulation
In `src/episense/baseline/timeseries.py` and `src/episense/anomaly/detector.py`:
- Incidents are partitioned into deterministic ISO weekly time bins $(\text{year}, \text{week})$ by series key $K = (\text{disease}, \text{geography})$.
- For a target bin with observed value $Y_t$ and historical reference baseline with sample mean $\mu_{\text{ref}}$ and sample standard deviation $s_{\text{ref}}$ over $N$ weeks:

$$s_{\text{ref}} = \sqrt{\frac{1}{N - 1} \sum_{i=1}^N (y_i - \mu_{\text{ref}})^2}$$

The standardized aberration score $Z_t$ is computed in `src/episense/anomaly/detector.py:73-80`:
$$Z_t = \begin{cases}
\text{round}\left(\dfrac{Y_t - \mu_{\text{ref}}}{s_{\text{ref}}}, \; 3\right) & \text{if } s_{\text{ref}} > 0.0 \\
0.0 & \text{if } s_{\text{ref}} = 0.0 \;\land\; Y_t = \mu_{\text{ref}} \\
\text{round}\left(\dfrac{Y_t - \mu_{\text{ref}}}{\max(1.0, \sqrt{\mu_{\text{ref}}})}, \; 3\right) & \text{if } s_{\text{ref}} = 0.0 \;\land\; Y_t \ne \mu_{\text{ref}}
\end{cases}$$

> [!IMPORTANT]
> **Zero-Variance & Zero-Baseline Fallback:** When historical history is all zeros ($\mu_{\text{ref}} = 0, s_{\text{ref}} = 0$) and a new outbreak appears ($Y_t > 0$), a naive formula would divide by zero. EpiSense uses the Poisson-consistent standard error denominator $\max(1.0, \sqrt{\mu_{\text{ref}}}) = 1.0$, yielding $Z_t = Y_t - 0 = Y_t$.

---

### B. CDC Early Aberration Reporting System (EARS) Detectors
Implemented in `src/episense/anomaly/ears.py`.

#### 1. EARS C1 (Mild Sensitivity, No Guard Band) — `ears.py:53-80`
Evaluates target period $t$ against the immediately preceding $B = 7$ historical weeks:
$$\mu_{C1} = \frac{1}{7} \sum_{k=1}^7 Y_{t-k}, \qquad s_{C1} = \sqrt{\frac{1}{6} \sum_{k=1}^7 (Y_{t-k} - \mu_{C1})^2}$$

$$C_1(t) = \frac{Y_t - \mu_{C1}}{\max(s_{C1}, \epsilon)}$$
where $\epsilon = 1.0$ is the smoothing floor.  
**Alert Condition:** $C_1(t) \ge \theta$ (default $\theta = 2.00$).

#### 2. EARS C2 (Standard Sensitivity, 2-Week Guard Band) — `ears.py:108-142`
Inserts a 2-week guard band ($g = 2$) between historical baseline and the target period to prevent contamination from early outbreak surge:
$$\mu_{C2} = \frac{1}{7} \sum_{k=3}^9 Y_{t-k}, \qquad s_{C2} = \sqrt{\frac{1}{6} \sum_{k=3}^9 (Y_{t-k} - \mu_{C2})^2}$$

$$C_2(t) = \frac{Y_t - \mu_{C2}}{\max(s_{C2}, \epsilon)}$$
**Alert Condition:** $C_2(t) \ge \theta$ (default $\theta = 2.00$).

#### 3. EARS C3 (Persistent Aberration Accumulator) — `ears.py:169-197`
Measures accumulated excess deviation over a 3-week window ($P = 3$) using C2 scores:
$$C_3(t) = \sum_{k=0}^{2} \max\Big(0.0, \; C_2(t-k) - 1.0\Big)$$
**Alert Condition:** $C_3(t) \ge \theta$ (default $\theta = 2.00$).

---

### C. Bounded Farrington-Style Overdispersion Detector
Implemented in `src/episense/anomaly/farrington.py:48-117`.

Unlike simple Poisson baselines which assume $\text{Var}(Y) = \text{E}(Y)$, surveillance count data is typically overdispersed ($\text{Var} > \text{E}$). The Bounded Farrington detector models this explicitly:

1. **Expected Baseline Mean:**
   $$\mu = \frac{1}{n} \sum_{i=1}^n y_i$$

2. **Quasi-Poisson Overdispersion Factor ($\phi$):**
   $$\text{quasi\_variance} = \frac{1}{\max(1, n - 1)} \sum_{i=1}^n (y_i - \mu)^2$$
   $$\phi = \max\left(1.0, \; \frac{\text{quasi\_variance}}{\max(\mu, \epsilon_{\text{smooth}})}\right)$$
   where $\epsilon_{\text{smooth}} = 0.001$.

3. **Anscombe $(2/3)$ Power Skewness Transformation:**
   To account for skewness in low-count Poisson distributions, the Farrington-Stroup transformation is applied:
   $$\text{inner} = \mu^{2/3} + \frac{2}{3} z_\alpha \sqrt{\phi \cdot \mu^{1/3}}$$
   $$\text{Threshold } U = \begin{cases}
   (\text{inner})^{3/2} & \text{if } \text{inner} > 0.0 \\
   \mu + z_\alpha \sqrt{\phi \cdot \mu} & \text{otherwise (fallback)}
   \end{cases}$$
   where $z_\alpha = 1.96$ ($95\%$ upper prediction bound).

4. **Alert Condition:**
   $$\text{is\_alert} = (Y_t > U)$$

---

### D. Signal Classification & Reliability Downgrade Rules
In `src/episense/anomaly/detector.py:140-164`:

$$\text{Signal Level} = \begin{cases}
\text{STRONG\_SIGNAL} & \text{if } \ge 2 \text{ detectors trigger } \land \text{STABLE\_BASELINE } \land \text{Sources} \ge 2 \\
\text{SIGNAL} & \text{if } (\text{any detector triggers } \lor Z_t \ge 2.0) \land \text{no downgrade} \\
\text{WATCH} & \text{if downgraded from SIGNAL due to:}\\
             & \quad \bullet \text{ INSUFFICIENT\_HISTORY } (N < 3)\\
             & \quad \bullet \text{ CONFLICTING\_DATA } (\texttt{has\_conflicts} = \text{True})\\
             & \quad \bullet \text{ HIGH\_VARIANCE with } \text{Sources} < 2\\
             & \text{OR if } Z_t \ge 1.5 \;\lor\; (\mu_{\text{ref}} = 0 \land Y_t > 0)\\
\text{NO\_SIGNAL} & \text{otherwise}
\end{cases}$$

---

## 4. Multi-Criteria Epidemiological Risk Scoring

In `src/episense/scoring/scorer.py` (lines 106–241), composite operational risk $R_{\text{composite}} \in [0.0, 1.0]$ is calculated across 5 dimensions:

$$R_{\text{raw}} = w_a \cdot S_{\text{anomaly}} + w_t \cdot S_{\text{threat}} + w_e \cdot S_{\text{evidence}} + w_c \cdot S_{\text{certainty}} + w_s \cdot S_{\text{spatial}}$$

### Reconciled Multi-Criteria Weights Matrix

| Weight Parameter | Backend Runtime (`scorer.py:53-57`) | Production Config (`config.example.yaml`) | Frontend Modal UI (`AlertDetailModal.tsx`) | Status |
| :--- | :--- | :--- | :--- | :--- |
| **$w_a$ (Anomaly)** | **0.30** | **0.30** | **0.30** | Fully Reconciled |
| **$w_t$ (Pathogen Threat)** | **0.25** | **0.25** | **0.25** | Fully Reconciled |
| **$w_e$ (Source Evidence)** | **0.20** | **0.20** | **0.20** | Fully Reconciled |
| **$w_c$ (Clinical Certainty)**| **0.15** | **0.15** | **0.15** | Fully Reconciled |
| **$w_s$ (Spatial Resolution)**| **0.10** | **0.10** | **0.10** | Fully Reconciled |
| **Sum** | **1.00** | **1.00** | **1.00** | **1.00** |

> [!NOTE]
> **Reconciliation Status:** All backend scoring algorithms, YAML configurations, and frontend UI components now strictly align to the canonical **0.30 / 0.25 / 0.20 / 0.15 / 0.10** weight set. Discrepant hardcoded strings in `AlertDetailModal.tsx` and legacy config defaults have been eliminated.

---

### Dimension Score Calculations

#### 1. Statistical Anomaly Score ($S_{\text{anomaly}}$) — `scorer.py:109-132`
- Let $s_z = \min(1.0, \max(0.0, (Z_t - 1.0) / 3.0))$.
- If `DetectionMethod.MULTI_DETECTOR`: $s_z = \min(1.0, s_z + 0.15)$.
- Clamping by signal level:
  $$S_{\text{anomaly}} = \begin{cases}
  0.0 & \text{if } \text{NO\_SIGNAL} \\
  \max(s_z, 0.85) & \text{if } \text{STRONG\_SIGNAL} \\
  \max(s_z, 0.65) & \text{if } \text{SIGNAL} \\
  \min(0.60, \max(0.25, s_z)) & \text{if } \text{WATCH}
  \end{cases}$$

#### 2. Pathogen Threat Score ($S_{\text{threat}}$) — `scorer.py:136`, `threat.py:88-93`
- Evaluated via `PathogenThreatClassifier`:
  $$S_{\text{threat}} = \begin{cases}
  1.00 & \text{Tier 4: High Consequence (Nipah, Chandipura, Avian Flu, Marburg, Ebola)} \\
  0.75 & \text{Tier 3: Severe Epidemic (Cholera, KFD, Rabies, JE, Leptospirosis)} \\
  0.50 & \text{Tier 2: Moderate / Vector-borne (Dengue, Malaria, Scrub Typhus, Measles)} \\
  0.25 & \text{Tier 1: Mild / Syndromic (Viral Fever, Generic Illness, RSV)}
  \end{cases}$$

#### 3. Source Evidence Score ($S_{\text{evidence}}$) — `scorer.py:142-170`
- Base score from independent source count $K$:
  $$S_{\text{base}} = \begin{cases} 1.00 & \text{if } K \ge 3 \\ 0.70 & \text{if } K = 2 \\ 0.35 & \text{if } K = 1 \end{cases}$$
- Official Public Health Agency Bonus: If any source is WHO, IDSP, MoHFW, PIB, or CDC:
  $$S_{\text{evidence}} = \min(1.00, \; S_{\text{base}} + 0.15)$$

#### 4. Clinical Certainty Score ($S_{\text{certainty}}$) — `scorer.py:175-207`
- Base score from diagnostic assertion:
  $$S_{\text{base}} = \begin{cases} 
  1.00 & \text{if } \text{any observation is } \text{CONFIRMED} \\
  0.70 & \text{if } \text{any observation is } \text{SUSPECTED} \\
  0.20 & \text{if } \text{all observations are } \text{HISTORICAL} \\
  0.00 & \text{if } \text{all observations are } \text{NEGATED}
  \end{cases}$$
- Mortality Confirmation Bonus: If verified deaths $> 0$:
  $$S_{\text{certainty}} = \min(1.00, \; S_{\text{base}} + 0.20)$$

#### 5. Spatial Resolution Score ($S_{\text{spatial}}$) — `scorer.py:212-229`
$$S_{\text{spatial}} = \begin{cases}
1.00 & \text{Admin 2–4 (District, City, Subdistrict: e.g., Kozhikode, Pune)} \\
0.75 & \text{Admin 1 (State / Province: e.g., Kerala, Gujarat)} \\
0.50 & \text{Admin 0 (Country / National: e.g., India)} \\
0.30 & \text{Unspecified / Global locus}
\end{cases}$$

---

### Safety Ceilings & Reliability Gating Rules
In `src/episense/scoring/scorer.py:245-302`:

1. **Negation Suppression:** If all observations are `NEGATED`:
   $$\text{Final Score} = 0.00, \qquad \text{Tier} = \text{INFORMATIONAL}$$
2. **Conflicting Data Penalty:** If $\texttt{has\_conflicts} = \text{True}$:
   $$\text{Penalty } P = 0.10, \qquad R_{\text{candidate}} = \max(0.0, \; R_{\text{raw}} - 0.10)$$
   **Ceiling:** $R_{\text{candidate}}$ cannot exceed $0.79$ (capped at `MEDIUM`).
3. **Insufficient Historical Baseline Cap:** If status is `INSUFFICIENT_HISTORY`:
   - If Pathogen Tier 4 and Sources $\ge 2$: Capped at $0.79$ (`MEDIUM`).
   - Otherwise: Capped at $0.64$ (`LOW`).
4. **Single Source Isolation Cap:** If independent sources $K = 1$:
   - Score capped at $0.79$ (`MEDIUM`); cannot trigger `HIGH` alert without independent corroboration.

### Operational Alert Tier Assignment
$$\text{Alert Tier} = \begin{cases}
\text{INFORMATIONAL} & \text{if } R_{\text{final}} < 0.40 \\
\text{LOW} & \text{if } 0.40 \le R_{\text{final}} < 0.65 \\
\text{MEDIUM} & \text{if } 0.65 \le R_{\text{final}} < 0.80 \\
\text{HIGH} & \text{if } R_{\text{final}} \ge 0.80
\end{cases}$$

---

## 5. Fully Worked Mathematical Reconstruction: Nipah Kozhikode Alert

We now trace the exact computation for Alert `76f8fdcb-537a-518d-96c9-eb3d04db939f` (observed in screenshot `03b_alert_modal.png` and verified via API query):

### Step 1: Input Observations
- Pathogen: Nipah virus disease
- Location: Kozhikode district, Kerala
- Period: ISO Week 2023-W37 (2023-09-11 to 2023-09-17)
- Observed Value: $Y_t = 2023.0$ cases
- Baseline History: $\mu_{\text{ref}} = 1.00$, $s_{\text{ref}} = 0.00$ (insufficient history)
- Standardized Deviation:
  $$Z = \frac{2023.0 - 1.00}{\max(1.0, \sqrt{1.00})} = \frac{2022.0}{1.0} = +2022.00$$
- Signal Level: Downgraded to `WATCH` due to insufficient history + quantity conflict.

### Step 2: Dimension Scoring
1. **$S_{\text{anomaly}}$:**
   $$s_z = \min(1.0, \max(0.0, (2022.00 - 1.0) / 3.0)) = 1.00$$
   Clamping for `WATCH`:
   $$S_{\text{anomaly}} = \min(0.60, \max(0.25, 1.00)) = \mathbf{0.600}$$

2. **$S_{\text{threat}}$:**
   Nipah is Tier 4 High Consequence:
   $$S_{\text{threat}} = \mathbf{1.000}$$

3. **$S_{\text{evidence}}$:**
   2 independent sources (WHO + ProMED) $\to S_{\text{base}} = 0.70$.  
   WHO is an official international agency $\to +0.15$ bonus:
   $$S_{\text{evidence}} = 0.70 + 0.15 = \mathbf{0.850}$$

4. **$S_{\text{certainty}}$:**
   Laboratory-confirmed diagnostic assertion $\to S_{\text{base}} = 1.00$.  
   Deaths present in text but extracted unit was general count $\to$ no mortality bonus applied:
   $$S_{\text{certainty}} = \mathbf{1.000}$$

5. **$S_{\text{spatial}}$:**
   Kozhikode is an Admin 2 District in SQLite Gazetteer:
   $$S_{\text{spatial}} = \mathbf{1.000}$$

### Step 3: Raw Weighted Sum
Using backend weights $[0.30, 0.25, 0.20, 0.15, 0.10]$:
$$R_{\text{raw}} = (0.30 \times 0.600) + (0.25 \times 1.000) + (0.20 \times 0.850) + (0.15 \times 1.000) + (0.10 \times 1.000)$$
$$R_{\text{raw}} = 0.180 + 0.250 + 0.170 + 0.150 + 0.100 = \mathbf{0.850}$$

### Step 4: Safety Gating & Penalty Enforcement
- Conflicting quantity reported across documents: $[2.0, 2023.0]$ cases.
- Penalty applied: $-0.100$.
$$R_{\text{candidate}} = 0.850 - 0.100 = \mathbf{0.750}$$
- Insufficient historical baseline cap for Tier 4 multi-source: Capped at $0.790$. Since $0.750 \le 0.790$, score remains $0.750$.
- Final Composite Score:
  $$\mathbf{R_{\text{final}} = 0.750}$$

### Step 5: Tier Assignment
$$0.65 \le 0.750 < 0.80 \implies \mathbf{MEDIUM\;ALERT}$$

$$\text{Exact Result: } \texttt{Score} = 0.750, \quad \texttt{Tier} = \text{MEDIUM}, \quad \texttt{Gating} = \text{Active (-0.10 penalty)}$$
*(Matches the database and screenshot values exactly.)*

# EpiSense — Technical Viva, Project Defense, and Live Demonstration Guide

**Target Audience:** Public health examiners, computer science viva panels, machine learning audit committees, and engineering interviewers.  
**Platform Overview:** EpiSense is an explainable NLP framework and streaming intelligence platform for early epidemic surveillance.

---

## 1. Core Problem Statement & Academic Justification

### The Fundamental Question
> *"Why can't public health departments just use keyword search or a commercial LLM like ChatGPT to find outbreaks in news articles?"*

### The Model Defense Answer
1. **Keyword Search Fails on Contextual Epistemics:** Keyword search triggers identically on negated rumors (*"Zero cases of Nipah in Kerala"*), historical reviews (*"In the 2018 Nipah outbreak..."*), and future policy advisories (*"Nipah containment protocol issued"*). EpiSense introduces a syntactic clause-level assertion analyzer (`ContextualAssertionAnalyzer`) that classifies mentions into `CONFIRMED`, `SUSPECTED`, `NEGATED`, `HISTORICAL`, and `HYPOTHETICAL`, suppressing non-active reports from positive epidemic alerting.
2. **LLMs Suffer from Coordinate Fabrication & Hallucination:** General-purpose LLMs hallucinate coordinates and create nondeterministic outputs. In epidemiology, sending response teams to fabricated coordinates is catastrophic. EpiSense enforces a **Zero Coordinate Fabrication Guardrail** (`CautiousLocationResolver` + `LocalGazetteer`): if a toponym cannot be matched to a verified GeoNames entry, coordinates remain `null` and the record is placed in an Unresolved Geometry Drawer.
3. **Media Velocity Distorts Case Counts:** When an outbreak occurs, 50 news websites publish the same story. LLMs or keyword systems summing numbers would count $50 \times 2 = 100$ cases. EpiSense implements an **Anti-Inflation Quantity Aggregator** (`QuantityAggregator`) that merges syndicated reports, tracks independent source agencies, takes the conservative maximum, and flags discrepancies rather than summing.
4. **Deterministic Auditability:** In public health, an alert can trigger quarantines, travel bans, or school closures. Every decision must have an unbroken audit trail. EpiSense provides an 8-step arithmetic audit trail sealed with a SHA-256 state checksum, linking every alert back to exact character offsets ($text[start:end] == span$).

---

## 2. Technical Viva Questions & In-Depth Model Answers

### Category A: NLP & Computational Linguistics

#### Q1: "Why did you use a hybrid model combining spaCy and scispaCy rather than fine-tuning a transformer like BioBERT?"
**Answer:**  
"We selected a hybrid pipeline composed of `en_core_web_sm` (general syntactic dependency, sentence segmentation, and administrative toponyms) and `en_core_sci_sm` (biomedical entity candidate generation), combined with an exact domain taxonomy (`DISEASE_LEXICON` with ICD-10 codes).  
This decision was guided by three principles:
1. **Deterministic Character Span Integrity:** Regulated public health surveillance requires character-level provenance. Our pipeline asserts $text[start:end] == span$ on every token.
2. **Computational Efficiency & Local Deployment:** The hybrid pipeline processes dispatches in milliseconds on local CPU (863 candidates/second), allowing deployment on air-gapped district health servers without expensive GPU infrastructure.
3. **Predictable Epistemic Control:** Epistemic negation and historical framing follow structured syntactic clause rules. Transformer classifiers often suffer from attention bleed across long sentences, misclassifying negated clauses. Our rule-based clause parser enforces strict boundary precedence: Negation > History > Hypothetical > Suspected > Confirmed."

#### Q2: "What are the common failure modes of your NLP pipeline?"
**Answer:**  
"Our empirical evaluation on the 18-document gold annotation benchmark revealed four specific failure modes:
1. **Quantity Extraction from Retrospective Years:** Numbers appearing in dates (e.g., the year *'2023'*) can be picked up by quantity regexes as case counts. We designed the downstream Event Fusion module to safely neutralize this by flagging conflicts ($reported\_values = [2.0, 2023.0]$) and applying a $-0.10$ reliability penalty rather than summing.
2. **Boundary Granularity Mismatches:** The model extracts *'Kozhikode district'* while gold annotations only labeled *'Kozhikode'*, lowering exact-match span F1 (32.32%) while maintaining semantic accuracy.
3. **Split Entity Mentions:** Phrases like *'avian influenza A(H9N2)'* are occasionally segmented into *'avian influenza'* and *'H9N2'* as separate spans.
4. **Unlisted Hamlet Toponyms:** Highly localized rural villages (e.g. *'Brahmagiri'*) absent from our 66-record SQLite gazetteer are flagged as `UNRESOLVED`."

---

### Category B: Statistical Surveillance & Anomaly Detection

#### Q3: "Explain the difference between EARS C1, C2, and C3."
**Answer:**  
"All three are CDC Early Aberration Reporting System detectors implemented in `src/episense/anomaly/ears.py`:
- **EARS C1:** Calculates deviation using the 7 historical weeks immediately preceding the target week:
  $$C_1(t) = \frac{Y_t - \bar{Y}_{t-1 \dots t-7}}{\max(s, 1.0)}$$
  It is highly sensitive to sudden acute spikes but susceptible to baseline contamination if an outbreak began 1–2 weeks earlier.
- **EARS C2:** Introduces a 2-week guard band ($t-9 \dots t-2$), evaluating the target against historical baseline prior to the immediate outbreak onset:
  $$C_2(t) = \frac{Y_t - \bar{Y}_{t-9 \dots t-3}}{\max(s, 1.0)}$$
  This prevents the baseline from inflating during an ongoing epidemic.
- **EARS C3:** Accumulates persistent excess deviation over a 3-week window using C2 scores:
  $$C_3(t) = \sum_{k=0}^2 \max(0, C_2(t-k) - 1.0)$$
  It detects slow, insidious epidemic build-ups that might not cross the acute single-week threshold."

#### Q4: "Why did you implement Bounded Farrington instead of a standard Gaussian Z-score?"
**Answer:**  
"Standard Gaussian $Z$-score assumes constant variance ($\sigma^2$). However, district-level infectious disease counts follow a Poisson or negative binomial distribution where counts are non-negative, right-skewed, and overdispersed ($\text{Var} > \text{E}$).  
Our `BoundedFarringtonDetector` (`farrington.py`) solves this by:
1. Explicitly estimating the quasi-Poisson overdispersion parameter:
   $$\phi = \max\left(1.0, \frac{\text{quasi\_variance}}{\mu}\right)$$
2. Applying the Anscombe $(2/3)$ power skewness transformation:
   $$\text{inner} = \mu^{2/3} + \frac{2}{3} z_\alpha \sqrt{\phi \cdot \mu^{1/3}}, \qquad \text{Threshold} = (\text{inner})^{3/2}$$
   This yields an asymmetric upper prediction bound far more statistically defensible than $\mu + 2\sigma$ on small count series."

---

### Category C: Multi-Criteria Scoring & Safety Ceilings

#### Q5: "How does the system ensure an alert does not cause panic based on a single unverified rumor?"
**Answer:**  
"EpiSense implements **Reliability Safety Ceilings** in `AlertScorer` (`scorer.py:245-302`):
1. **Single Source Isolation Cap:** If an incident is reported by only 1 source group, its composite score is strictly capped at $0.790$ (`MEDIUM`). It is mathematically impossible for an uncorroborated single source to generate a `HIGH` alert.
2. **Insufficient Baseline Cap:** If the time-series has fewer than 3 historical weeks ($N < 3$), the score is capped at $0.640$ (`LOW`), or $0.790$ (`MEDIUM`) only if it is a Tier 4 high-consequence pathogen supported by multiple independent sources.
3. **Conflicting Data Penalty:** If conflicting numbers are reported across sources, a mandatory $-0.10$ penalty is deducted, and the alert is capped below `HIGH`."

---

## 3. Practical Step-by-Step Live Demonstration Script

Follow this exact sequence during an oral examination or system demonstration:

### Step 1: Prove System Health & Microservices (2 Minutes)
1. Open browser to **System Status**: `http://localhost:5174` $\to$ click `System Status` on sidebar.
2. Point out:
   - API Gateway: `Healthy` (`GET /health`)
   - Readiness Probe: `Ready for Traffic` (`GET /health/ready`), showing current state counts (110 or 111 docs, 170 or 171 alerts).
   - In-process services: Continuous Surveillance Pipeline, State Store, SQLite Gazetteer, WebSocket Feed.

### Step 2: Executive Surveillance Dashboard Walkthrough (3 Minutes)
1. Click `Overview` on sidebar.
2. Point out the top 4 KPI cards:
   - `Active Alerts` (Badge: `31 High Consequence` — highlighting high CFR pathogens like Nipah, Chandipura).
   - `Fused Events` (Correlated across multi-source dispatches).
   - `Early Warning Signals` (EARS/Farrington statistical deviations).
   - `Documents Ingested` (Preloaded corpus).
3. Point out the **Risk Distribution Donut Chart**: Show that the system prioritizes threats, with only 1 alert in `Medium` and 0 in `High`, preventing alert fatigue.

### Step 3: Forensic Explainability Drilldown (5 Minutes) — *Crucial Step*
1. Click `Alerts` on sidebar.
2. Locate **Row 1**: `Nipah Virus Disease` | `Kozhikode` | `Medium Alert` | `0.750` | `Tier 4 Consequence` | `2 Sources`.
3. Click `Inspect >` to open the **Alert Detail Modal**:
   - **Risk Breakdown Tab:**
     - Point out the 5 Primary Driving Factors.
     - Point out the **Safety Ceiling & Reliability Gating** callout: *"Conflicting quantity reports detected across sources: -0.10 penalty applied"*.
     - Explain the raw composite score ($0.850$) minus penalty ($0.100$) equals the final score ($0.750$).
   - **Explainability Dossier Tab:**
     - Show the **5W1H Briefing** (Who, What, When, Where, Why, How).
     - Show the **Reconstructed Evidence Spans**: Highlight how the raw text from WHO and ProMED is displayed with highlighted character offsets ($text[68:89]$).
   - **Decision Audit Trail Tab:**
     - Walk through the 8 sequential evaluation steps.
     - Point to the cryptographic **SHA-256 Audit Checksum** (`cf6ce2e8...`).
   - **Provenance DAG Tab:**
     - Show the acyclic graph tracing from Document $\to$ Text Span $\to$ Fused Event $\to$ Signal $\to$ Alert.

### Step 4: Zero Coordinate Fabrication Verification (2 Minutes)
1. Click `Surveillance Map` on sidebar.
2. Show the mapped clusters in Kerala, Gujarat, Maharashtra, West Bengal, Odisha.
3. Click the orange button: `111 Unresolved Geometry`.
4. Explain: *"EpiSense strictly refuses to hallucinate coordinates. These 111 records represent national summaries or unlocated reports; instead of guessing a pin on the map, they are safely quarantined in this drawer."*

### Step 5: Live Document Ingestion & WebSocket Push (3 Minutes)
1. Open a second browser tab or split window showing `Live Surveillance`.
2. In the first window, navigate to `Submit Report`.
3. Click the scenario preset button: `Nipah Alert (Kerala)`.
4. Show that Title, Timestamp, Source (`who_don_surveillance`), and Dispatch text are populated.
5. Click `Submit to Continuous Pipeline`.
6. Show immediate green success banner returning `document_id`.
7. Switch to the `Live Surveillance` window: Show the real-time event frame pushed instantaneously over the WebSocket without page refresh.

### Step 6: Idempotent Deduplication Verification (1 Minute)
1. Without modifying the form in `Submit Report`, click `Submit to Continuous Pipeline` a second time.
2. Show that the backend returns `duplicate_skipped`:
   - SHA-256 hash match detected.
   - The system did NOT rerun NLP, did NOT create duplicate events, and did NOT inflate case counts.

### Step 7: Malformed Document Rejection (1 Minute)
1. Clear the text area, leaving it empty.
2. Click `Submit to Continuous Pipeline`.
3. Show that FastAPI Pydantic schema validation rejects the request with HTTP 422, routing the failure to `DeadLetterRecord` and maintaining system stability.

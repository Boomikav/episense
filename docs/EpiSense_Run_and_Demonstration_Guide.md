# EpiSense — Live Demonstration, Viva Defense & Operational Run Guide

## 1. System Runtime & Architecture Coordinates

| Component | URL / Location | Technology Stack | Operational Status |
| :--- | :--- | :--- | :--- |
| **Frontend Console** | `http://localhost:5173` | React 18, TypeScript, Vite, Tailwind CSS, Lucide Icons | Active & Serving |
| **Backend API** | `http://127.0.0.1:8008` | Python 3.11, FastAPI, Pydantic v2, Uvicorn | Active & Serving |
| **Interactive API Docs**| `http://127.0.0.1:8008/docs` | OpenAPI 3.0 / Swagger UI | Accessible |
| **Surveillance WebSocket**| `ws://127.0.0.1:8008/api/v1/ws/surveillance` | Asyncio WebSocket with subscription filtering | Operational |
| **Durable Database** | `data/surveillance_store.sqlite` | SQLite 3 in WAL mode (Write-Ahead Logging) | Synchronized |

---

## 2. Step-by-Step 10-View Demonstration Walkthrough

When presenting or defending the EpiSense project in a technical review, follow this sequential walkthrough:

### View 1: Live Overview (`/`)
- **Key Visual Elements:**
  - Active Feed Adapters badge: Displays **5 Active Feed Adapters** (WHO, PIB, CDC, ProMED, IDSP).
  - Segregated surveillance metrics: Separates live external documents from historical baseline records.
  - Prioritized alert stream with tier badges (`HIGH`, `MEDIUM`, `LOW`, `INFORMATIONAL`).
- **Talking Point:** *"Notice that historical baseline data (110 documents) is strictly segregated from live surveillance records. There are no fabricated metrics or fake '195 countries' counters."*

### View 2: Live Surveillance Feed (`/surveillance`)
- **Key Visual Elements:**
  - Real-time event updates arriving via WebSockets.
  - Dynamic status indicators, disease pathogen badges, and location centroid mappings.
- **Talking Point:** *"This feed streams new document ingestions and fused event updates in real time using an asyncio WebSocket broker."*

### View 3: NLP 17-Stage Workbench (`/workbench`)
- **Key Visual Elements:**
  - Document browser with origin filtering (`LIVE_EXTERNAL`, `HISTORICAL_CORPUS`, `BENCHMARK`).
  - Interactive Text Span Visualizer: Color-coded spans for Disease (Red), Location (Blue), Temporal (Purple), Quantity (Green), and Assertion (Amber).
  - Click-to-Verify Span Drawer: Clicking any highlighted span verifies that `text[start_char:end_char] == text_span`.
  - 17-Stage Pipeline Timeline: Step-by-step latency, input representations, and intermediate artifacts.
- **Talking Point:** *"Every extraction preserves character-level provenance. Click any entity to verify the exact string slice against the raw document."*

### View 4: Event Fusion Inspector (`/fusion`)
- **Key Visual Elements:**
  - Canonical fused event clusters with supporting observation lists.
  - Decision D05 Multi-Source Matching Matrix:
    $$S_{\text{match}} = 0.35 \cdot S_{\text{disease}} + 0.30 \cdot S_{\text{geo}} + 0.25 \cdot S_{\text{temporal}} + 0.10 \cdot S_{\text{assertion}} \ge 0.78$$
  - Anti-Inflation Syndication Proof: Demonstrates that when multiple news sources report the same event, case numbers take the maximum rather than accumulating spuriously.
- **Talking Point:** *"This is how EpiSense solves the media echo problem: multiple articles reporting the same patient do not inflate case counts."*

### View 5: Alerts & Explainability (`/alerts`)
- **Key Visual Elements:**
  - Comprehensive alert cards with composite risk scores ($R \in [0.0, 1.0]$).
  - Multi-Criteria Risk Breakdown radar: Anomaly ($0.30$), Threat ($0.25$), Evidence ($0.20$), Certainty ($0.15$), Spatial ($0.10$).
  - Clinical narrative explanations, driving factors, and reliability gating flags.
- **Talking Point:** *"Risk scoring is not a black-box machine learning model; it is an auditable, multi-criteria decision process with clinical safety guardrails."*

### View 6: Early Signals & Statistical Baselines (`/signals`)
- **Key Visual Elements:**
  - Time-series incidence charts comparing observed counts against expected historical baselines.
  - EARS C1, C2, C3 cumulative sum deviations.
  - Bounded Farrington algorithm thresholds with power transformation and trend weights.
- **Talking Point:** *"Signals represent statistical deviations above expected baseline incidence, separating routine seasonal increases from abnormal surges."*

### View 7: Geographic Surveillance Map (`/map`)
- **Key Visual Elements:**
  - Interactive Leaflet map with administrative boundary centroids.
  - Dynamic clustering of disease outbreaks across districts and states.
  - Marker popups linking directly to fused events and supporting documents.

### View 8: Research & Empirical Validation (`/validation`)
- **Key Visual Elements:**
  - **"Run Empirical Evaluation"** trigger button.
  - Real-time evaluation against `gold_annotations_v1.json` (18 verified documents, 96 gold spans).
  - Exact-Span F1 cards: Disease NER (34.62%), Geographic Grounding (53.73%), Temporal Normalization (68.57%), Quantity Extraction (36.59%), Assertion Accuracy (76.67%), Macro F1 (48.38%).
  - Documented research constraints and error analysis.
- **Talking Point:** *"We present honest, uninflated scientific metrics evaluated against expert annotations rather than synthetic test fixtures."*

### View 9: Public-Health Source Connectors (`/sources`)
- **Key Visual Elements:**
  - Grid of all 5 source connectors with live health status pills (`OPERATIONAL`, `UNAVAILABLE`, `AUTHENTICATION_REQUIRED`).
  - **"Poll Feed Now"** and **"Poll All Feeds Now"** action buttons.
  - Historical polling audit table with execution timestamps, HTTP statuses, and latencies.
- **Talking Point:** *"Click 'Poll Feed Now' on WHO News to fetch live bulletins, run them through the 17-stage pipeline, and watch the dashboard update in real time."*

### View 10: System Telemetry & Status (`/status`)
- **Key Visual Elements:**
  - SQLite database size and WAL mode confirmation.
  - Deterministic state checksum (`SHA-256`), global sequence number, and dead-letter queue count.
  - Ingestion throughput and memory utilization metrics.

---

## 3. Top Viva & Defense Questions

### Q1: How does EpiSense distinguish between an outbreak signal and an actual epidemic?
**Answer:** EpiSense explicitly distinguishes between statistical anomaly detection and epidemiological outbreak confirmation. A signal generated by EARS or Farrington indicates an atypical surge in textual surveillance mentions above the historical Poisson baseline. Formal epidemic confirmation requires laboratory serology, pathogen sequencing, and accredited health agency notification.

### Q2: How does the platform handle the "media echo" effect where dozens of outlets report the same single patient?
**Answer:** Through the Decision D05 multi-source event fusion engine (`src/episense/fusion/matcher.py`) and the Anti-Inflation Invariant (`src/episense/fusion/quantities.py`). Event candidates matching on disease, geography, and time window ($S_{\text{match}} \ge 0.78$) are clustered into a canonical event. Quantitative metrics take the supremum ($\max$) or the authoritative health agency figure rather than accumulating counts.

### Q3: What are the exact weights used for risk scoring, and why were they chosen?
**Answer:** Risk scoring uses five normalized weights $[0.30, 0.25, 0.20, 0.15, 0.10]$:
- $w_a = 0.30$ (Statistical Anomaly): Magnitude of deviation from baseline.
- $w_t = 0.25$ (Pathogen Threat Tier): Biological lethality and transmissibility (e.g., Tier 4 Nipah vs. Tier 1 Viral Fever).
- $w_e = 0.20$ (Source Evidence): Number of independent corroborating sources with an official agency bonus.
- $w_c = 0.15$ (Clinical Certainty): Laboratory-confirmed vs. suspected vs. historical status.
- $w_s = 0.10$ (Spatial Resolution): District-level precision vs. broad national mentions.

### Q4: Why are ProMED and IDSP connectors showing "Unavailable" and "Authentication Required"?
**Answer:** This reflects grounded reality rather than synthetic deception. ProMED sunset its unauthenticated public RSS feed in late 2024, returning HTTP 404. The Indian IDSP portal requires authenticated sessions and captcha for weekly PDF bundles. EpiSense honestly reports their true operational states instead of fabricating fake data.

### Q5: How is durability across server restarts guaranteed?
**Answer:** All accepted documents, 17-stage pipeline traces, canonical fused events, anomaly signals, alerts, explainability dossiers, and connector poll records are persisted directly to SQLite at `data/surveillance_store.sqlite` running in Write-Ahead Logging (WAL) mode. When the server restarts, state is restored idempotently without data loss.

# EpiSense
**Explainable Multi-Source NLP Framework & Continuous Streaming Platform for Early Epidemic Intelligence**

---

## 1. Executive Summary & What EpiSense Does
**EpiSense** is an open, modular, explainable Natural Language Processing (NLP) framework and continuous surveillance platform designed for public health epidemiologists and biosecurity analysts.

Traditional keyword-based alert systems suffer from overwhelming false-positive rates because they confuse simple keyword mentions with active epidemics (e.g. mistaking *"No cases of Nipah virus were confirmed"* for an outbreak, or re-alerting on historical retrospectives). EpiSense overcomes this through:
- **Context-Aware Clinical NLP**: Entity extraction, temporal scoping, and linguistic assertion classification (distinguishing confirmed cases from historical retrospectives, negated rumors, or hypothetical models).
- **Multi-Source Cross-Corroboration**: Clustering independent dispatches into canonical fused incidents while preventing media echo-chamber inflation.
- **Statistical Aberration Baselines**: CDC EARS (C1/C2/C3) and Farrington overdispersion algorithms calculating adaptive weekly thresholds.
- **5-Dimensional Risk Scoring**: Multi-criteria alert assessment bounded between [0.0, 1.0] across Anomaly, Pathogen Threat, Evidence Strength, Clinical Certainty, and Spatial Specificity.
- **Unbroken Forensic Provenance**: Every alert links to a 5W1H briefing, character-level raw text evidence spans, an 8-step decision audit path, and a SHA-256 state seal.
- **Zero-Fabrication Geospatial Console**: A real-time reactive GIS map strictly segregating unlocated territories from hallucinated map coordinates.

---

## 2. End-to-End Pipeline & System Architecture

```text
Heterogeneous Health Dispatches (WHO Bulletins, IDSP Reports, News Dispatches, Lab Feeds)
                               │
                               ▼
            ┌─────────────────────────────────────────┐
            │ ContinuousSurveillancePipeline (Ph. 11) │
            └─────────────────────────────────────────┘
                               │
  ┌────────────────────────────┼────────────────────────────┐
  │ 1. Document Ingestion      │ 2. Clinical NLP Extraction │ 3. Candidate Generation &
  │    Validation & Deduplication   Assertion Scoping          Cross-Source Event Fusion
  │    (SHA-256 Content Hash)  │    (spaCy/SciSpaCy Engine) │    (Cluster & Quantity Merge)
  └────────────────────────────┼────────────────────────────┘
                               │
  ┌────────────────────────────┼────────────────────────────┐
  │ 4. Temporal Normalization  │ 5. Baseline Estimation &   │ 6. 5-Dimensional
  │    & Weekly Time Bins      │    Anomaly Aberration      │    Epidemiological Risk
  │    (Deterministic ISO-Wks) │    (EARS C1-C3, Farrington)│    Scoring & Safety Gates
  └────────────────────────────┼────────────────────────────┘
                               │
            ┌──────────────────┴──────────────────────┐
            │ 7. Forensic Explainability & Lineage    │
            │    (5W1H, Evidence Spans, Audit, DAG)   │
            └──────────────────┬──────────────────────┘
                               │
                               ▼
            ┌─────────────────────────────────────────┐
            │  SurveillanceStateStore (Replay Engine) │
            │  110 Docs • 170 Events • 170 Alerts     │
            └──────────────────┬──────────────────────┘
                               │
               ┌───────────────┴───────────────┐
               ▼                               ▼
  FastAPI Production REST API       WebSocket Streaming Feed
  • /health, /health/ready, /live   • WS /api/v1/ws/surveillance
  • /api/v1/alerts (detail, audit)  • Connection ACK & Heartbeats
  • /api/v1/events (fused records)  • Dynamic Subscription Filters
  • /api/v1/signals (aberrations)   • Sub-millisecond Event Push
  • /api/v1/geo/alerts (GeoJSON)    • Full Fan-Out to Subscribed
  • POST /api/v1/documents            Operations Dashboards
               │                               │
               └───────────────┬───────────────┘
                               ▼
            ┌─────────────────────────────────────────┐
            │ EpiSense Operations Console (Frontend)  │
            │ React 19 + TypeScript + Vite + Leaflet  │
            └─────────────────────────────────────────┘
```

---

## 3. How Data Enters and Flows Through EpiSense

### A. Ingestion
Data enters the system through `POST /api/v1/documents` or streaming sources (`FileStreamIngestionSource`, RSS, public bulletins). Payloads contain:
- `title`: Headline or dispatch title
- `source_id`: Reporting agency / feed ID
- `source_type`: Category (`official_bulletin`, `news_media`, `lab_report`, `syndication`)
- `publication_date`: ISO-8601 timestamp
- `text`: Raw narrative text

### B. What Processing Happens
1. **Validation & Idempotency**: SHA-256 content hashes detect identical dispatches. Duplicates return `duplicate_skipped` without re-running NLP or inflating incident counts.
2. **Clinical NLP Extraction**: spaCy/SciSpaCy models identify diseases, symptoms, administrative territories, temporal spans, and quantities.
3. **Contextual Assertion Scoping**: Negation rules and assertion analyzers determine whether mentions are `confirmed`, `suspected`, `historical`, `negated`, or `hypothetical`. Negated and hypothetical mentions are suppressed from positive epidemiological alerting.
4. **Event Fusion**: Cross-source clustering groups duplicate reports into canonical fused incidents while tracking independent reporting groups to prevent media echo-chamber inflation.
5. **Time Bins & Anomaly Baselines**: Incidents are aggregated into weekly bins. EARS C1/C2/C3 and Farrington algorithms contrast observed counts against adaptive baselines.
6. **Risk Scoring**: Composite risk is calculated across 5 bounded dimensions:
   $$R = w_a \cdot S_{\text{anomaly}} + w_t \cdot S_{\text{threat}} + w_e \cdot S_{\text{evidence}} + w_c \cdot S_{\text{certainty}} + w_s \cdot S_{\text{spatial}}$$
7. **Forensic Dossier Creation**: A 5W1H briefing, reconstructed character-level text evidence spans, 8-step decision path, and provenance graph DAG are assembled and sealed with a SHA-256 state checksum.

### C. What Outputs the User Sees
- **Overview Dashboard**: Active alert tally, canonical fused incidents, early signals, documents processed, SVG trend curves, decile score distribution, and administrative region risk summaries.
- **Live Surveillance Monitor**: Real-time push ticker connected to the WebSocket feed with connection health indicator.
- **Alerts Ledger & Drilldown**: Searchable, paginated table with tier tags, risk scores, and one-click access to the full detail modal.
- **Explainability Center**: 5W1H briefing, driving risk factors, character-level raw text citations with context windows, decision audit steps, and visual SVG Directed Acyclic Graph (DAG).
- **Geospatial Surveillance Map**: CartoDB dark-matter Leaflet map with alert rings, fused event markers, heatmap density clusters, and an **Unresolved Geometry Drawer** enforcing the zero coordinate fabrication guardrail.
- **Document Submission Portal**: Analyst interface with 3 pre-loaded demonstration scenarios (Nipah Kerala, Chandipura Gujarat, Dengue Pune).
- **System Observability**: Real-time health probes (`/health`, `/health/ready`, `/health/live`).

---

## 4. Epistemic Boundaries & Safety Guardrails
* **NOT a Clinical Diagnostic Tool:** EpiSense does not diagnose individual patients or replace medical personnel.
* **NOT an Outbreak Confirmation Authority:** EpiSense detects statistical aberrations in text; human epidemiologist verification is always required.
* **Zero Coordinate Fabrication:** If a location cannot be resolved to an authoritative gazetteer coordinate, geometry remains `null` and the entity is shown in the unresolved geometry drawer. Coordinates are never invented or guessed.
* **Deterministic Provenance:** All scoring and extraction logic executes deterministically without nondeterministic cloud LLM wrappers.

---

## 5. Getting Started & Running the Application

### Prerequisites
- Python 3.10+ (tested on Python 3.11)
- Node.js 18+ (tested on Node.js 24)

### Method A: Single Command Full-Stack Launcher (Recommended)
From the project root directory, run:
```bash
python run_all.py
```
This launcher starts both the FastAPI backend and the React frontend concurrently:
- **Operations Console (Frontend UI):** `http://localhost:5173`
- **Backend API Server:** `http://127.0.0.1:8000`
- **Interactive OpenAPI Documentation (Swagger UI):** `http://127.0.0.1:8000/docs`
- **ReDoc:** `http://127.0.0.1:8000/redoc`

---

### Method B: Manual Individual Startup

#### 1. Backend Server
```bash
python run_server.py
```
* Preloads the authoritative 110-document corpus into memory on startup (170 alerts, 170 fused events, 170 signals).

#### 2. Frontend Operations Console
```bash
cd frontend
npm install
npm run dev
```
* Accessible at: `http://localhost:5173`

---

## 6. Verification & Automated Test Suites

### A. Backend Pytest Suite
Run all 224 backend tests:
```bash
python -m pytest tests/ -v
```
*Verifies clinical NLP pipelines, event fusion, baseline estimators, risk scoring, explainability, streaming state, REST routes, and WebSocket endpoints (224 passed, 0 failed).*

### B. Frontend Vitest Suite
Run all 19 frontend unit, view, and component tests:
```bash
cd frontend
npm run test
```
*Verifies API client methods, WebSocket handling, metric cards, alert filters, AlertDetailModal, EventTable, SignalTable, SystemHealthCard, and zero coordinate fabrication guardrails (7 test files, 19 passed, 0 failed).*

### C. Frontend Production Build
Compile the production bundle:
```bash
cd frontend
npm run build
```
*Executes TypeScript compilation (`tsc -b`) and Vite production bundle optimization (`vite build`), emitting zero-error production assets into `dist/`.*

### D. End-to-End Live Ingestion & Flow Demonstration
Run the automated end-to-end flow demonstration covering all 11 stages:
```bash
python scratch/final_demonstration.py
```
*Verifies the full pipeline lifecycle: Document Submission → Clinical NLP → Event Fusion → Time-Series Binning → Aberration Anomaly Detection → 5D Risk Scoring → Explainability Dossier → 8-Step Cryptographic Audit Trail → Lineage DAG → GeoJSON Layer → Live WebSocket Push → Duplicate Deduplication.*

### E. System Integration Verification
Verify all 14 integration endpoints (A through N) with live backend responses:
```bash
python scratch/verify_frontend_integration.py
```

---

## 7. Directory Structure
```
NLP/
├── data/                       # Authoritative benchmarks, background corpus, gazetteers
│   └── benchmarks/             # 20 benchmark docs + 90 background corpus dispatches
├── docs/                       # Architectural specifications, ADRs, evaluations (Phases 1-12)
├── frontend/                   # React 19 + TypeScript + Vite Operations Console
│   ├── src/
│   │   ├── __tests__/          # Vitest & Testing Library suites (6 test files)
│   │   ├── components/         # Modular dashboard, alert, GIS map, explainability UI
│   │   ├── services/           # REST API client & native WebSocket stream
│   │   ├── types/api.ts        # 100% typed mirrors of backend Pydantic models
│   │   ├── views/              # 8 distinct surveillance views
│   │   ├── App.tsx             # Main routing shell
│   │   └── index.css           # Obsidian theme design system
│   └── package.json
├── src/episense/
│   ├── anomaly/                # EARS (C1/C2/C3) & Farrington statistical detectors
│   ├── api/                    # FastAPI routes, models, websocket, services, server
│   ├── explainability/         # 5W1H dossiers, audit trails, provenance DAG
│   ├── fusion/                 # Cross-source event clustering & quantity merging
│   ├── nlp/                    # Clinical NER, temporal extraction, assertion engine
│   ├── schemas/                # Pydantic v2 schemas across all surveillance layers
│   ├── scoring/                # 5-dimensional multi-criteria risk assessment
│   └── streaming/              # Continuous streaming pipeline & state store
├── tests/                      # Pytest suite (224 automated tests)
├── run_all.py                  # Single command full-stack launcher
├── run_server.py               # Backend startup script
└── README.md
```

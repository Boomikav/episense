# EpiSense Surveillance Operations Console (Frontend)

The EpiSense frontend is a real-time epidemiological intelligence dashboard built with React 19, TypeScript, and Vite. It connects directly to the Phase 12 continuous streaming surveillance API and native WebSocket feed.

## Architecture & Features

1. **Overview Dashboard**
   - Active alerts, canonical fused events, early signal aberration counts, and total ingested documents.
   - Decile risk score distribution and pathogen threat tier stratification.
   - SVG temporal trend chart tracking multi-source case accelerations over time.
   - Deterministic geographic surveillance summary across all administrative territories.
   - Recent alert and signal activity cards with instant drill-down.

2. **Live Surveillance Monitoring**
   - Direct connection to native surveillance feed (`WS /api/v1/ws/surveillance`).
   - Dynamic subscription topic filtering (pathogen, minimum alert score, alert tier).
   - Real-time event ticker displaying incoming alerts, fused incidents, and signals.
   - Auto-reconnect with exponential backoff and periodic heartbeat pings.

3. **Epidemiological Alerts & Multi-Dimensional Scoring**
   - Paginated, searchable alert ledger (`GET /api/v1/alerts`).
   - 5-dimensional risk score breakdown (Anomaly, Threat, Evidence, Certainty, Spatial).
   - Interactive detail modal with comprehensive gating rationale and lifecycle status.

4. **Forensic Explainability & Provenance DAG**
   - **5W1H Briefing**: Structured Who, What, When, Where, Why, and How epidemiological breakdown.
   - **Reconstructed Evidence Spans**: Character-level citation matches against immutable raw source documents with context windows.
   - **Decision Audit Trail**: 8-step decision path sealed with a cryptographic SHA-256 state checksum.
   - **Provenance Graph**: Interactive visual Directed Acyclic Graph (DAG) tracing alerts back through signals, time bins, and fused events to original source documents.

5. **Canonical Fused Events & Early Warning Signals**
   - Fused incidents view with case/death aggregations, temporal windows, and independent source group counts.
   - Early statistical signals view showing EARS (C1/C2/C3) and Farrington aberrations, expected baselines, and reliability states.

6. **Geospatial Surveillance Map**
   - Dark-matter GIS canvas powered by Leaflet.
   - Color-coded severity alert rings and fused incident markers.
   - Interactive density clusters and heatmap layers.
   - **Zero Coordinate Fabrication Guardrail**: Locations without authoritative gazetteer coordinates are strictly segregated into an unresolved geometry drawer and never hallucinated on map coordinates.

7. **Document Ingestion & Pipeline Simulation**
   - Analyst submission form with pre-loaded outbreak scenarios (Nipah Kerala, Chandipura Gujarat, Dengue Pune).
   - Direct injection into `POST /api/v1/documents`.
   - Real-time pipeline response (accepted, duplicate skipped, or dead-lettered) with immediate fan-out to WebSocket subscribers.

8. **System Health & Observability**
   - Multi-probe health dashboard connecting to `/health`, `/health/ready`, and `/health/live`.

---

## Getting Started

### Prerequisites
- Node.js 18+ (tested on Node.js 24)
- Running EpiSense backend server (`http://localhost:8000`)

### Environment Configuration
Copy `.env.example` to `.env`:
```bash
cp .env.example .env
```
Default configuration:
```env
VITE_API_BASE_URL=http://localhost:8000
```
*(WebSocket feed URL `ws://localhost:8000/api/v1/ws/surveillance` is automatically derived from `VITE_API_BASE_URL`)*.

### Installation
```bash
npm install
```

### Running in Development Mode
```bash
npm run dev
```
The application will be accessible at: `http://localhost:5173`.

### Running Automated Test Suite
```bash
npm run test
```
Executes all 15 Vitest and React Testing Library tests covering API clients, WebSocket handling, dashboard cards, alert filters, and zero-coordinate fabrication guardrails.

### Building for Production
```bash
npm run build
```
Typechecks and compiles production bundle to `dist/`.

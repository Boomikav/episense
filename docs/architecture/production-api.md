# EpiSense Production REST API Architecture (Phase 12)

## 1. System Overview & Service Boundary

The EpiSense Production REST API exposes the underlying epidemiological intelligence engines (Phases 1–11) through a strongly typed, deterministic, and stateless HTTP service layer.

```text
                  External Consumers
     (Monitoring Dashboards, GIS Systems, Triage Clients)
                           │
             ┌─────────────┴─────────────┐
             │                           │
          REST API                 WebSocket Feed
      (/api/v1/...)             (/api/v1/ws/surveillance)
             │                           │
             └─────────────┬─────────────┘
                           ▼
               EpiSense API Layer (FastAPI)
         Middleware: Correlation, Security, CORS
                           │
       ┌───────────────────┼───────────────────┐
       ▼                   ▼                   ▼
 Alert Query Service  Event Query Service  Geo Query Service
       │                   │                   │
       └───────────────────┼───────────────────┘
                           ▼
               SurveillanceStateStore
             (In-Memory / SQLite State)
                           ▲
                           │ Updates
             ContinuousSurveillancePipeline
             (Phases 1–10 Domain Engines)
```

### Architectural Principle: Zero Duplicate Logic
The API layer operates strictly as a service boundary. It **never** recalculates risk scores, baseline statistics, Farrington/EARS anomalies, event fusion, or explainability dossiers. All domain entities originate from the verified Phase 1–11 pipelines and are queried via service abstractions.

---

## 2. API Endpoint Catalog

All public endpoints are versioned under `/api/v1/`.

| Method | Path | Summary | Description & Query Parameters |
| :--- | :--- | :--- | :--- |
| `GET` | `/health` | Service Health | Overall health, uptime, and engine availability |
| `GET` | `/health/ready` | Readiness Probe | Confirms state store readiness and active alert count |
| `GET` | `/health/live` | Liveness Probe | Kubernetes liveness probe |
| `POST` | `/api/v1/documents` | Ingest Document | Ingests news/bulletin dispatch into continuous pipeline |
| `GET` | `/api/v1/alerts` | Query Alerts | Deterministic alert listing with multi-field filtering |
| `GET` | `/api/v1/alerts/{alert_id}` | Alert Detail | Full epidemiological alert object |
| `GET` | `/api/v1/alerts/{alert_id}/dossier` | Explainability Dossier | 5W1H briefing, driving factors, and evidence |
| `GET` | `/api/v1/alerts/{alert_id}/audit` | Audit Trail | 8-step scoring decision trail with SHA-256 checksum |
| `GET` | `/api/v1/alerts/{alert_id}/provenance` | Provenance Graph | Directed acyclic lineage graph and traversal |
| `GET` | `/api/v1/events` | Query Fused Events | Canonical fused epidemiological incidents |
| `GET` | `/api/v1/events/{event_id}` | Fused Event Detail | Specific fused event with independent source count |
| `GET` | `/api/v1/signals` | Query Early Signals | Statistical aberration signals with baseline info |
| `GET` | `/api/v1/signals/{signal_id}` | Signal Detail | Single early warning signal observation |
| `GET` | `/api/v1/geo/alerts` | Alert GeoJSON | RFC 7946 FeatureCollection of alerts |
| `GET` | `/api/v1/geo/events` | Event GeoJSON | RFC 7946 FeatureCollection of fused events |
| `GET` | `/api/v1/geo/heatmap` | Risk Heatmap GeoJSON | Point features weighted by composite risk score |
| `GET` | `/api/v1/geo/summary` | Geospatial Summary | Regional alert and event aggregations |
| `WS` | `/api/v1/ws/surveillance` | Real-Time Feed | WebSocket streaming updates of incoming events |

---

## 3. Dependency Injection Architecture

To prevent global mutable state and support automated unit/integration testing with isolated state, all core dependencies are managed through FastAPI's dependency injection system in `episense.api.dependencies`:

```python
# episense/api/dependencies.py
def get_state_store() -> SurveillanceStateStore: ...
def get_pipeline() -> ContinuousSurveillancePipeline: ...
def get_publisher() -> SurveillanceEventPublisher: ...
def get_geo_resolver() -> GeoResolver: ...
def get_alert_service(...) -> AlertQueryService: ...
def get_event_service(...) -> EventQueryService: ...
def get_signal_service(...) -> SignalQueryService: ...
def get_provenance_service(...) -> ProvenanceQueryService: ...
def get_geo_service(...) -> GeoQueryService: ...
```

In tests, instances can be replaced cleanly via `set_dependencies(...)` and restored via `reset_dependencies()`.

---

## 4. Query Service Layer & Deterministic Pagination

FastAPI route handlers delegate data operations to dedicated service classes:
- **`AlertQueryService`**: Filters by `pathogen`, `location`, `alert_tier`, `threat_tier`, `min_score`, `max_score`, `start_date`, `end_date`.
  - **Deterministic Ordering**: `composite_score DESC, alert_id ASC`.
- **`EventQueryService`**: Filters by `pathogen`, `location`, `assertion_status`, `source_group`, `start_date`, `end_date`.
  - **Deterministic Ordering**: `event_window_end DESC, fused_event_id ASC`.
- **`SignalQueryService`**: Filters by `pathogen`, `location`, `signal_level`, `detection_method`, `reliability_status`.
  - **Deterministic Ordering**: `target_period_start DESC, signal_id ASC`.
- **`ProvenanceQueryService`**: Fetches dossiers, audits, and DAGs directly from the state store or generates them on demand using Phase 10 engines if absent.
- **`GeoQueryService`**: Projects domain models to RFC 7946 GeoJSON representations with grounded coordinates.

All collections use bounded pagination (`page >= 1`, `1 <= page_size <= max_page_size`) returning:
```json
{
  "total": 170,
  "page": 1,
  "page_size": 20,
  "total_pages": 9,
  "items": [...]
}
```

---

## 5. Centralized Error Model

Errors return consistent, machine-readable JSON bodies conforming to `APIErrorResponse`:

```json
{
  "error": {
    "code": "ALERT_NOT_FOUND",
    "message": "Alert with identifier '76f8fdcb-537a-518d-96c9-eb3d04db939f' was not found.",
    "request_id": "req-9b819f72-911a",
    "details": null
  }
}
```

### HTTP Status Code Mapping
- `400 Bad Request` (`BAD_REQUEST`, `INGESTION_FAILED`): Malformed syntax or unexpected processing failures.
- `404 Not Found` (`{RESOURCE}_NOT_FOUND`): Non-existent alert, event, signal, or document.
- `409 Conflict` (`DUPLICATE_RESOURCE`): Conflicting identifiers.
- `413 Content Too Large` (`PAYLOAD_TOO_LARGE`): Request payload exceeding `max_payload_bytes`.
- `422 Unprocessable Content` (`VALIDATION_ERROR`): Schema validation errors, invalid UUIDs, or empty required strings.
- `500 Internal Server Error` (`INTERNAL_SERVER_ERROR`): Unhandled exceptions (internal stack traces are logged securely and never leaked).

---

## 6. Request Correlation & Determinism Protection

The `RequestCorrelationMiddleware` automatically inspects incoming requests for an `X-Request-ID` header (or generates a standard correlation ID if omitted) and attaches it to response headers and error diagnostics.

**Strict Determinism Invariant**: Request correlation IDs operate exclusively at the HTTP boundary. They **never** interact with or modify:
- Domain UUID5 identifiers (`alert_id`, `fused_event_id`, `bin_id`, `signal_id`, `dossier_id`)
- Cryptographic content hashes (`content_hash_sha256`)
- 8-step decision audit checksums (`audit_checksum`)
- GeoJSON feature sequencing

---

## 7. Security Boundary & Production Hardening

1. **Payload Size Guard**: Enforced via `PayloadSizeLimitMiddleware`. Requests exceeding configured `max_payload_bytes` (default 1 MB) are rejected immediately with HTTP 413.
2. **CORS Policy**: Configured via `CORSMiddleware` with explicit allowed origins, methods, and headers.
3. **Strict Validation**: All endpoints use Pydantic v2 schemas with `extra="forbid"`, preventing property injection and prototype pollution.
4. **No Arbitrary Deserialization**: JSON serialization only; no unsafe pickle or eval execution.
5. **No Filesystem Traversal**: File manifest paths are strictly managed in local configuration and never accepted from untrusted HTTP parameters.

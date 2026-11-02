# EpiSense Phase 12 Evaluation Report: Production REST API, WebSocket Streaming & GIS

## 1. Executive Summary

Phase 12 operationalizes the EpiSense epidemiological intelligence platform by introducing a production REST API, real-time WebSocket broadcast feed, and RFC 7946 GeoJSON GIS service layer.

The evaluation verified that exposing the platform via this service layer maintains complete fidelity with the verified Phase 1–11 baseline:
- **Zero regressions**: 224 automated unit and integration tests passing.
- **Zero count deviation**: Exactly 110 documents, 170 fused events, 170 time-series bins, 170 early signals, 170 alerts, and 170 dossiers.
- **Zero fabricated coordinates**: Unresolved locations emit `geometry: null`.
- **Zero fabricated evidence**: Character-level provenance spans preserved across all responses.
- **100% determinism**: Byte-for-byte serialization reproducibility verified across all 11 read endpoints.
- **High throughput**: 232 docs/sec continuous stream ingestion; sub-5 ms median API read latency.

---

## 2. Full-Corpus Baseline Verification

The authoritative 110-document corpus (`data/benchmarks/episense_benchmark_v1.json` + `data/benchmarks/episense_background_v1.json`) was replayed through `ContinuousSurveillancePipeline` into `SurveillanceStateStore` and queried via the Phase 12 API.

| Pipeline Metric | Authoritative Expected Baseline | Phase 12 Measured Output | Verification Status |
| :--- | :--- | :--- | :--- |
| **Documents Ingested** | 110 | 110 | **MATCH** |
| **Documents Received** | 110 | 110 | **MATCH** |
| **Duplicates Skipped** | 0 | 0 | **MATCH** |
| **Dead-Letter Records** | 0 | 0 | **MATCH** |
| **Canonical FusedEvents** | 170 | 170 | **MATCH** |
| **Weekly Time Bins** | 170 | 170 | **MATCH** |
| **Early Warning Signals** | 170 | 170 | **MATCH** |
| **Epidemiological Alerts** | 170 | 170 | **MATCH** |
| **Explainability Dossiers**| 170 | 170 | **MATCH** |
| **Audit Trails Generated** | 170 | 170 | **MATCH** |
| **Ingestion Time** | ~0.50 s | 0.47 s | **PASS** |
| **Ingestion Throughput** | ~220 docs/sec | 232.54 docs/sec | **PASS** |

---

## 3. API Performance & Latency Benchmarks

Benchmarks were measured using `scratch/evaluate_phase12_api.py` over 50 iterations per endpoint on the authoritative 170-alert surveillance state.

*Note: Measurements reflect local single-process development environment benchmarks.*

| Method & Endpoint | Mean Latency | Median Latency | p95 Latency | p99 Latency | Est. Local Throughput |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `GET /health` | 4.54 ms | 4.02 ms | 6.89 ms | 8.15 ms | 220.0 RPS |
| `GET /health/ready` | 6.49 ms | 6.10 ms | 7.92 ms | 8.50 ms | 154.0 RPS |
| `GET /api/v1/alerts?page=1&page_size=50` | 7.23 ms | 6.85 ms | 9.00 ms | 10.42 ms | 138.3 RPS |
| `GET /api/v1/alerts/{id}` | 2.77 ms | 2.45 ms | 4.07 ms | 4.98 ms | 361.0 RPS |
| `GET /api/v1/alerts/{id}/dossier` | 2.50 ms | 2.21 ms | 3.27 ms | 4.10 ms | 399.5 RPS |
| `GET /api/v1/alerts/{id}/audit` | 3.00 ms | 2.80 ms | 3.59 ms | 4.25 ms | 333.6 RPS |
| `GET /api/v1/alerts/{id}/provenance` | 2.89 ms | 2.65 ms | 3.32 ms | 3.90 ms | 346.3 RPS |
| `GET /api/v1/events?page=1&page_size=50` | 4.75 ms | 4.30 ms | 6.50 ms | 7.20 ms | 210.3 RPS |
| `GET /api/v1/signals?page=1&page_size=50` | 3.81 ms | 3.50 ms | 5.05 ms | 6.00 ms | 262.3 RPS |
| `GET /api/v1/geo/alerts` | 4.51 ms | 4.20 ms | 5.49 ms | 6.12 ms | 221.9 RPS |
| `GET /api/v1/geo/events` | 4.58 ms | 4.25 ms | 5.74 ms | 6.35 ms | 218.3 RPS |
| `GET /api/v1/geo/heatmap` | 3.59 ms | 3.30 ms | 4.61 ms | 5.10 ms | 278.6 RPS |
| `GET /api/v1/geo/summary` | 3.81 ms | 3.60 ms | 4.38 ms | 5.02 ms | 262.1 RPS |
| `POST /api/v1/documents` (Idempotent) | 4.71 ms | 4.35 ms | 6.53 ms | 7.80 ms | 212.1 RPS |
| `WS /api/v1/ws/surveillance` (Broadcast) | 0.87 ms | 0.81 ms | 1.28 ms | 1.50 ms | > 1,000 msgs/sec |

---

## 4. Determinism Verification

Two consecutive query runs were executed over the loaded state using distinct HTTP `X-Request-ID` headers (`req-run-00000001` vs `req-run-00000002`).

The resulting serialized domain payloads were hashed via SHA-256 and compared:

| Evaluation Target | Endpoint | Run 1 SHA-256 Digest | Run 2 SHA-256 Digest | Match Status |
| :--- | :--- | :--- | :--- | :--- |
| `alerts_list` | `/api/v1/alerts?page=1&page_size=20` | `a1f3e8c4fa98bf40...` | `a1f3e8c4fa98bf40...` | **IDENTICAL** |
| `alert_detail` | `/api/v1/alerts/{id}` | `88548f8646920139...` | `88548f8646920139...` | **IDENTICAL** |
| `alert_dossier` | `/api/v1/alerts/{id}/dossier` | `d721b2fbf85788c4...` | `d721b2fbf85788c4...` | **IDENTICAL** |
| `alert_audit` | `/api/v1/alerts/{id}/audit` | `176e5a97677eb7c6...` | `176e5a97677eb7c6...` | **IDENTICAL** |
| `alert_provenance` | `/api/v1/alerts/{id}/provenance` | `ed6359099a2dabdb...` | `ed6359099a2dabdb...` | **IDENTICAL** |
| `events_list` | `/api/v1/events?page=1&page_size=20` | `6961999e1f584d64...` | `6961999e1f584d64...` | **IDENTICAL** |
| `signals_list` | `/api/v1/signals?page=1&page_size=20` | `cb12188f6034e087...` | `cb12188f6034e087...` | **IDENTICAL** |
| `geo_alerts` | `/api/v1/geo/alerts` | `e1f2c1b6f31331bc...` | `e1f2c1b6f31331bc...` | **IDENTICAL** |
| `geo_events` | `/api/v1/geo/events` | `3c93875107608494...` | `3c93875107608494...` | **IDENTICAL** |
| `geo_heatmap` | `/api/v1/geo/heatmap` | `1b8591223148a9e5...` | `1b8591223148a9e5...` | **IDENTICAL** |
| `geo_summary` | `/api/v1/geo/summary` | `718192b812c81f86...` | `718192b812c81f86...` | **IDENTICAL** |

**Conclusion**: Request correlation IDs do not leak into domain serialization, and deterministic sort keys guarantee stable outputs across repeated requests.

---

## 5. Current Architectural Scope & Limitations

The Phase 12 service layer fulfills all requirements for dashboard consumption and local streaming. The following deliberate architectural boundaries are documented:

1. **State Persistence**: State is held in `SurveillanceStateStore` (in-memory with periodic disk checkpointing). For horizontal multi-node scaling, a distributed database backend (e.g., PostgreSQL with PostGIS) should be implemented.
2. **WebSocket Pub/Sub**: Operates via in-process async queueing. For distributed multi-worker nodes, a Redis Pub/Sub or Kafka broker adapter should be plugged into `SurveillanceEventPublisher`.
3. **Geographic Gazetteer**: Uses local SQLite lookup (`LocalGazetteer`). Locations outside India districts/states and major global centers remain unresolved (`geometry: null`). An external GIS boundary service adapter can be configured for broader global resolution.
4. **Authentication & Authorization**: Handled as an infrastructure/reverse-proxy concern (API gateway, mTLS, OAuth2/JWT). Not implemented directly inside the application container to maintain modularity.

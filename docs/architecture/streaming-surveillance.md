# EpiSense Continuous Epidemiological Surveillance Pipeline — Architectural Specification

**Document Version:** 1.0.0  
**Phase:** Phase 11 (Real-Time Streaming Ingestion & Continuous Epidemiological Surveillance Pipeline)  
**Status:** IMPLEMENTED & VERIFIED  
**Target Scope:** Source-Agnostic Ingestion, State Store Management, Idempotent Processing, Late-Arrival Handling, Alert Lifecycle Tracking, Dead-Letter Failure Isolation, and Deterministic Checkpointing  

---

## 1. Architectural Philosophy & Objectives

Public health surveillance requires continuous, incremental intelligence. Outbreak signals unfold dynamically as new reports, clinical bulletins, news dispatches, and laboratory updates arrive asynchronously from disparate sources. Recomputing the entire historical corpus from scratch upon every incoming document is computationally prohibitive, latency-prone, and contrary to continuous monitoring paradigms.

**Phase 11** transitions EpiSense from a purely batch-oriented analytical engine into a **production-grade continuous surveillance pipeline**. The architecture enables incremental document processing, real-time event fusion, temporal binning, anomaly detection, multi-criteria risk scoring, and explainability dossier generation, while preserving 100% of the deterministic, auditable, and zero-fabrication guarantees established in Phases 1–10.

```text
Incoming Document / News / Bulletin / Dispatch
        │
        ▼
[1. Ingestion Abstraction] (src/episense/streaming/ingestion.py)
  ├── Source-agnostic IngestionSource (Single, Batch, FileStream, Mock)
  └── StreamingDocumentValidator (schema validation, UUID/hash verification, clock bounds)
        │
        ├── [Malformed / Invalid] ──► DeadLetterQueue (Isolated Failure Record)
        │
        ▼
[2. Idempotency & Deduplication Gate] (src/episense/streaming/state.py)
  ├── Processed Document ID registry check
  └── SHA-256 Content Hash collision check
        │
        ├── [Duplicate Detected] ──► Return IngestionStatus.DUPLICATE_SKIPPED (0 Count Inflation)
        │
        ▼
[3. NLP Extraction Engine] (src/episense/nlp/pipeline.py)
  ├── Entity recognition (Diseases, Symptoms, Locations, Quantities)
  └── Context association, assertion resolution, and temporal normalization
        │
        ▼
[4. Event Candidate Builder] (src/episense/events/builder.py)
  └── Deterministic UUID5 observation and candidate derivation
        │
        ▼
[5. Incremental Event Fusion] (src/episense/fusion/engine.py)
  ├── Match against active FusedEvents in SurveillanceStateStore
  ├── Multi-source clustering with anti-inflation quantity rules
  └── Creates new FusedEvent OR updates existing cluster with provenance edge
        │
        ▼
[6. Incremental Time-Series Engine] (src/episense/baseline/timeseries.py)
  ├── Late-Arrival Routing: Event date precedence over publication date
  ├── Assigns observation to authentic ISO year-week (historical or contemporary)
  └── Anti-inflation quantity aggregation & conflict tracking
        │
        ▼
[7. Baseline & Early Signal Detector] (src/episense/anomaly/detector.py)
  ├── Historical reference window retrieval from StateStore (up to 52 prior bins)
  ├── EARS C1/C2/C3 & Farrington dispersion-aware statistical evaluations
  └── Single-source signal downgrading to prevent uncorroborated panic alerts
        │
        ▼
[8. Risk Scorer & Alert Lifecycle Engine] (src/episense/scoring/scorer.py)
  ├── Multi-criteria bounded scoring: S_anomaly, S_threat, S_evidence, S_certainty, S_spatial
  ├── Safety ceilings & gating (negation, conflicting data, insufficient history)
  └── Lifecycle State Machine: NEW, UPDATED, CONFIRMED_UNCHANGED, RESOLVED
        │
        ▼
[9. Explainability & Provenance Traversal] (src/episense/explainability/dossier.py)
  ├── Reconstructs character-level text spans [start_char:end_char]
  ├── Generates 5W1H briefing & SHA-256 decision audit trail
  └── Saves revision snapshot in alert_history
        │
        ▼
SurveillanceEventUpdate & State Store Checkpoint (Tamper-evident SHA-256 checksum)
```

---

## 2. Core Domain Schemas (`src/episense/schemas/streaming.py`)

Streaming state management, operational monitoring, and error handling are governed by strongly typed Pydantic models:

| Schema / Enum | Role | Key Attributes |
| :--- | :--- | :--- |
| `IngestionStatus` | Processing outcome enum. | `ACCEPTED`, `DUPLICATE_SKIPPED`, `REJECTED`, `FAILED`. |
| `AlertLifecycleState` | Status of alert in lifecycle. | `NEW`, `UPDATED`, `CONFIRMED_UNCHANGED`, `RESOLVED`. |
| `DeadLetterRecord` | Dead-letter queue record. | `record_id`, `document_id`, `stage`, `error_type`, `error_message`, `raw_payload`, `timestamp`. |
| `SurveillanceMetrics` | Operational telemetry. | `documents_received`, `documents_accepted`, `duplicates_skipped`, `documents_rejected`, `fused_events_created`, `fused_events_updated`, `bins_created`, `bins_updated`, `signals_generated`, `alerts_generated`, `alerts_updated`, `processing_failures`, `provenance_failures`. |
| `SurveillanceEventUpdate` | Single-document emission. | `update_id`, `document_id`, `status`, `fused_events_affected`, `bins_affected`, `signals_generated`, `alerts_generated`, `alert_lifecycle_states`, `timestamp`, `message`. |
| `SurveillanceStateCheckpoint` | Immutable state snapshot. | `checkpoint_id`, `sequence_number`, `timestamp`, `metrics`, `state_checksum_sha256`, `total_documents_processed`, `total_fused_events`, `total_bins`, `total_alerts`, `dead_letter_count`. |

---

## 3. Streaming Ingestion Abstraction (`src/episense/streaming/ingestion.py`)

The ingestion layer abstracts data sources, decoupling upstream transport mechanisms (HTTP webhooks, S3 buckets, RSS feeds, local files) from analytical processing.

### Clean Source-Agnostic Interface
```python
class IngestionSource(ABC):
    @abstractmethod
    def stream_documents(self) -> Generator[Union[Document, Dict[str, Any]], None, None]:
        """Yields Document instances or raw dictionary payloads."""
        pass
```

### Concrete Implementations
1. `MockIngestionSource`: Yields pre-configured documents with deterministic delays for unit and integration testing.
2. `SingleDocumentIngestionSource`: Ingests an individual document or payload for webhook/real-time handler integration.
3. `DocumentBatchIngestionSource`: Ingests in-memory batches of documents while preserving ingestion order.
4. `FileStreamIngestionSource`: Streams line-delimited JSON (`.jsonl`) or JSON array files incrementally without loading massive corpora entirely into RAM.

### Streaming Document Validation
`StreamingDocumentValidator` validates documents before they enter the analytical pipeline:
- Validates text length ($\ge 1$ char) and title presence.
- Verifies SHA-256 `content_hash` against raw `text` content to prevent corrupted payloads.
- Validates ISO-8601 publication timestamps and flags future-dated anomalies ($> 24$ hours ahead of reference clock).
- Coerces raw dictionary payloads into strongly typed `Document` instances.

---

## 4. Surveillance State Store (`src/episense/streaming/state.py`)

The `SurveillanceStateStore` provides an in-memory, file-backed state repository with deterministic query and update semantics.

### Primary State Registries
1. `processed_document_ids: Set[UUID]`: Tracks all ingested document IDs.
2. `processed_content_hashes: Set[str]`: Tracks all ingested document SHA-256 hashes to catch duplicate content submitted under new UUIDs.
3. `candidates_by_id: Dict[UUID, EventCandidate]`: Registry of all extracted event candidates.
4. `fused_events: Dict[UUID, FusedEvent]`: Active registry of canonical fused events.
5. `bins_by_id: Dict[UUID, EpidemiologicalTimeBin]`: Active registry of time-series bins.
6. `series_bins: Dict[Tuple[str, str], List[UUID]]`: Temporal index mapping `(disease_key, geo_key)` to chronologically sorted bin IDs.
7. `signals: Dict[UUID, SignalObservation]`: Active registry of generated early signals.
8. `alerts: Dict[UUID, EpidemiologicalAlert]`: Current active alerts.
9. `alert_history: Dict[UUID, List[EpidemiologicalAlert]]`: Full audit trail of alert revisions over time.
10. `dead_letter_queue: List[DeadLetterRecord]`: Structured failure isolation log.

### Tamper-Evident SHA-256 Checksum
The state store computes a deterministic SHA-256 checksum over its canonical sorted state:
$$\text{Checksum} = \mathcal{H}\left(\text{doc\_ids} \parallel \text{fused\_event\_ids} \parallel \text{bin\_ids} \parallel \text{alert\_ids} \parallel \text{alert\_tiers} \parallel \text{scores}\right)$$
Any unauthorized modification, dropped record, or non-deterministic reordering immediately alters this checksum.

### Checkpointing & Zero-Loss Recovery
`state.checkpoint(checkpoint_dir)` serializes all state tables into canonical JSON artifacts (`checkpoint.json`, `metrics.json`, `dead_letter_queue.json`, `fused_events.json`, `bins.json`, `alerts.json`). `state.restore(checkpoint_dir)` reconstructs the identical state, enabling pipeline restarts without data loss or duplicate reprocessing.

---

## 5. Critical Surveillance Policies

### Exactly-Once & Idempotency Strategy
Epidemiological metrics cannot tolerate double-counting. If an upstream wire service syndicates the same document three times or a network retry resends a bulletin:
1. Document ID or content hash is matched in `processed_document_ids` or `processed_content_hashes`.
2. Pipeline immediately returns `IngestionStatus.DUPLICATE_SKIPPED`.
3. `metrics.duplicates_skipped` is incremented.
4. **Zero** counts are added to time-series bins, **zero** duplicate fused events are created, and **zero** duplicate alerts or provenance edges are recorded.

### Late-Arriving Event Policy
Reports frequently mention outbreaks that occurred days or weeks earlier (e.g. an article published in August 2024 reporting Cholera cases from May 2024).
- **Rule:** Event time strictly supersedes publication time.
- The pipeline resolves the authentic `normalized_start` timestamp of the event.
- The observation is routed to the historical bin corresponding to that period (e.g., `2024-W21`), updating historical baseline baselines.
- The observation is **never** artificially injected into the publication week (e.g., `2024-W32`), preventing artificial contemporary spikes.

### Generic Historical Segregation & Negation Handling
- Events with `assertion_status == HISTORICAL` lacking explicit temporal anchors are quarantined to historical background and excluded from contemporary surveillance bins.
- Events with `assertion_status == NEGATED` (e.g., *"tested negative for Nipah"*) are completely suppressed from positive case/death incidence counts and gated to `AlertTier.INFORMATIONAL` with score $0.0$.

### Alert Lifecycle State Machine
Alerts evolve as new corroborating reports arrive:
1. `NEW`: First time an alert is generated for a `(disease_key, geo_key, period)` window.
2. `UPDATED`: Additional corroborating documents or changed case numbers modify the composite risk score or alert tier.
3. `CONFIRMED_UNCHANGED`: New documents arrive confirming the situation without altering the risk score or tier.
4. `RESOLVED`: Epidemiological incidence subsides back below baseline thresholds.
Every revision is appended to `alert_history[alert_id]`, ensuring historical alerts are never silently overwritten or deleted.

### Dead-Letter Queue & Failure Isolation
Malformed documents, JSON syntax errors, or localized NLP extraction failures are caught by try/except boundaries, formatted into typed `DeadLetterRecord` instances, and logged to `dead_letter_queue`. The pipeline isolates the failing record and continues processing subsequent documents seamlessly.

---

## 6. Batch vs Streaming Equivalence & Determinism

The streaming pipeline was designed as an extension of the established batch architecture:
- **Batch Mode:** Processes a static snapshot of candidates across an entire corpus simultaneously.
- **Streaming Mode:** Ingests documents sequentially, clustering observations incrementally into active fused events and dynamically updating time-series bins and alert dossiers.
- **Replay Verification:** Replaying the authoritative 110-document corpus twice produces **bit-for-bit identical** outputs across all serialized artifacts (`checkpoint.json`, `metrics.json`, `alerts.json`, `fused_events.json`, `bins.json`) with an identical SHA-256 state store checksum.

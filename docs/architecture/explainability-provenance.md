# EpiSense Explainability Dossiers, Audit Trails & Provenance Traversal Engine — Architectural Specification

**Document Version:** 1.0.0  
**Phase:** Phase 10 (Explainability Dossiers, Audit Trails & Provenance Traversal Engine)  
**Status:** IMPLEMENTED & VERIFIED  
**Target Scope:** Bidirectional Lineage Graphs, Character-Level Evidence Reconstruction, Decision Path Auditing with SHA-256 Integrity, Structured 5W1H Briefings, and Deterministic Dossier Generation  

---

## 1. Architectural Philosophy & Objectives

In automated epidemic intelligence, numerical scores and black-box alert levels are insufficient for public health decision-makers. An alert that assigns a risk score of $0.75$ without transparent reasoning cannot be audited, verified, or defended in critical public health interventions.

Phase 10 introduces the **Explainability Dossiers, Audit Trails & Provenance Traversal Engine**. It establishes a complete, bidirectional audit trail that allows every final `EpidemiologicalAlert` to be traced backward through its full analytical lineage down to the exact character spans in the underlying source text:

$$\text{EpidemiologicalAlert} \longrightarrow \text{Risk Breakdown} \longrightarrow \text{SignalObservation} \longrightarrow \text{BaselineEstimate} / \text{TimeBin} \longrightarrow \text{FusedEvent} \longrightarrow \text{Document} \longrightarrow \text{EvidenceReference}$$

### Core Invariants:
1. **The Zero-Fabrication Principle:** The system must **never** invent missing evidence. If a source document or span is missing or invalid, the engine explicitly marks provenance as incomplete, records the specific gap, and preserves the alert without manufacturing artificial certainty.
2. **Character-Level Ground Truth:** Every claimed fact (disease, case count, death count, location, event date) is verified against raw document text offsets `[start_char:end_char]`.
3. **Cryptographic Decision Integrity:** Every audit trail computes a deterministic SHA-256 checksum over the complete decision state (inputs, weights, rules, penalties, ceilings, and final output), providing tamper-evident reproducibility.
4. **Human-Centered Explainability:** Rather than expecting epidemiologists to parse raw JSON logs, the engine synthesizes a structured **Epidemiological 5W1H** briefing (Who, What, When, Where, Why, How) with surrounding context snippets.

```text
EpidemiologicalAlert (Phase 9 Output: Tier, Scores, Constraints)
        ↓
AuditTrailEngine (src/episense/explainability/auditor.py)
  ├── 8 discrete decision steps (anomaly -> threat -> evidence -> certainty -> spatial -> composite -> ceilings -> tier)
  └── SHA-256 state checksum computation
        ↓
ProvenanceGraphBuilder (src/episense/explainability/graph.py)
  ├── Multi-level DAG construction (Alert, Signal, Baseline, TimeBin, FusedEvent, Document, EvidenceSpan)
  ├── Kahn's algorithm acyclicity enforcement (is_acyclic = True)
  └── Deterministic traversal queries (Alert -> Documents, Alert -> Evidence, Alert -> FusedEvents)
        ↓
EvidenceSpanReconstructor (src/episense/explainability/reconstructor.py)
  ├── Raw text slicing: raw_text[start_char:end_char]
  ├── Boundary validation: 0 <= start <= end <= len(doc)
  ├── Textual integrity verification: extracted == expected span text
  └── Surrounding context window extraction (e.g. ±50 characters)
        ↓
DossierGenerator (src/episense/explainability/dossier.py)
  ├── Epidemiological 5W1H briefing synthesis
  ├── Completeness ratio assessment & gap logging
  └── Implements abstract EvidenceProvider interface
        ↓
ExplainabilityDossier (UUID5 IDs, Created At anchored to period_end)
```

---

## 2. Core Domain Schemas (`src/episense/schemas/explainability.py`)

Phase 10 introduces strongly typed Pydantic models for lineage graphs, audit trails, and dossiers:

| Schema / Enum | Role | Definition & Fields |
| :--- | :--- | :--- |
| `ProvenanceNodeType` | Entity type in lineage DAG. | `ALERT`, `SIGNAL`, `BASELINE`, `TIME_BIN`, `FUSED_EVENT`, `DOCUMENT`, `EVIDENCE_SPAN`. |
| `ProvenanceEdgeType` | Lineage relationship type. | `SCORED_FROM`, `BASELINE_FOR`, `AGGREGATED_INTO`, `COMPOSED_OF`, `GROUNDED_IN`, `EVIDENCED_BY`, `SPAN_OF`. |
| `ReconstructedEvidenceSpan` | Verified character span. | `document_id`, `source_id`, `start_char`, `end_char`, `expected_text`, `extracted_text`, `surrounding_context`, `attribute_role`, `is_valid`, `validation_error`. |
| `ProvenanceNode` | Discrete graph vertex. | `node_id`, `node_type`, `entity_id`, `label`, `metadata`. |
| `ProvenanceEdge` | Directed graph connection. | `source_node_id`, `target_node_id`, `edge_type`, `description`. |
| `ProvenanceGraph` | Deterministic lineage DAG. | `graph_id` (UUID5), `alert_id`, `nodes`, `edges`, `is_acyclic`, `completeness_ratio`, `missing_nodes`. |
| `AuditDecisionStep` | Discrete scoring decision. | `step_number`, `step_name`, `inputs`, `rule_applied`, `output_value`, `is_gated`, `gating_detail`. |
| `AlertAuditTrail` | Complete decision audit log. | `audit_id` (UUID5), `alert_id`, `signal_id`, `decision_steps` (1–8), `applied_weights`, `score_breakdown`, `final_score`, `final_alert_tier`, `is_gated`, `audit_checksum` (SHA-256). |
| `Epidemiological5W1H` | Structured public health briefing. | `who_pathogen`, `what_event`, `when_period`, `where_location`, `why_aberration`, `how_corroboration`. |
| `ExplainabilityDossier`| Comprehensive audit dossier. | `dossier_id` (UUID5), `alert_id`, `briefing`, `executive_summary`, `driving_risk_factors`, `applied_safety_constraints`, `reconstructed_evidence`, `audit_trail`, `provenance_graph`, `provenance_complete`, `completeness_notes`. |

---

## 3. Evidence Span Reconstruction & Grounding

The `EvidenceSpanReconstructor` (`src/episense/explainability/reconstructor.py`) validates every `EvidenceReference` against raw source text:

1. **Boundary Checking:**
   - Enforces $0 \le \text{start\_char} \le \text{end\_char} \le \text{len}(\text{raw\_text})$.
   - Out-of-bounds, negative, or reversed offsets fail gracefully with explicit diagnostic error messages (`is_valid = False`).
2. **Text Integrity Verification:**
   - Extracts $\text{raw\_text}[\text{start\_char}:\text{end\_char}]$.
   - When an expected `span_text` is present, verifies exact case-insensitive match. Any discrepancy triggers `is_valid = False` with mismatch details.
3. **Surrounding Context Window:**
   - Extracts a surrounding text buffer (default: $\pm 50$ characters, bounded by document start and end) to provide human reviewers with immediate sentence context without loading the entire document.
4. **Safe Failure & Missing Documents:**
   - If a source document UUID is not present in the local document store, returns `is_valid = False` with `"Source document text not found in registry"`, ensuring the pipeline never halts or crashes on missing references.

---

## 4. Provenance Lineage Graph & Traversal

The `ProvenanceGraphBuilder` (`src/episense/explainability/graph.py`) constructs a directed acyclic lineage graph:

### Graph Topology
* **Root:** `alert:<alert_id>` (`ALERT`)
* **Intermediate Nodes:**
  - `signal:<signal_id>` (`SIGNAL`)
  - `baseline:<baseline_id>` (`BASELINE`)
  - `time_bin:<bin_id>` (`TIME_BIN`)
  - `fused_event:<fused_event_id>` (`FUSED_EVENT`)
* **Leaves:**
  - `evidence_span:<doc_id>:<start>:<end>` (`EVIDENCE_SPAN`)
  - `document:<doc_id>` (`DOCUMENT`)

### Graph Invariants & Algorithms
1. **Acyclicity Enforcement:** Kahn’s topological sort algorithm executes on every graph build, verifying `is_acyclic = True`.
2. **Completeness Ratio:**
   $$\text{CompletenessRatio} = \frac{|\text{Available Nodes}|}{|\text{Expected Nodes}|}$$
   Any document referenced in evidence spans that is absent from local manifests is recorded in `missing_nodes`.
3. **Deterministic Traversal Queries:**
   - `traverse_alert_to_documents(graph) -> List[UUID]`
   - `traverse_alert_to_fused_events(graph) -> List[UUID]`
   - `traverse_alert_to_evidence(graph) -> List[ProvenanceNode]`
   - `traverse_alert_to_signals(graph) -> List[UUID]`
   All traversal queries return deterministic, stably sorted collections.

---

## 5. Decision Path Auditing & Cryptographic Integrity

The `AuditTrailEngine` (`src/episense/explainability/auditor.py`) records the complete 8-step decision sequence:

| Step | Decision Phase | Evaluated Inputs | Applied Rule / Methodology |
| :---: | :--- | :--- | :--- |
| **1** | Statistical Anomaly | Standardized $Z$, detection method, signal level | Normalized $Z$-score scaling with detector consensus bonus |
| **2** | Pathogen Clinical Threat | Disease taxonomy key, assigned consequence tier | Deterministic pathogen severity and CFR classification |
| **3** | Source Diversity | Independent source group count, source IDs | Source scaling ($1 \to 0.35, 2 \to 0.70, \ge 3 \to 1.0$) with $+0.15$ official agency bonus |
| **4** | Clinical Certainty | Assertion status (`CONFIRMED`, `SUSPECTED`), deaths | Assertion weighting with $+0.20$ verified mortality confirmation |
| **5** | Spatial Granularity | Geographic level (Admin 2 district, State, National) | Administrative resolution weighting (Admin 2: 1.00, State: 0.75) |
| **6** | Composite Scoring | 5 dimension scores, applied weights | Linear weighted sum ($0.30, 0.25, 0.20, 0.15, 0.10$) bounded to $[0, 1]$ |
| **7** | Reliability Safety Gating | Baseline reliability state, conflict flags, source count | Safety penalties ($-0.10$ for conflicts) and ceilings (`LOW`/`MEDIUM`) |
| **8** | Alert Tier Assignment | Final score | Operational thresholds ($<0.40$ Info, $0.40$ Low, $0.65$ Med, $\ge 0.80$ High) |

### Cryptographic Checksum
To guarantee that the audit record has not been altered, the engine serializes the canonical state dictionary and computes a SHA-256 hash:
$$\text{AuditChecksum} = \text{SHA256}(\text{CanonicalJSON}(\text{StateDict}))$$
Any change to inputs, weights, penalties, or intermediate scores fundamentally alters the checksum.

---

## 6. Interface Implementation (`EvidenceProvider`)

The `DossierGenerator` implements the abstract `EvidenceProvider` interface established in Phase 2 (`src/episense/interfaces/explainability.py`):
```python
class EvidenceProvider(ABC):
    @abstractmethod
    def generate_dossier(self, alert_id: UUID) -> Dict[str, Any]:
        """Traverses provenance graph from Alert down to source text character spans."""
        pass
```
The implementation validates that `alert_id` exists in the registry, traverses the graph, validates all character spans against raw text, records the audit trail, and returns a JSON-serializable dictionary.

---

## 7. Determinism & Serialization Invariants

1. **Deterministic UUID5 Identifiers:**
   ```python
   dossier_id = uuid5(NAMESPACE_DNS, f"{alert_id}:{checksum[:16]}:dossier")
   graph_id = uuid5(NAMESPACE_DNS, f"{alert_id}:provenance_graph")
   audit_id = uuid5(NAMESPACE_DNS, f"{alert_id}:{checksum[:16]}:audit_trail")
   ```
2. **Deterministic Timestamps:** Anchored strictly to `alert.period_end`, eliminating system-clock discrepancies across repeated runs.
3. **Reproducibility Guarantee:** Two independent batch executions over the identical corpus produce 100% byte-for-byte identical output files (`dossiers.json`, `audit_trails.json`, and `provenance_summary.json`).

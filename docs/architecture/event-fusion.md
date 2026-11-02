# EpiSense Event Fusion & Epidemiological Signal Construction Engine — Architectural Specification

**Document Version:** 1.0.0  
**Phase:** Phase 7 (Event Fusion & Epidemiological Signal Construction Engine)  
**Status:** IMPLEMENTED & FROZEN  
**Target Scope:** Deterministic Cross-Document Event Clustering, Anti-Inflation Quantity Synthesis, and Evidence Provenance for Public Health Intelligence  

---

## 1. Architectural Philosophy & Objective

EpiSense is an explainable early epidemic intelligence framework. In Phase 6, the Context-Aware NLP Extraction Engine converted raw documents into sentence-level entities, assertions, temporal expressions, resolved locations, and quantities.

However, public health surveillance text is highly redundant and fragmented:
* A single outbreak incident is typically reported across multiple news outlets, wire services, official bulletins, and agency communiques.
* If three independent news articles each report *"2 confirmed Nipah virus cases in Kozhikode"*, naive aggregation would sum them into 6 cases, creating a severe artificial epidemic spike (signal inflation).
* Conversely, distinct outbreaks of the same pathogen occurring in different districts or different weeks must not be collapsed into one global event.

Phase 7 introduces the **Event Fusion & Epidemiological Signal Construction Engine**. It synthesizes linguistic mentions into canonical, deduplicated, spatio-temporally coherent epidemiological event records (`FusedEvent`) while strictly preserving character-level evidence provenance and conflict logs.

```text
Raw Documents (110 Docs: Benchmark v1 + Background v1)
        ↓
Phase 6 NLP Extraction Engine (Tokens, Spans, Gazetteers, Negation, Temporals)
        ↓
NLPOutput Records (Sentence Context Associations, Locations, Quantities)
        ↓
EventCandidateBuilder (Grounded typed observations with raw_text offset checks)
        ↓
EventCandidates & EventObservations
        ↓
Cross-Document Deterministic Clustering (EventFusionEngine)
  ├── DiseaseLinker (ICD-10, canonical taxonomy, synonyms)
  ├── GeographicLinker (Admin 0–4 hierarchy, strict false-merge protection)
  ├── TemporalLinker (Configurable window, explicit event time vs publication time)
  ├── SourceIndependenceTracker (Syndication clustering, independent source count)
  └── QuantityAggregator (Anti-inflation invariant, conflict preservation)
        ↓
Canonical FusedEvents (UUID5 deterministic IDs, Evidence References, Conflict Logs)
```

---

## 2. Core Domain Representations & Lifecycle

To ensure strict separation between document mentions and epidemiological reality, Phase 7 defines distinct domain concepts in `src/episense/schemas/event.py`:

| Schema | Role | Mutability | Granularity |
| :--- | :--- | :--- | :--- |
| `EvidenceReference` | Pointer to raw text character offsets `[start_char:end_char]` documenting an attribute (disease, location, count, time). | Immutable | Character span |
| `EventObservation` | Grounded observation extracted from a single sentence or document context. | Immutable | Document-level |
| `EventCandidate` | Pairing of an `EventObservation` with normalized indexing keys (`disease_key`, `geo_key`, `temporal_window`). | Immutable | Document-level |
| `MatchEvaluation` | Structured decision (`MATCH`, `POSSIBLE_MATCH`, `NO_MATCH`) with dimension scores and human-readable rationale. | Ephemeral | Candidate pair |
| `SourceGroup` | Cluster of source identifiers sharing corporate or journalistic ownership (e.g. wire syndication). | Deterministic | Source ID |
| `EpidemiologicalQuantities`| Structured cases, deaths, hospitalizations with conflict flags and raw reported lists. | Value object | Incident |
| `FusedEvent` | Canonical underlying incident representing an epidemiological event across all observed sources. | Synthesis | Multi-document |

---

## 3. The Strict Anti-Inflation Invariant

A central vulnerability of text-based biosurveillance is **count inflation**:
$$\text{Inflated Cases} = \sum_{i=1}^{N} \text{cases}_i \quad \text{(Fatal Flaw of Naive Systems)}$$

EpiSense enforces the **Anti-Inflation Invariant**:
* Repeated reports of identical case counts for the same event do **NOT** sum.
* If Document A reports 2 cases and Document B reports 2 cases:
  $$\text{reported\_case\_count} = 2, \quad \text{supporting\_observation\_count} = 2, \quad \text{independent\_source\_count} = 2$$
* If Document A reports 2 cases and Document B reports 5 cases:
  * The event is flagged with `has_conflicts = True`.
  * `conflict_summary` records: `"Conflicting cases counts reported: [2.0, 5.0]"`.
  * `reported_values["cases"] = [2.0, 5.0]` preserves every raw reported value.
  * The conservative maximum estimate is tracked while explicitly exposing the epistemic divergence to downstream algorithms and human epidemiologists.

---

## 4. Multi-Dimensional Compatibility Matrix & Matcher

The `EventMatcher` evaluates candidate pairs $(A, B)$ across four orthogonal dimensions:

### 4.1. Disease Compatibility (`DiseaseLinker`)
* Compares normalized canonical disease names and ICD-10 codes.
* Matches exact strings, confirmed synonyms (e.g. *"Nipah virus"* $\leftrightarrow$ *"Nipah virus infection"* $\leftrightarrow$ *"Henipavirus"*), and shared ICD-10 parent blocks (`B27.8`, `A00`, `A98.4`).
* Incompatible pathogens immediately abort matching with `score = 0.0` (Hard Constraint).

### 4.2. Geographic Compatibility & False-Merge Protection (`GeographicLinker`)
* Evaluates locations against the verified 5-level administrative hierarchy:
  $$\text{COUNTRY (Admin 0)} \rightarrow \text{REGION (Admin 1)} \rightarrow \text{DISTRICT (Admin 2)} \rightarrow \text{SUBDISTRICT (Admin 3)} \rightarrow \text{CITY (Admin 4)}$$
* **Exact Match:** Same normalized name and level $\rightarrow \text{score} = 1.0$.
* **Parent-Child Containment:** One entity is topologically contained in the other (e.g. Kozhikode district inside Kerala state) $\rightarrow \text{score} = 0.90$. The canonical location resolves to the most specific child entity.
* **Strict False-Merge Protection:** Mentions with `UNRESOLVED` or `AMBIGUOUS` resolution state are strictly prohibited from merging solely on lexical similarity.
* **Unspecified Location Protection:** If locations are unspecified, they are never merged into specific district outbreaks.

### 4.3. Temporal Compatibility (`TemporalLinker`)
* Preserves strict separation between **Event Date** (when clinical onset occurred) and **Publication Date** (when the report was released).
* Configurable fusion window parameter (default $W = 7$ days).
* When both reports contain explicit event date intervals $[S_A, E_A]$ and $[S_B, E_B]$:
  * Overlapping intervals $\rightarrow \text{score} = 1.0$.
  * Gap $\le W$ days $\rightarrow \text{score} = \max(0.60, 1.0 - \frac{\text{gap}}{2W})$.
  * Gap $> W$ days $\rightarrow \text{score} = 0.0$ (`NO_MATCH`).
* When event dates are unstated, publication dates within $W$ days are used with `is_event_time_estimated = True`.

### 4.4. Epistemic Assertion Compatibility
* Outbreak reports must be epistemically compatible:
  * `CONFIRMED` $\leftrightarrow$ `SUSPECTED` are compatible (confidence adjustment).
  * `NEGATED` statements are never merged into `CONFIRMED` outbreaks.
  * `HISTORICAL` references (background retrospective mentions) are segregated from active contemporary incidents.

### 4.5. Composite Match Scoring
$$\text{Score} = 0.35 \cdot S_{\text{disease}} + 0.30 \cdot S_{\text{geo}} + 0.25 \cdot S_{\text{temporal}} + 0.10 \cdot S_{\text{assertion}}$$

* Decision rule:
  $$\text{Decision} = \begin{cases} \text{MATCH} & \text{if } \text{Score} \ge 0.75 \land S_{\text{dis}} \ge 0.90 \land S_{\text{geo}} \ge 0.75 \land S_{\text{temp}} \ge 0.60 \\ \text{POSSIBLE\_MATCH} & \text{if } \text{Score} \ge 0.50 \\ \text{NO\_MATCH} & \text{otherwise} \end{cases}$$

---

## 5. Source Independence Tracking

To prevent echo-chamber bias from syndicated media:
* Public health news wires frequently syndicate the exact same story across dozens of publisher portals.
* `SourceIndependenceTracker` maps source identifiers to known parent syndicates (`WHO`, `CDC`, `PROMED`, `REUTERS_SYNDICATE`, `AP_SYNDICATE`, `INDEPENDENT_MEDIA`).
* `independent_source_count` reflects distinct reporting entities, while `supporting_observation_count` tracks raw mentions.
* High observation count with low independent source count indicates an echoed wire story, appropriately downweighted in multi-source consensus scoring.

---

## 6. Full Evidence Provenance & Auditability

Every `FusedEvent` maintains an unbroken link to the original character spans:
* `contributing_observation_ids`: List of constituent observation UUIDs.
* `evidence_references`: Union of all `EvidenceReference` records from constituent documents.
* Each reference records `[start_char:end_char]`, `span_text`, `document_id`, `source_id`, and `attribute_role` (`primary_disease`, `location`, `temporal`, `quantity_cases`, `quantity_deaths`).
* Verified against raw document text: $\text{raw\_text}[\text{start}:\text{end}] == \text{span\_text}$.

---

## 7. Determinism & Conflict Management

* **Deterministic Sorting:** Candidates are pre-sorted by disease canonical key, temporal start, document UUID, and candidate UUID before clustering.
* **Deterministic Event IDs:** Fused event UUIDs are generated via `uuid5(NAMESPACE_DNS, f"{disease}:{location}:{window_start}")` ensuring 100% reproducible identifiers across runs.
* **Conflict Logging:** Quantity discrepancies, date ambiguities, and administrative disagreements are serialized into `conflict_summary` rather than silently averaged or dropped.

---

## 8. Extensibility for Phase 8 (Statistical Baselines & Signals)

Phase 7 constructs clean, deduplicated `FusedEvent` sequences. This cleanly enables Phase 8:
* Historical outbreak frequency tables can be generated per disease and geographic unit without multi-counting syndicated news wire echoes.
* Case count trajectories represent true reported incident curves rather than media velocity spikes.
* Early warning anomaly detection algorithms (e.g. EARS C1/C2/C3, Farrington quasi-Poisson) can consume coherent incident counts with verified provenance.

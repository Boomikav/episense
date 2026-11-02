# ADR-001: EpiSense Architecture Foundation & Technology Freeze
**Date:** 2026-09-06  
**Status:** ACCEPTED (Phase 1 Approved, Phase 2 Initialized)  

---

## Context
Public health textual surveillance systems require high accuracy, transparent explainability, and deterministic reproducibility. Naive keyword matching or black-box closed-cloud LLM wrappers fail due to lack of auditability, cost, rate limits, and uncontrollable hallucinations. EpiSense requires a modular, local-first Python framework where every extraction and alert maintains unbroken token-level provenance to source documents.

---

## Decision Statuses

### A. DECIDED (Immutable Architectural Foundation)
1. **Local-First Execution:** The framework executes locally on standard workstation hardware (CPU / optional consumer GPU). No dependencies on external closed-cloud LLM APIs or metered SaaS.
2. **Strict Modular Decoupling:** Core components (NER, Assertion, Temporal, Geospatial, Fusion, Anomaly, Scoring, API) are decoupled using abstract interfaces (`abc.ABC`). Models can be swapped without changing downstream modules.
3. **Initial NLP Backbone (D01):** `scispaCy` / `spaCy` is the initial local entity extraction backbone, wrapped behind the `EntityExtractor` interface.
4. **Rule-Based Assertion & Negation (D02):** Context and negation analysis initially uses syntactic dependency parsing (ConText/NegEx logic) behind the `AssertionAnalyzer` interface.
5. **Geographic Scope (D03):** Initial prototype focuses on **India** (Admin levels 0 through 3) with a local SQLite gazetteer provider behind the `LocationResolver` interface.
6. **Web API Framework (D04):** `FastAPI` is selected for the future REST API layer.
7. **Persistence Layer:** SQLite 3 via SQLAlchemy 2.0 provides zero-config, portable relational storage for the research prototype.
8. **No Premature Enterprise Overhead:** No Kubernetes, Kafka, Celery, or microservice architecture.

### B. PROVISIONAL (Requires Empirical Calibration)
1. **Multi-Source Fusion Parameters (D05):** 7-day sliding temporal window, Admin-2 (District) spatial aggregation, and 0.80 MinHash deduplication threshold.
2. **Alert Scoring Weights:** Initial heuristic weights:
   * $w_a = 0.40$ (Anomaly magnitude)
   * $w_d = 0.30$ (Source diversity)
   * $w_c = 0.15$ (Assertion certainty)
   * $w_s = 0.15$ (Spatial clustering density)
   * **Explicit Note:** *PROVISIONAL — REQUIRES EMPIRICAL CALIBRATION* against historical benchmark outbreaks.
3. **Statistical Anomaly Algorithm:** EARS C2 is the primary default, subject to comparative evaluation against Poisson aberration models during benchmark validation.

---

## Consequences
* High modularity enables isolated testing of each layer.
* Pydantic schemas enforce type safety and data integrity at every module boundary.
* Abstract interfaces guarantee that future deep learning models can be introduced with zero changes to data pipelines or analytics.

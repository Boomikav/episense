# ADR-002: Real Data Acquisition, Source Verification, and Benchmark Foundation
**Date:** 2026-09-06  
**Status:** ACCEPTED (Phase 3 Completed)  

---

## Context
EpiSense requires a technically, scientifically, and legally defensible data foundation. Synthetic, fabricated, or ungrounded data creates artificial evaluation results and invalidates public health applicability. Furthermore, web scraping without source verification risks violating rate limits, licensing terms, and site availability. Phase 3 establishes the ground rules, source registry, validation, deduplication, and benchmark schema.

---

## Decisions

### 1. Zero Data Fabrication Rule (MANDATORY)
No synthetic or fabricated news articles, health bulletins, case counts, or locations will be generated or presented as real benchmark data. Evaluation benchmarks will be constructed solely from verified public health documents.

### 2. Dual-Mode Acquisition Architecture
The framework separates **Historical/Offline Benchmark Mode** from **Incremental/Live Ingestion Mode**. All model development and baseline evaluations operate offline using curated static manifests, ensuring 100% reproducibility without external network dependencies.

### 3. Verified Candidate Sources
Five candidate sources have been verified and registered:
* `ncdc_idsp_india` (NCDC IDSP Weekly Outbreak Reports, India)
* `who_don` (WHO Disease Outbreak News, Global)
* `pib_mohfw_india` (PIB Ministry of Health Press Releases, India)
* `promed_mail` (ProMED-mail Public Archives, ISID)
* `medrxiv_preprints` (medRxiv Biomedical Preprints REST API)

### 4. Deduplication Protocol
* Phase 3 enforces **strict exact duplicate suppression** using 64-character SHA-256 cryptographic content hashes.
* Near-duplicate MinHash / LSH clustering is formally scheduled for Phase 7 (Multi-Source Fusion).

### 5. Benchmark Annotation & Character Offset Grounding
* Ground-truth evaluation annotations are structured using the `AnnotationSpan` schema, tracking `start_char`, `end_char`, and layer categories.
* Character offsets are strictly anchored to the raw document text.

### 6. Incident-Grouped Dataset Splits
Dataset splitting must be grouped by incident `(disease, location, time)` to prevent cross-document event leakage between development and benchmark splits.

---

## Consequences
* The system remains legally compliant and technically reproducible.
* Offline evaluation guarantees that tests run reliably on standard developer workstations.
* Downstream NLP and anomaly models can be evaluated against verifiable public health records.

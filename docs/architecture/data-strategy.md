# EpiSense Data Architecture & Strategy
**Document Version:** 1.0  
**Phase:** Phase 3 (Real Data Acquisition & Benchmark Foundation)  
**Status:** FROZEN SPECIFICATION  

---

## 1. Data Requirements Analysis

EpiSense processes five distinct categories of data to accomplish context-aware epidemic intelligence:

### A. Raw & Cleaned Health Documents
Textual observations published by credible authorities, syndication services, and news outlets.
* **Fields:** Publication date, source ID, title, full text, author/publisher, URL, SHA-256 hash.
* **Integrity:** The raw text must be preserved immutably. Character offsets for all downstream extractions are anchored to this raw text.

### B. Historical / Background Activity Observations
Time-series event counts aggregated across epidemiological weeks (Epi-Weeks) per disease and administrative region.
* **Purpose:** Provides baseline mean ($\mu$) and standard deviation ($\sigma$) to detect aberrations.
* **Requirement:** Requires 7 to 28 days of immediate historical data plus seasonal historical references.

### C. Current / Recent Observations
Incoming stream of new documents processed within sliding surveillance windows (e.g. past 7 days).
* **Purpose:** Clustered across sources into `FusedEventCluster` instances to compare against expected baselines.

### D. Geographic Reference Data
Hierarchical gazetteer information for toponym grounding (focused on India Admin 0 through Admin 3).
* **Components:** Standardized place names, alternative spellings, administrative parents, and centroid coordinates.

### E. Evaluation Annotations (Ground Truth)
Gold-standard human annotations capturing token spans and epistemic status:
* **Entity Layer:** Disease, symptom, quantity, affected population.
* **Assertion Layer:** Confirmed, suspected, negated, historical, hypothetical.
* **Temporal Layer:** Point date, interval, relative time expression.
* **Geographic Layer:** Admin 0 (Country), Admin 1 (State), Admin 2 (District), Admin 3 (Tehsil).

---

## 2. Verified Candidate Public Sources Matrix

Every candidate source has been verified for institutional credibility, accessibility, and legal terms:

| Source ID | Organization | Official URL | Source Type | Geographic Scope | Temporal Coverage | Format | Machine Readable? | Auth Required? | Licensing / Terms | Suitable for Benchmark | Suitable for Future Ingestion | Notes / Constraints |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `ncdc_idsp_india` | National Centre for Disease Control (MoHFW) | `https://ncdc.mohfw.gov.in/` | Official Bulletin | India | 2009–present | PDF / HTML | No | No | Government Open Data License (GODL) | **YES** | No (PDF only) | Primary ground-truth weekly outbreak monitoring reports in India. PDF format requires offline text parsing. |
| `who_don` | World Health Organization (WHO) | `https://www.who.int/emergencies/disease-outbreak-news` | Official Bulletin | Global | 1996–present | HTML | No (no HQ RSS) | No | CC BY-NC-SA 3.0 IGO | **YES** | **YES** | Highly structured epidemiological reports. Verified that WHO HQ does not maintain an active public RSS feed; ingestion requires targeted URL monitoring. |
| `pib_mohfw_india` | Press Information Bureau (PIB) | `https://pib.gov.in/` | Official Bulletin | India | Contemporary | XML / RSS | **YES** | No | Government Open Data License (GODL) | **YES** | **YES** | General PIB RSS feed available; requires ministry filter for Health & Family Welfare. |
| `promed_mail` | International Society for Infectious Diseases (ISID) | `https://promedmail.org/` | Public Syndication | Global | 1994–present | HTML / Text | No (API is paid) | No (for web archive) | Copyright ISID (Non-commercial research use) | **YES** | No (API is paid) | Global expert-moderated surveillance. API is enterprise/paid; public web archive is suitable for manual benchmark curation. |
| `medrxiv_preprints` | Cold Spring Harbor Laboratory / BMJ / Yale | `https://www.medrxiv.org/` | Public Syndication | Global | 2019–present | JSON / REST API | **YES** | No | Author-retained copyright / CC licenses | **YES** | **YES** | Free public REST API available (`https://api.biorxiv.org/details/medrxiv/`). Excellent for field investigation reports. |

---

## 3. Dual-Mode Operating Strategy

```text
┌─────────────────────────────────────────────────────────────────────────────┐
│ 1. HISTORICAL / OFFLINE MODE                                                │
│    - Used for: Benchmark evaluation, model training, baseline calibration   │
│    - Source: Curated static benchmark corpus in data/benchmarks/            │
│    - Deterministic, repeatable, zero external network dependency            │
└─────────────────────────────────────────────────────────────────────────────┘
                                      ▲
                                      │ Common Document Schema
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ 2. INCREMENTAL / LIVE INGESTION MODE (Future Phases)                        │
│    - Used for: Near-real-time surveillance and operational triage           │
│    - Source: Polled public RSS feeds & whitelisted public bulletins          │
│    - Rate-limited, cached, failure-isolated dead letter queue               │
└─────────────────────────────────────────────────────────────────────────────┘
```

The system is architected so that **the entire evaluation and testing pipeline functions completely offline** using static benchmark datasets. Continuous surveillance mode is an additive ingestion provider, not a prerequisite for system operation.

---

## 4. Benchmark Dataset Design (50–100 Documents)

### Inclusion Criteria:
1. **Verifiable Provenance:** Document must originate from an identified, verifiable public health authority or syndication source.
2. **Clinical / Health Signal:** Must contain at least one explicit disease or syndrome mention.
3. **Spatiotemporal Grounding:** Must refer to a discernable geographic area (country/region/district) and have a known publication date.
4. **Epistemic Diversity:** The corpus must include a balanced mix of:
   * Active confirmed outbreak reports
   * Active suspected case investigations
   * Explicit refutations / negations (e.g., *"Suspected cholera ruled out"*)
   * Historical retrospectives (e.g., *"Comparing this season to the 2019 surge"*)
   * Preventative advisories (e.g., *"Vaccination drives for measles"*)

### Exclusion Criteria:
1. Fabricated or synthetic documents presented as real text.
2. Documents behind paywalls, subscription logins, or private databases.
3. Word-for-word exact duplicates (filtered out via SHA-256 hash).
4. Content with ambiguous copyright prohibiting research analysis.

---

## 5. Grouped Dataset Split Strategy (Preventing Leakage)

Standard random document-level splitting causes severe data leakage in epidemic intelligence: if 5 news articles cover the exact same local outbreak, placing 4 in training and 1 in test leaks the event specifics.

**EpiSense Split Protocol:**
* Documents are first clustered into **Incident Groups** based on `(disease, location, time_window)`.
* Splitting is performed at the **Incident Group Level**:
  * **Development (Train/Dev):** 70% of incident clusters
  * **Evaluation (Test/Benchmark):** 30% of incident clusters
* This guarantees that models are evaluated on completely unseen outbreak incidents.

---

## 6. Raw Text Preservation & Provenance Guarantee

To guarantee auditability:
1. The original raw text is stored immutably upon ingestion with its SHA-256 hash.
2. All character offsets (`start_char`, `end_char`) in entities, assertions, and annotations refer directly to this raw text.
3. Preprocessing (whitespace normalization, HTML stripping) generates a cleaned view but **does not replace** the raw text record in storage.

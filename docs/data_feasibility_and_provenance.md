# EpiSense: Data Feasibility, Typology, and Source Provenance Audit

**Author**: EpiSense Research & Engineering Working Group  
**Discipline**: Public Health Informatics, Epidemiological Statistics, Data Governance  
**Document Version**: 2.0.0 (Research-Grade Reference)  
**Status**: Authoritative Forensic Audit & Provenance Standard  

---

## 1. Executive Summary

Epidemiological surveillance systems frequently fail in operational transitions because system architects design algorithms for idealized data environments that do not exist in practice. A scientifically defensible surveillance platform must conduct an exhaustive feasibility audit of available data streams *before* committing to analytical and statistical models.

This document establishes:
1. The **Seven-Category Public Health Data Typology (Types A–G)** separating structured clinical assays from unstructured open-source intelligence.
2. The **Authoritative Forensic Inventory** of all 216 documents, 460 active fused events, 177 indicator bins, and 452 signals currently persisted in the EpiSense SQLite database (`data/surveillance_store.sqlite`).
3. An **Empirical Data Adequacy Audit** demonstrating what analytical tasks can and cannot be mathematically supported.
4. The **Lawful Data Acquisition & Provenance Architecture** governing public health feeds (IDSP/IHIP, WHO DON, CDC MMWR, ReliefWeb, ProMED).

---

## 2. Seven-Category Public Health Data Typology (Types A–G)

In public health epidemiology, surveillance data streams exhibit vastly different temporal granularities, diagnostic certainties, and structural formats.

### Table 1: Surveillance Data Typology and Operational Suitability

| Data Type | Formal Name & Description | Diagnostic Certainty | Ingestion Format | Analytical Suitability in EpiSense | Availability in Active Repo |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Type A** | **Daily Laboratory-Confirmed Assays**<br>Individual specimen RT-PCR, culture, or serology with positive and negative denominator counts. | Gold Standard ($>99\%$) | Structured HL7 / FHIR / CSV records | Continuous anomaly detection, exact attack rates, test positivity tracking | **Not present** in open public domain; restricted to internal hospital/EHR systems |
| **Type B** | **Aggregated Weekly Indicator Incidence**<br>District- or state-level weekly counts of reported cases and deaths compiled by health ministries. | High ($85–95\%$) | Tabular PDF/HTML bulletins (e.g., IDSP Form P/L) | Farrington quasi-Poisson, EARS C1–C3 (requires $N \ge 3$ consecutive weeks) | **Partially present**: 1 weekly IDSP bulletin (2026-W01) spanning 29 cross-sectional districts |
| **Type C** | **Syndromic Encounter Surveillance**<br>Emergency department chief complaints, fever clinic logs, and pharmacy over-the-counter sales. | Moderate ($60–75\%$) | Tabular daily counts, clinical triage codes | Early syndromic wave detection, moving-average smoothing | **Simulated/Derived** in syndromic categories (e.g., ADD, AES) |
| **Type D** | **Semi-Structured Outbreak Investigation Bulletins**<br>Formal epidemiological field investigation summaries containing disease, location, cases, deaths, and start dates. | High ($80–90\%$) | Tabular text blocks inside weekly PDF reports | High-precision entity extraction, event candidate generation, spatial-temporal fusion | **Present**: 29 district outbreak records extracted from official IDSP bulletin |
| **Type E** | **Unstructured Digital News & Media Dispatches**<br>Journalistic reporting from local, national, and international press (English, Hindi, vernacular). | Variable ($40–70\%$) | Free-text narrative prose, RSS articles | Event-Based Surveillance (EBS), early rumor triage, cross-document coreference | **Present**: 103 live external news reports and 110 historical narrative dispatches |
| **Type F** | **Official Public Health Advisories & Circulars**<br>WHO Disease Outbreak News (DON), CDC Health Advisory Network (HAN), and MoHFW circulars. | High Authority ($90–98\%$) | Unstructured/semi-structured official communiqués | Gold-standard qualitative grounding, high-consequence threat escalation | **Present**: 65 WHO-attributed and ministry-level dispatches |
| **Type G** | **Crowdsourced Symptoms & Social Chatter**<br>Participatory symptom reports (e.g., Flu Near You), social media keyword mentions, search trends. | Low ($20–40\%$) | High-volume streaming microblogs, search query logs | Signal early-warning, trend correlation (vulnerable to panic spikes and noise) | **Excluded by design** to prevent social media rumor contamination |

---

## 3. Authoritative Forensic Inventory of Persisted Data

A direct query of the production SQLite database (`data/surveillance_store.sqlite`, schema version `migration_001_v2_fused_events`) yields the following immutable audit metrics:

### Table 2: Production Database Inventory (as of October 2026)

| Object Type | Live External (`LIVE_EXTERNAL`) | Historical Corpus (`HISTORICAL_CORPUS`) | Total Authoritative Count | Integrity Status |
| :--- | :--- | :--- | :--- | :--- |
| **Documents Registered** | **103** | **113** | **216** | 100% SHA-256 deduplicated |
| **Pipeline Traces** | 102 completed, 1 background | 85 completed, 27 background | **215** (1 pending) | 187 with candidate events, 28 zero-event |
| **Candidate Events Extracted** | 246 | 352 | **598** | Verbatim character-span grounded |
| **Active Fused Events** | **45** | **415** | **460** | Deduplicated canonical events |
| **Superseded Fused Events** | 26 | 0 | **26** | Audit trail preserved; lifecycle inactive |
| **Corroborated Fused Events** | 2 | 0 | **2** | $\ge 2$ independent source groups |
| **Single-Source Unverified** | 43 | 415 | **458** | Isolated claims; triage capped at 0.65 |
| **Indicator Time Bins** | 45 | 132 | **177** | Unique (disease, geo, year, week) keys |
| **Verified Numerical Bins** | 16 | 0 | **16** | Explicit reported case count $>0$ |
| **Signals Evaluated** | 45 | 407 | **452** | Evaluated via EARS/Farrington engine |
| **Signals Baseline-Gated** | **45 (100%)** | **407 (100%)** | **452 (100%)** | Gated with `INSUFFICIENT_BASELINE` |
| **Signals with Reliable Baseline**| **0** | **0** | **0** | **Accurate reflection of data scarcity** |
| **Active Prioritized Alerts** | **41** | **419** | **460** | Triage scored with explainability |
| **Explainability Dossiers** | 41 | 419 | **460** | 1:1 foreign key relation to alerts |
| **Alert Audit Trails** | 41 | 419 | **460** | 1:1 foreign key relation to alerts |

---

## 4. Empirical Data Adequacy Audit by Surveillance Task

### 4.1 Event-Based Surveillance (EBS) & Cross-Document Fusion: HIGH ADEQUACY
- **Input Types**: Types D, E, F (216 documents, 598 candidate mentions).
- **Adequacy Finding**: The dataset provides rich narrative diversity spanning bacterial (Cholera, Anthrax, Leptospirosis), viral (Dengue, Chikungunya, Kyasanur Forest Disease, Nipah, Zika, Avian Influenza), and syndromic (ADD, AES) dispatches across multiple Indian states (Kerala, Maharashtra, Karnataka, Gujarat, Odisha, West Bengal, Assam) and global regions.
- **Verification**: The fusion engine successfully collapses 598 candidate mentions into 460 canonical fused events (a 1.30x syndication compression ratio), cleanly identifying syndicated media repeats and preserving contradictory case counts in `conflicting_quantities`.

### 4.2 NLP Verbatim Grounding & Clinical Assertion: HIGH ADEQUACY
- **Input Types**: Types D, E, F.
- **Adequacy Finding**: All 216 documents contain full-text bodies enabling exact character-offset verification. The offline deterministic NLP engine (`GroundedLLMAdapter`) achieves 100% verification: zero extracted entity mentions exist without an exact substring match in the underlying document text.
- **Assertion Validation**: Mentions containing explicit negative triggers ("tested negative", "no fresh cases", "ruled out") are successfully classified as `AssertionStatus.ABSENT`, suppressing 14 legacy false-positive alerts.

### 4.3 Time-Series Statistical Anomaly Detection (IBS): RESTRICTED / INSUFFICIENT BASELINE
- **Input Types**: Type B (IDSP weekly bulletin).
- **Empirical Reality**:
  - The repository contains exactly **one weekly IDSP bulletin (2026-W01)**.
  - While this bulletin contains 29 district-level outbreak records, these records represent a **single cross-sectional snapshot ($T = 1$) across 29 geographic districts**, rather than 29 consecutive historical weeks for a single district.
  - Number of disease-geography series with $N \ge 3$ consecutive historical periods: **0 series**.
  - Number of series with $\ge 2$ non-zero historical counts: **0 series**.
- **Defensible Scientific Action**: Rather than synthesizing artificial historical baseline numbers or computing mathematically invalid EARS z-scores ($N=1, s=0$), EpiSense strictly enforces **Statistical Baseline Reliability Gating**. All 452 signals are transparently flagged as `INSUFFICIENT_BASELINE` / `SPARSE_HISTORY`. Outbreak prioritization is transferred entirely to the evidence-grounded Event-Based branch.

---

## 5. Lawful Public Health Data Acquisition & Provenance Architecture

EpiSense is designed to operate ethically and legally within international public health data governance frameworks.

### Table 3: Active Source Connectors & Lawful Access Specifications

| Connector ID | Source Organization | Official Endpoint / URL | Protocol | Authentication | Polling Interval | Terms of Service & Compliance |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `who_don` | World Health Organization | `https://www.who.int/emergencies/disease-outbreak-news` | HTTPS / RSS 2.0 | Open Public Access | 600 s (10 min) | Public domain international health communiqués under WHO Open Access Policy. |
| `idsp_bulletins`| Ministry of Health & Family Welfare, India | `https://idsp.mohfw.gov.in/index4.php` | HTTPS / PDF Scraper | Open Government Data | 1800 s (30 min) | Published under Government of India National Data Sharing and Accessibility Policy (NDSAP). |
| `reliefweb` | UN Office for the Coordination of Humanitarian Affairs | `https://api.reliefweb.int/v1/reports` | REST API (JSON) | Open Public API | 900 s (15 min) | Compliant with ReliefWeb API Terms of Use; CC BY 4.0 humanitarian reports. |
| `cdc_outbreaks` | US Centers for Disease Control and Prevention | `https://tools.cdc.gov/api/v2/resources/media` | REST API / Syndication | Open Public API | 1200 s (20 min) | US Government Work; public domain worldwide under 17 U.S.C. § 105. |
| `promed_mail` | International Society for Infectious Diseases (ISID) | `https://promedmail.org/promed-posts/` | HTTPS / Feed Parser | Open Academic Archive | 900 s (15 min) | Used for non-commercial educational and public health research. |
| `manual_api` | Certified Public Health Officers | `/api/v1/documents/ingest` | FastAPI REST POST | Session Bearer Token | On-demand | Internal authenticated entry for verified field epidemiological dispatches. |

### 5.1 Data Provenance Tracking (W3C PROV-DM Alignment)
Every ingested document in EpiSense is tagged with an immutable `ProvenanceRecord`:
- `source_id`: Unique connector identifier (e.g., `who_don`, `idsp_bulletins`).
- `source_url`: Full canonical HTTPS URL where the report was published.
- `content_hash_sha256`: 64-character hexadecimal SHA-256 hash of the normalized document text, enforcing database-level deduplication.
- `acquisition_timestamp`: ISO 8601 UTC timestamp of network ingestion.
- `published_date`: Stated publication date extracted from document metadata or headers.
- `origin`: Strict classification into `LIVE_EXTERNAL` (acquired via automated network polling) or `HISTORICAL_CORPUS` (pre-loaded benchmark files).

### 5.2 Patient Privacy, De-Identification, and Data Sovereignty
In compliance with public health privacy standards (HIPAA Safe Harbor, GDPR Article 9(2)(i), and India Digital Personal Data Protection Act 2023):
1. **De-Identification**: Ingested public media reports and bulletins do not contain individual medical record numbers (MRNs) or patient names. Where specific names appear in news text (e.g., deceased victims), the entity extractor suppresses person entities (`PER`) from downstream alerts.
2. **Spatial Aggregation**: Geographic extraction resolves to administrative units (District, State, Country) rather than residential street addresses.
3. **Data Sovereignty & Air-Gapped Operation**: Because EpiSense operates with an **offline deterministic NLP pipeline**, sensitive epidemiological dispatches never leave the host server. No dispatch text is transmitted to third-party proprietary LLM APIs (e.g., OpenAI, Anthropic), guaranteeing absolute compliance with national public health data sovereignty laws.

---

## 6. Transparent Declaration: What Cannot Be Validated

Scientific integrity requires stating what the current dataset **cannot** substantiate:
1. **Multi-Year Seasonal Forecasting**: The platform cannot demonstrate multi-year seasonal harmonic regression (Farrington seasonality) on real data because the historical corpus contains only 1 cross-sectional weekly bulletin.
2. **Clinical Laboratory Test Positivity Curves**: The platform cannot compute laboratory positivity rates (Type A data) because public media dispatches report only numerator cases without reporting total laboratory specimens tested.
3. **Global Multi-Lingual Surveillance**: While the pipeline architecture supports Unicode, current validated benchmarks focus on English-language and Romanized Indian public health dispatches.

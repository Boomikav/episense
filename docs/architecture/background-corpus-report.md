# EpiSense Background Surveillance Corpus Report
**Corpus Release:** EpiSense Background v1.0 (`episense_background_v1.json`)  
**Phase:** Phase 5 (Benchmark Audit, Annotation & Baseline Expansion)  
**Date Generated:** 2026-09-06  
**Status:** COMPLETED & FROZEN  

---

## 1. Corpus Purpose & Epistemic Role
The primary objective of `EpiSense Background v1.0` is to provide an empirical corpus of **routine public health surveillance, seasonal monitoring, and non-outbreak reporting** to reduce the extreme positive/outbreak bias inherent in traditional news corpora.

### Critical Epistemic Separation:
* **`episense_benchmark_v1` (52 documents):** Evaluation corpus for context-aware NLP extraction (NER, negation, temporal, spatial, and event synthesis).
* **`episense_background_v1` (58 documents):** Background textual surveillance corpus representing expected routine operations, seasonal advisories, and NIL outbreak returns.

> **CRITICAL EPIDEMIOLOGICAL DISCLAIMER:**  
> This collection of documents is a **background/routine textual surveillance corpus**, NOT an epidemiologically confirmed statistical baseline. It must not be presented as a statistically representative disease frequency model until mathematical baseline algorithms (e.g. EARS C1/C2/C3) are fitted and validated in subsequent phases.

---

## 2. Temporal Coverage & 2025 Gap Resolution
The original Benchmark v1.0 contained a noticeable temporal gap (no documents from 2025). The background corpus intentionally resolves this gap using authentic, verified public health releases:

* **2023:** 6 documents (Baseline historical monitoring & deworming rounds)
* **2024:** 19 documents (Routine seasonal advisories, NIL weekly reports, and vector campaigns)
* **2025:** **29 documents** (Comprehensive coverage: National Influenza Chintan Shivir, Joint Monitoring Group respiratory illness reviews, seasonal dengue reviews, World Malaria Day NFME updates, and multiple state IDSP NIL reports)
* **2026:** 4 documents (Pre-monsoon preparedness advisories, World Health Day, U-WIN vaccination milestones)
* **Total Documents:** **58 authentic public health documents**

---

## 3. Source Distribution
| Source ID | Organization | Document Count | Percentage |
| :--- | :--- | :--- | :--- |
| `pib_mohfw_india` | Press Information Bureau (Ministry of Health & Family Welfare) | 28 | 48.3% |
| `ncdc_idsp_india` | National Centre for Disease Control (IDSP Weekly Returns) | 18 | 31.0% |
| `who_don` | World Health Organization (Global & Regional Routine Summaries) | 8 | 13.8% |
| `medrxiv_preprints` | medRxiv Health Sciences (Longitudinal Baseline Cohorts) | 4 | 6.9% |
| **Total** | | **58** | **100.0%** |

---

## 4. Routine & Background Surveillance Categorization
Every document in `episense_background_v1` represents routine, non-surge surveillance activity:

| Category | Count | Percentage | Description |
| :--- | :--- | :--- | :--- |
| `routine_surveillance` | 49 | 84.5% | Official weekly NIL outbreak returns, annual disease program reports (TB, Malaria NFME), global influenza updates, and primary health center screenings. |
| `precautionary_advisory` | 7 | 12.1% | Pre-monsoon vector control advisories, inter-ministerial preparedness task force meetings, and clinical heatwave guidelines. |
| `negation_statement` | 2 | 3.4% | Official ministerial clarifications confirming absence of unusual ILI/SARI or HMPV respiratory surges. |
| **Outbreak Reports** | **0** | **0.0%** | Strictly zero positive epidemic surges, ensuring pure background activity representation. |

---

## 5. Temporal Leakage Prevention Architecture
To prevent future temporal data leakage when training baseline models:
1. **Strict Directionality:** Baseline statistics for any target surveillance week $W_t$ are constructed **strictly from historical observations $W_{<t}$**.
2. **No Future Mixing:** Documents published during or after $W_t$ are reserved exclusively as evaluation observation signals.
3. **Partitioning:** The background corpus is indexed by publication timestamp and epidemiological week (Epi-Week) to enforce temporal causality.

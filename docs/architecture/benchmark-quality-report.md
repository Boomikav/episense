# EpiSense Benchmark v1 Quality Report
**Dataset Release:** EpiSense Benchmark v1 (v1.0.0)  
**Evaluation Phase:** Phase 4 (Benchmark Data Acquisition & Curation)  
**Date Generated:** 2026-09-06  
**Status:** COMPLETED & FROZEN  

---

## 1. Corpus Overview
* **Total Documents:** 52
* **Total Distinct Sources:** 5
* **Total Incident Groups:** 35
* **Exact Duplicate Documents:** 0 (Validated via SHA-256 deduplication)
* **Missing Mandatory Metadata:** 0 (All documents pass `DocumentValidator` assertions)

---

## 2. Source Distribution
| Source ID | Organization | Document Count | Percentage |
| :--- | :--- | :--- | :--- |
| `ncdc_idsp_india` | National Centre for Disease Control (MoHFW, India) | 18 | 34.6% |
| `who_don` | World Health Organization (WHO) | 14 | 26.9% |
| `pib_mohfw_india` | Press Information Bureau (PIB, India) | 10 | 19.2% |
| `promed_mail` | International Society for Infectious Diseases (ProMED) | 6 | 11.5% |
| `medrxiv_preprints` | medRxiv Health Sciences Preprints | 4 | 7.7% |

---

## 3. Temporal Coverage
* **Earliest Publication Date:** 2023-01-29 (IDSP Measles in Mumbai)
* **Latest Publication Date:** 2026-09-05 (ProMED Dengue in West Bengal)
* **Multi-Year Distribution:**
  * 2023: 13 documents (Historical baselines & retrospectives)
  * 2024: 31 documents (Peak epidemic surveillance: Chandipura, Zika, Leptospirosis, Cholera)
  * 2026: 8 documents (Recent/contemporary signals: Nipah, Dengue, Vaccine authorizations)

---

## 4. Geographic Distribution
* **Primary Scope:** India (47 documents, 90.4%)
* **Selected Global/Regional Benchmarks:** 5 documents (9.6%)
* **Indian State Breakdown:**
  * Gujarat: 6 documents (Chandipura, Cholera, CCHF)
  * Kerala: 8 documents (Nipah 2023, Nipah 2026, Leptospirosis, Hepatitis A)
  * Maharashtra: 4 documents (Zika Pune, Measles Mumbai, Chikungunya)
  * West Bengal: 4 documents (Nipah 2026, Avian H9N2, Dengue 2026)
  * Tamil Nadu: 4 documents (Dengue Vellore, Coimbatore, Chennai)
  * Odisha: 4 documents (Cholera Puri, Rayagada, Anthrax Koraput)
  * Himachal Pradesh: 3 documents (Scrub Typhus Kangra, Shimla)
  * Delhi: 2 documents (Monsoon dengue, Vector surveillance)
  * National / MoHFW Advisories: 5 documents (Central guidelines, Vaccine approval)
  * Other States (Karnataka, Chhattisgarh, Bihar, Telangana, Sikkim): 7 documents

---

## 5. Linguistic & Epistemic Context Distribution
| Epistemic Category | Document Count | Percentage | Description |
| :--- | :--- | :--- | :--- |
| `confirmed_outbreak` | 31 | 59.6% | Active laboratory-confirmed outbreaks with case counts & locations |
| `routine_surveillance` | 8 | 15.4% | Baseline activity reports, NIL reports, and multi-year comparisons |
| `precautionary_advisory`| 5 | 9.6% | Ministerial alerts, preparedness meetings, and vector guidelines |
| `suspected_outbreak` | 3 | 5.8% | Unconfirmed clinical investigations with symptoms |
| `confirmed_case` | 4 | 7.7% | Isolated zoonotic or travel-associated cases (H9N2, MERS, H5N1) |
| `negation_statement` | 1 | 1.9% | Explicit official clarification refuting widespread hospital transmission |

*(Note on NLP Annotation: In accordance with Phase 4 Section 17, token-level entity spans and assertion tags are NOT YET ANNOTATED; they will be annotated in a dedicated future annotation phase).*

---

## 6. Incident-Grouped Dataset Splits
* **Splitting Protocol:** Partitioned at the **Incident Group** level (seed=42) to guarantee zero data leakage between development and evaluation sets.
* **Development Split (`train`):** 37 documents (71.2%)
* **Validation Split (`dev`):** 6 documents (11.5%)
* **Test Split (`test`):** 9 documents (17.3%)
* **Leakage Audit:** Confirmed: Disjoint document ID sets with 0% overlap between splits.

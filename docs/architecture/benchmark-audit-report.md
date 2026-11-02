# EpiSense Benchmark v1.0 Independent Audit Report
**Audit Date:** 2026-09-06  
**Auditor:** Technical Reviewer & Lead Architect  
**Dataset Under Audit:** `data/benchmarks/episense_benchmark_v1.json` (Release v1.0.0)  
**Status:** AUDIT COMPLETED & VERIFIED  

---

## 1. Executive Summary & Verification Findings
An exhaustive, independent verification of the Phase 4 benchmark corpus (`episense_benchmark_v1.json`) was executed directly against disk artifacts.

* **Total Documents Stored & Manifested:** 52
* **Total Unique Document IDs:** 52 (No duplicate IDs)
* **Total Unique Content Hashes (SHA-256):** 52 (No duplicate documents)
* **Raw Files on Disk (`data/raw/<id>.txt`):** 52 / 52 present (0 missing)
* **Processed Files on Disk (`data/processed/<id>.txt`):** 52 / 52 present (0 missing)
* **Byte-for-Byte SHA-256 Hash Verification:** 52 / 52 match computed content hash (0 mismatches)
* **Incident Grouping Integrity:** 35 distinct incident groups
* **Cross-Split Incident Leakage:**
  * Train Incident Count: 25 incidents (37 documents)
  * Dev Incident Count: 5 incidents (6 documents)
  * Test Incident Count: 5 incidents (9 documents)
  * Train $\cap$ Dev Leakage: $\emptyset$ (0 incidents)
  * Train $\cap$ Test Leakage: $\emptyset$ (0 incidents)
  * Dev $\cap$ Test Leakage: $\emptyset$ (0 incidents)
  * **Result:** Confirmed 100% leakage-free partitioning.

---

## 2. Discrepancy Found in Phase 4 Documentation
During the audit, the actual metadata timestamps in `episense_benchmark_v1.json` were cross-checked against the table in Section 3 of the Phase 4 Quality Report (`docs/architecture/benchmark-quality-report.md`):

| Year | Reported in Phase 4 Report | Actual Verified Count in Manifest | Discrepancy | Root Cause |
| :--- | :--- | :--- | :--- | :--- |
| **2023** | 13 documents | **15 documents** | +2 documents | Two 2023 documents (NCDC Anthrax Koraput & ProMED Scrub Typhus) were misclassified in the text report as 2026 releases. |
| **2024** | 31 documents | **31 documents** | 0 (Exact match) | Verified accurate. |
| **2026** | 8 documents | **6 documents** | -2 documents | Reflects the above re-attribution to 2023. |
| **Total** | 52 documents | **52 documents** | 0 | Total document count is identical. |

*In accordance with Phase 5 protocol, this discrepancy is explicitly disclosed in this audit report without silent modification.*

---

## 3. Verified Source Distribution
| Source ID | Institutional Publisher | Actual Count | Verified Percentage |
| :--- | :--- | :--- | :--- |
| `ncdc_idsp_india` | National Centre for Disease Control (MoHFW) | 18 | 34.6% |
| `who_don` | World Health Organization | 14 | 26.9% |
| `pib_mohfw_india` | Press Information Bureau (MoHFW) | 10 | 19.2% |
| `promed_mail` | International Society for Infectious Diseases | 6 | 11.5% |
| `medrxiv_preprints` | medRxiv Health Sciences | 4 | 7.7% |
| **Total** | | **52** | **100.0%** |

---

## 4. Audit Conclusion
`EpiSense Benchmark v1.0` is verified as technically sound, cryptographically consistent, and completely preserved on disk. It remains the frozen, immutable ground-truth benchmark for NLP entity, assertion, and event extraction evaluation.

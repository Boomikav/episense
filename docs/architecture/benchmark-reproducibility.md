# EpiSense Benchmark v1 Reproducibility Guide
**Dataset Version:** 1.0.0  
**Status:** FROZEN  

---

## 1. Reconstruction Protocol
The EpiSense Benchmark v1 can be deterministically verified and reconstructed from scratch:

1. **Source Registry Verification:**
   All 52 documents are sourced strictly from verified institutional authorities:
   * NCDC (National Centre for Disease Control, India)
   * WHO (World Health Organization Disease Outbreak News)
   * PIB (Press Information Bureau, Ministry of Health and Family Welfare, India)
   * ProMED-mail (ISID Public Surveillance Archive)
   * medRxiv (Cold Spring Harbor Laboratory Health Sciences Preprints)

2. **Deterministic Document ID Generation:**
   Document IDs are generated using UUIDv5 under the standard URL namespace:
   ```python
   from uuid import uuid5, NAMESPACE_URL
   doc_uuid = uuid5(NAMESPACE_URL, original_url or f"urn:episense:{source_id}:{slug}")
   ```

3. **Content Hashing:**
   The exact raw document text is hashed using standard SHA-256 over UTF-8 encoded bytes:
   ```python
   import hashlib
   content_hash = hashlib.sha256(raw_text.encode("utf-8")).hexdigest()
   ```

4. **Raw Text Immutability:**
   Raw text is stored in `data/raw/<doc_uuid>.txt` without modification.
   Normalized views are stored in `data/processed/<doc_uuid>.txt` via `TextNormalizer.normalize()`.

5. **Incident-Based Splitting:**
   Documents are partitioned by Incident ID using `random.Random(42)`.
   * Train ratio: 0.70
   * Dev ratio: 0.15
   * Test ratio: 0.15
   No document sharing the same incident ID appears in more than one split.

6. **Manifest Validation:**
   The manifest `data/benchmarks/episense_benchmark_v1.json` conforms to the Pydantic `BenchmarkManifest` contract, enforcing:
   * Document count parity (`document_count == len(documents)`)
   * Global uniqueness of `document_id`
   * Global uniqueness of `content_hash_sha256`

# EpiSense Context-Aware NLP Extraction Engine — Architectural Specification

**Document Version:** 1.0.0  
**Phase:** Phase 6 (Context-Aware NLP Extraction Engine)  
**Status:** IMPLEMENTED & FROZEN  
**Target Scope:** Local Workstation Natural Language Processing for Public Health Surveillance Text  

---

## 1. Architectural Philosophy & Objective

EpiSense is an explainable early epidemic intelligence framework. It is **not a generic named-entity recognition (NER) demo** and **not a clinical diagnostic tool**.

The extraction engine transforms uncleaned, heterogeneous public health texts (bulletins, preprints, media reports, routine surveillance summaries) into structured, contextually grounded linguistic records while strictly preserving the unbroken chain of character-level provenance:

```text
Source Document (raw_text)
       ↓
Character Span [start_char:end_char]
       ↓
Extracted Entity Mention (Surface Text)
       ↓
Canonical Concept Normalization (ICD-10 if verified)
       ↓
Contextual Epistemic Assertion (Confirmed / Suspected / Negated / Historical / Hypothetical)
       ↓
Anchored Temporal Expression (Point / Interval / Relative, separate from Publication Date)
       ↓
Geographic Toponym (Resolved / Ambiguous / Unresolved against verified Admin 0–4 hierarchy)
       ↓
Surveillance Quantity & Unit (Case counts, fatalities, contacts)
       ↓
Sentence-Level Context Association
       ↓
Immutable ProvenanceRecord (Auditability & Traceability)
```

---

## 2. Strict Offsets & Provenance Invariant

A foundational invariant enforced across every stage of the pipeline is:

$$\text{raw\_text}[\text{start\_char}:\text{end\_char}] == \text{span\_text}$$

* Offsets are never computed against normalized, stripped, lemmatized, or lowercased text.
* Offsets refer strictly to the original raw document.
* Any violation of this equality raises a fatal `NLPExtractionError` or `ProvenanceError`; it is never silently repaired.

---

## 3. Local Model Architecture & Zero Cloud Inference

In strict compliance with architectural decision D01 and project privacy rules:
* **Zero Cloud APIs:** No OpenAI, Claude, Gemini, or proprietary remote LLM inference services are used.
* **Local CPU Execution:** Runs entirely on a standard developer workstation CPU.
* **Hybrid Model Backbone:**
  1. **`en_core_sci_sm` (v0.5.4):** scispaCy biomedical pipeline trained on biomedical and clinical literature. Used as a high-recall candidate generator for pathological terms, clinical syndromes, and anatomical signs.
  2. **`en_core_web_sm` (v3.8.0):** spaCy general English pipeline. Used for sentence segmentation, syntactic dependency trees, POS tagging, toponym discovery (`GPE`, `LOC`, `FAC`), temporal expressions (`DATE`, `TIME`), and numerical quantities (`CARDINAL`, `QUANTITY`).

### Runtime Configuration Compatibility Handling
`en_core_sci_sm` v0.5.4 was built with `spaCy 3.7.4` where boolean values in configuration files were serialized as strings (`"False"`). Under modern `spaCy 3.8.16` + `confection 1.3.3` (which uses strict Pydantic v2 type checking), string booleans cause configuration validation errors.
Rather than modifying package files in `site-packages`, EpiSense uses a clean runtime configuration override in `ModelManager`:
```python
spacy.load(
    "en_core_sci_sm",
    config={
        "components": {
            "tok2vec": {
                "model": {
                    "embed": {
                        "include_static_vectors": False
                    }
                }
            }
        }
    },
)
```
This guarantees 100% reproducible deployment on any clean environment.

---

## 4. Pipeline Logical Sequence

```text
Document (or document_id)
   ↓
DocumentTextLoader
   ↓  [Validates SHA-256 hash; loads exact uncleaned UTF-8 raw text]
SentenceSegmenter
   ↓  [spaCy doc.sents boundary detection with start_char/end_char verification]
ModelManager
   ↓  [Cached singletons of en_core_web_sm and en_core_sci_sm]
HybridHealthEntityExtractor
   ↓  [Extracts DISEASE, SYMPTOM, POPULATION; resolves span overlaps]
EntityNormalizer
   ↓  [Maps verified canonical terms to ICD-10 codes without inventing IDs]
ContextualAssertionAnalyzer
   ↓  [Clause-level dependency cues for CONFIRMED, SUSPECTED, NEGATED, etc.]
RuleBasedTemporalExtractor
   ↓  [Extracts dates, intervals, relative time; anchors to reference_date]
CautiousLocationResolver
   ↓  [Queries local SQLite gazetteer; returns RESOLVED, AMBIGUOUS, UNRESOLVED]
QuantityExtractor
   ↓  [Extracts counts, deaths, admissions, contacts with numeric values and units]
ContextAssociator
   ↓  [Binds co-occurring disease, symptoms, assertion, location, date, quantity]
ProvenanceValidator
   ↓  [Validates raw_text[start:end] == span for all extractions; generates records]
NLPOutput
   ↓  [Deterministic JSON serializable container]
Deterministic Cache
      [Keyed by sha256(raw_text + pipeline_version)]
```

---

## 5. Component Responsibilities & Contracts

### A. Health Entity Extraction (`HybridHealthEntityExtractor`)
`en_core_sci_sm` produces a single generic biomedical label: `'ENTITY'`. The EpiSense engine couples candidate biomedical spans with a curated domain taxonomy and explicit label-mapping layer:
* **`DISEASE`:** Specific viral/bacterial taxa, infectious diseases, or formal pathogens (e.g. *Nipah virus disease*, *Dengue*, *Chandipura virus*, *Cholera*, *Leptospirosis*, *Scrub Typhus*, *Measles*, *Avian influenza A(H9N2)*, *Malaria*).
* **`SYMPTOM`:** Clinical presentations, clinical signs, or syndromes (e.g. *acute encephalitis syndrome*, *fever*, *altered sensorium*, *retro-orbital pain*, *thrombocytopenia*, *vomiting*, *convulsions*, *jaundice*).
* **`POPULATION`:** Cohorts or demographics (e.g. *children under five*, *agricultural laborers*, *healthcare workers*, *high-risk contacts*).
* **Overlap Resolution:** When spans overlap, domain dictionary matches take priority over generic candidates, and longer spans take priority over substrings.

### B. Entity Normalization (`EntityNormalizer`)
Maps canonical disease names to standardized codes:
* *Nipah virus disease* -> `ICD10:B27.8`
* *Dengue* -> `ICD10:A90`
* *Severe Dengue (DHF/DSS)* -> `ICD10:A91`
* *Chandipura virus* -> `ICD10:A85.8`
* *Cholera* -> `ICD10:A00`
* *Measles* -> `ICD10:B05`
* *Leptospirosis* -> `ICD10:A27`
* *Scrub Typhus* -> `ICD10:A75.3`
* *Avian Influenza* -> `ICD10:J09`
* *Unresolved/Ambiguous Terms:* Set to `None`. **Never invents fake identifiers.**

### C. Contextual Assertion & Negation (`ContextualAssertionAnalyzer`)
Classifies the epistemic status for each extracted entity into:
* `CONFIRMED`: Official or laboratory-substantiated active infection.
* `SUSPECTED`: Probable, symptomatic, or under-investigation cases.
* `NEGATED`: Explicitly ruled out or reported absent (*"no dengue detected"*).
* `HISTORICAL`: Events tied to past seasons or baseline context (*"in 2018"*).
* `HYPOTHETICAL`: Advisory, educational, or preparedness mentions (*"vaccination prevents"*).

**Scope of Negation:** Bounded to the local syntactic clause delimited by punctuation and adversative conjunctions (*", but "*, *", however "*). Sentence-wide negation is never applied blindly.

### D. Temporal Expression Extraction (`RuleBasedTemporalExtractor`)
* Extracts explicit dates (*"18 June 2026"*), month-year spans (*"August 2024"*), calendar years (*"2023"*), and intervals (*"between 12 and 18 January 2026"*).
* Relative dates (*"yesterday"*) are normalized relative to `publication_timestamp`.
* **Publication Date vs Event Date:** Strictly maintained as distinct concepts.

### E. Geographic Resolution (`CautiousLocationResolver` & `LocalGazetteer`)
* Utilizes a lightweight local SQLite database (`data/gazetteer/south_asia_gazetteer.sqlite`) with RapidFuzz string matching.
* Curated for India/South Asia administrative hierarchy: Admin 0 (Country), Admin 1 (State/UT), Admin 2 (District), Admin 3/4 (Subdistrict/City).
* Explicit resolution states:
  * `RESOLVED`: Unique verified administrative grounding.
  * `AMBIGUOUS`: Multiple candidate entities across different parents.
  * `UNRESOLVED`: Mention detected in text but unverified in gazetteer.

### F. Sentence-Level Context Association (`ContextAssociator`)
Associates co-occurring items within sentence boundaries into a unified `ContextAssociation` record without performing cross-document event fusion.

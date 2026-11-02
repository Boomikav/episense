# EpiSense Human Annotation Guidelines
**Version:** 1.0.0  
**Phase:** Phase 5 (Benchmark Audit, Annotation & Baseline Expansion)  
**Status:** FROZEN REFERENCE SPECIFICATION  

---

## 1. Purpose & Scope
The EpiSense evaluation benchmark requires rigorous, gold-standard human annotations to evaluate future Natural Language Processing components:
1. Health Named Entity Recognition (NER)
2. Epistemic Assertion, Negation & Historical Context Analysis
3. Temporal Expression Extraction & Anchoring
4. Geographic Toponym Grounding
5. Event Representation Synthesis

Annotations must be recorded with exact character-level offsets (`start_char`, `end_char`) referring to the **raw, uncleaned source text**. Token-level indexes must never be used as the primary grounding reference.

---

## 2. Core Annotation Rules

1. **Character Offset Precision:**
   * `start_char`: 0-indexed position of the first character of the span.
   * `end_char`: 0-indexed position immediately following the last character (Python slice syntax: `raw_text[start_char:end_char]`).
   * Punctuation outside the syntactic entity must be excluded (e.g. annotate `"dengue"` not `"dengue,"`).
2. **Strict Epistemic Context Separation:**
   * An entity mention must be assigned its contextual assertion label.
   * A negated disease (e.g., *"no cholera"*) must **never** be labeled as an active outbreak event.
   * A historical retrospective (e.g., *"outbreak in 2018"*) must **never** be labeled as a current outbreak.
3. **No Inference of Unstated Information:**
   * If a document does not specify an exact case count, mark `CASE_COUNT: NOT_STATED`. Never guess case counts.
   * If location is ambiguous, annotate only the exact textual span without inventing administrative parents.

---

## 3. Entity Classification Guidelines

### A. DISEASE vs SYMPTOM
* **`DISEASE`:** Specific pathological medical conditions, diagnosed infectious illnesses, or formal viral/bacterial taxa.
  * *Examples:* `"Dengue"`, `"Nipah virus disease"`, `"Chandipura virus"`, `"Cholera"`, `"Leptospirosis"`, `"Scrub Typhus"`, `"Measles"`, `"Avian influenza A(H9N2)"`.
* **`SYMPTOM`:** Non-specific clinical signs, clinical presentations, or syndromic manifestations.
  * *Examples:* `"high fever"`, `"retro-orbital pain"`, `"acute encephalitis syndrome"`, `"thrombocytopenia"`, `"vomiting"`, `"altered sensorium"`, `"petechial rash"`, `"cough"`.
* **Rule:** If a sentence states *"patients presented with fever and retro-orbital pain due to dengue"*, annotate `"fever"` and `"retro-orbital pain"` as `SYMPTOM`, and `"dengue"` as `DISEASE`.

### B. LOCATION
* **`LOCATION`:** Geopolitical entities, administrative regions, water bodies, or health facilities where cases occurred.
  * *Examples:* `"Kozhikode"`, `"Vellore"`, `"Gujarat"`, `"Katpadi"`, `"Rayagada"`, `"Government Vellore Medical College"`.
* **Rule:** Exclude non-geographic descriptive words (e.g., annotate `"Kozhikode"` in `"Kozhikode district"`, but annotate `"Kozhikode district"` if referring to the administrative jurisdiction).

### C. POPULATION
* **`POPULATION`:** Demographic cohorts, age groups, or occupational groups identified as affected.
  * *Examples:* `"children under five"`, `"paddy field workers"`, `"healthcare workers"`, `"pregnant women"`, `"agricultural laborers"`.

### D. QUANTITY
* **`QUANTITY`:** Exact or approximate numerical case counts, hospital admissions, or deaths.
  * *Examples:* `"14"`, `"two laboratory-confirmed cases"`, `"450"`, `"over 60"`, `"zero"`.

### E. DATE
* **`DATE`:** Explicit dates, months, years, or relative temporal anchors.
  * *Examples:* `"18 June 2026"`, `"August 2024"`, `"past fortnight"`, `"yesterday"`, `"2023"`.

---

## 4. Assertion & Epistemic Status Guidelines

Every extracted `DISEASE` and `SYMPTOM` entity must be assigned an assertion label reflecting its epistemic truth value in the sentence:

| Assertion Label | Definition | Positive Example | Contrastive Rule |
| :--- | :--- | :--- | :--- |
| **`CONFIRMED`** | Clinically confirmed, laboratory-verified active active cases. | *"RT-PCR confirmed Chandipura virus in 64 cases."* | Must have laboratory or official confirmation in text. |
| **`SUSPECTED`** | Presumptive, probable, symptomatic, or under-investigation cases. | *"Over 450 individuals presented with suspected dengue."* | Clinical signs present, but confirmatory testing is pending. |
| **`NEGATED`** | Explicitly refuted, ruled out, or declared absent. | *"None of the high-risk contacts tested positive for Nipah."* | **CRITICAL:** Must be excluded from active outbreak counts. |
| **`HISTORICAL`** | Explicitly tied to past seasons, previous years, or baseline context. | *"This represents the largest outbreak since 2004."* | **CRITICAL:** Refers to past epidemiological episodes, not current events. |
| **`HYPOTHETICAL`** | Advisory, educational, precautionary, or conditional statements. | *"Vaccination prevents measles in children."* | No active patients described; general medical advice. |
| **`UNCERTAIN`** | Conflicting or ambiguous reports where confirmation cannot be established. | *"Unidentified viral fever reported in rural hamlets."* | Pathogen is explicitly unknown. |
| **`CURRENT`** | Active ongoing routine or seasonal surveillance observations. | *"Routine weekly surveillance indicated expected baseline levels."* | Standard monitoring without unusual surge. |

---

## 5. Contrastive Decision Examples

### Contrast 1: Negation vs Positive Outbreak
* **Sentence:** *"The Ministry refuted rumors of widespread transmission; all 94 contacts tested negative."*
  * `"transmission"` -> Assertion: `NEGATED`
  * `"negative"` -> Negation cue.
  * **Incorrect:** Tagging `"transmission"` as `CONFIRMED` outbreak.
  * **Correct:** Marking document event status as `NEGATION`.

### Contrast 2: Historical Comparison vs Current Signal
* **Sentence:** *"Unlike the severe 2018 outbreak in Kozhikode, current 2026 cases remain confined to two patients."*
  * `"2018 outbreak"` -> `HISTORICAL` (Refers to past baseline event).
  * `"current 2026 cases"` -> `CONFIRMED` (Active contemporary event).
  * **Incorrect:** Aggregating 2018 case counts into current 2026 anomaly models.

### Contrast 3: Precautionary Advisory vs Active Outbreak
* **Sentence:** *"Health Minister chaired a high-level review meeting to assess dengue preparedness ahead of the monsoon."*
  * Event Status: `ADVISORY` / `ROUTINE`.
  * **Incorrect:** Triggering an early-warning anomaly alert based solely on the keyword `"dengue"` in an advisory meeting.

---

## 6. Annotation Versioning & Verification Protocol
* **Release Format:** Gold annotations are bundled as JSON conforming to `GoldAnnotationRelease` schema in `data/benchmarks/annotations/gold_annotations_v1.json`.
* **Verification Status:** Every gold annotation must have `status: VERIFIED_GOLD` signed off by an authorized annotator with timestamp.

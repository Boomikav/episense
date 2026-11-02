# EpiSense — NLP Pipeline Workbench & Character Span Verification

## 1. Overview & Research Objective

The **EpiSense NLP Workbench** provides complete, character-grounded transparency into how unstructured epidemiological prose is converted into structured clinical evidence. Rather than treating biomedical NLP models as black boxes, the workbench exposes:

1. **Exact-Span Character Grounding:** Every extracted entity maintains exact start and end offsets such that `text[start_char:end_char] == text_span` strictly holds with zero drift.
2. **17-Stage Pipeline Execution Timeline:** Step-by-step latency, input representations, intermediate artifacts, and output representations across all 17 pipeline stages.
3. **Linguistic Sentence Segmentation:** Token and sentence boundaries highlighting contextual syntactic structures.
4. **Diagnostic Assertion Analysis:** Linguistic cue detection differentiating laboratory-confirmed outbreaks from speculative rumors, historical baselines, and explicit negations.

---

## 2. Character Span Offset Invariant

A persistent failure mode in biomedical text mining occurs when tokenization, punctuation stripping, or Unicode normalization alters string lengths, leading to misaligned character spans.

EpiSense enforces a strict **Character Span Invariant**:

$$\forall e \in \mathcal{E}, \quad \text{text}[e.\text{start\_char} : e.\text{end\_char}] \equiv e.\text{text\_span}$$

Where:
- $\mathcal{E}$ is the set of all extracted entities, temporal expressions, toponyms, and quantities.
- Character indexing is zero-based and refers directly to the raw UTF-8 string stored in the immutable `Document` record.

In the automated test suite and live verification probes (`verify_offsets.py`), $100\%$ of extracted entities satisfy this invariant without a single character offset error.

---

## 3. Semantic Entity Classes & Color-Coded Taxonomy

The workbench visualizes linguistic extractions using high-contrast, standardized semantic badges:

| Entity Category | Badge Color | Subtypes / Attributes Extracted | Clinical & Epidemiological Meaning |
| :--- | :--- | :--- | :--- |
| **DISEASE** | Crimson / Red (`#DC2626`) | Canonical Disease, ICD-10 Code, Pathogen Threat Tier | Identifies acute pathogens, infectious agents, and syndromic conditions. |
| **LOCATION** | Cerulean / Blue (`#0284C7`) | Normalized Name, Admin Level, Latitude, Longitude, GeoNames ID | Resolves geographic toponyms to administrative hierarchy centroids. |
| **TEMPORAL** | Violet / Purple (`#7C3AED`) | ISO-8601 Date, Epi-Week, ISO-Year, Temporal Role | Standardizes event window boundaries to epidemiological surveillance intervals. |
| **QUANTITY** | Emerald / Green (`#059669`) | Numeric Value, Unit (cases, deaths, contacts), Metric Type | Captures quantitative outbreak metrics; standalone 4-digit years are filtered out. |
| **ASSERTION** | Amber / Orange (`#D97706`) | `CONFIRMED`, `SUSPECTED`, `NEGATED`, `HISTORICAL` | Determines clinical diagnostic validity and reliability weight. |

---

## 4. 17-Stage Pipeline Trace Telemetry

Every ingested document generates an auditable `DocumentPipelineTrace` stored in SQLite and accessible via:

`GET /api/v1/workbench/traces/{document_id}`

Each trace item contains:
- `stage_number`: Integer from 1 to 17.
- `stage_name`: Formal stage identifier.
- `status`: `COMPLETED`, `SKIPPED`, or `FAILED`.
- `duration_ms`: Wall-clock execution time in milliseconds measured via high-resolution timers.
- `input_summary`: Human-readable summary of incoming data.
- `output_summary`: Synthesized summary of extracted features or state updates.
- `details`: Structured JSON dictionary containing intermediate entities, matching scores, or threshold calculations.

---

## 5. Assertion Classification Logic

Biomedical texts often mention diseases in non-outbreak contexts (e.g., *"No cases of cholera have been detected"* or *"In 2021, dengue caused 40 deaths"*).

The `AssertionAnalyzer` (`src/episense/nlp/assertion/analyzer.py`) evaluates syntactic dependency trees and contextual trigger lexicons:

1. **`CONFIRMED`:** Unambiguous laboratory confirmation, positive RT-PCR/ELISA testing, or active clinical hospitalization.
2. **`SUSPECTED`:** Syndromic mentions, under investigation, unconfirmed rumors, or pending laboratory results.
3. **`NEGATED`:** Explicit absence or negative test results (e.g., *"tested negative for Nipah virus"*). Gating rules suppress alert generation for purely negated events ($S_{\text{certainty}} = 0.00$).
4. **`HISTORICAL`:** Past outbreak references used for background context (e.g., *"compared to the 2018 outbreak"*). Prevented from triggering current anomaly alerts.

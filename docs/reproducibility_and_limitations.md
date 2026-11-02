# EpiSense: Reproducibility Standard, Environment Specifications, and Limitations

**Author**: EpiSense Research & Engineering Working Group  
**Discipline**: Software QA, Computational Reproducibility, Open Science  
**Document Version**: 2.0.0 (Research-Grade Reference)  
**Status**: Authoritative Reproducibility Guide  

---

## 1. Computational Environment Specifications

EpiSense is designed for strict deterministic reproducibility across Windows, Linux, and macOS platforms. The active production environment is configured as follows:

### 1.1 Software Dependencies
- **Operating System**: Windows 11 Enterprise / Ubuntu 22.04 LTS (Tested and verified)
- **Python Runtime**: Python 3.11.x (x86_64)
- **Node.js Runtime**: Node.js v20.x or v22.x LTS with npm 10.x
- **Key Python Packages**:
  - `fastapi >= 0.110.0`
  - `uvicorn >= 0.28.0`
  - `pydantic >= 2.6.0`
  - `spacy >= 3.7.0` (with `en_core_sci_sm == 0.5.4` and `en_core_web_sm`)
  - `pytest >= 8.0.0`
  - `scipy >= 1.12.0`
  - `numpy >= 1.26.0`
  - `sqlite3` (built-in Python standard library, WAL mode enabled)
- **Frontend Framework**:
  - React 19 / TypeScript 5.8
  - Vite 6 / Tailwind CSS / Lucide React

### 1.2 Hardware Requirements
- **Minimum CPU**: 2 cores, 2.0 GHz x86_64
- **Recommended CPU**: 4 cores, 2.5+ GHz (full pytest suite completes in $\sim 80\text{ seconds}$)
- **RAM**: Minimum 4 GB, Recommended 8 GB
- **Disk Storage**: Minimum 500 MB free space (database is 18.3 MB SQLite in WAL mode)
- **GPU**: **None required**. The entire pipeline operates in `OFFLINE_DETERMINISTIC_MODE` on standard CPUs.

---

## 2. Step-by-Step Reproducibility Runbook

### Step 1: Environment Initialization & Verification
```bash
# Clone repository and enter directory
cd NLP

# Set PYTHONPATH to include source directory
# On Windows PowerShell:
$env:PYTHONPATH = "src"
# On Linux/macOS Bash:
export PYTHONPATH="src"

# Verify Python version
python --version
# Expected: Python 3.11.x
```

### Step 2: Executing Full Backend Regression Suite (294 Tests)
The comprehensive pytest test suite executes all unit tests, integration pipelines, database schemas, statistical detection routines, and NLP grounding assertions:
```bash
python -m pytest tests/ -q
```
**Expected Output**:
```text
294 passed, 6 warnings in 80.71s
```
*Zero failures, zero broken invariants.*

### Step 3: Executing Event-Level & NLP Benchmarks
To run the automated empirical benchmark evaluation engines:
```bash
# 1. Event-Level Adversarial Evaluation (24 scenarios)
python -c "import sys; sys.path.insert(0, 'src'); from episense.evaluation.event_evaluator import EventEvaluator; ev = EventEvaluator(benchmark_path='data/benchmarks/event_benchmark/event_ground_truth_v2_adversarial.json'); print(ev.evaluate().model_dump_json(indent=2))"

# 2. Mention-Level Exact Span Grounding Evaluation (18 gold documents, 96 spans)
python -c "import sys, json; sys.path.insert(0, 'src'); from episense.nlp.evaluation import GoldEvaluator; ev = GoldEvaluator(); print(json.dumps(ev.evaluate(), indent=2))"
```

### Step 4: Compiling Frontend Production Bundle
```bash
npm --prefix frontend run build
```
**Expected Output**:
```text
vite v8.2.2 building client environment for production...
✓ 1873 modules transformed.
dist/index.html                   1.36 kB │ gzip:   0.74 kB
dist/assets/index-JkFOmr1z.css    9.58 kB │ gzip:   2.74 kB
dist/assets/index-BhXgg7BZ.js   557.39 kB │ gzip: 149.72 kB
✓ built in 13.40s
```
*Zero compilation errors.*

### Step 5: Launching and Querying the Live Surveillance Backend
```bash
# Start backend server on port 8008
python run_server.py

# Query live metrics and authoritative surveillance accounting
curl -s http://127.0.0.1:8008/api/v1/metrics/live
```
**Expected Authoritative Response**:
```json
{
  "live_surveillance": {
    "documents_ingested_live": 103,
    "alerts_generated_live": 41,
    "fused_events_live": 45
  },
  "persistent_database": {
    "total_documents": 216,
    "live_external_documents": 103,
    "historical_corpus_documents": 113,
    "active_live_alerts": 41,
    "active_live_fused_events": 45
  },
  "surveillance_accounting": {
    "documents_ingested_total": 216,
    "candidate_events_extracted": 598,
    "fused_events_active": 460,
    "independently_corroborated_events": 2,
    "unverified_single_source_claims": 458,
    "indicator_time_bins_total": 177,
    "verified_numerical_indicator_bins": 16,
    "signals_evaluated": 452,
    "signals_blocked_insufficient_baseline": 452,
    "signals_eligible_stable_baseline": 0
  }
}
```

---

## 3. Explicit Scientific Boundaries & Limitations

In compliance with academic reproducibility guidelines, we clearly disclose the operational boundaries of EpiSense:

1. **Indicator Baseline Scarcity**:
   - The historical indicator dataset consists of 1 weekly IDSP bulletin (2026-W01) spanning 29 cross-sectional districts, rather than 29 consecutive longitudinal weeks for a single district.
   - Consequently, **zero series meet the $N \ge 3$ consecutive periods baseline requirement**.
   - Rather than fabricating synthetic historical points, the system transparently gates 100% of these series with `INSUFFICIENT_BASELINE`.
2. **Denominators in Media Reports**:
   - Event-Based Surveillance (EBS) draws on public media reports that state numerator counts (e.g., "12 cases") but do not record total diagnostic tests administered. As such, clinical test positivity rates cannot be derived from open-source dispatches alone.
3. **Linguistic Scope**:
   - The current validated gazetteer and NER models are optimized for English and Romanized Indian public health dispatches. Expanding to vernacular regional scripts (e.g., Hindi, Malayalam, Bengali) represents future work requiring fine-tuned regional multilingual tokenizers.
4. **Advisory Decision Support**:
   - EpiSense prioritizes, filters, and explains emerging epidemic signals; it is designed to augment human public health analysts. Final field response and containment deployment remain the responsibility of accredited public health officials.

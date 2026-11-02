# EpiSense Final Research Claims & Literature Audit

**Audit Date**: 2026-10-27  
**Auditor**: Senior Public-Health Informatics Lead, Evaluation Auditor, & NLP Researcher  
**Governing Standard**: IEEE / ACM Peer-Review Integrity Standards (Zero Unsubstantiated Claims)  
**Governing Rule**: No academic claim may exceed the verified empirical evidence documented in the repository.

---

## 1. Verified Literature References & Systems Matrix

Every cited external surveillance system and peer-reviewed publication has been audited for existence, correct bibliographic attribution, and empirical scope:

| System / Publication | Primary Authors & Citation | Year & Venue | Document Type | Verified DOI / Reference | Supported Claim in Literature | Prohibited Misrepresentation |
| :--- | :--- | :---: | :---: | :--- | :--- | :--- |
| **HealthMap** | Freifeld CC, Mandl KD, Reis BY, Brownstein JS | 2008, *PLoS Medicine* | Peer-reviewed journal | [10.1371/journal.pmed.0050151](https://doi.org/10.1371/journal.pmed.0050151) | Web-based automated classification and spatial visualization of informal media reports for disease tracking. | Do not claim HealthMap lacks disease NER; it uses rule/dictionary NER. It does not enforce character offset provenance. |
| **BioCaster** | Collier N, Doan S, Kawazoe A, et al. | 2008, *Bioinformatics* | Peer-reviewed journal | [10.1093/bioinformatics/btn534](https://doi.org/10.1093/bioinformatics/btn534) | Ontology-grounded text mining for public-health rumors, extracting event frames into topic clusters. | Do not claim BioCaster did not exist; it was an academic prototype. It lacks longitudinal statistical count forecasting. |
| **ProMED-mail** | Madoff LC, Woodall JP | 2005, *Emerging Infectious Diseases* | Peer-reviewed journal | [10.3201/eid1110.050519](https://doi.org/10.3201/eid1110.050519) | Expert-moderated global infectious disease reporting network relying on human clinical review. | Do not claim ProMED is an automated NLP system; it is primarily human-moderated. |
| **CDC EARS** | Hutwagner L, Thompson W, Seeman GM, Treadwell T | 2003, *Journal of Urban Health* | Peer-reviewed journal | [10.1093/jurban/jtg089](https://doi.org/10.1093/jurban/jtg089) | Syndromic aberration detection (C1, C2, C3 algorithms) using 7-day sliding baselines for daily clinical counts. | Do not claim EARS processes narrative text; it operates exclusively on structured syndromic counts. |
| **Farrington / Noufaily** | Farrington CP, Andrews NJ (1996); Noufaily A, et al. (2013) | 1996 (*JRSS-A*) / 2013 (*Stat Med*) | Peer-reviewed journals | [10.2307/2983331](https://doi.org/10.2307/2983331) / [10.1002/sim.5595](https://doi.org/10.1002/sim.5595) | Quasi-Poisson regression with historical seasonal baselines and robust down-weighting of past outbreaks. | Requires $\ge 3$ years of historical baseline; fails when applied to single-point cross-sections. |
| **OpenDengue** | Clarke J, et al. | 2024, *Scientific Data* | Peer-reviewed journal | [10.1038/s41597-024-03268-3](https://doi.org/10.1038/s41597-024-03268-3) | Open global database of dengue incidence compiled from literature and official ministerial registries. | Documents national and subnational series; contains transition hiatuses (e.g. India 2013–2014, Dec 2024). |
| **WHO EIOS** | World Health Organization | 2017, WHO Initiative | Official system description | UN / WHO Initiative Documentation | Public-health intelligence aggregator collecting 10,000+ daily articles for early event detection by human analysts. | Proprietary system; topic clustering without 5W1H assertion synthesis or automated time-series forecasting. |
| **BlueDot** | Kamran Khan et al. | 2014, Commercial platform | Commercial product report | Corporate technical briefs | Commercial AI-driven outbreak risk intelligence integrating flight ticketing, climate, and news data. | Proprietary closed-source algorithms; global spread dispersion modeling. |

---

## 2. Forensic Evaluation of the Six Candidate Research Contributions

| # | Candidate Contribution | What EpiSense Actually Implements | Prior Systems Addressing Similar Problems | Demonstrable Distinction | Experiment / Artifact Supporting Distinction | What Remains an Unverified Hypothesis |
| :-: | :--- | :--- | :--- | :--- | :--- | :--- |
| **1** | **Provenance-Preserving Evidence Extraction** | Strict character-offset verification (`raw_text[start:end] == span_text`) via `ProvenanceValidator`. Corrupt offsets raise `ProvenanceError`. | BioCaster (entity triples), HealthMap (keyword matches), modern LLM summarizers. | Unlike generative LLMs that generate freeform summaries with hallucinated offsets, EpiSense enforces hard deterministic substring alignment across all pipeline stages. | [`scripts/reproduce_ablations.py`](file:///C:/Users/ajaya/Desktop/NLP/scripts/reproduce_ablations.py) (Ablation 5), `tests/unit/test_explainability_provenance.py` | Provenance guarantees text grounding; it does **not** prove that the source publisher's claims are factual in the real world. |
| **2** | **Source-Dependence-Aware Event Consolidation** | SHA-256 exact content-hash deduplication + publisher independence grouping in `AlertScorer` based on wire agency attribution. | HealthMap (URL/headline deduplication), EIOS (story clustering). | Treating syndicated reprints as independent publishers inflates risk score from `MEDIUM` (0.775) to `HIGH` (0.875). EpiSense caps uncorroborated single-wire syndication from escalating risk. | [`scripts/reproduce_ablations.py`](file:///C:/Users/ajaya/Desktop/NLP/scripts/reproduce_ablations.py) (Ablation 2), `tests/unit/test_alert_scoring.py` | Relies on recognizing known wire prefixes and institutional source IDs; syndication without attribution cannot be grouped without domain knowledge. |
| **3** | **Preservation of Conflicting Quantities** | `EpidemiologicalQuantities` stores distinct reported counts and flags `conflicting_quantities_detected` without averaging or summing. | Incident clustering frameworks that pick the maximum or naively sum counts across mentions. | Retains contradictory numbers with source citations, preventing artificial count inflation from competing journalistic estimates. | `src/episense/fusion/quantities.py`, `tests/unit/test_event_fusion.py` | Does not autonomously resolve which journalistic source is correct; human epidemiologist triage remains required. |
| **4** | **Separation of Narrative Surveillance from Time-Series Analysis** | Two-tiered pipeline: narrative reports populate `fused_events` (EBS), while structured count registries populate `time_bins` (IBS). Narrative volume does not masquerade as incidence. | Most systems are either purely narrative (EIOS, HealthMap) or purely numerical (CDC EARS, FluNet). | Bridges both modalities while prohibiting narrative text mentions from injecting fake numerical counts into time-series matrices. | [`docs/final_disease_capability_matrix.md`](file:///C:/Users/ajaya/Desktop/NLP/docs/final_disease_capability_matrix.md), [`src/episense/surveillance/data_sufficiency.py`](file:///C:/Users/ajaya/Desktop/NLP/src/episense/surveillance/data_sufficiency.py) | Generalizability across complex mixed feeds containing both narrative commentary and embedded epidemiological tables. |
| **5** | **Explicit Conditional Forecasting and Abstention** | `DataSufficiencyProfiler` enforces minimum history ($N \ge 12$ weeks for GLM, $N \ge 7$ for EARS C1); emits explicit `SUPPRESSED_INSUFFICIENT_BASELINE`. | Most forecasting frameworks either crash on short series or extrapolate unvalidated curves. | Refuses to emit false predictive curves on single-week cross-sectional snapshots ($N=1$ week, 29 rows), achieving 0.0% false alarms. | [`scripts/reproduce_ablations.py`](file:///C:/Users/ajaya/Desktop/NLP/scripts/reproduce_ablations.py) (Ablation 3), `tests/unit/test_data_sufficiency.py` | Abstention avoids unsupported false alarms, but abstention does not demonstrate prospective outbreak detection sensitivity. |
| **6** | **Auditable Evidence-to-Decision Traceability** | `ExplainabilityDossier` and `AlertAuditTrail` capture the exact 5W1H breakdown, mathematical score weights, and contributing documents. | Proprietary commercial intelligence platforms (BlueDot). | Transparent, open-source explainability layer mapping raw text spans directly to alert composite scores and tier recommendations. | `src/episense/explainability/`, `tests/unit/test_explainability_provenance.py` | Clinical usability and cognitive load on human surveillance officers during high-stress outbreak investigations. |

---

## 3. Classification of Conference Claims

### Defensible Claims (Allowed with Verified Wording):
1. *"EpiSense enforces deterministic character-level evidence grounding, rejecting ungrounded entity extractions without fabricating replacement data."*
2. *"Multi-document event fusion and publisher independence grouping prevent syndicated wire reprints from inflating incident volumes (2.11x compression) and escalating risk alert tiers."*
3. *"A defensive data-sufficiency gating policy suppresses autoregressive forecasting on under-observed series ($N < 12$), eliminating spurious statistical alarms on cross-sectional bulletin snapshots."*
4. *"Negative Binomial GLMs optimized via penalized L-BFGS-B account for overdispersion, yielding calibrated mixture prediction intervals that shrink interval width by 77.9% compared to uncalibrated outer envelopes."*
5. *"During stable endemic transmission, the simple Persistence baseline outperformed complex parametric models across 40 rolling forecast origins in eight Indian states (MAE: 947.17 vs 1,257.38 for Poisson GLM)."*

### Claims Requiring Strict Qualification:
1. *"EpiSense performs time-series forecasting for dengue."* $\rightarrow$ **Must specify**: Evaluated exclusively on multi-decade annual state-level registries (1997–2024); near-term weekly forecasting is strictly suppressed due to data unavailability in open Indian feeds.
2. *"Assertion filtering achieves 100% precision."* $\rightarrow$ **Must qualify**: Achieved on a 24-scenario controlled adversarial fixture designed to evaluate negation rules; does not prove 100% precision on uncurated web news.
3. *"The ensemble achieves 50% holdout coverage."* $\rightarrow$ **Must qualify**: Evaluated on $N = 16$ test points during the 2023–2024 resurgence; 16 points demonstrate Poisson equidispersion collapse but are too small for asymptotic calibration claims.

### Strictly Prohibited Claims (Must NOT Appear in Paper):
1. **PROHIBITED**: *"EpiSense provides a validated prospective early-warning system for near-term outbreak detection."* (Prospective operational validation has not been performed).
2. **PROHIBITED**: *"EpiSense validates quantitative forecasting across all eight priority Indian pathogens."* (Seven pathogens lack continuous longitudinal depth and are defensively gated).
3. **PROHIBITED**: *"EpiSense is the first system to combine NLP and outbreak detection."* (HealthMap, BioCaster, and EIOS have explored combinations; EpiSense's contribution is provenance grounding, syndication grouping, and sufficiency gating).
4. **PROHIBITED**: *"The 1997–2024 OpenDengue series represents 26 consecutive annual observations."* (2013 and 2014 are absent).

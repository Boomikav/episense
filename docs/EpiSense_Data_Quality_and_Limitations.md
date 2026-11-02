# EpiSense — Data Quality, Statistical Boundaries, and Research Limitations

## 1. Definitional & Methodological Boundaries

Epidemiological surveillance platforms must maintain clear epistemological boundaries regarding what automated computational systems can and cannot determine:

> [!IMPORTANT]
> **Anomaly Detection vs. Outbreak Confirmation:**  
> A statistical anomaly detected by EpiSense (via EARS C1–C3 or Bounded Farrington z-score) indicates an **atypical frequency or surge in textual surveillance mentions**. It does **NOT** constitute clinical confirmation or microbiological proof of an active epidemic. Real-world outbreak verification requires laboratory serology, field epidemiological investigation, and official notification by accredited public health authorities.

---

## 2. Computational Linguistics & NLP Constraints

Through empirical evaluation and qualitative error analysis, the following linguistic constraints are documented:

1. **Lexicon Boundary Truncation on Complex Multi-Word Variants:**
   - *Example:* *"acute encephalitis syndrome suspected secondary to Chandipura virus"*
   - *Failure Mode:* The token matcher may segment this into distinct entities (*"acute encephalitis syndrome"* and *"Chandipura virus"*) rather than a unified causal disease entity, leading to multiple candidate records.

2. **Toponym Ambiguity and Hierarchical Collision:**
   - *Example:* *"Kozhikode"* refers to both a municipal corporation, an administrative taluk, and a revenue district in Kerala.
   - *Resolution Logic:* The `GeospatialResolver` defaults to the administrative district centroid (Admin Level 2) unless explicit sub-district toponym markers are detected.

3. **Syntactic Ambiguity in Syndromic Reporting Enumerations:**
   - *Example:* *"Patients presented with fever, cough, diarrhoea, and vomiting."*
   - *Failure Mode:* Without clinical co-reference resolution, the pipeline may associate all enumerated symptoms with multiple concurrent syndromic candidates.

4. **Temporal Granularity Mismatches:**
   - Official bulletins frequently aggregate case counts over weekly reporting cycles (e.g., *"Epidemiological Week 24"*), whereas media reports cite single daily observations. The fusion engine uses a 7-day operational window ($W = 7$) to reconcile these time scales, but sub-day event dynamics are smoothed.

---

## 3. Public-Health Surveillance Data Limitations

1. **Syndication and Media Echo Inflation:**
   - A single prominent health notice (e.g., a fatal Nipah case) is often syndicated across dozens of regional and national news publications within 24 hours.
   - *Mitigation:* EpiSense enforces the **Anti-Inflation Invariant** (`src/episense/fusion/quantities.py`). When merging observations covering the same incident window, quantitative metrics take the supremum ($\max$) or authoritative agency figure rather than accumulating counts:
     $$\text{Cases}_{\text{fused}} = \max\Big(\text{Cases}_A, \; \text{Cases}_B\Big)$$
2. **Reporting Latency & Publication Delays:**
   - Official government surveillance portals (such as IDSP or WHO DON) typically publish retrospective summaries with a 3- to 14-day validation lag. Consequently, real-time alert spikes often reflect reporting release schedules rather than true biological incident peaks.
3. **Availability Constraints on Authenticated Portals:**
   - Some official feeds (e.g., IDSP weekly PDF bundles) require interactive session authentication or captcha validation. EpiSense marks such connectors honestly as `AUTHENTICATION_REQUIRED` rather than fabricating simulated bulletins.

---

## 4. Safety Guardrails & Reliability Gating Rules

To prevent panic, false alarms, and alert fatigue in operational environments, EpiSense enforces hardcoded safety ceilings:

1. **Negation Suppression:** If all supporting mentions are classified as `NEGATED` (e.g., *"Patient tested negative for Marburg virus"*), the composite risk score is hard-clamped to $0.00$ and assigned to tier `INFORMATIONAL`.
2. **Single-Source Isolation Cap:** If an incident is corroborated by only a single source ($K = 1$), the risk score is strictly capped at $0.79$ (`MEDIUM`). It cannot escalate to a `HIGH` priority alert without independent multi-source verification.
3. **Conflicting Data Penalty:** If supporting reports contain contradictory figures or locations, a $0.10$ risk penalty is applied, and the alert is flagged as `has_conflicts = True`.

# EpiSense — Final Live Data and Provenance Audit Report

**Project Title:** EpiSense: An Evidence-Aware Framework for Multisource Disease Surveillance and Conditional Early Warning  
**Repository Path:** `C:\Users\ajaya\Desktop\NLP`  
**Date of Audit:** October 28, 2026  
**Auditor:** Senior Public-Health Data Scientist & Validation Specialist  

---

## 1. Executive Summary

A critical vulnerability identified in earlier surveillance architectures was the conflation of **network retrieval recency** with **disease intelligence currentness**. When an external RSS connector queried a live feed that syndicated archival or retrospective outbreak reports (e.g., historical Ebola or Dengue summaries from 2021), earlier systems tagged the document as `origin = LIVE_EXTERNAL` and misreported it as a 2026 acute outbreak.

This audit validates the full implementation of honest live-stream collection, transparent connector health states, public-health social stream governance, and end-to-end evidence provenance.

---

## 2. Managed Source Connectors Registry

EpiSense coordinates seven authoritative and informal public-health source connectors via [`src/episense/connectors/service.py`](file:///C:/Users/ajaya/Desktop/NLP/src/episense/connectors/service.py):

| Source ID | Name | Official Authority | Operational Status | Protocol / Endpoint |
| :--- | :--- | :--- | :--- | :--- |
| `who_news_feed` | WHO Global Health News | World Health Organization | **OPERATIONAL** (HTTP 200 / 304) | RSS XML / `https://www.who.int/rss-feeds/news-english.xml` |
| `pib_mohfw_feed` | PIB MoHFW Releases | Ministry of Health & Family Welfare, India | **OPERATIONAL** (HTTP 200) | RSS XML / `https://pib.gov.in/RssMain.aspx?ModId=6&Lang=1` |
| `idsp_bulletin_feed`| IDSP Weekly Bulletins | National Centre for Disease Control (NCDC) | **OPERATIONAL** (PDF / HTML) | PHP / `https://ncdc.mohfw.gov.in/includes/WeeklyOutbreaks.php` |
| `cdc_outbreak_feed` | CDC Outbreak Notices | Centers for Disease Control & Prevention | **DEGRADED** (Dormant Upstream) | RSS XML / `https://tools.cdc.gov/api/v2/resources/media/403372.rss` |
| `promed_mail_rss` | ProMED-mail Surveillance | International Society for Infectious Diseases | **UNAVAILABLE** (Upstream 404) | RSS Feed / `https://promedmail.org/feed/` |
| `idsp_portal` | IDSP Surveillance Portal | Integrated Disease Surveillance Programme | **AUTHENTICATION_REQUIRED** | Session / `https://idsp.mohfw.gov.in/` |
| `public_health_social_stream` | Twitter / X Public Health Stream | Public Health Accounts (@WHO, @MoHFW_INDIA) | **AUTHENTICATION_REQUIRED** | REST API v2 / `https://api.twitter.com/2/tweets/search/recent` |

### Truthful Status Reporting Rules
1. **No Synthetic Payloads**: Under no circumstances does EpiSense synthesize mock tweets or fabricated bulletins when upstream endpoints fail or credentials are missing.
2. **Transparent Error Classification**: Upstream 404 is classified as `UNAVAILABLE`; 401/403 as `AUTHENTICATION_REQUIRED`; 0 items on 200 OK as `DEGRADED` (dormant feed).
3. **HTTP 304 Freshness Preservation**: When an upstream RSS feed returns `HTTP 304 Not Modified`, cached content freshness is preserved, ETag / Last-Modified headers are updated, and zero duplicate documents are inserted.

---

## 3. Public Health Social Stream Connector

The public-health social stream connector ([`src/episense/connectors/social.py`](file:///C:/Users/ajaya/Desktop/NLP/src/episense/connectors/social.py)) operates under rigorous scientific constraints:

### A. Credential Enforcement
- Evaluates `EPISENSE_SOCIAL_API_TOKEN` and `TWITTER_BEARER_TOKEN` from the process environment.
- When tokens are absent or credentials fail, it returns:
  - `status = SourceConnectorStatus.AUTHENTICATION_REQUIRED`
  - `http_status = 401`
  - `documents_found = 0`, `documents_ingested = 0`
  - Setup instructions in `details.setup_instructions` guiding the user on how to obtain and export a compliant API Bearer token.

### B. Signal Verification Semantics
- Social stream signals are tagged `SourceType.SOCIAL_MEDIA` and marked as unverified informal signals:
  `is_unverified_informal_signal = True`, `requires_independent_verification = True`.
- They never trigger automated high-severity alerts without independent confirmation from official bulletins.

### C. Source Dependence Enforcement (Anti-Astroturfing)
- To prevent retweets, reposts, or automated quote-tweets from artificially corroborating each other, the connector identifies `referenced_tweets` and text prefixes (`RT @`).
- Posts identified as reposts receive `is_repost = True` and are assigned to the `dependence_cluster_id` of the original tweet ID.
- The downstream fusion engine treats all reposts within the same cluster as a single source entity, preventing artificial evidence inflation.

---

## 4. Provenance Tracking & Character-Level Evidence Spans

Every epidemiological attribute extracted by EpiSense retains strict character-level provenance:
- **`document_id`**: Deterministic UUID5 anchored to source URI and text content hash.
- **`source_id`**: Originating feed identifier (e.g. `who_news_feed`, `idsp_bulletin_feed`).
- **`start_char` & `end_char`**: Exact UTF-8 character boundary offsets within the original raw text.
- **`span_text`**: Exact substring extracted from the raw document.
- **`extraction_method`**: Specific rule, NER model, or dictionary component that produced the mention.

### Verification of Seroprevalence Document `4f9d7ddf-9986-5f7a-b0b4-52d43e0bd47a`
- Raw Text Excerpt: *"Cross-sectional seroprevalence of dengue in 3,800 individuals across Southern India... conducted over 36 months during non-outbreak inter-epidemic periods to establish endemic equilibrium."*
- Relevance: `EPIDEMIOLOGICAL_STUDY_OR_RESEARCH` (`is_epidemiological_event = False`).
- Quantities Extracted:
  - Mention: `3,800 individuals` $\rightarrow$ `quantity_type = POPULATION_OR_COHORT`, `case_count = None`, `population = 3800`.
- Temporals Extracted:
  - Mention: `36 months` $\rightarrow$ `temporal_type = DURATION`, `is_duration = True`, `duration_unit = "months"`, `duration_value = 36.0`.
- Calendar grounding: Bounded to publication timestamp; never converted into a false single-day acute event.

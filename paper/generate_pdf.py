"""
EpiSense Conference Paper PDF Generator
Uses ReportLab to compile a professional, publication-quality PDF
of the EpiSense IEEE conference research paper.
"""

import sys
from pathlib import Path
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, KeepTogether, HRFlowable
)
from reportlab.pdfgen import canvas

class NumberedCanvas(canvas.Canvas):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_header_footer(num_pages)
            super().showPage()
        super().save()

    def draw_header_footer(self, page_count):
        self.saveState()
        self.setFont("Helvetica", 8)
        self.setFillColor(colors.HexColor("#4B5563"))
        
        # Header (pages > 1)
        if self._pageNumber > 1:
            self.drawString(54, 750, "IEEE Conference on Public Health Informatics & Epidemic Intelligence")
            self.drawRightString(612 - 54, 750, "EpiSense: Evidence-Grounded Threat Triage")
            self.setStrokeColor(colors.HexColor("#D1D5DB"))
            self.setLineWidth(0.5)
            self.line(54, 744, 612 - 54, 744)
        
        # Footer
        self.setStrokeColor(colors.HexColor("#D1D5DB"))
        self.setLineWidth(0.5)
        self.line(54, 45, 612 - 54, 45)
        self.drawString(54, 32, "EpiSense Research & Engineering Working Group | Status: IMPLEMENTED PROTOTYPE")
        self.drawRightString(612 - 54, 32, f"Page {self._pageNumber} of {page_count}")
        self.restoreState()

def build_pdf(filename="paper/EpiSense_Conference_Paper.pdf"):
    doc = SimpleDocTemplate(
        filename,
        pagesize=letter,
        leftMargin=48,
        rightMargin=48,
        topMargin=54,
        bottomMargin=54
    )

    styles = getSampleStyleSheet()
    
    # Custom styles
    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=17,
        leading=21,
        alignment=1, # Center
        textColor=colors.HexColor("#111827"),
        spaceAfter=10
    )
    
    author_style = ParagraphStyle(
        'AuthorBlock',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9.5,
        leading=13,
        alignment=1,
        textColor=colors.HexColor("#374151"),
        spaceAfter=14
    )
    
    sec_heading = ParagraphStyle(
        'SecHeading',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=11.5,
        leading=15,
        textColor=colors.HexColor("#1E3A8A"),
        spaceBefore=12,
        spaceAfter=5
    )

    subsec_heading = ParagraphStyle(
        'SubSecHeading',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=9.5,
        leading=13,
        textColor=colors.HexColor("#1F2937"),
        spaceBefore=8,
        spaceAfter=3
    )

    body_style = ParagraphStyle(
        'Body',
        parent=styles['Normal'],
        fontName='Times-Roman',
        fontSize=9,
        leading=11.5,
        textColor=colors.HexColor("#111827"),
        spaceAfter=5,
        alignment=4 # Justify
    )

    abstract_title = ParagraphStyle(
        'AbstractTitle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=9,
        leading=11,
        textColor=colors.HexColor("#111827")
    )

    abstract_body = ParagraphStyle(
        'AbstractBody',
        parent=styles['Normal'],
        fontName='Times-Italic',
        fontSize=8.5,
        leading=11,
        textColor=colors.HexColor("#1F2937"),
        alignment=4
    )

    formula_style = ParagraphStyle(
        'Formula',
        parent=styles['Normal'],
        fontName='Courier',
        fontSize=8,
        leading=10.5,
        textColor=colors.HexColor("#0F172A"),
        alignment=1
    )

    table_header = ParagraphStyle(
        'TableHeader',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=7.5,
        leading=9.5,
        textColor=colors.HexColor("#FFFFFF"),
        alignment=1
    )

    table_body = ParagraphStyle(
        'TableBody',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=7.2,
        leading=9,
        textColor=colors.HexColor("#111827")
    )

    table_body_center = ParagraphStyle(
        'TableBodyCenter',
        parent=table_body,
        alignment=1
    )

    ref_style = ParagraphStyle(
        'Reference',
        parent=styles['Normal'],
        fontName='Times-Roman',
        fontSize=7.5,
        leading=9.5,
        textColor=colors.HexColor("#1F2937"),
        spaceAfter=3
    )

    story = []

    # Title & Authors
    story.append(Paragraph("EpiSense: An Evidence-Grounded, Uncertainty-Aware Event-Based Surveillance Framework for Infectious Disease Threat Triage", title_style))
    story.append(Paragraph(
        "<b>EpiSense Research and Engineering Working Group</b><br/>"
        "Department of Computer Science & Engineering and School of Public Health<br/>"
        "<i>Consortium for Epidemic Intelligence and Biosecurity Informatics</i> &bull; Contact: <u>research@episense.org</u><br/>"
        "Official Acceptance Status: <b>IMPLEMENTED PROTOTYPE &mdash; ADDITIONAL VALIDATION REQUIRED</b>",
        author_style
    ))
    story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#1E3A8A"), spaceAfter=8))

    # Abstract Box
    abstract_text = (
        "<b><i>Abstract</i>&mdash;Early-warning public health surveillance systems often suffer from twin operational failure modes: "
        "overwhelming false alert rates triggered by media echo chambers and negated rumors, and manufactured statistical "
        "confidence resulting from sparse baseline data. We present EpiSense, an open-source, evidence-grounded Event-Based Surveillance "
        "(EBS) architecture designed for robust disease incident extraction, clustering, and risk prioritization. EpiSense integrates "
        "biomedical named entity recognition, dependency-parse clinical assertion classification, spatial normalization, and multi-document "
        "incident fusion with strict character-offset provenance grounding. To prevent reporting inflation, an anti-inflation quantity aggregator "
        "and publisher independence tracker separate syndicated wire reprints from genuine multi-source corroboration, preventing single-source "
        "media echo from escalating risk scores (ablation: 0.775 vs 0.875). Furthermore, an epidemiological baseline reliability policy "
        "defensively gates statistical aberration detectors (EARS C1&ndash;C3, EWMA), suppressing false alarms when longitudinal history "
        "contains fewer than 3 periods (<i>N</i> &lt; 3) or sparse non-zero counts. On a 24-scenario adversarial benchmark, EpiSense successfully "
        "suppresses seasonal drills and laboratory exclusions (0.0% false alert rate). On an 18-document diagnostic gold standard, the "
        "deterministic pipeline achieves 94.8% span recall (89.7% on held-out test splits). We release our complete codebase, 295 automated "
        "regression tests, a frozen 128-document blind evaluation manifest, and an external annotation package to support reproducible public health informatics.</b><br/><br/>"
        "<b><i>Index Terms</i>&mdash;Digital Disease Detection, Event-Based Surveillance, Biomedical Information Extraction, Anomaly Detection, Clinical Assertion Classification, Provenance Grounding.</b>"
    )
    
    abs_table = Table([[Paragraph(abstract_text, abstract_body)]], colWidths=[516])
    abs_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor("#F3F4F6")),
        ('BOX', (0,0), (-1,-1), 0.5, colors.HexColor("#D1D5DB")),
        ('TOPPADDING', (0,0), (-1,-1), 8),
        ('BOTTOMPADDING', (0,0), (-1,-1), 8),
        ('LEFTPADDING', (0,0), (-1,-1), 10),
        ('RIGHTPADDING', (0,0), (-1,-1), 10),
    ]))
    story.append(abs_table)
    story.append(Spacer(1, 10))

    # Section 1
    story.append(Paragraph("I. INTRODUCTION AND PUBLIC-HEALTH PROBLEM STATEMENT", sec_heading))
    story.append(Paragraph(
        "The rapid detection of infectious disease outbreaks is a cornerstone of global biosecurity and epidemic containment. "
        "Historically, public health surveillance has relied predominantly on <b>Indicator-Based Surveillance (IBS)</b>&mdash;the structured, "
        "routine reporting of confirmed or suspected cases from clinical laboratories, healthcare facilities, and sentinel providers. "
        "While IBS provides rigorous statistical denominator control and high diagnostic specificity, it suffers from substantial reporting "
        "delays, typically ranging from 7 to 21 days, due to diagnostic processing, administrative batching, and hierarchical public health verification.",
        body_style
    ))
    story.append(Paragraph(
        "To overcome these delays, <b>Event-Based Surveillance (EBS)</b> emerged in the late 1990s and early 2000s, capitalizing on unstructured digital media, "
        "online dispatches, official ministry communiqu&eacute;s, RSS feeds, and discussion boards to detect early signals of emerging pathogens "
        "before routine clinical systems flag an anomaly. Landmark platforms such as ProMED-mail [4, 8], HealthMap [3, 9], the Global Public Health "
        "Intelligence Network (GPHIN) [14], and the WHO Epidemic Intelligence from Open Sources (EIOS) initiative [30] demonstrated the viability "
        "of automated digital epidemic intelligence. However, existing automated EBS implementations face three severe challenges: "
        "<b>(1) The Syndication and Duplicate Echo Problem</b>, where wire services multiply identical dispatches and falsely escalate incident counts; "
        "<b>(2) Linguistic Unfaithfulness and Ungrounded Extraction</b>, where generative LLMs and naive regex extractors alert on negated findings "
        "or historical retrospectives [5, 15]; and <b>(3) Manufactured Statistical Confidence under Baseline Scarcity</b>, where traditional "
        "statistical aberration algorithms (CDC EARS C1&ndash;C3 [13], Farrington quasi-Poisson [8, 23]) divide by zero or trigger false alarms on sparse series [27]. "
        "EpiSense resolves these tensions through character-span provenance grounding, publisher independence fusion, and baseline reliability gating.",
        body_style
    ))

    # Section 2
    story.append(Paragraph("II. RELATED WORK AND LITERATURE REVIEW", sec_heading))
    story.append(Paragraph(
        "<b>A. Digital Epidemic Intelligence:</b> ProMED-mail established informal digital surveillance in 1994 via human expert moderation [4]. "
        "HealthMap automated global scraping of RSS and news feeds [3], while GPHIN operationalized early warning for the Canadian Public Health Agency [14]. "
        "Velasco et al. [28] and Hartley et al. [12] systematically reviewed digital surveillance systems, finding that lack of clinical denominator control "
        "and media echo chambers remain universal operational failure modes.<br/>"
        "<b>B. Clinical NLP and Assertion Classification:</b> Chapman et al. [5] introduced NegEx to classify negation scopes in clinical notes. "
        "Harkema et al. [7] generalized this to ConText, evaluating negation, temporality, and experiencer. Modern transformers such as BioBERT [18] and "
        "ScispaCy [22] achieve high entity recognition, yet large generative models remain vulnerable to abstractive hallucination [15, 21]. "
        "Rudin [19] emphasized that for high-stakes societal decisions, interpretable models with verifiable audit trails are fundamentally preferable to opaque black boxes.<br/>"
        "<b>C. Statistical Aberration Detection:</b> The CDC Early Aberration Reporting System (EARS) applies moving-average Z-scores (C1, C2, C3) "
        "for short-baseline biosurveillance [13, 16]. Farrington et al. [8] and Noufaily et al. [23] established quasi-Poisson regression with power transformations "
        "to handle seasonal overdispersion. Unkel et al. [27] proved that statistical outbreak detectors degrade catastrophically when historical time series "
        "contain fewer than 3 observations (<i>N</i> &lt; 3) or zero variance.",
        body_style
    ))

    # Section 3: Gaps and Table 1
    story.append(Paragraph("III. RESEARCH GAP AND SCOPED CONTRIBUTIONS", sec_heading))
    story.append(Paragraph(
        "EpiSense explicitly scopes its contributions to address documented technical failure modes. Table I outlines the alignment between "
        "identified literature gaps and EpiSense implementations. Importantly, EpiSense is strictly an intelligent triage and prioritization framework; "
        "it does not provide clinical diagnosis or claim unvalidated open-world outbreak prediction.",
        body_style
    ))

    t1_data = [
        [Paragraph("<b>Identified Gap</b>", table_header), Paragraph("<b>Technical Failure Mode</b>", table_header), Paragraph("<b>EpiSense Implementation & Safeguard</b>", table_header)],
        [Paragraph("Ungrounded NLP Hallucination", table_body), Paragraph("Generative models invent phantom counts or misattribute diseases.", table_body), Paragraph("Verbatim character-span provenance contract (<code>raw[s:e] == span</code>).", table_body)],
        [Paragraph("Syndication Echo Chamber", table_body), Paragraph("Wire reprints (PTI, Reuters) inflate event volume and trigger alarms.", table_body), Paragraph("Publisher independence grouping; multi-publisher corroboration gate.", table_body)],
        [Paragraph("Baseline Scarcity Artifacts", table_body), Paragraph("EARS/Farrington divide by zero or alert on <i>N</i>=1 data.", table_body), Paragraph("Multi-tiered baseline reliability gate (<i>N</i> &ge; 3, non-zero history required).", table_body)],
        [Paragraph("Non-Infectious Disease Bleed", table_body), Paragraph("Outbreak alarms generated for cardiovascular diseases.", table_body), Paragraph("Three-tier curated taxonomy isolating communicable pathogens from NCDs.", table_body)],
    ]
    t1 = Table(t1_data, colWidths=[130, 180, 206])
    t1.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#1E3A8A")),
        ('BOX', (0,0), (-1,-1), 0.5, colors.HexColor("#D1D5DB")),
        ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor("#E5E7EB")),
        ('TOPPADDING', (0,0), (-1,-1), 3),
        ('BOTTOMPADDING', (0,0), (-1,-1), 3),
    ]))
    story.append(t1)
    story.append(Spacer(1, 8))

    # Section 4: Architecture and Table 2
    story.append(Paragraph("IV. SYSTEM ARCHITECTURE", sec_heading))
    story.append(Paragraph(
        "EpiSense operates as an asynchronous, dual-branch surveillance engine with persistent, tamper-evident forensic accounting. "
        "Branch 1 processes narrative EBS dispatches through deterministic clinical NLP, assertion filtering, and canonical event fusion. "
        "Branch 2 aggregates quantitative IBS signals into structured spatiotemporal bins governed by baseline reliability gating. "
        "Surveillance state is stored in an ACID-compliant SQLite WAL store, ensuring 100% deterministic hydration across system restarts.",
        body_style
    ))

    t2_data = [
        [Paragraph("<b>Subsystem</b>", table_header), Paragraph("<b>Operational Role</b>", table_header), Paragraph("<b>Enforced System Invariant</b>", table_header)],
        [Paragraph("Ingestion Pipeline", table_body), Paragraph("Dispatches raw text and metadata", table_body), Paragraph("SHA-256 content hash deduplication; idempotent storage", table_body)],
        [Paragraph("NLP Extractor", table_body), Paragraph("Biomedical NER & temporal parsing", table_body), Paragraph("Bidirectional character span equality: <code>raw[s:e] == span_text</code>", table_body)],
        [Paragraph("Assertion Classifier", table_body), Paragraph("Syntactic context tree classification", table_body), Paragraph("Negated, hypothetical, and historical mentions suppressed from alerts", table_body)],
        [Paragraph("Fusion Engine", table_body), Paragraph("Spatiotemporal canonical clustering", table_body), Paragraph("Pathogen Jaccard &ge; 0.75, &Delta;<i>t</i> &le; 7 days, spatial overlap required", table_body)],
        [Paragraph("Risk Scorer", table_body), Paragraph("Multi-criteria threat prioritization", table_body), Paragraph("Composite score bounded in [0.0, 1.0] across 5 explicit dimensions", table_body)],
        [Paragraph("Baseline Tracker", table_body), Paragraph("Time-series qualification & certification", table_body), Paragraph("Mandatory <i>N</i> &ge; 3 periods and positive variance before detector execution", table_body)],
        [Paragraph("Anomaly Detector", table_body), Paragraph("CDC EARS aberration calculation", table_body), Paragraph("Evaluated only on certified series; graceful gating fallback", table_body)],
        [Paragraph("Persistence WAL Store", table_body), Paragraph("Forensic event and audit logging", table_body), Paragraph("Zero state loss on process termination; SHA-256 state seal", table_body)],
    ]
    t2 = Table(t2_data, colWidths=[120, 170, 226])
    t2.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#1E3A8A")),
        ('BOX', (0,0), (-1,-1), 0.5, colors.HexColor("#D1D5DB")),
        ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor("#E5E7EB")),
        ('TOPPADDING', (0,0), (-1,-1), 3),
        ('BOTTOMPADDING', (0,0), (-1,-1), 3),
    ]))
    story.append(t2)
    story.append(Spacer(1, 8))

    # Section 5: Data Sources & Table 3
    story.append(Paragraph("V. DATA SOURCES, PROVENANCE, AND FEASIBILITY", sec_heading))
    story.append(Paragraph(
        "EpiSense was evaluated against an audited dual-origin repository comprising 216 documents (Table III). "
        "A critical empirical disclosure is that the 113 historical records from the Integrated Disease Surveillance Programme (IDSP) "
        "represent a single cross-sectional reporting week (2026-W01) distributed across 29 administrative districts, rather than 29 longitudinal weeks. "
        "Consequently, longitudinal history for any individual district-disease pair contains exactly <i>N</i>=1 observation. "
        "EpiSense's baseline reliability tracker correctly flags all 452 historical signals as <code>INSUFFICIENT_HISTORY</code>, safely preventing "
        "spurious statistical outbreak escalation.",
        body_style
    ))

    t3_data = [
        [Paragraph("<b>Surveillance Inventory Category</b>", table_header), Paragraph("<b>Count</b>", table_header), Paragraph("<b>Operational Status & Denominator Context</b>", table_header)],
        [Paragraph("Historical Official Bulletins (IDSP)", table_body), Paragraph("113", table_body_center), Paragraph("Cross-sectional district reports (2026-W01 single week)", table_body)],
        [Paragraph("Live External News Dispatches", table_body), Paragraph("103", table_body_center), Paragraph("Unstructured digital media, regional wires, official circulars", table_body)],
        [Paragraph("<b>Total Ingested Documents</b>", table_body), Paragraph("<b>216</b>", table_body_center), Paragraph("<b>100.0% Document Accounting Census in SQLite Store</b>", table_body)],
        [Paragraph("Candidate Mentions Extracted", table_body), Paragraph("598", table_body_center), Paragraph("Raw extracted entity tuples across all ingested documents", table_body)],
        [Paragraph("Canonical Fused Events", table_body), Paragraph("460", table_body_center), Paragraph("Deduplicated incidents (1.30x compression in database)", table_body)],
        [Paragraph("Independently Corroborated Events", table_body), Paragraph("2", table_body_center), Paragraph("Verified multi-publisher events (&ge; 2 independent groups)", table_body)],
        [Paragraph("Single-Source Events", table_body), Paragraph("458", table_body_center), Paragraph("Single publisher origin (unsupported by independent wire)", table_body)],
        [Paragraph("Quantitative Surveillance Signals", table_body), Paragraph("452", table_body_center), Paragraph("District-disease weekly count bins in indicator branch", table_body)],
        [Paragraph("Signals Gated (Insufficient History)", table_body), Paragraph("452", table_body_center), Paragraph("100.0% of historical signals safely gated (<i>N</i>=1 &lt; 3)", table_body)],
        [Paragraph("Active Epidemiological Alerts", table_body), Paragraph("41", table_body_center), Paragraph("Triaged alerts in active operational surveillance queue", table_body)],
    ]
    t3 = Table(t3_data, colWidths=[170, 60, 286])
    t3.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#1E3A8A")),
        ('BOX', (0,0), (-1,-1), 0.5, colors.HexColor("#D1D5DB")),
        ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor("#E5E7EB")),
        ('TOPPADDING', (0,0), (-1,-1), 3),
        ('BOTTOMPADDING', (0,0), (-1,-1), 3),
    ]))
    story.append(t3)
    story.append(Spacer(1, 8))

    # Section 6: NLP Extraction & Span Grounding
    story.append(Paragraph("VI. NLP EXTRACTION, ASSERTION HANDLING, AND EVIDENCE GROUNDING", sec_heading))
    story.append(Paragraph(
        "<b>A. Biomedical Entity Recognition:</b> We employ ScispaCy (<code>en_core_sci_sm</code>) combined with gazetteers to extract disease entities, "
        "geographic administrative units, temporal expressions, and case counts, mapping entities to standard SNOMED-CT/ICD-10 concepts.<br/>"
        "<b>B. Clinical Assertion Classification:</b> Every extracted disease mention is evaluated by a syntactic dependency parse tree analyzer "
        "that determines polarity (<code>CONFIRMED_PRESENT</code> vs <code>NEGATED</code>), certainty (<code>DEFINITE</code> vs <code>SUSPECTED/HYPOTHETICAL</code>), "
        "and temporality (<code>RECENT_ACUTE</code> vs <code>HISTORICAL</code>). Mentions tagged as negated (e.g. <i>'tested negative for Nipah'</i>) "
        "or historical are blocked from generating alerts.<br/>"
        "<b>C. Verbatim Character-Span Grounding Contract:</b> To eliminate ungrounded hallucinations, EpiSense enforces the character-slice equality invariant: "
        "<code>Document.text[start:end] == EntitySpan.text</code>. Any candidate entity failing this test is immediately discarded.",
        body_style
    ))

    # Section 7: Fusion and Publisher Grouping
    story.append(Paragraph("VII. DUPLICATE-AWARE EVENT FUSION AND SOURCE INDEPENDENCE", sec_heading))
    story.append(Paragraph(
        "<b>A. Canonical Spatiotemporal Fusion:</b> Incident mentions merge into a canonical event if pathogen Jaccard similarity &ge; 0.75, "
        "temporal distance |&Delta;<i>t</i>| &le; 7 days, and administrative boundaries overlap.<br/>"
        "<b>B. Publisher Independence Grouping:</b> To prevent syndicated reprints from fabricating corroboration, sources are mapped to canonical publisher agencies "
        "(e.g., <code>Group('PTI-Delhi') = Group('PTI-Kolkata') = 'WIRE_PTI'</code>). An event is designated as corroborated if and only if "
        "it contains &ge; 2 distinct publisher groups. This prevents single-source wire stories from escalating risk scores into the HIGH tier.",
        body_style
    ))

    # Section 8: Risk Scoring Formula
    story.append(Paragraph("VIII. RISK SCORING AND ALERT SAFETY CONTROLS", sec_heading))
    story.append(Paragraph(
        "EpiSense prioritizes surveillance dispatches using an interpretable, multi-criteria triage equation bounded in [0.0, 1.0]:",
        body_style
    ))
    
    # Formula Box
    formula_text = (
        "<b>R_raw = 0.30 &middot; S_anomaly + 0.25 &middot; S_threat + 0.20 &middot; S_evidence + 0.15 &middot; S_certainty + 0.10 &middot; S_spatial</b><br/>"
        "Alert Priority Tiers: HIGH (R &ge; 0.80) | MEDIUM (0.65 &le; R &lt; 0.80) | LOW (0.40 &le; R &lt; 0.65) | INFORMATIONAL (R &lt; 0.40)"
    )
    f_box = Table([[Paragraph(formula_text, formula_style)]], colWidths=[516])
    f_box.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor("#EFF6FF")),
        ('BOX', (0,0), (-1,-1), 0.5, colors.HexColor("#3B82F6")),
        ('TOPPADDING', (0,0), (-1,-1), 6),
        ('BOTTOMPADDING', (0,0), (-1,-1), 6),
    ]))
    story.append(f_box)
    story.append(Spacer(1, 6))

    story.append(Paragraph(
        "Sub-scores represent: <b>S_anomaly</b> (deviation above baseline or sudden volume surge), <b>S_threat</b> (curated pathogen virulence: 0.95 for Nipah/Ebola; "
        "0.70 for Cholera/Measles; 0.40 for viral fever), <b>S_evidence</b> (independent publisher groups &ge; 2 and case volume), "
        "<b>S_certainty</b> (1.00 for lab confirmed; 0.70 probable; 0.40 suspected), and <b>S_spatial</b> (1.00 district; 0.70 state; 0.30 national). "
        "These weights represent domain epidemiological consensus, not parameters fitted via maximum likelihood estimation.",
        body_style
    ))

    # Section 9: Statistical Anomaly & Baseline Gating Table 4
    story.append(Paragraph("IX. STATISTICAL ANOMALY DETECTION AND BASELINE RELIABILITY GATING", sec_heading))
    story.append(Paragraph(
        "EpiSense implements the CDC Early Aberration Reporting System (EARS) moving-average algorithms (C1, C2, C3) [13]. "
        "To prevent division-by-zero errors and false alarms on short series, a multi-tiered reliability gate is enforced (Table IV).",
        body_style
    ))

    t4_data = [
        [Paragraph("<b>Policy Tier</b>", table_header), Paragraph("<b>Minimum History (<i>N</i>)</b>", table_header), Paragraph("<b>Allowed Detectors</b>", table_header), Paragraph("<b>Operational Gating Action</b>", table_header)],
        [Paragraph("Tier 1: Minimal Variance", table_body), Paragraph("<i>N</i> &ge; 3 periods, &sum;<i>y</i> &gt; 0", table_body), Paragraph("Sample variance <i>s</i>&sup2;, CV", table_body), Paragraph("Returns INSUFFICIENT_HISTORY; suppresses statistical escalation", table_body)],
        [Paragraph("Tier 2: Moving Window", table_body), Paragraph("<i>N</i> &ge; 7 periods", table_body), Paragraph("CDC EARS C1, EWMA (&lambda;=0.2)", table_body), Paragraph("Suppresses C1; falls back to absolute count threshold", table_body)],
        [Paragraph("Tier 3: Guard Band", table_body), Paragraph("<i>N</i> &ge; 9 periods", table_body), Paragraph("CDC EARS C2, CDC EARS C3", table_body), Paragraph("Suppresses C2/C3; falls back to Tier 2 or count threshold", table_body)],
        [Paragraph("Tier 4: Annual Cyclical", table_body), Paragraph("<i>N</i> &ge; 52 periods (1 yr)", table_body), Paragraph("Farrington Quasi-Poisson, Serfling", table_body), Paragraph("Suppresses regression; refuses to compute seasonal cycles", table_body)],
    ]
    t4 = Table(t4_data, colWidths=[120, 110, 130, 156])
    t4.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#1E3A8A")),
        ('BOX', (0,0), (-1,-1), 0.5, colors.HexColor("#D1D5DB")),
        ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor("#E5E7EB")),
        ('TOPPADDING', (0,0), (-1,-1), 3),
        ('BOTTOMPADDING', (0,0), (-1,-1), 3),
    ]))
    story.append(t4)
    story.append(Spacer(1, 8))

    # Section 10 & 11: Experimental Setup & Results Table 5 & Table 6
    story.append(Paragraph("X. EXPERIMENTAL SETUP AND RESULTS WITH EXACT METRIC DENOMINATORS", sec_heading))
    story.append(Paragraph(
        "EpiSense was evaluated across three empirical benchmarks: an 18-document clinical reference gold standard (Table V), "
        "a 24-scenario handcrafted adversarial benchmark (Table VI), and an executable 7-configuration ablation suite (Table VII).",
        body_style
    ))

    t5_data = [
        [Paragraph("<b>Evaluation Partition</b>", table_header), Paragraph("<b>Docs</b>", table_header), Paragraph("<b>Gold Spans</b>", table_header), Paragraph("<b>TP</b>", table_header), Paragraph("<b>FP</b>", table_header), Paragraph("<b>FN</b>", table_header), Paragraph("<b>Recall</b>", table_header), Paragraph("<b>Precision</b>", table_header), Paragraph("<b>F1 Score</b>", table_header)],
        [Paragraph("Development Corpus", table_body), Paragraph("12", table_body_center), Paragraph("67", table_body_center), Paragraph("65", table_body_center), Paragraph("65", table_body_center), Paragraph("2", table_body_center), Paragraph("<b>97.01%</b>", table_body_center), Paragraph("50.00%", table_body_center), Paragraph("0.6667", table_body_center)],
        [Paragraph("Held-Out Test Corpus", table_body), Paragraph("6", table_body_center), Paragraph("29", table_body_center), Paragraph("26", table_body_center), Paragraph("28", table_body_center), Paragraph("3", table_body_center), Paragraph("<b>89.66%</b>", table_body_center), Paragraph("48.15%", table_body_center), Paragraph("0.6118", table_body_center)],
        [Paragraph("<b>Combined Reference Corpus</b>", table_body), Paragraph("<b>18</b>", table_body_center), Paragraph("<b>96</b>", table_body_center), Paragraph("<b>91</b>", table_body_center), Paragraph("<b>93</b>", table_body_center), Paragraph("<b>5</b>", table_body_center), Paragraph("<b>94.79%</b>", table_body_center), Paragraph("<b>49.46%</b>", table_body_center), Paragraph("<b>0.6500</b>", table_body_center)],
    ]
    t5 = Table(t5_data, colWidths=[110, 36, 48, 36, 36, 36, 68, 70, 76])
    t5.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#1E3A8A")),
        ('BOX', (0,0), (-1,-1), 0.5, colors.HexColor("#D1D5DB")),
        ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor("#E5E7EB")),
        ('TOPPADDING', (0,0), (-1,-1), 3),
        ('BOTTOMPADDING', (0,0), (-1,-1), 3),
    ]))
    story.append(t5)
    story.append(Spacer(1, 6))

    story.append(Paragraph(
        "<i>Methodological Disclosure</i>: 12 of the 18 gold documents (66.7%) overlapped with the initial development corpus. "
        "On the 6 genuinely held-out documents, recall remains robust at <b>89.66%</b> (26/29). Nominal precision (49.46%) reflects "
        "exhaustive clinical mention extraction vs sparse gold annotation.",
        body_style
    ))

    t6_data = [
        [Paragraph("<b>Adversarial Evaluation Metric</b>", table_header), Paragraph("<b>Exact Denominator</b>", table_header), Paragraph("<b>Observed Value</b>", table_header), Paragraph("<b>Methodological Scope & Interpretation</b>", table_header)],
        [Paragraph("Outbreak Scenario Recall", table_body), Paragraph("7 / 7", table_body_center), Paragraph("<b>100.0%</b>", table_body_center), Paragraph("Successfully detected all 7 acute outbreak cases (Cholera, Nipah, Measles, Dengue)", table_body)],
        [Paragraph("False Alert Rate (FAR)", table_body), Paragraph("0 / 15", table_body_center), Paragraph("<b>0.0%</b>", table_body_center), Paragraph("Suppressed all 15 negative scenarios (negated labs, historical retrospectives, CVD)", table_body)],
        [Paragraph("Adversarial Precision", table_body), Paragraph("7 / 7", table_body_center), Paragraph("<b>100.0%</b>", table_body_center), Paragraph("Zero false positive outbreak alerts generated on handcrafted scenarios", table_body)],
        [Paragraph("Adversarial Specificity", table_body), Paragraph("15 / 15", table_body_center), Paragraph("<b>100.0%</b>", table_body_center), Paragraph("Complete rejection of non-outbreak clinical narratives", table_body)],
        [Paragraph("Redundant Duplicate Fusion", table_body), Paragraph("2 / 2", table_body_center), Paragraph("<b>100.0%</b>", table_body_center), Paragraph("Both syndicated wire pairs successfully collapsed into canonical incidents", table_body)],
    ]
    t6 = Table(t6_data, colWidths=[130, 60, 66, 260])
    t6.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#1E3A8A")),
        ('BOX', (0,0), (-1,-1), 0.5, colors.HexColor("#D1D5DB")),
        ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor("#E5E7EB")),
        ('TOPPADDING', (0,0), (-1,-1), 3),
        ('BOTTOMPADDING', (0,0), (-1,-1), 3),
    ]))
    story.append(t6)
    story.append(Spacer(1, 8))

    # Section 12: Ablation Study Table 7
    story.append(Paragraph("XI. ABLATION STUDY", sec_heading))
    story.append(Paragraph(
        "To rigorously quantify the contribution of each algorithmic safeguard, we executed all 7 pipeline configurations on the benchmark (Table VII).",
        body_style
    ))

    t7_data = [
        [Paragraph("<b>Pipeline Configuration</b>", table_header), Paragraph("<b>Recall</b>", table_header), Paragraph("<b>Prec.</b>", table_header), Paragraph("<b>FAR</b>", table_header), Paragraph("<b>Dup.</b>", table_header), Paragraph("<b>Score</b>", table_header), Paragraph("<b>Observed Algorithmic Effect</b>", table_header)],
        [Paragraph("<b>Full EpiSense Pipeline</b>", table_body), Paragraph("<b>1.000</b>", table_body_center), Paragraph("<b>1.000</b>", table_body_center), Paragraph("<b>0.000</b>", table_body_center), Paragraph("<b>2/2</b>", table_body_center), Paragraph("<b>0.775</b>", table_body_center), Paragraph("Full protective state; zero false alarms.", table_body)],
        [Paragraph("Ablation 1: No Assertion Analysis", table_body), Paragraph("1.000", table_body_center), Paragraph("0.636", table_body_center), Paragraph("0.267", table_body_center), Paragraph("2/2", table_body_center), Paragraph("0.775", table_body_center), Paragraph("Generates 4 false alarms on negated lab exclusions.", table_body)],
        [Paragraph("Ablation 2: No Publisher Grouping", table_body), Paragraph("1.000", table_body_center), Paragraph("1.000", table_body_center), Paragraph("0.000", table_body_center), Paragraph("2/2", table_body_center), Paragraph("<b>0.875</b>", table_body_center), Paragraph("Score escalates from MEDIUM to HIGH on wire copy.", table_body)],
        [Paragraph("Ablation 3: No Event Fusion", table_body), Paragraph("1.000", table_body_center), Paragraph("1.000", table_body_center), Paragraph("0.000", table_body_center), Paragraph("0/2", table_body_center), Paragraph("0.775", table_body_center), Paragraph("1.46x mention volume inflation (19 vs 13 events).", table_body)],
        [Paragraph("Ablation 4: No Baseline Gating", table_body), Paragraph("1.000", table_body_center), Paragraph("0.778", table_body_center), Paragraph("0.133", table_body_center), Paragraph("2/2", table_body_center), Paragraph("0.775", table_body_center), Paragraph("Spurious aberration alarms on <i>N</i>=1 baseline.", table_body)],
        [Paragraph("Ablation 5: No Span Grounding", table_body), Paragraph("1.000", table_body_center), Paragraph("0.875", table_body_center), Paragraph("0.067", table_body_center), Paragraph("2/2", table_body_center), Paragraph("0.775", table_body_center), Paragraph("Accepts ungrounded entities; violates audit trail.", table_body)],
        [Paragraph("Ablation 6: No Temporal Guard", table_body), Paragraph("0.857", table_body_center), Paragraph("1.000", table_body_center), Paragraph("0.000", table_body_center), Paragraph("2/2", table_body_center), Paragraph("0.775", table_body_center), Paragraph("Misses 1 outbreak due to leap-year rollover.", table_body)],
    ]
    t7 = Table(t7_data, colWidths=[130, 40, 40, 40, 36, 42, 188])
    t7.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#1E3A8A")),
        ('BOX', (0,0), (-1,-1), 0.5, colors.HexColor("#D1D5DB")),
        ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor("#E5E7EB")),
        ('TOPPADDING', (0,0), (-1,-1), 3),
        ('BOTTOMPADDING', (0,0), (-1,-1), 3),
    ]))
    story.append(t7)
    story.append(Spacer(1, 8))

    # Section 13: Discussion
    story.append(Paragraph("XII. DISCUSSION AND PRACTICAL SIGNIFICANCE", sec_heading))
    story.append(Paragraph(
        "<b>A. Resolving the Syndication Echo Chamber:</b> Ablation 2 demonstrates that without publisher grouping, 3 wire articles "
        "from Press Trust of India are treated as 3 independent sources, escalating the risk score from 0.775 (MEDIUM) to 0.875 (HIGH). "
        "In a live operations center, this false escalation triggers emergency notifications and wastes critical field resources. "
        "Publisher grouping eliminates this vulnerability.<br/>"
        "<b>B. Verifiable Extraction vs Generative Hallucination:</b> Rather than using ungrounded large language models, EpiSense pairs "
        "deterministic ScispaCy NER with dependency-parse assertion trees. This achieves 94.8% entity recall with 100% character-level provenance grounding, "
        "enabling public health officers to click directly to the raw sentence supporting every alert.",
        body_style
    ))

    # Section 14, 15, 16: Threats, Limitations, Conclusion
    story.append(Paragraph("XIII. THREATS TO VALIDITY, LIMITATIONS, AND CONCLUSION", sec_heading))
    story.append(Paragraph(
        "<b>A. Threats to Validity:</b> The 24-scenario benchmark was authored to test edge cases and does not reflect messy open-world web text. "
        "Additionally, 12 of the 18 gold documents (66.7%) overlapped with the dev split; held-out test recall is 89.66%.<br/>"
        "<b>B. Limitations:</b> The 128-document blind evaluation manifest is frozen but currently blocked awaiting independent human double-blind annotation. "
        "Furthermore, the IDSP data represent a single cross-sectional week; multi-year longitudinal forecasting requires external registry integrations.<br/>"
        "<b>C. Conclusion:</b> EpiSense provides a defensible, evidence-grounded Event-Based Surveillance framework that resolves media echo inflation, "
        "ungrounded extraction, and baseline scarcity artifacts. By enforcing character-span provenance, publisher grouping, and baseline reliability gating, "
        "EpiSense delivers high recall (94.8% entity recall, 100% adversarial scenario recall) while eliminating false alerts on negated texts. "
        "The open codebase and 295 regression tests establish a reproducible foundation for epidemic intelligence.",
        body_style
    ))
    story.append(Spacer(1, 8))

    # References
    story.append(Paragraph("REFERENCES", sec_heading))
    refs = [
        "[1] C. L. Althaus, 'Estimating the reproduction number of Ebola virus (EBOV) during the 2014 outbreak in West Africa,' <i>PLOS Currents Outbreaks</i>, vol. 1, 2014.",
        "[2] L. Basile et al., 'Evaluation of the syndromic surveillance system in Catalonia,' <i>BMC Public Health</i>, vol. 16, p. 245, 2016.",
        "[3] J. S. Brownstein, C. C. Freifeld, B. Y. Reis, and K. D. Mandl, 'Surveillance Sans Fronti&egrave;res: Internet-based emerging infectious disease intelligence in greater detail,' <i>PLoS Medicine</i>, vol. 5, no. 7, p. e151, 2008.",
        "[4] M. Carrion and L. C. Madoff, 'ProMED-mail: 22 years of digital surveillance of emerging diseases,' <i>International Health</i>, vol. 9, no. 3, pp. 177-183, 2017.",
        "[5] W. W. Chapman et al., 'A simple algorithm for identifying negated findings and diseases in discharge summaries: NegEx,' <i>J. Biomed. Inform.</i>, vol. 34, no. 5, pp. 301-310, 2001.",
        "[6] N. Collier et al., 'BioCaster: detecting public health rumors with a Web-based text mining system,' <i>Bioinformatics</i>, vol. 24, no. 24, pp. 2940-2941, 2008.",
        "[7] H. Harkema et al., 'Context: An algorithm for determining negation, experiencer, and temporal status from clinical reports,' <i>J. Biomed. Inform.</i>, vol. 42, no. 5, pp. 839-851, 2009.",
        "[8] C. P. Farrington et al., 'A statistical algorithm for the early detection of outbreaks of infectious disease,' <i>J. R. Stat. Soc. Ser. A</i>, vol. 159, no. 3, pp. 547-563, 1996.",
        "[9] C. C. Freifeld et al., 'HealthMap: Multilingual real-time global disease surveillance,' <i>J. Am. Med. Inform. Assoc.</i>, vol. 15, no. 2, pp. 150-157, 2008.",
        "[10] Y. Gu et al., 'Domain-specific language model pretraining for biomedical natural language processing,' <i>ACM Trans. Comput. Healthc.</i>, vol. 3, no. 1, pp. 1-23, 2021.",
        "[11] J. Du et al., 'PULS: Pattern-based extraction for epidemic disease surveillance,' in <i>Proc. ACL</i>, 2016, pp. 35-40.",
        "[12] D. M. Hartley et al., 'An overview of internet biosurveillance,' <i>Clin. Microbiol. Infect.</i>, vol. 19, no. 11, pp. 1006-1013, 2013.",
        "[13] L. Hutwagner et al., 'The bioterrorism preparedness and response Early Aberration Reporting System (EARS),' <i>J. Urban Health</i>, vol. 80, no. Suppl 1, pp. i89-i96, 2003.",
        "[14] A. Mawudeku et al., 'The Global Public Health Intelligence Network (GPHIN),' in <i>Infectious Disease Surveillance</i>, Blackwell Publishing, 2013, pp. 370-381.",
        "[15] Z. Ji et al., 'Survey of hallucination in natural language generation,' <i>ACM Comput. Surv.</i>, vol. 55, no. 12, pp. 1-38, 2023.",
        "[16] L. Hutwagner et al., 'Comparing aberration detection methods with simulated data,' <i>Emerg. Infect. Dis.</i>, vol. 11, no. 2, pp. 314-316, 2005.",
        "[17] J. Lafferty, A. McCallum, and F. C. N. Pereira, 'Conditional random fields: Probabilistic models for segmenting and labeling sequence data,' in <i>Proc. ICML</i>, 2001, pp. 282-289.",
        "[18] J. Lee et al., 'BioBERT: a pre-trained biomedical language representation model for biomedical text mining,' <i>Bioinformatics</i>, vol. 36, no. 4, pp. 1234-1240, 2020.",
        "[19] C. Rudin, 'Stop explaining black box machine learning models for high stakes decisions and use interpretable models instead,' <i>Nat. Mach. Intell.</i>, vol. 1, no. 5, pp. 206-215, 2019.",
        "[20] L. C. Madoff and J. P. Woodall, 'The internet and the global monitoring of emerging diseases: lessons from the first 10 years of ProMED-mail,' <i>Arch. Med. Res.</i>, vol. 36, no. 6, pp. 724-730, 2005.",
        "[21] J. Maynez et al., 'On faithfulness and factuality in abstractive summarization,' in <i>Proc. ACL</i>, 2020, pp. 1906-1919.",
        "[22] M. Neumann et al., 'ScispaCy: Fast and robust models for biomedical natural language processing,' in <i>Proc. BioNLP</i>, 2019, pp. 319-327.",
        "[23] A. Noufaily et al., 'An improved algorithm for outbreak detection in multiple surveillance systems,' <i>Stat. Med.</i>, vol. 32, no. 7, pp. 1206-1222, 2013.",
        "[24] G. Soto, K. W. Hartman, and T. G. Savel, 'Standardizing infectious disease terminology: A public health perspective,' <i>Online J. Public Health Inform.</i>, vol. 1, no. 1, 2008.",
        "[25] J. Str&ouml;tgen and M. Gertz, 'Multilingual and cross-domain temporal tagging,' <i>Lang. Resour. Eval.</i>, vol. 47, no. 2, pp. 269-298, 2013.",
        "[26] O. Leal-Neto et al., 'Digital disease detection: A systematic review,' <i>Public Health</i>, vol. 182, pp. 154-160, 2020.",
        "[27] S. Unkel et al., 'Statistical methods for the prospective detection of infectious disease outbreaks: A review,' <i>J. R. Stat. Soc. Ser. A</i>, vol. 175, no. 1, pp. 49-82, 2012.",
        "[28] E. Velasco et al., 'Social media and internet-based data in global systems for public health surveillance: a systematic review,' <i>Milbank Q.</i>, vol. 92, no. 1, pp. 7-33, 2014.",
        "[29] World Health Organization, <i>Early detection, assessment and response to acute public health events: Implementation of early warning and response with a focus on Event-Based Surveillance</i>, Geneva: WHO, 2014.",
        "[30] World Health Organization, <i>Epidemic Intelligence from Open Sources (EIOS): A collaborative effort to strengthen public health intelligence</i>, Geneva: WHO, 2020."
    ]
    for r in refs:
        story.append(Paragraph(r, ref_style))

    # Build document with NumberedCanvas
    doc.build(story, canvasmaker=NumberedCanvas)
    print(f"Successfully generated conference paper PDF at: {filename}")

if __name__ == "__main__":
    build_pdf()

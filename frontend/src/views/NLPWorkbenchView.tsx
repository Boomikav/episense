import React, { useEffect, useState } from "react";
import {
  AlertTriangle,
  CheckCircle2,
  Clock,
  Code2,
  ExternalLink,
  Eye,
  FileText,
  Filter,
  Layers,
  MapPin,
  Plus,
  RefreshCw,
  Search,
  Sparkles,
  Tag,
  Zap,
} from "lucide-react";
import { api } from "../services/api";
import type { DocumentPipelineTrace, OriginClassification, PipelineStageExecution } from "../types/api";
import { LoadingSpinner } from "../components/common/LoadingSpinner";
import { ErrorBanner } from "../components/common/ErrorBanner";
import { Modal } from "../components/common/Modal";
import { DocumentSubmitForm } from "../components/ingestion/DocumentSubmitForm";

interface DocumentSummary {
  document_id: string;
  source_id: string;
  source_type: string;
  origin: OriginClassification;
  title: string;
  text: string;
  content_hash_sha256: string;
  publication_timestamp?: string;
  ingestion_timestamp?: string;
}

interface SpanHighlight {
  start: number;
  end: number;
  text: string;
  type: "disease" | "location" | "quantity" | "temporal";
  label: string;
  normalized?: string;
  confidence?: number;
  assertion?: string;
}

interface NLPWorkbenchViewProps {
  initialOpenSubmitModal?: boolean;
}

export const NLPWorkbenchView: React.FC<NLPWorkbenchViewProps> = ({
  initialOpenSubmitModal = false,
}) => {
  const [documents, setDocuments] = useState<DocumentSummary[]>([]);
  const [originFilter, setOriginFilter] = useState<string>("ALL");
  const [freshnessFilter, setFreshnessFilter] = useState<string>("ALL");
  const [diseaseFilter, setDiseaseFilter] = useState<string>("ALL");
  const [selectedDocId, setSelectedDocId] = useState<string | null>(null);
  const [trace, setTrace] = useState<DocumentPipelineTrace | null>(null);
  const [loadingDocs, setLoadingDocs] = useState<boolean>(true);
  const [loadingTrace, setLoadingTrace] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [selectedSpan, setSelectedSpan] = useState<SpanHighlight | null>(null);
  const [selectedStage, setSelectedStage] = useState<PipelineStageExecution | null>(null);
  const [searchQuery, setSearchQuery] = useState<string>("");

  const [isSubmitModalOpen, setIsSubmitModalOpen] = useState<boolean>(initialOpenSubmitModal);
  const [isAnalyzing, setIsAnalyzing] = useState<boolean>(false);
  const [analysisNotice, setAnalysisNotice] = useState<string | null>(null);

  // Load documents
  const loadDocuments = async () => {
    setLoadingDocs(true);
    setError(null);
    try {
      const docs = await api.listWorkbenchDocuments({
        origin: originFilter !== "ALL" ? originFilter : undefined,
        freshness: freshnessFilter !== "ALL" ? freshnessFilter : undefined,
        disease: diseaseFilter !== "ALL" ? diseaseFilter : undefined,
        limit: 100,
      });
      setDocuments(docs);
      if (docs.length > 0 && !selectedDocId) {
        setSelectedDocId(docs[0].document_id);
      }
    } catch (err: any) {
      setError(err.message || "Failed to load workbench documents.");
    } finally {
      setLoadingDocs(false);
    }
  };

  useEffect(() => {
    loadDocuments();
  }, [originFilter, freshnessFilter, diseaseFilter]);

  // Load trace when selected document changes
  useEffect(() => {
    if (!selectedDocId) return;
    const fetchTrace = async () => {
      setLoadingTrace(true);
      setError(null);
      setSelectedSpan(null);
      setSelectedStage(null);
      setAnalysisNotice(null);
      try {
        const traceData = await api.getDocumentTrace(selectedDocId);
        setTrace(traceData);
        if (traceData.stages && traceData.stages.length > 0) {
          setSelectedStage(traceData.stages[0]);
        }
      } catch (err: any) {
        setError(err.message || `Failed to load pipeline trace for document ${selectedDocId}`);
      } finally {
        setLoadingTrace(false);
      }
    };
    fetchTrace();
  }, [selectedDocId]);

  const handleRunDownstreamAnalysis = async () => {
    if (!selectedDocId) return;
    setIsAnalyzing(true);
    setAnalysisNotice(null);
    try {
      const res = await api.analyzeDocument(selectedDocId);
      setAnalysisNotice(
        `Downstream analysis completed: ${res.candidates_extracted} candidates extracted, ${res.fused_events_produced} fused events generated.`
      );
      const traceData = await api.getDocumentTrace(selectedDocId);
      setTrace(traceData);
    } catch (err: any) {
      setError(err.message || "Failed to execute downstream analysis.");
    } finally {
      setIsAnalyzing(false);
    }
  };

  const handleDocumentSubmitted = async (res: any) => {
    setIsSubmitModalOpen(false);
    await loadDocuments();
    if (res?.document_id) {
      setSelectedDocId(res.document_id);
    }
  };

  // Compute text highlights from trace NLP output
  const highlights: SpanHighlight[] = [];
  if (trace && trace.nlp_output) {
    const raw = trace.raw_text;

    // Disease mentions
    if (trace.nlp_output.entities) {
      for (const ent of trace.nlp_output.entities) {
        const s = ent.start_char;
        const e = ent.end_char;
        const spanText = raw.substring(s, e);
        highlights.push({
          start: s,
          end: e,
          text: spanText,
          type: "disease",
          label: "Disease / Pathogen",
          normalized: ent.normalized_value || "ICD-10 Concept",
          confidence: ent.extraction_confidence ?? 1.0,
        });
      }
    }

    // Locations
    if (trace.nlp_output.locations) {
      for (const loc of trace.nlp_output.locations) {
        const s = loc.start_char;
        const e = loc.end_char;
        const spanText = raw.substring(s, e);
        const normName = loc.resolved_location?.normalized_name || loc.raw_text;
        highlights.push({
          start: s,
          end: e,
          text: spanText,
          type: "location",
          label: "Geographic Toponym",
          normalized: normName,
          confidence: loc.confidence ?? 1.0,
        });
      }
    }

    // Quantities
    if (trace.nlp_output.quantities) {
      for (const qty of trace.nlp_output.quantities) {
        const s = qty.start_char;
        const e = qty.end_char;
        const spanText = raw.substring(s, e);
        highlights.push({
          start: s,
          end: e,
          text: spanText,
          type: "quantity",
          label: "Epidemiological Count",
          normalized: `${qty.numeric_value} ${qty.unit || "cases"}`,
          confidence: 1.0,
        });
      }
    }

    // Temporal
    if (trace.nlp_output.temporal_expressions) {
      for (const t of trace.nlp_output.temporal_expressions) {
        const s = t.start_char;
        const e = t.end_char;
        const spanText = raw.substring(s, e);
        highlights.push({
          start: s,
          end: e,
          text: spanText,
          type: "temporal",
          label: "Temporal Expression",
          normalized: t.normalized_start ? new Date(t.normalized_start).toISOString().split("T")[0] : undefined,
          confidence: t.confidence ?? 1.0,
        });
      }
    }
  }

  // Render text with non-overlapping highlighted spans
  const renderAnnotatedText = () => {
    if (!trace) return null;
    const raw = trace.raw_text;
    if (!raw) return <span>No raw text available.</span>;

    if (highlights.length === 0) {
      return <span>{raw}</span>;
    }

    // Sort highlights by start offset
    const sorted = [...highlights].sort((a, b) => a.start - b.start);
    const elements: React.ReactNode[] = [];
    let curIndex = 0;

    sorted.forEach((h, idx) => {
      if (h.start < curIndex) return; // Skip overlapping spans for clean rendering

      if (h.start > curIndex) {
        elements.push(<span key={`text-${curIndex}`}>{raw.substring(curIndex, h.start)}</span>);
      }

      const isSelected = selectedSpan && selectedSpan.start === h.start && selectedSpan.end === h.end;

      let bg = "#FEE2E2";
      let border = "#FCA5A5";
      let textCol = "#DC2626";

      if (h.type === "location") {
        bg = "#E0F2FE";
        border = "#7DD3FC";
        textCol = "#0369A1";
      } else if (h.type === "quantity") {
        bg = "#FEF3C7";
        border = "#FCD34D";
        textCol = "#B45309";
      } else if (h.type === "temporal") {
        bg = "#EDE9FE";
        border = "#C4B5FD";
        textCol = "#6D28D9";
      }

      elements.push(
        <mark
          key={`mark-${idx}`}
          onClick={() => setSelectedSpan(h)}
          style={{
            background: bg,
            borderBottom: `2px solid ${border}`,
            color: textCol,
            fontWeight: 600,
            padding: "2px 4px",
            borderRadius: "4px",
            cursor: "pointer",
            outline: isSelected ? `2px solid ${textCol}` : "none",
            outlineOffset: "2px",
            transition: "all 0.15s ease",
          }}
          title={`${h.label}: ${h.normalized || h.text} (Click to inspect offsets)`}
        >
          {raw.substring(h.start, h.end)}
        </mark>
      );
      curIndex = h.end;
    });

    if (curIndex < raw.length) {
      elements.push(<span key={`text-end`}>{raw.substring(curIndex)}</span>);
    }

    return elements;
  };

  const filteredDocs = documents.filter((d) => {
    if (!searchQuery) return true;
    const q = searchQuery.toLowerCase();
    return d.title.toLowerCase().includes(q) || d.source_id.toLowerCase().includes(q) || d.text.toLowerCase().includes(q);
  });

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "24px" }}>
      {/* Header */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", flexWrap: "wrap", gap: "16px" }}>
        <div>
          <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
            <h1 className="page-title">NLP Processing Workbench</h1>
            <span
              style={{
                fontSize: "12px",
                fontWeight: 700,
                padding: "3px 10px",
                borderRadius: "9999px",
                background: "#F1EDFD",
                color: "#7047F5",
                border: "1px solid #DDD6FE",
              }}
            >
              17-Stage Forensic Engine
            </span>
          </div>
          <p className="page-subtitle">
            Inspect character-level span offsets, entity extractions, assertion certainty, and stage-by-stage pipeline telemetry.
          </p>
        </div>

        <div style={{ display: "flex", gap: "10px" }}>
          <button
            onClick={() => setIsSubmitModalOpen(true)}
            style={{
              display: "flex",
              alignItems: "center",
              gap: "6px",
              padding: "8px 16px",
              borderRadius: "10px",
              background: "#7047F5",
              border: "none",
              color: "#FFFFFF",
              fontSize: "13px",
              fontWeight: 700,
              cursor: "pointer",
              boxShadow: "var(--shadow-xs)",
            }}
          >
            <Plus size={15} />
            + Ingest Report
          </button>

          <button
            onClick={loadDocuments}
            style={{
              display: "flex",
              alignItems: "center",
              gap: "8px",
              padding: "8px 16px",
              borderRadius: "10px",
              background: "#FFFFFF",
              border: "1px solid var(--border-default)",
              color: "var(--text-primary)",
              fontSize: "13px",
              fontWeight: 600,
              cursor: "pointer",
            }}
          >
            <RefreshCw size={14} className={loadingDocs ? "animate-spin" : ""} />
            Refresh Documents
          </button>
        </div>
      </div>

      {error && <ErrorBanner message={error} onRetry={loadDocuments} />}

      {/* Filter Tabs & Search Bar */}
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          flexWrap: "wrap",
          gap: "12px",
          background: "#FFFFFF",
          padding: "12px 18px",
          borderRadius: "14px",
          border: "1px solid var(--border-default)",
        }}
      >
        <div style={{ display: "flex", gap: "8px", flexWrap: "wrap" }}>
          {[
            { id: "ALL", label: "All Operational & Archival" },
            { id: "LIVE_EXTERNAL", label: "Live External" },
            { id: "HISTORICAL_CORPUS", label: "Historical Corpus" },
            { id: "BENCHMARK", label: "Benchmark" },
            { id: "MANUAL_SUBMISSION", label: "Manual Submission" },
            { id: "SYNTHETIC_TEST", label: "Test Fixtures (Synthetic Only)" },
          ].map((tab) => (
            <button
              key={tab.id}
              onClick={() => setOriginFilter(tab.id)}
              style={{
                padding: "6px 14px",
                borderRadius: "8px",
                fontSize: "12.5px",
                fontWeight: 600,
                border: originFilter === tab.id ? "1px solid #7047F5" : "1px solid transparent",
                background: originFilter === tab.id ? (tab.id === "SYNTHETIC_TEST" ? "#FEF2F2" : "#F1EDFD") : "transparent",
                color: originFilter === tab.id ? (tab.id === "SYNTHETIC_TEST" ? "#DC2626" : "#7047F5") : "var(--text-secondary)",
                cursor: "pointer",
              }}
            >
              {tab.label}
            </button>
          ))}
        </div>

        <div style={{ display: "flex", gap: "10px", alignItems: "center", flexWrap: "wrap", width: "100%", marginTop: "6px", paddingTop: "8px", borderTop: "1px dashed var(--border-default)" }}>
          <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
            <span style={{ fontSize: "11.5px", fontWeight: 700, color: "#64748B" }}>Freshness:</span>
            {["ALL", "CURRENT", "RECENT", "HISTORICAL"].map((f) => (
              <button
                key={f}
                onClick={() => setFreshnessFilter(f)}
                style={{
                  padding: "3px 8px",
                  borderRadius: "6px",
                  fontSize: "11px",
                  fontWeight: 600,
                  border: freshnessFilter === f ? "1px solid #0284C7" : "1px solid #CBD5E1",
                  background: freshnessFilter === f ? "#E0F2FE" : "#FFFFFF",
                  color: freshnessFilter === f ? "#0369A1" : "#475569",
                  cursor: "pointer",
                }}
              >
                {f}
              </button>
            ))}
          </div>

          <div style={{ display: "flex", alignItems: "center", gap: "6px", marginLeft: "auto" }}>
            <span style={{ fontSize: "11.5px", fontWeight: 700, color: "#64748B" }}>Priority Disease:</span>
            <select
              value={diseaseFilter}
              onChange={(e) => setDiseaseFilter(e.target.value)}
              style={{
                padding: "4px 8px",
                borderRadius: "6px",
                border: "1px solid #CBD5E1",
                fontSize: "11.5px",
                color: "#1E293B",
              }}
            >
              <option value="ALL">All Priority Pathogens</option>
              <option value="dengue">Dengue</option>
              <option value="malaria">Malaria</option>
              <option value="chikungunya">Chikungunya</option>
              <option value="leptospirosis">Leptospirosis</option>
              <option value="cholera">Cholera</option>
              <option value="diarrhoeal">Acute Diarrhoeal Disease</option>
              <option value="encephalitis">Japanese Encephalitis</option>
              <option value="scrub typhus">Scrub Typhus</option>
            </select>
          </div>
        </div>

        <div style={{ position: "relative", minWidth: "260px" }}>
          <Search size={14} style={{ position: "absolute", left: "12px", top: "10px", color: "var(--text-muted)" }} />
          <input
            type="text"
            placeholder="Search documents by disease, keyword..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            style={{
              width: "100%",
              padding: "7px 12px 7px 34px",
              borderRadius: "8px",
              border: "1px solid var(--border-default)",
              fontSize: "12.5px",
            }}
          />
        </div>
      </div>

      {/* Main Split Layout: Document Browser & Pipeline Trace */}
      <div style={{ display: "grid", gridTemplateColumns: "340px 1fr", gap: "20px", alignItems: "start" }}>
        {/* Document Selection Column */}
        <div
          style={{
            background: "#FFFFFF",
            borderRadius: "16px",
            border: "1px solid var(--border-default)",
            overflow: "hidden",
            maxHeight: "780px",
            display: "flex",
            flexDirection: "column",
          }}
        >
          <div style={{ padding: "14px 18px", borderBottom: "1px solid var(--border-default)", fontWeight: 700, fontSize: "13px" }}>
            Corpus Documents ({filteredDocs.length})
          </div>

          <div style={{ overflowY: "auto", flex: 1 }}>
            {loadingDocs ? (
              <LoadingSpinner height="200px" />
            ) : filteredDocs.length === 0 ? (
              <div style={{ padding: "30px", textAlign: "center", color: "var(--text-muted)", fontSize: "13px" }}>
                No documents found for this filter.
              </div>
            ) : (
              filteredDocs.map((doc) => {
                const isSelected = doc.document_id === selectedDocId;
                const isLive = doc.origin === "LIVE_EXTERNAL";
                return (
                  <div
                    key={doc.document_id}
                    onClick={() => setSelectedDocId(doc.document_id)}
                    style={{
                      padding: "12px 16px",
                      borderBottom: "1px solid var(--border-default)",
                      cursor: "pointer",
                      background: isSelected ? "#F8FAFC" : "transparent",
                      borderLeft: isSelected ? "4px solid #7047F5" : "4px solid transparent",
                      transition: "background 0.15s ease",
                    }}
                  >
                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "4px", flexWrap: "wrap", gap: "4px" }}>
                      <div style={{ display: "flex", gap: "4px", alignItems: "center" }}>
                        <span
                          style={{
                            fontSize: "10px",
                            fontWeight: 700,
                            padding: "2px 6px",
                            borderRadius: "4px",
                            background: isLive ? "#E8F8F2" : "#F1F5F9",
                            color: isLive ? "#059669" : "#475569",
                          }}
                        >
                          {doc.origin}
                        </span>
                        {(doc as any).freshness && (
                          <span
                            style={{
                              fontSize: "9.5px",
                              fontWeight: 700,
                              padding: "2px 5px",
                              borderRadius: "4px",
                              background: (doc as any).freshness === "CURRENT" ? "#DCFCE7" : ((doc as any).freshness === "RECENT" ? "#DBEAFE" : "#F1F5F9"),
                              color: (doc as any).freshness === "CURRENT" ? "#166534" : ((doc as any).freshness === "RECENT" ? "#1E40AF" : "#64748B"),
                            }}
                          >
                            {(doc as any).freshness}
                          </span>
                        )}
                      </div>
                      <span style={{ fontSize: "11px", color: "var(--text-muted)", fontFamily: "var(--font-mono)" }}>
                        {doc.source_id}
                      </span>
                    </div>

                    <div style={{ fontSize: "13px", fontWeight: 600, color: "var(--text-primary)", lineHeight: 1.3, marginBottom: "4px" }}>
                      {doc.title || "Untitled Surveillance Report"}
                    </div>

                    <div style={{ fontSize: "11px", color: "var(--text-muted)", display: "flex", justifyContent: "space-between" }}>
                      <span>
                        Pub: {doc.publication_timestamp ? new Date(doc.publication_timestamp).toLocaleDateString() : "No pub date"}
                      </span>
                      {(doc as any).currentness_status && (
                        <span style={{ fontSize: "10px", fontWeight: 600, color: (doc as any).currentness_status === "CURRENT_EVENT" ? "#15803D" : "#64748B" }}>
                          {(doc as any).currentness_status === "CURRENT_EVENT" ? "Current Event" : ((doc as any).currentness_status === "RECENTLY_PUBLISHED_HISTORICAL_EVENT" ? "Recent Pub / Hist Event" : "Archival")}
                        </span>
                      )}
                    </div>
                  </div>
                );
              })
            )}
          </div>
        </div>

        {/* Trace and Span Inspector Column */}
        <div style={{ display: "flex", flexDirection: "column", gap: "20px" }}>
          {loadingTrace ? (
            <LoadingSpinner height="400px" message="Retrieving 17-stage forensic trace..." />
          ) : !trace ? (
            <div
              style={{
                background: "#FFFFFF",
                borderRadius: "16px",
                border: "1px solid var(--border-default)",
                padding: "60px 20px",
                textAlign: "center",
                color: "var(--text-muted)",
              }}
            >
              Select a document from the left column to inspect its complete 17-stage NLP trace.
            </div>
          ) : (
            <>
              {/* Document Metadata Banner */}
              <div
                style={{
                  background: "#FFFFFF",
                  borderRadius: "16px",
                  border: "1px solid var(--border-default)",
                  padding: "18px 22px",
                }}
              >
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: "12px", marginBottom: "8px" }}>
                  <h2 style={{ fontSize: "17px", fontWeight: 700, color: "var(--text-primary)" }}>{trace.title}</h2>
                  <span
                    style={{
                      fontSize: "11px",
                      fontWeight: 700,
                      padding: "4px 10px",
                      borderRadius: "6px",
                      background: "#E8F8F2",
                      color: "#059669",
                      border: "1px solid #B6EADA",
                    }}
                  >
                    Status: {trace.overall_status.toUpperCase()}
                  </span>
                </div>

                <div style={{ display: "flex", flexWrap: "wrap", gap: "20px", fontSize: "12px", color: "var(--text-secondary)" }}>
                  <div>
                    <span style={{ fontWeight: 600, color: "var(--text-primary)" }}>Document ID: </span>
                    <span style={{ fontFamily: "var(--font-mono)" }}>{trace.document_id}</span>
                  </div>
                  <div>
                    <span style={{ fontWeight: 600, color: "var(--text-primary)" }}>Source: </span>
                    <span>{trace.source_id}</span>
                  </div>
                  <div>
                    <span style={{ fontWeight: 600, color: "var(--text-primary)" }}>Origin: </span>
                    <span style={{ fontWeight: 700, color: trace.origin === "LIVE_EXTERNAL" ? "#059669" : "#7047F5" }}>
                      {trace.origin}
                    </span>
                  </div>
                  <div>
                    <span style={{ fontWeight: 600, color: "var(--text-primary)" }}>Total Execution Time: </span>
                    <span style={{ fontFamily: "var(--font-mono)" }}>{trace.total_duration_ms.toFixed(2)} ms</span>
                  </div>
                  <div>
                    <span style={{ fontWeight: 600, color: "var(--text-primary)" }}>SHA-256: </span>
                    <span style={{ fontFamily: "var(--font-mono)" }}>{trace.content_hash_sha256.substring(0, 16)}...</span>
                  </div>
                </div>
              </div>

              {/* Analysis Success Notice */}
              {analysisNotice && (
                <div
                  style={{
                    padding: "12px 18px",
                    borderRadius: "12px",
                    background: "#E8F8F2",
                    border: "1px solid #B6EADA",
                    color: "#065F46",
                    fontSize: "13px",
                    fontWeight: 600,
                    display: "flex",
                    alignItems: "center",
                    gap: "8px",
                  }}
                >
                  <CheckCircle2 size={16} />
                  <span>{analysisNotice}</span>
                </div>
              )}

              {/* Event Relevance & Downstream Eligibility Decision Banner */}
              {(() => {
                const relevanceStage = trace.stages.find((s) => s.stage_number === 10);
                const stageDetails = relevanceStage?.details || {};
                const isRelevant = stageDetails.is_epidemiological_event !== false;
                const category = stageDetails.category || (isRelevant ? "ACUTE_OUTBREAK_REPORT" : "HEALTH_POLICY_OR_ADMINISTRATION");

                // Determine authoritative disposition
                let disposition = stageDetails.disposition;
                if (!disposition) {
                  const combined = `${trace.title || ""} ${trace.raw_text || ""}`.toLowerCase();
                  if (
                    category === "NEGATIVE_RULE_OUT" ||
                    category === "NEGATED_SURVEILLANCE" ||
                    combined.includes("nil outbreak") ||
                    combined.includes("nil report") ||
                    combined.includes("0 cases, 0 deaths") ||
                    combined.includes("tested negative") ||
                    combined.includes("ruled out")
                  ) {
                    disposition = "NEGATIVE_RULE_OUT";
                  } else if (
                    category === "OUT_OF_SCOPE_EVENT" ||
                    ["nipah", "zika", "ebola", "marburg", "mpox", "monkeypox"].some((p) => combined.includes(p)) &&
                    !["dengue", "malaria", "cholera", "chikungunya", "leptospirosis", "scrub typhus", "japanese encephalitis", "diarrhoeal"].some((p) => combined.includes(p))
                  ) {
                    disposition = "OUT_OF_SCOPE";
                  } else if (["HEALTH_POLICY_OR_ADMINISTRATION", "CONTEXTUAL_HEALTH_NEWS", "POLICY_ADMINISTRATIVE_NEWS", "PREPAREDNESS_OR_TRAINING", "GENERAL_DISEASE_REFERENCE", "IRRELEVANT"].includes(category)) {
                    disposition = "ADMINISTRATIVE_CONTEXT";
                  } else if (["SURVEILLANCE_REPORT", "CASE_CLUSTER_REPORT", "SUSPECTED_OUTBREAK_REPORT"].includes(category)) {
                    disposition = "SUSPECTED_REPORT";
                  } else if (isRelevant) {
                    disposition = "QUALIFYING_POSITIVE_REPORT";
                  } else {
                    disposition = "AMBIGUOUS_REQUIRES_REVIEW";
                  }
                }

                interface DispStyle {
                  badgeText: string;
                  bg: string;
                  border: string;
                  badgeBg: string;
                  badgeColor: string;
                  textColor: string;
                  descColor: string;
                  desc: string;
                }

                const styleMap: Record<string, DispStyle> = {
                  QUALIFYING_POSITIVE_REPORT: {
                    badgeText: "Eligible for Downstream Fusion",
                    bg: "#ECFDF5",
                    border: "#A7F3D0",
                    badgeBg: "#D1FAE5",
                    badgeColor: "#059669",
                    textColor: "#065F46",
                    descColor: "#047857",
                    desc: stageDetails.explanation || "Clinical disease cases or active outbreak surge detected. Document is eligible for cross-document fusion and statistical signal detection.",
                  },
                  SUSPECTED_REPORT: {
                    badgeText: "Eligible for Triage & Tracking",
                    bg: "#FFFBEB",
                    border: "#FDE68A",
                    badgeBg: "#FEF3C7",
                    badgeColor: "#D97706",
                    textColor: "#92400E",
                    descColor: "#B45309",
                    desc: stageDetails.explanation || "Suspected disease cluster or unconfirmed transmission signals. Flagged for triage surveillance and prospective monitoring.",
                  },
                  NEGATIVE_RULE_OUT: {
                    badgeText: "Negative Evidence Preserved",
                    bg: "#EFF6FF",
                    border: "#BFDBFE",
                    badgeBg: "#DBEAFE",
                    badgeColor: "#2563EB",
                    textColor: "#1E40AF",
                    descColor: "#1D4ED8",
                    desc: "Negative rule-out or NIL outbreak report (0 cases). Preserved for negative evidence reconciliation and rule-out auditing; downstream positive alert escalation safely bypassed.",
                  },
                  OUT_OF_SCOPE: {
                    badgeText: "Non-Priority Scope Document",
                    bg: "#F3F4F6",
                    border: "#E5E7EB",
                    badgeBg: "#E5E7EB",
                    badgeColor: "#4B5563",
                    textColor: "#374151",
                    descColor: "#4B5563",
                    desc: stageDetails.explanation || "Pathogen or condition detected outside the 8 canonical priority diseases. Maintained in observational archive without trigger.",
                  },
                  ADMINISTRATIVE_CONTEXT: {
                    badgeText: "Administrative Policy / Non-Clinical",
                    bg: "#F8FAFC",
                    border: "#E2E8F0",
                    badgeBg: "#E2E8F0",
                    badgeColor: "#475569",
                    textColor: "#1E293B",
                    descColor: "#334155",
                    desc: stageDetails.explanation || "Administrative agreement, strategic policy review, or routine advisory. Downstream fusion and alerting bypassed to prevent false alarms.",
                  },
                  AMBIGUOUS_REQUIRES_REVIEW: {
                    badgeText: "Requires Human Review",
                    bg: "#FFF7ED",
                    border: "#FFEDD5",
                    badgeBg: "#FFEDD5",
                    badgeColor: "#EA580C",
                    textColor: "#9A3412",
                    descColor: "#C2410C",
                    desc: stageDetails.explanation || "Ambiguous epidemiological context or conflicting signals. Preserved for public-health analyst inspection.",
                  },
                };

                const cfg = styleMap[disposition] || styleMap["AMBIGUOUS_REQUIRES_REVIEW"];

                return (
                  <div
                    style={{
                      padding: "14px 18px",
                      borderRadius: "14px",
                      background: cfg.bg,
                      border: `1px solid ${cfg.border}`,
                      display: "flex",
                      justifyContent: "space-between",
                      alignItems: "center",
                      flexWrap: "wrap",
                      gap: "12px",
                    }}
                  >
                    <div>
                      <div style={{ display: "flex", alignItems: "center", gap: "8px", flexWrap: "wrap" }}>
                        <span style={{ fontSize: "13px", fontWeight: 700, color: cfg.textColor }}>
                          Relevance Classification: {category}
                        </span>
                        <span
                          style={{
                            fontSize: "11px",
                            fontWeight: 700,
                            padding: "2px 8px",
                            borderRadius: "4px",
                            background: cfg.badgeBg,
                            color: cfg.badgeColor,
                          }}
                        >
                          {cfg.badgeText}
                        </span>
                      </div>
                      <div style={{ fontSize: "12px", color: cfg.descColor, marginTop: "3px" }}>
                        {cfg.desc}
                      </div>
                    </div>

                    <button
                      onClick={handleRunDownstreamAnalysis}
                      disabled={isAnalyzing || disposition === "NEGATIVE_RULE_OUT" || disposition === "OUT_OF_SCOPE"}
                      style={{
                        padding: "8px 16px",
                        borderRadius: "8px",
                        background: "#FFFFFF",
                        border: "1px solid var(--border-default)",
                        color: (disposition === "NEGATIVE_RULE_OUT" || disposition === "OUT_OF_SCOPE") ? "var(--text-muted)" : "var(--text-primary)",
                        fontSize: "12.5px",
                        fontWeight: 600,
                        cursor: (isAnalyzing || disposition === "NEGATIVE_RULE_OUT" || disposition === "OUT_OF_SCOPE") ? "not-allowed" : "pointer",
                        display: "flex",
                        alignItems: "center",
                        gap: "6px",
                        boxShadow: "var(--shadow-xs)",
                      }}
                      title={disposition === "NEGATIVE_RULE_OUT" ? "Negative rule-out documents are protected from positive outbreak escalation" : "Execute downstream stages 11-17"}
                    >
                      <Zap size={14} className={isAnalyzing ? "animate-spin" : ""} color={disposition === "NEGATIVE_RULE_OUT" ? "#94A3B8" : "#7047F5"} />
                      {isAnalyzing ? "Executing Stages 11-17..." : (disposition === "NEGATIVE_RULE_OUT" ? "Positive Fusion Safely Bypassed" : "Run Downstream Analysis On-Demand")}
                    </button>
                  </div>
                );
              })()}

              {/* Interactive Annotated Text View with Legend */}
              <div
                style={{
                  background: "#FFFFFF",
                  borderRadius: "16px",
                  border: "1px solid var(--border-default)",
                  padding: "20px 24px",
                }}
              >
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "16px", flexWrap: "wrap", gap: "10px" }}>
                  <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                    <Eye size={17} style={{ color: "#7047F5" }} />
                    <h3 style={{ fontSize: "14px", fontWeight: 700, color: "var(--text-primary)" }}>
                      Interactive Grounded Text Spans
                    </h3>
                  </div>

                  {/* Highlight Legend */}
                  <div style={{ display: "flex", gap: "12px", fontSize: "11px", fontWeight: 600 }}>
                    <span style={{ display: "flex", alignItems: "center", gap: "4px" }}>
                      <span style={{ width: "10px", height: "10px", borderRadius: "2px", background: "#FEE2E2", border: "1px solid #FCA5A5" }} />
                      Disease ({trace.nlp_output?.entities?.length ?? 0})
                    </span>
                    <span style={{ display: "flex", alignItems: "center", gap: "4px" }}>
                      <span style={{ width: "10px", height: "10px", borderRadius: "2px", background: "#E0F2FE", border: "1px solid #7DD3FC" }} />
                      Location ({trace.nlp_output?.locations?.length ?? 0})
                    </span>
                    <span style={{ display: "flex", alignItems: "center", gap: "4px" }}>
                      <span style={{ width: "10px", height: "10px", borderRadius: "2px", background: "#FEF3C7", border: "1px solid #FCD34D" }} />
                      Quantity ({trace.nlp_output?.quantities?.length ?? 0})
                    </span>
                    <span style={{ display: "flex", alignItems: "center", gap: "4px" }}>
                      <span style={{ width: "10px", height: "10px", borderRadius: "2px", background: "#EDE9FE", border: "1px solid #C4B5FD" }} />
                      Date/Time ({trace.nlp_output?.temporal_expressions?.length ?? 0})
                    </span>
                  </div>
                </div>

                {/* Annotated Text Body */}
                <div
                  style={{
                    lineHeight: 1.8,
                    fontSize: "13.5px",
                    color: "var(--text-primary)",
                    padding: "16px",
                    background: "#F8FAFC",
                    borderRadius: "12px",
                    border: "1px solid var(--border-default)",
                    maxHeight: "260px",
                    overflowY: "auto",
                  }}
                >
                  {renderAnnotatedText()}
                </div>

                {/* Selected Span Verification Card */}
                {selectedSpan && (
                  <div
                    style={{
                      marginTop: "16px",
                      padding: "14px 18px",
                      borderRadius: "12px",
                      background: "#F1EDFD",
                      border: "1px solid #DDD6FE",
                      display: "flex",
                      justifyContent: "space-between",
                      alignItems: "center",
                      flexWrap: "wrap",
                      gap: "12px",
                    }}
                  >
                    <div>
                      <div style={{ display: "flex", alignItems: "center", gap: "8px", marginBottom: "4px" }}>
                        <CheckCircle2 size={15} style={{ color: "#059669" }} />
                        <span style={{ fontSize: "12px", fontWeight: 700, color: "#5B21B6" }}>
                          Character Span Verified: text[{selectedSpan.start}:{selectedSpan.end}] == &quot;{selectedSpan.text}&quot;
                        </span>
                      </div>
                      <div style={{ fontSize: "12px", color: "#475569" }}>
                        Concept Label: <strong>{selectedSpan.label}</strong> | Normalized Value: <strong>{selectedSpan.normalized || "N/A"}</strong>
                      </div>
                    </div>

                    <div style={{ fontSize: "12px", color: "#6D28D9", fontWeight: 600 }}>
                      Extraction Confidence: {Math.round((selectedSpan.confidence ?? 1.0) * 100)}%
                    </div>
                  </div>
                )}
              </div>

              {/* 17-Stage Pipeline Forensic Timeline */}
              <div
                style={{
                  background: "#FFFFFF",
                  borderRadius: "16px",
                  border: "1px solid var(--border-default)",
                  padding: "20px 24px",
                }}
              >
                <div style={{ display: "flex", alignItems: "center", gap: "8px", marginBottom: "16px" }}>
                  <Layers size={17} style={{ color: "#7047F5" }} />
                  <h3 style={{ fontSize: "14px", fontWeight: 700, color: "var(--text-primary)" }}>
                    17-Stage Continuous Surveillance Timeline
                  </h3>
                </div>

                <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(280px, 1fr))", gap: "12px" }}>
                  {trace.stages.map((st) => {
                    const isSelected = selectedStage?.stage_number === st.stage_number;
                    const isCompleted = st.status === "COMPLETED";
                    const isFailed = st.status === "FAILED";
                    const isSkipped = st.status === "SKIPPED";
                    return (
                      <div
                        key={st.stage_number}
                        onClick={() => setSelectedStage(st)}
                        style={{
                          padding: "12px 14px",
                          borderRadius: "12px",
                          border: isSelected
                            ? "2px solid #7047F5"
                            : isSkipped
                            ? "1px dashed #E2E8F0"
                            : "1px solid var(--border-default)",
                          background: isSelected ? "#F8FAFC" : isSkipped ? "#FAFAFA" : "#FFFFFF",
                          cursor: "pointer",
                          transition: "all 0.15s ease",
                          opacity: isSkipped ? 0.85 : 1.0,
                        }}
                      >
                        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "4px" }}>
                          <span style={{ fontSize: "11px", fontWeight: 700, color: isSkipped ? "#94A3B8" : "#7047F5" }}>
                            Stage {st.stage_number}
                          </span>
                          <span
                            style={{
                              fontSize: "10px",
                              fontWeight: 700,
                              padding: "2px 6px",
                              borderRadius: "4px",
                              background: isCompleted ? "#E8F8F2" : isFailed ? "#FEE2E2" : isSkipped ? "#F1F5F9" : "#F8FAFC",
                              color: isCompleted ? "#059669" : isFailed ? "#DC2626" : isSkipped ? "#64748B" : "#475569",
                              border: isSkipped ? "1px dashed #CBD5E1" : "none",
                            }}
                          >
                            {st.status} ({st.duration_ms.toFixed(1)} ms)
                          </span>
                        </div>

                        <div style={{ fontSize: "12.5px", fontWeight: 600, color: isSkipped ? "var(--text-secondary)" : "var(--text-primary)", marginBottom: "4px" }}>
                          {st.stage_name}
                        </div>

                        <div style={{ fontSize: "11px", color: isSkipped ? "#94A3B8" : "var(--text-muted)", lineHeight: 1.3 }}>
                          {st.output_summary}
                        </div>
                      </div>
                    );
                  })}
                </div>

                {/* Selected Stage Detail Drawer */}
                {selectedStage && (
                  <div
                    style={{
                      marginTop: "16px",
                      padding: "16px",
                      borderRadius: "12px",
                      background: "#F8FAFC",
                      border: "1px solid var(--border-default)",
                    }}
                  >
                    <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "8px" }}>
                      <span style={{ fontSize: "13px", fontWeight: 700, color: "var(--text-primary)" }}>
                        Stage {selectedStage.stage_number}: {selectedStage.stage_name} Details
                      </span>
                      <span style={{ fontSize: "12px", fontFamily: "var(--font-mono)", color: "var(--brand-primary)" }}>
                        Execution: {selectedStage.duration_ms.toFixed(2)} ms
                      </span>
                    </div>

                    <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "12px", fontSize: "12px", marginBottom: "8px" }}>
                      <div>
                        <span style={{ fontWeight: 600, color: "var(--text-secondary)" }}>Input: </span>
                        <span>{selectedStage.input_summary}</span>
                      </div>
                      <div>
                        <span style={{ fontWeight: 600, color: "var(--text-secondary)" }}>Output: </span>
                        <span>{selectedStage.output_summary}</span>
                      </div>
                    </div>

                    {selectedStage.details && Object.keys(selectedStage.details).length > 0 && (
                      <pre
                        style={{
                          background: "#0F172A",
                          color: "#F8FAFC",
                          padding: "10px",
                          borderRadius: "8px",
                          fontSize: "11px",
                          overflowX: "auto",
                          margin: 0,
                        }}
                      >
                        {JSON.stringify(selectedStage.details, null, 2)}
                      </pre>
                    )}
                  </div>
                )}
              </div>
            </>
          )}
        </div>
      </div>

      {/* Embedded Document Submission Modal */}
      <Modal
        isOpen={isSubmitModalOpen}
        onClose={() => setIsSubmitModalOpen(false)}
        title="Ingest Epidemiological Report"
        subtitle="Submit public health bulletins, lab reports, or news dispatches directly into the 17-stage surveillance pipeline"
      >
        <DocumentSubmitForm onDocumentSubmitted={handleDocumentSubmitted} />
      </Modal>
    </div>
  );
};

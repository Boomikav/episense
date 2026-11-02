import React from "react";
import { CheckCircle, FileText, AlertTriangle } from "lucide-react";
import type { ReconstructedEvidenceSpan } from "../../types/api";

interface EvidenceSpansViewProps {
  spans: ReconstructedEvidenceSpan[];
}

export const EvidenceSpansView: React.FC<EvidenceSpansViewProps> = ({ spans }) => {
  if (!spans || spans.length === 0) {
    return (
      <div className="card" style={{ textAlign: "center", padding: "32px", color: "var(--text-tertiary)" }}>
        No reconstructed evidence spans attached to this record.
      </div>
    );
  }

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
      <div style={{ fontSize: "13px", color: "var(--text-secondary)", marginBottom: "4px" }}>
        Character-level NLP evidence spans validated against immutable source documents ({spans.length} spans):
      </div>

      {spans.map((s, idx) => (
        <div
          key={idx}
          className="card"
          style={{
            background: "var(--bg-surface-2)",
            border: "1px solid var(--border-default)",
            padding: "16px",
          }}
        >
          {/* Header */}
          <div
            style={{
              display: "flex",
              justifyContent: "space-between",
              alignItems: "center",
              marginBottom: "10px",
              flexWrap: "wrap",
              gap: "8px",
            }}
          >
            <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
              <FileText size={15} style={{ color: "var(--brand-primary)" }} />
              <span style={{ fontSize: "12px", fontWeight: 700, color: "var(--text-primary)", textTransform: "capitalize" }}>
                {s.attribute_role || "Evidence Span"}
              </span>
              <span className="code-badge" style={{ fontSize: "10px" }}>
                chars [{s.start_char}..{s.end_char}]
              </span>
              <span style={{ fontSize: "11px", color: "var(--text-muted)" }}>
                Source: {s.source_id}
              </span>
            </div>

            <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
              {s.is_valid ? (
                <span className="badge badge-success" style={{ fontSize: "10px" }}>
                  <CheckCircle size={11} /> Verified Provenance
                </span>
              ) : (
                <span className="badge badge-high" style={{ fontSize: "10px" }}>
                  <AlertTriangle size={11} /> Validation Mismatch
                </span>
              )}
            </div>
          </div>

          {/* Context Snippet */}
          <div
            style={{
              padding: "10px 14px",
              borderRadius: "var(--radius-sm)",
              background: "var(--bg-canvas)",
              border: "1px solid var(--border-subtle)",
              fontFamily: "var(--font-sans)",
              fontSize: "13px",
              lineHeight: 1.5,
              color: "var(--text-secondary)",
            }}
          >
            {s.surrounding_context ? (
              <span>
                "...{s.surrounding_context.split(s.extracted_text)[0]}
                <mark
                  style={{
                    backgroundColor: "rgba(112, 71, 245, 0.15)",
                    color: "var(--brand-primary)",
                    padding: "2px 4px",
                    borderRadius: "3px",
                    fontWeight: 600,
                  }}
                >
                  {s.extracted_text}
                </mark>
                {s.surrounding_context.split(s.extracted_text)[1]}..."
              </span>
            ) : (
              <mark
                style={{
                  backgroundColor: "rgba(112, 71, 245, 0.15)",
                  color: "var(--brand-primary)",
                  padding: "2px 4px",
                  borderRadius: "3px",
                  fontWeight: 600,
                }}
              >
                {s.extracted_text}
              </mark>
            )}
          </div>

          <div
            style={{
              display: "flex",
              justifyContent: "space-between",
              alignItems: "center",
              marginTop: "8px",
              fontSize: "11px",
              color: "var(--text-muted)",
            }}
          >
            <span>Extraction Engine: {s.extraction_method || "canonical_nlp_v1"}</span>
            <span className="code-badge" style={{ fontSize: "10px" }}>
              Doc ID: {s.document_id}
            </span>
          </div>
        </div>
      ))}
    </div>
  );
};

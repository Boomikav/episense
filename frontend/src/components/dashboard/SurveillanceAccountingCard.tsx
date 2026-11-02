import React, { useState } from "react";
import { ShieldAlert, CheckCircle2, AlertTriangle, HelpCircle, Layers, FileText, Database, Activity } from "lucide-react";
import type { SurveillanceAccounting } from "../../types/api";

interface SurveillanceAccountingCardProps {
  accounting?: SurveillanceAccounting | null;
}

export const SurveillanceAccountingCard: React.FC<SurveillanceAccountingCardProps> = ({ accounting }) => {
  const [showDefinitions, setShowDefinitions] = useState(false);

  if (!accounting) return null;

  return (
    <div
      className="card"
      style={{
        padding: "20px 24px",
        marginBottom: "28px",
        background: "#FFFFFF",
        borderRadius: "16px",
        border: "1px solid var(--border-default)",
        boxShadow: "var(--shadow-xs)",
      }}
    >
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          marginBottom: "16px",
          flexWrap: "wrap",
          gap: "12px",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
          <div
            style={{
              width: "32px",
              height: "32px",
              borderRadius: "8px",
              background: "#EEF2FF",
              color: "#4F46E5",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
            }}
          >
            <ShieldAlert size={18} />
          </div>
          <div>
            <h3 style={{ fontSize: "15px", fontWeight: 700, color: "#0F172A", margin: 0 }}>
              Authoritative Surveillance Accounting &amp; Statistical Baseline Audit
            </h3>
            <p style={{ fontSize: "12px", color: "#64748B", margin: 0 }}>
              Independent telemetry separating raw documents, extracted mentions, fused canonical events, corroboration status, and baseline gating.
            </p>
          </div>
        </div>

        <button
          onClick={() => setShowDefinitions(!showDefinitions)}
          style={{
            display: "inline-flex",
            alignItems: "center",
            gap: "6px",
            background: "#F8FAFC",
            border: "1px solid #E2E8F0",
            borderRadius: "8px",
            padding: "5px 12px",
            fontSize: "12px",
            fontWeight: 600,
            color: "#475569",
            cursor: "pointer",
          }}
        >
          <HelpCircle size={14} />
          {showDefinitions ? "Hide Metric Standards" : "Scientific Definitions"}
        </button>
      </div>

      {showDefinitions && (
        <div
          style={{
            padding: "14px 18px",
            background: "#F8FAFC",
            borderRadius: "12px",
            border: "1px solid #E2E8F0",
            marginBottom: "18px",
            fontSize: "12px",
            lineHeight: 1.6,
            color: "#334155",
          }}
        >
          <div style={{ fontWeight: 700, color: "#0F172A", marginBottom: "6px" }}>
            Scientific Integrity Principles Applied in Active Telemetry:
          </div>
          <ul style={{ margin: 0, paddingLeft: "18px" }}>
            <li>
              <strong>Candidate Mentions vs. Fused Events:</strong> Raw NLP extractions generate candidate mentions. Cross-document fusion deduplicates these into canonical events using spatiotemporal and pathogen matching to prevent wire-syndication inflation.
            </li>
            <li>
              <strong>Corroboration Threshold:</strong> Single-source claims (N=1) are labeled unverified and gated from automated outbreak escalation until confirmed by &ge;2 independent source groups.
            </li>
            <li>
              <strong>Baseline Reliability Gating:</strong> Indicator anomaly detection algorithms (EARS C1–C3, Farrington) strictly require &ge;3 historical weekly periods with &ge;2 non-zero observations. With 0 series meeting this threshold in current data, 100% of statistical signals are gated to prevent false-alarm escalation.
            </li>
          </ul>
        </div>
      )}

      {/* 4 Multi-Column Audit Grid */}
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))",
          gap: "16px",
        }}
      >
        {/* Column 1: Document Corpus Ingestion */}
        <div
          style={{
            background: "#F8FAFC",
            borderRadius: "12px",
            padding: "14px 16px",
            border: "1px solid #E2E8F0",
          }}
        >
          <div style={{ display: "flex", alignItems: "center", gap: "8px", color: "#2563EB", marginBottom: "10px" }}>
            <Database size={16} />
            <span style={{ fontSize: "12px", fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.04em" }}>
              1. Document Ingestion
            </span>
          </div>
          <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "6px", fontSize: "13px" }}>
            <span style={{ color: "#64748B" }}>Total Documents:</span>
            <span style={{ fontWeight: 700, color: "#0F172A" }}>{accounting.documents_ingested_total}</span>
          </div>
          <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "6px", fontSize: "12px" }}>
            <span style={{ color: "#64748B" }}>• Live External:</span>
            <span style={{ fontWeight: 600, color: "#059669" }}>{accounting.documents_ingested_live}</span>
          </div>
          <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "6px", fontSize: "12px" }}>
            <span style={{ color: "#64748B" }}>• Historical Corpus:</span>
            <span style={{ fontWeight: 600, color: "#475569" }}>{accounting.documents_ingested_historical}</span>
          </div>
          <div style={{ display: "flex", justifyContent: "space-between", fontSize: "12px", paddingTop: "6px", borderTop: "1px dashed #CBD5E1" }}>
            <span style={{ color: "#64748B" }}>Parsed with Events:</span>
            <span style={{ fontWeight: 600, color: "#0F172A" }}>{accounting.documents_parsed_successfully} / {accounting.documents_ingested_total}</span>
          </div>
        </div>

        {/* Column 2: Candidate Mentions vs Fused Events */}
        <div
          style={{
            background: "#F8FAFC",
            borderRadius: "12px",
            padding: "14px 16px",
            border: "1px solid #E2E8F0",
          }}
        >
          <div style={{ display: "flex", alignItems: "center", gap: "8px", color: "#7C3AED", marginBottom: "10px" }}>
            <Layers size={16} />
            <span style={{ fontSize: "12px", fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.04em" }}>
              2. Extraction &amp; Fusion
            </span>
          </div>
          <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "6px", fontSize: "13px" }}>
            <span style={{ color: "#64748B" }}>Candidate Mentions:</span>
            <span style={{ fontWeight: 700, color: "#0F172A" }}>{accounting.candidate_events_extracted}</span>
          </div>
          <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "6px", fontSize: "12px" }}>
            <span style={{ color: "#64748B" }}>Active Canonical Events:</span>
            <span style={{ fontWeight: 600, color: "#7C3AED" }}>{accounting.fused_events_active}</span>
          </div>
          <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "6px", fontSize: "12px" }}>
            <span style={{ color: "#64748B" }}>Superseded / Retracted:</span>
            <span style={{ fontWeight: 600, color: "#64748B" }}>{accounting.fused_events_superseded}</span>
          </div>
          <div style={{ display: "flex", justifyContent: "space-between", fontSize: "12px", paddingTop: "6px", borderTop: "1px dashed #CBD5E1" }}>
            <span style={{ color: "#64748B" }}>Syndication Compression:</span>
            <span style={{ fontWeight: 600, color: "#0F172A" }}>
              {(accounting.candidate_events_extracted / (accounting.fused_events_active || 1)).toFixed(2)}x
            </span>
          </div>
        </div>

        {/* Column 3: Corroboration Status */}
        <div
          style={{
            background: "#F8FAFC",
            borderRadius: "12px",
            padding: "14px 16px",
            border: "1px solid #E2E8F0",
          }}
        >
          <div style={{ display: "flex", alignItems: "center", gap: "8px", color: "#D97706", marginBottom: "10px" }}>
            <Activity size={16} />
            <span style={{ fontSize: "12px", fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.04em" }}>
              3. Source Corroboration
            </span>
          </div>
          <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "6px", fontSize: "13px" }}>
            <span style={{ color: "#64748B" }}>Corroborated (&ge;2 src):</span>
            <span style={{ fontWeight: 700, color: "#059669" }}>{accounting.independently_corroborated_events}</span>
          </div>
          <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "6px", fontSize: "12px" }}>
            <span style={{ color: "#64748B" }}>Single-Source Claims:</span>
            <span style={{ fontWeight: 600, color: "#D97706" }}>{accounting.unverified_single_source_claims}</span>
          </div>
          <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "6px", fontSize: "12px" }}>
            <span style={{ color: "#64748B" }}>Verified Indicator Bins:</span>
            <span style={{ fontWeight: 600, color: "#0F172A" }}>{accounting.verified_numerical_indicator_bins} / {accounting.indicator_time_bins_total}</span>
          </div>
          <div style={{ display: "flex", justifyContent: "space-between", fontSize: "12px", paddingTop: "6px", borderTop: "1px dashed #CBD5E1" }}>
            <span style={{ color: "#64748B" }}>Field Verification:</span>
            <span style={{ fontWeight: 600, color: "#D97706" }}>Pending Investigation</span>
          </div>
        </div>

        {/* Column 4: Baseline Gating Audit */}
        <div
          style={{
            background: "#FFFBEB",
            borderRadius: "12px",
            padding: "14px 16px",
            border: "1px solid #FDE68A",
          }}
        >
          <div style={{ display: "flex", alignItems: "center", gap: "8px", color: "#B45309", marginBottom: "10px" }}>
            <AlertTriangle size={16} />
            <span style={{ fontSize: "12px", fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.04em" }}>
              4. Statistical Baseline Gating
            </span>
          </div>
          <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "6px", fontSize: "13px" }}>
            <span style={{ color: "#78350F" }}>Total Signals Evaluated:</span>
            <span style={{ fontWeight: 700, color: "#78350F" }}>{accounting.signals_evaluated}</span>
          </div>
          <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "6px", fontSize: "12px" }}>
            <span style={{ color: "#92400E" }}>• Gated (Sparse Baseline):</span>
            <span style={{ fontWeight: 700, color: "#B45309" }}>{accounting.signals_blocked_insufficient_baseline} (100%)</span>
          </div>
          <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "6px", fontSize: "12px" }}>
            <span style={{ color: "#92400E" }}>• Eligible (Stable Baseline):</span>
            <span style={{ fontWeight: 600, color: "#059669" }}>{accounting.signals_eligible_stable_baseline}</span>
          </div>
          <div style={{ display: "flex", justifyContent: "space-between", fontSize: "12px", paddingTop: "6px", borderTop: "1px dashed #FCD34D" }}>
            <span style={{ color: "#78350F" }}>Statistical Integrity:</span>
            <span style={{ fontWeight: 700, color: "#B45309" }}>False Escalation Blocked</span>
          </div>
        </div>
      </div>
    </div>
  );
};

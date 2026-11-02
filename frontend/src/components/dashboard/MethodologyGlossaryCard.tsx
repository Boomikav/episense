import React, { useState } from "react";
import { BookOpen, ChevronDown, ChevronUp, ShieldCheck } from "lucide-react";

export const MethodologyGlossaryCard: React.FC = () => {
  const [isOpen, setIsOpen] = useState(false);

  const definitions = [
    {
      term: "Event-Based Surveillance (EBS)",
      acronym: "EBS",
      definition:
        "The rapid capture, filtering, and verification of unstructured ad hoc narrative reports (e.g., media reports, public health bulletins, and official outbreak news) prior to formal clinical coding.",
      context: "Primary source of EpiSense live news feeds; treated as unverified field signals requiring corroboration.",
    },
    {
      term: "Indicator-Based Surveillance (IBS)",
      acronym: "IBS",
      definition:
        "The routine, structured collection and reporting of aggregate numerical counts (e.g., weekly or monthly clinic/hospital admissions) with standardized diagnostic criteria.",
      context: "Essential foundation for statistical anomaly detection and forecasting. Gated when multi-year counts are absent.",
    },
    {
      term: "Canonical Fused Event",
      acronym: "D05 Clustering",
      definition:
        "A deduplicated, spatio-temporally clustered real-world outbreak incident synthesized from multiple independent reports under Decision D05 (similarity threshold ≥ 0.78).",
      context: "Prevents double-counting and media inflation across syndicated wire services.",
    },
    {
      term: "Independent Corroboration",
      acronym: "Cross-Source",
      definition:
        "Cross-verification of an incident across distinct institutional or geographic source registries with separate data provenance chains.",
      context: "Multiplies triage certainty; prevents single-source reporting artifacts from triggering false alarms.",
    },
    {
      term: "Baseline Sufficiency",
      acronym: "N ≥ 12 periods",
      definition:
        "The empirical requirement that a series possess at least 12 consecutive, comparable, non-missing historical reporting periods prior to model fitting.",
      context: "If baseline criteria are not met, statistical anomaly detectors and ML forecasters strictly abstain.",
    },
    {
      term: "Statistical Anomaly",
      acronym: "EARS / Farrington",
      definition:
        "A statistically significant aberration where current observed cases exceed the expected baseline value beyond a parameterized variance threshold (Z ≥ 2.0).",
      context: "Distinct from narrative reviews. Currently 0 active anomalies because historical baselines are gated.",
    },
    {
      term: "Forecast Prediction Interval",
      acronym: "95% Bounds",
      definition:
        "A probabilistic interval reflecting count regression parameter estimation uncertainty and negative binomial overdispersion.",
      context: "Evaluated empirically: 50% holdout coverage on 2023–2024 national dengue series is an acknowledged research limitation.",
    },
    {
      term: "Suppressed Result",
      acronym: "Safe Fallback",
      definition:
        "An intentional algorithmic refusal to issue an early warning signal or forecast when data fail strict completeness, comparability, or sample-size checks.",
      context: "Guarantees zero hallucination; prevents unvalidated models from issuing unfounded public health advisories.",
    },
  ];

  return (
    <div
      className="card"
      style={{
        padding: "16px 20px",
        marginBottom: "20px",
        background: "#FFFFFF",
        borderRadius: "14px",
        border: "1px solid var(--border-default)",
        boxShadow: "var(--shadow-xs)",
      }}
    >
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          cursor: "pointer",
          userSelect: "none",
        }}
        onClick={() => setIsOpen(!isOpen)}
      >
        <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
          <div
            style={{
              width: "32px",
              height: "32px",
              borderRadius: "8px",
              background: "#F1EDFD",
              color: "#7047F5",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
            }}
          >
            <BookOpen size={16} strokeWidth={2.2} />
          </div>
          <div>
            <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
              <span style={{ fontSize: "13.5px", fontWeight: 700, color: "#0F172A" }}>
                Methodological Reference & Epidemiological Semantics
              </span>
              <span
                style={{
                  padding: "2px 7px",
                  borderRadius: "9999px",
                  background: "#E8F8F2",
                  color: "#059669",
                  fontSize: "10.5px",
                  fontWeight: 700,
                  display: "inline-flex",
                  alignItems: "center",
                  gap: "4px",
                }}
              >
                <ShieldCheck size={11} />
                <span>Research Standard</span>
              </span>
            </div>
            <div style={{ fontSize: "11px", color: "#64748B", marginTop: "1px" }}>
              Rigorous definitions for Event-based surveillance, Baseline sufficiency, Heuristic triage vs Statistical anomalies
            </div>
          </div>
        </div>

        <button
          style={{
            display: "inline-flex",
            alignItems: "center",
            gap: "4px",
            background: "none",
            border: "none",
            color: "#7047F5",
            fontSize: "12px",
            fontWeight: 700,
            cursor: "pointer",
          }}
        >
          <span>{isOpen ? "Hide Definitions" : "View Definitions (8)"}</span>
          {isOpen ? <ChevronUp size={15} /> : <ChevronDown size={15} />}
        </button>
      </div>

      {isOpen && (
        <div
          style={{
            marginTop: "16px",
            paddingTop: "16px",
            borderTop: "1px solid var(--border-subtle)",
            display: "grid",
            gridTemplateColumns: "repeat(auto-fit, minmax(280px, 1fr))",
            gap: "14px",
          }}
        >
          {definitions.map((def, idx) => (
            <div
              key={idx}
              style={{
                padding: "12px 14px",
                borderRadius: "10px",
                background: "var(--bg-canvas)",
                border: "1px solid var(--border-default)",
                display: "flex",
                flexDirection: "column",
                gap: "4px",
              }}
            >
              <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
                <span style={{ fontSize: "12px", fontWeight: 700, color: "#0F172A" }}>
                  {def.term}
                </span>
                <span
                  style={{
                    padding: "1px 6px",
                    borderRadius: "4px",
                    background: "#EEF2FF",
                    color: "#4F46E5",
                    fontSize: "10px",
                    fontWeight: 700,
                    fontFamily: "var(--font-mono)",
                  }}
                >
                  {def.acronym}
                </span>
              </div>
              <p style={{ fontSize: "11.5px", color: "#334155", lineHeight: 1.45, margin: 0 }}>
                {def.definition}
              </p>
              <div
                style={{
                  fontSize: "10.5px",
                  color: "#64748B",
                  fontStyle: "italic",
                  marginTop: "2px",
                  paddingTop: "4px",
                  borderTop: "1px dashed var(--border-subtle)",
                }}
              >
                {def.context}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

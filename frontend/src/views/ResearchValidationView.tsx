import { useState } from "react";
import {
  AlertTriangle,
  Award,
  BarChart3,
  CheckCircle2,
  Database,
  FileCheck,
  FileText,
  Play,
  RefreshCw,
  Scale,
  ShieldCheck,
} from "lucide-react";
import { api } from "../services/api";
import type { NLPEvaluationReport } from "../types/api";
import { LoadingSpinner } from "../components/common/LoadingSpinner";
import { ErrorBanner } from "../components/common/ErrorBanner";

export const ResearchValidationView = () => {
  const [report, setReport] = useState<NLPEvaluationReport | null>(null);
  const [running, setRunning] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  const handleRunEvaluation = async () => {
    setRunning(true);
    setError(null);
    try {
      const result = await api.runEvaluation();
      setReport(result);
    } catch (err: any) {
      setError(err.message || "Failed to execute empirical evaluation.");
    } finally {
      setRunning(false);
    }
  };

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "24px" }}>
      {/* Header */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", flexWrap: "wrap", gap: "16px" }}>
        <div>
          <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
            <h1 className="page-title">Research & Empirical Validation</h1>
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
              Gold Benchmark v1.0
            </span>
          </div>
          <p className="page-subtitle">
            Scientific evaluation against expert-annotated gold surveillance records, offset verification, and documented research constraints.
          </p>
        </div>

        <button
          onClick={handleRunEvaluation}
          disabled={running}
          style={{
            display: "flex",
            alignItems: "center",
            gap: "8px",
            padding: "10px 20px",
            borderRadius: "10px",
            background: "#7047F5",
            border: "none",
            color: "#FFFFFF",
            fontSize: "13px",
            fontWeight: 700,
            cursor: running ? "not-allowed" : "pointer",
            boxShadow: "var(--shadow-sm)",
          }}
        >
          <Play size={14} className={running ? "animate-spin" : ""} />
          {running ? "Evaluating Benchmark Corpus..." : "Run Empirical Evaluation"}
        </button>
      </div>

      {error && <ErrorBanner message={error} onRetry={handleRunEvaluation} />}

      {/* Benchmark Specification Banner */}
      <div
        style={{
          background: "#FFFFFF",
          borderRadius: "16px",
          border: "1px solid var(--border-default)",
          padding: "20px 24px",
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))",
          gap: "18px",
        }}
      >
        <div>
          <div style={{ display: "flex", alignItems: "center", gap: "6px", marginBottom: "4px" }}>
            <Database size={15} style={{ color: "#7047F5" }} />
            <span style={{ fontSize: "12px", fontWeight: 700, color: "var(--text-secondary)" }}>
              NLP Benchmark Corpus
            </span>
          </div>
          <div style={{ fontSize: "20px", fontWeight: 800, color: "var(--text-primary)" }}>110 Documents</div>
          <div style={{ fontSize: "11px", color: "var(--text-muted)" }}>52 annotated benchmarks + 58 background EBS texts</div>
        </div>

        <div>
          <div style={{ display: "flex", alignItems: "center", gap: "6px", marginBottom: "4px" }}>
            <FileCheck size={15} style={{ color: "#059669" }} />
            <span style={{ fontSize: "12px", fontWeight: 700, color: "var(--text-secondary)" }}>
              Verified Gold Annotations
            </span>
          </div>
          <div style={{ fontSize: "20px", fontWeight: 800, color: "#059669" }}>18 Verified Outbreak Reports</div>
          <div style={{ fontSize: "11px", color: "var(--text-muted)" }}>Character-grounded spans with ICD-10 & GeoNames</div>
        </div>

        <div>
          <div style={{ display: "flex", alignItems: "center", gap: "6px", marginBottom: "4px" }}>
            <Scale size={15} style={{ color: "#2563EB" }} />
            <span style={{ fontSize: "12px", fontWeight: 700, color: "var(--text-secondary)" }}>
              Evaluation Criterion
            </span>
          </div>
          <div style={{ fontSize: "20px", fontWeight: 800, color: "#2563EB" }}>Exact Span Overlap</div>
          <div style={{ fontSize: "11px", color: "var(--text-muted)" }}>Strict boundary match & concept normalization</div>
        </div>

        <div>
          <div style={{ display: "flex", alignItems: "center", gap: "6px", marginBottom: "4px" }}>
            <Award size={15} style={{ color: "#D97706" }} />
            <span style={{ fontSize: "12px", fontWeight: 700, color: "var(--text-secondary)" }}>
              Evaluation Status
            </span>
          </div>
          <div style={{ fontSize: "20px", fontWeight: 800, color: report ? "#059669" : "var(--text-muted)" }}>
            {report ? `Macro F1: ${(report.macro_f1 * 100).toFixed(1)}%` : "Ready to Run"}
          </div>
          <div style={{ fontSize: "11px", color: "var(--text-muted)" }}>
            {report ? `Evaluated ${report.total_documents_evaluated} docs` : "Click button above to execute"}
          </div>
        </div>
      </div>

      {/* Evaluation Results Cards */}
      {running ? (
        <LoadingSpinner height="300px" message="Evaluating pipeline precision and recall against gold annotations..." />
      ) : report ? (
        <div style={{ display: "flex", flexDirection: "column", gap: "20px" }}>
          {/* Main 5 Metrics Grid */}
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))", gap: "16px" }}>
            {/* Disease NER */}
            <div style={{ background: "#FFFFFF", borderRadius: "14px", border: "1px solid var(--border-default)", padding: "18px" }}>
              <div style={{ fontSize: "12px", fontWeight: 700, color: "#DC2626", marginBottom: "4px" }}>
                Disease / Pathogen NER
              </div>
              <div style={{ fontSize: "26px", fontWeight: 800, color: "var(--text-primary)", marginBottom: "6px" }}>
                {(report.ner_disease_f1.f1 * 100).toFixed(1)}% <span style={{ fontSize: "12px", color: "var(--text-muted)", fontWeight: 500 }}>F1</span>
              </div>
              <div style={{ fontSize: "11.5px", color: "var(--text-secondary)" }}>
                Precision: {(report.ner_disease_f1.precision * 100).toFixed(1)}% | Recall: {(report.ner_disease_f1.recall * 100).toFixed(1)}%
              </div>
            </div>

            {/* Geographic Resolution */}
            <div style={{ background: "#FFFFFF", borderRadius: "14px", border: "1px solid var(--border-default)", padding: "18px" }}>
              <div style={{ fontSize: "12px", fontWeight: 700, color: "#0284C7", marginBottom: "4px" }}>
                Geographic Grounding
              </div>
              <div style={{ fontSize: "26px", fontWeight: 800, color: "var(--text-primary)", marginBottom: "6px" }}>
                {(report.geographic_resolution_f1.f1 * 100).toFixed(1)}% <span style={{ fontSize: "12px", color: "var(--text-muted)", fontWeight: 500 }}>F1</span>
              </div>
              <div style={{ fontSize: "11.5px", color: "var(--text-secondary)" }}>
                Precision: {(report.geographic_resolution_f1.precision * 100).toFixed(1)}% | Recall: {(report.geographic_resolution_f1.recall * 100).toFixed(1)}%
              </div>
            </div>

            {/* Quantity Extraction */}
            <div style={{ background: "#FFFFFF", borderRadius: "14px", border: "1px solid var(--border-default)", padding: "18px" }}>
              <div style={{ fontSize: "12px", fontWeight: 700, color: "#D97706", marginBottom: "4px" }}>
                Case Count Extraction
              </div>
              <div style={{ fontSize: "26px", fontWeight: 800, color: "var(--text-primary)", marginBottom: "6px" }}>
                {(report.quantity_extraction_f1.f1 * 100).toFixed(1)}% <span style={{ fontSize: "12px", color: "var(--text-muted)", fontWeight: 500 }}>F1</span>
              </div>
              <div style={{ fontSize: "11.5px", color: "var(--text-secondary)" }}>
                Precision: {(report.quantity_extraction_f1.precision * 100).toFixed(1)}% | Recall: {(report.quantity_extraction_f1.recall * 100).toFixed(1)}%
              </div>
            </div>

            {/* Temporal Resolution */}
            <div style={{ background: "#FFFFFF", borderRadius: "14px", border: "1px solid var(--border-default)", padding: "18px" }}>
              <div style={{ fontSize: "12px", fontWeight: 700, color: "#7C3AED", marginBottom: "4px" }}>
                Temporal Normalization
              </div>
              <div style={{ fontSize: "26px", fontWeight: 800, color: "var(--text-primary)", marginBottom: "6px" }}>
                {(report.temporal_normalization_f1.f1 * 100).toFixed(1)}% <span style={{ fontSize: "12px", color: "var(--text-muted)", fontWeight: 500 }}>F1</span>
              </div>
              <div style={{ fontSize: "11.5px", color: "var(--text-secondary)" }}>
                Precision: {(report.temporal_normalization_f1.precision * 100).toFixed(1)}% | Recall: {(report.temporal_normalization_f1.recall * 100).toFixed(1)}%
              </div>
            </div>

            {/* Assertion Accuracy */}
            <div style={{ background: "#FFFFFF", borderRadius: "14px", border: "1px solid var(--border-default)", padding: "18px" }}>
              <div style={{ fontSize: "12px", fontWeight: 700, color: "#059669", marginBottom: "4px" }}>
                Assertion Epistemic Accuracy
              </div>
              <div style={{ fontSize: "26px", fontWeight: 800, color: "var(--text-primary)", marginBottom: "6px" }}>
                {(report.assertion_accuracy * 100).toFixed(1)}%
              </div>
              <div style={{ fontSize: "11.5px", color: "var(--text-secondary)" }}>
                Confirmed vs Suspected vs Negated classification
              </div>
            </div>
          </div>
        </div>
      ) : null}

      {/* Documented Research Limitations & Failure Modes */}
      <div
        style={{
          background: "#FFFFFF",
          borderRadius: "16px",
          border: "1px solid var(--border-default)",
          padding: "22px 26px",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: "8px", marginBottom: "14px" }}>
          <AlertTriangle size={18} style={{ color: "#D97706" }} />
          <h3 style={{ fontSize: "15px", fontWeight: 700, color: "var(--text-primary)" }}>
            Documented Scientific Limitations & Edge Cases
          </h3>
        </div>

        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(280px, 1fr))", gap: "16px" }}>
          <div style={{ padding: "14px", background: "#FEF2F2", borderRadius: "12px", border: "1px solid #FECACA" }}>
            <h4 style={{ fontSize: "13px", fontWeight: 700, color: "#991B1B", marginBottom: "4px" }}>
              1. Compound Lexicon Boundary Truncation
            </h4>
            <p style={{ fontSize: "12px", color: "#7F1D1D", margin: 0, lineHeight: 1.4 }}>
              Multi-word clinical syndromes (e.g. &quot;acute encephalitis syndrome&quot;, &quot;hemorrhagic fever&quot;) can occasionally truncate to parent terms when matched via tokenized SciSpacy heads.
            </p>
          </div>

          <div style={{ padding: "14px", background: "#EFF6FF", borderRadius: "12px", border: "1px solid #BFDBFE" }}>
            <h4 style={{ fontSize: "13px", fontWeight: 700, color: "#1E40AF", marginBottom: "4px" }}>
              2. Toponym Collision & Ambiguity
            </h4>
            <p style={{ fontSize: "12px", color: "#1E3A8A", margin: 0, lineHeight: 1.4 }}>
              Locations sharing identical names across administrative tiers (e.g. Kozhikode district vs Kozhikode municipality) require contextual gazetteer heuristics to disambiguate.
            </p>
          </div>

          <div style={{ padding: "14px", background: "#FFFBEB", borderRadius: "12px", border: "1px solid #FDE68A" }}>
            <h4 style={{ fontSize: "13px", fontWeight: 700, color: "#92400E", marginBottom: "4px" }}>
              3. Baseline Time-Series Data Limitation
            </h4>
            <p style={{ fontSize: "12px", color: "#78350F", margin: 0, lineHeight: 1.4 }}>
              The 110 historical documents provide narrative Event-Based Surveillance (EBS) texts, not longitudinal Indicator-Based Surveillance (IBS) case series. When historical observations are scarce (&lt; 3 weekly non-zero points), statistical anomaly detection is blocked (<code>INSUFFICIENT_BASELINE</code>) to prevent false alarms.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
};

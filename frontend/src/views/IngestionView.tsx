import { DocumentSubmitForm } from "../components/ingestion/DocumentSubmitForm";
import type { NavView } from "../components/layout/Sidebar";

interface IngestionViewProps {
  onNavigate: (view: NavView) => void;
}

export const IngestionView = ({ onNavigate }: IngestionViewProps) => {
  return (
    <div style={{ maxWidth: "860px", margin: "0 auto" }}>
      <div style={{ marginBottom: "20px" }}>
        <h2 style={{ fontSize: "20px", fontWeight: 800, color: "var(--text-primary)" }}>
          Ingest Epidemiological Report
        </h2>
        <p style={{ fontSize: "13px", color: "var(--text-secondary)", marginTop: "4px" }}>
          Submit public health bulletins, news dispatches, or lab reports directly into the continuous surveillance pipeline (Phase 11/12).
          Payloads are validated, deduplicated, extracted via clinical NLP, and fused incrementally into active surveillance time series.
        </p>
      </div>

      <DocumentSubmitForm
        onDocumentSubmitted={() => {
          // Document processed successfully
        }}
      />
      <div style={{ marginTop: "16px", textAlign: "right" }}>
        <button
          onClick={() => onNavigate("live")}
          className="btn btn-secondary btn-sm"
        >
          View Live Feed →
        </button>
      </div>
    </div>
  );
};

import { useState } from "react";
import { Send, CheckCircle2, AlertTriangle, Copy, Sparkles, RefreshCcw } from "lucide-react";
import type { DocumentIngestionRequest, DocumentIngestionResponse, SourceType } from "../../types/api";
import { api } from "../../services/api";
import { ErrorBanner } from "../common/ErrorBanner";

interface DocumentSubmitFormProps {
  onDocumentSubmitted?: (res: DocumentIngestionResponse) => void;
}

export const DocumentSubmitForm = ({ onDocumentSubmitted }: DocumentSubmitFormProps) => {
  const [title, setTitle] = useState("");
  const [sourceId, setSourceId] = useState("who_don_feed");
  const [sourceType, setSourceType] = useState<SourceType>("official_bulletin");
  const [publicationDate, setPublicationDate] = useState(new Date().toISOString().slice(0, 16));
  const [text, setText] = useState("");

  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<DocumentIngestionResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  const presets = [
    {
      label: "Nipah Alert (Kerala)",
      title: "Nipah virus outbreak suspected in Kozhikode district",
      source: "who_don_surveillance",
      type: "official_bulletin" as SourceType,
      text: "State health authorities confirmed 8 new cases of Nipah virus disease in Kozhikode on Thursday. Surveillance teams have isolated 42 high-risk contacts.",
    },
    {
      label: "Chandipura Outbreak (Gujarat)",
      title: "Acute encephalitis syndrome cases associated with Chandipura virus",
      source: "idsp_bulletin",
      type: "official_bulletin" as SourceType,
      text: "Health departments recorded 14 suspected cases of Chandipura virus across Sabarkantha district. Two pediatric deaths were reported yesterday.",
    },
    {
      label: "Dengue Surge (Pune)",
      title: "Vector-borne disease surge: Dengue cases in Pune municipal area",
      source: "pune_health_dispatch",
      type: "news_media" as SourceType,
      text: "Civic hospitals registered 45 confirmed cases of Dengue across urban zones in Pune during the past week.",
    },
  ];

  const handleApplyPreset = (preset: typeof presets[0]) => {
    setTitle(preset.title);
    setSourceId(preset.source);
    setSourceType(preset.type);
    setText(preset.text);
    setResult(null);
    setError(null);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!title.trim() || !text.trim()) {
      setError("Title and Report Text are required fields.");
      return;
    }

    setLoading(true);
    setError(null);
    setResult(null);

    const payload: DocumentIngestionRequest = {
      title: title.trim(),
      source_id: sourceId.trim() || "api_analyst_desk",
      source_type: sourceType,
      text: text.trim(),
      publication_date: new Date(publicationDate).toISOString(),
    };

    try {
      const resp = await api.submitDocument(payload);
      setResult(resp);
      onDocumentSubmitted?.(resp);
    } catch (err: any) {
      setError(err.message || "Document submission failed");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "24px" }}>
      {/* Preset Quick Loaders */}
      <div className="card">
        <div style={{ display: "flex", alignItems: "center", gap: "8px", marginBottom: "12px" }}>
          <Sparkles size={16} style={{ color: "var(--brand-primary)" }} />
          <h4 style={{ fontSize: "14px", fontWeight: 700, color: "var(--text-primary)" }}>
            Analyst Demonstration Scenarios
          </h4>
        </div>
        <p style={{ fontSize: "12px", color: "var(--text-secondary)", marginBottom: "14px" }}>
          Click a scenario to populate clinical dispatch text and observe real-time pipeline ingestion:
        </p>

        <div style={{ display: "flex", gap: "10px", flexWrap: "wrap" }}>
          {presets.map((p) => (
            <button
              key={p.label}
              type="button"
              onClick={() => handleApplyPreset(p)}
              className="btn btn-secondary btn-sm"
              style={{ fontSize: "12px" }}
            >
              <Copy size={12} /> {p.label}
            </button>
          ))}
        </div>
      </div>

      {/* Submission Form */}
      <div className="card">
        <form onSubmit={handleSubmit} style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
          <div className="grid-2">
            <div>
              <label style={{ display: "block", fontSize: "12px", fontWeight: 600, color: "var(--text-secondary)", marginBottom: "6px" }}>
                Document Title *
              </label>
              <input
                type="text"
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                placeholder="e.g. Nipah virus alert in Kozhikode..."
                className="input"
                required
              />
            </div>

            <div>
              <label style={{ display: "block", fontSize: "12px", fontWeight: 600, color: "var(--text-secondary)", marginBottom: "6px" }}>
                Publication Timestamp
              </label>
              <input
                type="datetime-local"
                value={publicationDate}
                onChange={(e) => setPublicationDate(e.target.value)}
                className="input"
              />
            </div>
          </div>

          <div className="grid-2">
            <div>
              <label style={{ display: "block", fontSize: "12px", fontWeight: 600, color: "var(--text-secondary)", marginBottom: "6px" }}>
                Source Feed Identifier
              </label>
              <input
                type="text"
                value={sourceId}
                onChange={(e) => setSourceId(e.target.value)}
                placeholder="e.g. who_don_surveillance"
                className="input"
              />
            </div>

            <div>
              <label style={{ display: "block", fontSize: "12px", fontWeight: 600, color: "var(--text-secondary)", marginBottom: "6px" }}>
                Source Category
              </label>
              <select
                value={sourceType}
                onChange={(e) => setSourceType(e.target.value as SourceType)}
                className="select"
              >
                <option value="official_bulletin">Official Health Bulletin</option>
                <option value="news_media">News Media Report</option>
                <option value="public_syndication">Public Syndication Feed</option>
                <option value="benchmark_corpus">Benchmark Corpus</option>
              </select>
            </div>
          </div>

          <div>
            <label style={{ display: "block", fontSize: "12px", fontWeight: 600, color: "var(--text-secondary)", marginBottom: "6px" }}>
              Public Health Dispatch Text / Narrative *
            </label>
            <textarea
              rows={6}
              value={text}
              onChange={(e) => setText(e.target.value)}
              placeholder="Paste or enter clinical surveillance dispatch content..."
              className="textarea"
              required
            />
          </div>

          <div style={{ display: "flex", justifyContent: "flex-end", gap: "10px" }}>
            <button
              type="submit"
              disabled={loading || !title.trim() || !text.trim()}
              className="btn btn-primary"
            >
              {loading ? (
                <>
                  <RefreshCcw size={14} style={{ animation: "spin 1s linear infinite" }} /> Ingesting...
                </>
              ) : (
                <>
                  <Send size={14} /> Submit to Continuous Pipeline
                </>
              )}
            </button>
          </div>
        </form>
      </div>

      {/* Error Display */}
      {error && <ErrorBanner message={error} onRetry={() => setError(null)} />}

      {/* Ingestion Response Display */}
      {result && (
        <div
          className="card"
          style={{
            borderColor:
              result.status === "accepted"
                ? "rgba(16, 168, 120, 0.4)"
                : result.status === "duplicate_skipped"
                ? "rgba(255, 138, 50, 0.4)"
                : "rgba(240, 68, 98, 0.4)",
            background:
              result.status === "accepted"
                ? "rgba(16, 168, 120, 0.05)"
                : result.status === "duplicate_skipped"
                ? "rgba(255, 138, 50, 0.05)"
                : "rgba(240, 68, 98, 0.05)",
          }}
        >
          <div style={{ display: "flex", alignItems: "center", gap: "10px", marginBottom: "12px" }}>
            {result.status === "accepted" ? (
              <CheckCircle2 size={20} style={{ color: "var(--status-success)" }} />
            ) : (
              <AlertTriangle size={20} style={{ color: "var(--tier-medium)" }} />
            )}
            <div>
              <div style={{ fontSize: "15px", fontWeight: 700, color: "var(--text-primary)", textTransform: "uppercase" }}>
                Pipeline Status: {result.status.replace("_", " ")}
              </div>
              <div style={{ fontSize: "12px", color: "var(--text-secondary)" }}>
                {result.message || "Document processed through continuous surveillance stack."}
              </div>
            </div>
          </div>

          <div className="grid-4" style={{ marginTop: "16px" }}>
            <div className="card" style={{ background: "var(--bg-canvas)", padding: "10px 14px" }}>
              <div style={{ fontSize: "11px", color: "var(--text-secondary)" }}>Alerts Generated</div>
              <div style={{ fontSize: "20px", fontWeight: 800, color: "var(--text-primary)" }}>{result.alerts_generated}</div>
            </div>
            <div className="card" style={{ background: "var(--bg-canvas)", padding: "10px 14px" }}>
              <div style={{ fontSize: "11px", color: "var(--text-secondary)" }}>Fused Events Affected</div>
              <div style={{ fontSize: "20px", fontWeight: 800, color: "var(--text-primary)" }}>{result.fused_events_affected}</div>
            </div>
            <div className="card" style={{ background: "var(--bg-canvas)", padding: "10px 14px" }}>
              <div style={{ fontSize: "11px", color: "var(--text-secondary)" }}>Signals Detected</div>
              <div style={{ fontSize: "20px", fontWeight: 800, color: "var(--text-primary)" }}>{result.signals_generated}</div>
            </div>
            <div className="card" style={{ background: "var(--bg-canvas)", padding: "10px 14px" }}>
              <div style={{ fontSize: "11px", color: "var(--text-secondary)" }}>Weekly Bins Affected</div>
              <div style={{ fontSize: "20px", fontWeight: 800, color: "var(--text-primary)" }}>{result.bins_affected}</div>
            </div>
          </div>

          <div style={{ display: "flex", justifyContent: "space-between", marginTop: "16px", fontSize: "11px", color: "var(--text-muted)" }}>
            <span>Update ID: <code className="code-badge">{result.update_id}</code></span>
            <span>Doc ID: <code className="code-badge">{result.document_id || "None"}</code></span>
            <span>Time: {new Date(result.timestamp).toLocaleTimeString()}</span>
          </div>
        </div>
      )}
    </div>
  );
};

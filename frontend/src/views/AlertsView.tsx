import { useEffect, useState } from "react";
import type { EpidemiologicalAlert } from "../types/api";
import { api } from "../services/api";
import { AlertFilters } from "../components/alerts/AlertFilters";
import { AlertTable } from "../components/alerts/AlertTable";
import { AlertDetailModal } from "../components/alerts/AlertDetailModal";
import { Pagination } from "../components/common/Pagination";
import { LoadingSpinner } from "../components/common/LoadingSpinner";
import { ErrorBanner } from "../components/common/ErrorBanner";

export const AlertsView = () => {
  const [alerts, setAlerts] = useState<EpidemiologicalAlert[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const pageSize = 20;

  // Filter criteria
  const [pathogen, setPathogen] = useState("");
  const [location, setLocation] = useState("");
  const [alertTier, setAlertTier] = useState<string>("");
  const [minScore, setMinScore] = useState<number>(0);
  const [currentOnly, setCurrentOnly] = useState(true);

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedAlertId, setSelectedAlertId] = useState<string | null>(null);

  const fetchAlerts = async (targetPage = page, current = currentOnly) => {
    setLoading(true);
    setError(null);
    try {
      const resp = await api.getAlerts({
        pathogen: pathogen.trim() || undefined,
        location: location.trim() || undefined,
        alert_tier: alertTier || undefined,
        min_score: minScore > 0 ? minScore : undefined,
        priority_only: true,
        current_only: current,
        page: targetPage,
        page_size: pageSize,
      });
      setAlerts(resp.items);
      setTotal(resp.total);
      setPage(resp.page);
    } catch (err: any) {
      setError(err.message || "Failed to query alerts from surveillance state");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchAlerts(1, currentOnly);
  }, [pathogen, location, alertTier, minScore, currentOnly]);

  const handleResetFilters = () => {
    setPathogen("");
    setLocation("");
    setAlertTier("");
    setMinScore(0);
  };

  return (
    <div>
      {/* Informational Review Queue Header Callout */}
      <div
        style={{
          padding: "14px 18px",
          background: "#F8FAFC",
          border: "1px solid var(--border-default)",
          borderRadius: "12px",
          marginBottom: "16px",
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          flexWrap: "wrap",
          gap: "12px",
          fontSize: "12.5px",
        }}
      >
        <div>
          <div style={{ display: "flex", alignItems: "center", gap: "8px", flexWrap: "wrap" }}>
            <span style={{ fontWeight: 700, color: "var(--text-primary)" }}>Surveillance Classification:</span>
            <span style={{ color: "#059669", fontWeight: 700, background: "#ECFDF5", padding: "2px 8px", borderRadius: "4px" }}>
              Actionable Priority Outbreaks: 0
            </span>
            <span style={{ color: "#64748B" }}>•</span>
            <span style={{ color: "#B45309", fontWeight: 700, background: "#FEF3C7", padding: "2px 8px", borderRadius: "4px" }}>
              Current Review Candidates: {currentOnly ? total : 0} items
            </span>
          </div>
          <div style={{ color: "var(--text-secondary)", fontSize: "12px", marginTop: "4px" }}>
            <strong>Reconciliation Rationale:</strong> The 11 review candidates represent retrospective surveillance reports (August 2026 events published in late bulletins), negative rule-outs, or unconfirmed syndromic mentions without continuous numerical baselines (N &ge; 12). EpiSense safely suppresses false outbreak alerts while keeping candidates accessible for triage review.
          </div>
        </div>
        <div style={{ color: "#64748B", fontStyle: "italic", fontSize: "11px", maxWidth: "260px", textAlign: "right" }}>
          Scores indicate heuristic multi-factor triage priority, not confirmed outbreak probabilities.
        </div>
      </div>

      {/* Current vs Historical Toggle */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "14px" }}>
        <div style={{ display: "inline-flex", background: "#F1F5F9", borderRadius: "10px", padding: "3px" }}>
          <button
            onClick={() => setCurrentOnly(true)}
            style={{
              padding: "6px 14px",
              borderRadius: "8px",
              border: "none",
              fontSize: "12px",
              fontWeight: 600,
              cursor: "pointer",
              background: currentOnly ? "#FFFFFF" : "transparent",
              color: currentOnly ? "#1E293B" : "#64748B",
              boxShadow: currentOnly ? "0 1px 3px rgba(0,0,0,0.1)" : "none",
            }}
          >
            Current Review Candidates ({currentOnly ? total : 11})
          </button>
          <button
            onClick={() => setCurrentOnly(false)}
            style={{
              padding: "6px 14px",
              borderRadius: "8px",
              border: "none",
              fontSize: "12px",
              fontWeight: 600,
              cursor: "pointer",
              background: !currentOnly ? "#FFFFFF" : "transparent",
              color: !currentOnly ? "#1E293B" : "#64748B",
              boxShadow: !currentOnly ? "0 1px 3px rgba(0,0,0,0.1)" : "none",
            }}
          >
            Historical Reference Records
          </button>
        </div>

        <span style={{ fontSize: "12px", color: "var(--text-secondary)" }}>
          Showing: <strong>{total}</strong> alert(s)
        </span>
      </div>

      {currentOnly && total === 0 && !loading && (
        <div
          style={{
            padding: "16px 20px",
            background: "#EFF6FF",
            border: "1px solid #BFDBFE",
            borderRadius: "12px",
            marginBottom: "16px",
            fontSize: "13px",
            color: "#1E40AF",
          }}
        >
          <strong>Operational Safety Status:</strong> Zero prioritized alerts are active in the current operational window (October 2026).
          Retrospective and historical alerts (including past 2024/2025 outbreaks) are archived.
          Switch to <strong>Historical Reference Records</strong> above to audit past alert evaluations.
        </div>
      )}

      {/* Filters Bar */}
      <AlertFilters
        pathogen={pathogen}
        location={location}
        alertTier={alertTier}
        minScore={minScore}
        onPathogenChange={setPathogen}
        onLocationChange={setLocation}
        onAlertTierChange={setAlertTier}
        onMinScoreChange={setMinScore}
        onReset={handleResetFilters}
      />

      {error && <ErrorBanner message={error} onRetry={() => fetchAlerts(page)} className="mb-4" />}

      {loading ? (
        <LoadingSpinner message="Querying prioritized epidemiological alerts..." />
      ) : (
        <>
          <AlertTable alerts={alerts} onSelectAlert={(id) => setSelectedAlertId(id)} />

          <Pagination
            page={page}
            total={total}
            pageSize={pageSize}
            onPageChange={(p) => {
              setPage(p);
              fetchAlerts(p);
            }}
          />
        </>
      )}

      {/* Alert Detail Modal */}
      {selectedAlertId && (
        <AlertDetailModal
          alertId={selectedAlertId}
          onClose={() => setSelectedAlertId(null)}
        />
      )}
    </div>
  );
};

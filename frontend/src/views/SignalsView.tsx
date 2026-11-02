import React, { useEffect, useState } from "react";
import { Filter, Search, RotateCcw } from "lucide-react";
import type { SignalObservation } from "../types/api";
import { api } from "../services/api";
import { SignalTable } from "../components/signals/SignalTable";
import { Pagination } from "../components/common/Pagination";
import { LoadingSpinner } from "../components/common/LoadingSpinner";
import { ErrorBanner } from "../components/common/ErrorBanner";

export const SignalsView: React.FC = () => {
  const [signals, setSignals] = useState<SignalObservation[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const pageSize = 20;

  // Filters
  const [pathogen, setPathogen] = useState("");
  const [location, setLocation] = useState("");
  const [signalLevel, setSignalLevel] = useState("");
  const [currentOnly, setCurrentOnly] = useState(true);

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchSignals = async (targetPage = page, current = currentOnly) => {
    setLoading(true);
    setError(null);
    try {
      const resp = await api.getSignals({
        pathogen: pathogen.trim() || undefined,
        location: location.trim() || undefined,
        signal_level: signalLevel || undefined,
        priority_only: true,
        current_only: current,
        page: targetPage,
        page_size: pageSize,
      });
      setSignals(resp.items);
      setTotal(resp.total);
      setPage(resp.page);
    } catch (err: any) {
      setError(err.message || "Failed to retrieve early warning signals");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchSignals(1, currentOnly);
  }, [pathogen, location, signalLevel, currentOnly]);

  const handleReset = () => {
    setPathogen("");
    setLocation("");
    setSignalLevel("");
  };

  return (
    <div>
      {/* Filters Bar */}
      <div
        className="card"
        style={{
          padding: "16px 20px",
          marginBottom: "20px",
          display: "flex",
          flexWrap: "wrap",
          gap: "14px",
          alignItems: "center",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: "8px", color: "var(--brand-primary)" }}>
          <Filter size={16} />
          <span style={{ fontSize: "13px", fontWeight: 700, color: "var(--text-primary)" }}>Filter Signals</span>
        </div>

        {/* Current vs Historical Window Toggle */}
        <div style={{ display: "inline-flex", background: "#F1F5F9", borderRadius: "10px", padding: "3px" }}>
          <button
            onClick={() => setCurrentOnly(true)}
            style={{
              padding: "6px 12px",
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
            Current Window (Oct 2026)
          </button>
          <button
            onClick={() => setCurrentOnly(false)}
            style={{
              padding: "6px 12px",
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
            Historical Archival Signals
          </button>
        </div>

        <div style={{ flex: "1 1 180px", position: "relative" }}>
          <input
            type="text"
            placeholder="Pathogen (e.g. Dengue, Cholera)..."
            value={pathogen}
            onChange={(e) => setPathogen(e.target.value)}
            className="input"
            style={{ paddingLeft: "32px" }}
          />
          <Search size={14} style={{ position: "absolute", left: "10px", top: "11px", color: "var(--text-tertiary)" }} />
        </div>

        <div style={{ flex: "1 1 160px" }}>
          <input
            type="text"
            placeholder="Location (e.g. Kozhikode)..."
            value={location}
            onChange={(e) => setLocation(e.target.value)}
            className="input"
          />
        </div>

        <div style={{ width: "160px" }}>
          <select
            value={signalLevel}
            onChange={(e) => setSignalLevel(e.target.value)}
            className="select"
          >
            <option value="">All Signal Levels</option>
            <option value="strong_signal">Strong Signal</option>
            <option value="signal">Signal</option>
            <option value="watch">Watch</option>
            <option value="noise">Noise</option>
          </select>
        </div>

        <button onClick={handleReset} className="btn btn-secondary btn-sm" title="Reset Filters">
          <RotateCcw size={13} /> Reset
        </button>
      </div>

      {currentOnly && total === 0 && !loading && (
        <div
          style={{
            padding: "16px 20px",
            background: "#EFF6FF",
            border: "1px solid #BFDBFE",
            borderRadius: "12px",
            marginBottom: "20px",
            fontSize: "13px",
            color: "#1E40AF",
          }}
        >
          <strong>Operational Safety Status:</strong> No statistical anomaly signals are active for the current operational window (October 2026).
          All 8 canonical priority pathogen baseline series have fewer than 12 consecutive observations and are cleanly suppressed to prevent ungrounded false alarms.
          Toggle to <strong>Historical Archival Signals</strong> above to audit retrospective signal performance.
        </div>
      )}

      {error && <ErrorBanner message={error} onRetry={() => fetchSignals(page)} className="mb-4" />}

      {loading ? (
        <LoadingSpinner message="Evaluating statistical aberration signals..." />
      ) : (
        <>
          <SignalTable signals={signals} />

          <Pagination
            page={page}
            total={total}
            pageSize={pageSize}
            onPageChange={(p) => {
              setPage(p);
              fetchSignals(p);
            }}
          />
        </>
      )}
    </div>
  );
};

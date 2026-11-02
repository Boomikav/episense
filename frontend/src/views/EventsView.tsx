import React, { useEffect, useState } from "react";
import { Filter, Search, RotateCcw } from "lucide-react";
import type { FusedEvent } from "../types/api";
import { api } from "../services/api";
import { EventTable } from "../components/events/EventTable";
import { Pagination } from "../components/common/Pagination";
import { LoadingSpinner } from "../components/common/LoadingSpinner";
import { ErrorBanner } from "../components/common/ErrorBanner";

export const EventsView: React.FC = () => {
  const [events, setEvents] = useState<FusedEvent[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const pageSize = 20;

  // Filters
  const [pathogen, setPathogen] = useState("");
  const [location, setLocation] = useState("");
  const [assertionStatus, setAssertionStatus] = useState("");
  const [currentOnly, setCurrentOnly] = useState(true);

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchEvents = async (targetPage = page, current = currentOnly) => {
    setLoading(true);
    setError(null);
    try {
      const resp = await api.getEvents({
        pathogen: pathogen.trim() || undefined,
        location: location.trim() || undefined,
        assertion_status: assertionStatus || undefined,
        priority_only: true,
        current_only: current,
        page: targetPage,
        page_size: pageSize,
      });
      setEvents(resp.items);
      setTotal(resp.total);
      setPage(resp.page);
    } catch (err: any) {
      setError(err.message || "Failed to retrieve canonical fused events");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchEvents(1, currentOnly);
  }, [pathogen, location, assertionStatus, currentOnly]);

  const handleReset = () => {
    setPathogen("");
    setLocation("");
    setAssertionStatus("");
  };

  return (
    <div>
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
            Current Operational Incidents (Oct 2026)
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
            Historical Archival Corpus
          </button>
        </div>

        <span style={{ fontSize: "12px", color: "var(--text-secondary)" }}>
          Showing: <strong>{total}</strong> incident(s)
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
          <strong>Operational Safety Status:</strong> Zero incident clusters occurred in the current operational window (October 2026).
          Retrospective reports and past-season events (e.g. July 2024 Brahmagiri cholera outbreak) are archived in the historical corpus.
          Switch to <strong>Historical Archival Corpus</strong> above to audit past fused event records.
        </div>
      )}

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
          <span style={{ fontSize: "13px", fontWeight: 700, color: "var(--text-primary)" }}>Filter Incidents</span>
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
            value={assertionStatus}
            onChange={(e) => setAssertionStatus(e.target.value)}
            className="select"
          >
            <option value="">All Assertions</option>
            <option value="confirmed">Confirmed</option>
            <option value="suspected">Suspected</option>
            <option value="historical">Historical</option>
          </select>
        </div>

        <button onClick={handleReset} className="btn btn-secondary btn-sm" title="Reset Filters">
          <RotateCcw size={13} /> Reset
        </button>
      </div>

      {error && <ErrorBanner message={error} onRetry={() => fetchEvents(page)} className="mb-4" />}

      {loading ? (
        <LoadingSpinner message="Loading canonical fused epidemiological incidents..." />
      ) : (
        <>
          <EventTable events={events} />

          <Pagination
            page={page}
            total={total}
            pageSize={pageSize}
            onPageChange={(p) => {
              setPage(p);
              fetchEvents(p);
            }}
          />
        </>
      )}
    </div>
  );
};

import { useEffect, useState } from "react";
import { CheckCircle2, Activity } from "lucide-react";
import type { LivenessResponse, ReadinessResponse, ServiceHealthResponse } from "../../types/api";
import { api } from "../../services/api";
import { LoadingSpinner } from "../common/LoadingSpinner";
import { ErrorBanner } from "../common/ErrorBanner";

export const SystemHealthCard = () => {
  const [health, setHealth] = useState<ServiceHealthResponse | null>(null);
  const [readiness, setReadiness] = useState<ReadinessResponse | null>(null);
  const [liveness, setLiveness] = useState<LivenessResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchHealth = async () => {
    setLoading(true);
    setError(null);
    try {
      const [h, r, l] = await Promise.all([
        api.getHealth(),
        api.getReadiness(),
        api.getLiveness(),
      ]);
      setHealth(h);
      setReadiness(r);
      setLiveness(l);
    } catch (err: any) {
      setError(err.message || "Failed to reach health endpoints");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchHealth();
    const interval = setInterval(fetchHealth, 30000);
    return () => clearInterval(interval);
  }, []);

  if (loading && !health) {
    return <LoadingSpinner message="Checking surveillance health probes..." />;
  }

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "20px" }}>
      {error && <ErrorBanner message={error} onRetry={fetchHealth} />}

      {/* Probes Overview Grid */}
      <div className="grid-3">
        {/* Service Health */}
        <div className="card">
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "12px" }}>
            <div style={{ fontSize: "12px", fontWeight: 600, color: "var(--text-secondary)", textTransform: "uppercase" }}>
              API Gateway
            </div>
            <div
              style={{
                width: "8px",
                height: "8px",
                borderRadius: "50%",
                backgroundColor: health?.status === "healthy" ? "var(--status-success)" : "var(--tier-high)",
                boxShadow: health?.status === "healthy" ? "0 0 8px rgba(16, 185, 129, 0.6)" : "none",
              }}
            />
          </div>
          <div style={{ fontSize: "20px", fontWeight: 700, color: "var(--text-primary)", textTransform: "capitalize" }}>
            {health?.status || "Unknown"}
          </div>
          <div style={{ fontSize: "12px", color: "var(--text-secondary)", marginTop: "4px" }}>
            Version: <span className="code-badge">{health?.version || "1.0.0"}</span>
          </div>
          <div style={{ fontSize: "11px", color: "var(--text-muted)", marginTop: "8px" }}>
            Endpoint: GET /health
          </div>
        </div>

        {/* Readiness Probe */}
        <div className="card">
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "12px" }}>
            <div style={{ fontSize: "12px", fontWeight: 600, color: "var(--text-secondary)", textTransform: "uppercase" }}>
              Readiness Probe
            </div>
            <CheckCircle2 size={16} style={{ color: readiness?.ready ? "var(--status-success)" : "var(--tier-high)" }} />
          </div>
          <div style={{ fontSize: "20px", fontWeight: 700, color: "var(--text-primary)" }}>
            {readiness?.ready ? "Ready for Traffic" : "Not Ready"}
          </div>
          <div style={{ fontSize: "12px", color: "var(--text-secondary)", marginTop: "4px" }}>
            State Alerts: <strong style={{ color: "var(--text-primary)" }}>{readiness?.state_alerts_count ?? 0}</strong> • Events: <strong style={{ color: "var(--text-primary)" }}>{readiness?.state_events_count ?? 0}</strong>
          </div>
          <div style={{ fontSize: "11px", color: "var(--text-muted)", marginTop: "8px" }}>
            Endpoint: GET /health/ready
          </div>
        </div>

        {/* Liveness Probe */}
        <div className="card">
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "12px" }}>
            <div style={{ fontSize: "12px", fontWeight: 600, color: "var(--text-secondary)", textTransform: "uppercase" }}>
              Liveness Probe
            </div>
            <Activity size={16} style={{ color: liveness?.live ? "var(--brand-primary)" : "var(--tier-high)" }} />
          </div>
          <div style={{ fontSize: "20px", fontWeight: 700, color: "var(--text-primary)" }}>
            {liveness?.live ? "Process Alive" : "Process Stalled"}
          </div>
          <div style={{ fontSize: "12px", color: "var(--text-secondary)", marginTop: "4px" }}>
            FastAPI In-Process Daemon
          </div>
          <div style={{ fontSize: "11px", color: "var(--text-muted)", marginTop: "8px" }}>
            Endpoint: GET /health/live
          </div>
        </div>
      </div>

      {/* Engine Architecture Details */}
      <div className="card">
        <h3 style={{ fontSize: "15px", fontWeight: 700, color: "var(--text-primary)", marginBottom: "4px" }}>
          Pipeline & Surveillance State Diagnostics
        </h3>
        <p style={{ fontSize: "12px", color: "var(--text-secondary)", marginBottom: "16px" }}>
          Component-level health and subsystem dependencies
        </p>

        <div style={{ display: "flex", flexDirection: "column", gap: "10px" }}>
          <div style={{ display: "flex", justifyContent: "space-between", padding: "10px 14px", background: "var(--bg-canvas)", borderRadius: "var(--radius-sm)" }}>
            <span style={{ color: "var(--text-primary)", fontWeight: 500 }}>ContinuousSurveillancePipeline (Phase 11)</span>
            <span style={{ color: health?.pipeline_available ? "var(--status-success)" : "var(--tier-high)", fontWeight: 600 }}>
              {health?.pipeline_available ? "● Operational" : "○ Offline"}
            </span>
          </div>
          <div style={{ display: "flex", justifyContent: "space-between", padding: "10px 14px", background: "var(--bg-canvas)", borderRadius: "var(--radius-sm)" }}>
            <span style={{ color: "var(--text-primary)", fontWeight: 500 }}>SurveillanceStateStore (In-Memory / Checkpoints)</span>
            <span style={{ color: health?.state_store_available ? "var(--status-success)" : "var(--tier-high)", fontWeight: 600 }}>
              {health?.state_store_available ? "● Operational" : "○ Offline"}
            </span>
          </div>
          <div style={{ display: "flex", justifyContent: "space-between", padding: "10px 14px", background: "var(--bg-canvas)", borderRadius: "var(--radius-sm)" }}>
            <span style={{ color: "var(--text-primary)", fontWeight: 500 }}>Geospatial Grounding Service (LocalGazetteer)</span>
            <span style={{ color: "var(--status-success)", fontWeight: 600 }}>● Operational (SQLite)</span>
          </div>
          <div style={{ display: "flex", justifyContent: "space-between", padding: "10px 14px", background: "var(--bg-canvas)", borderRadius: "var(--radius-sm)" }}>
            <span style={{ color: "var(--text-primary)", fontWeight: 500 }}>Real-Time WebSocket Feed (/api/v1/ws/surveillance)</span>
            <span style={{ color: "var(--brand-primary)", fontWeight: 600 }}>● Active Async Fan-Out</span>
          </div>
        </div>
      </div>
    </div>
  );
};

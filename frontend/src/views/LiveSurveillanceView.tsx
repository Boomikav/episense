import { useEffect, useState } from "react";
import { Radio, Filter, RotateCcw, AlertOctagon, Activity, Layers, CheckCircle2 } from "lucide-react";
import type { AlertTier, SurveillanceEventUpdate } from "../types/api";
import { wsService, type ConnectionStatus } from "../services/websocket";
import { AlertDetailModal } from "../components/alerts/AlertDetailModal";

export const LiveSurveillanceView = () => {
  const [updates, setUpdates] = useState<SurveillanceEventUpdate[]>([]);
  const [connectionStatus, setConnectionStatus] = useState<ConnectionStatus>("disconnected");

  // Subscription Filters
  const [filterPathogen, setFilterPathogen] = useState("");
  const [filterTier, setFilterTier] = useState<AlertTier | "">("");
  const [filterMinScore, setFilterMinScore] = useState<number>(0);

  const [selectedAlertId, setSelectedAlertId] = useState<string | null>(null);

  useEffect(() => {
    // Connect WebSocket
    wsService.connect();

    const unsubEvent = wsService.onEvent((newUpdate) => {
      setUpdates((prev) => [newUpdate, ...prev.slice(0, 99)]); // Keep last 100 updates
    });

    const unsubStatus = wsService.onStatusChange((status) => {
      setConnectionStatus(status);
    });

    return () => {
      unsubEvent();
      unsubStatus();
    };
  }, []);

  const handleApplyFilter = () => {
    wsService.setSubscriptionFilter({
      pathogen: filterPathogen.trim() || undefined,
      alert_tier: filterTier || undefined,
      min_score: filterMinScore > 0 ? filterMinScore : undefined,
    });
  };

  const handleResetFilter = () => {
    setFilterPathogen("");
    setFilterTier("");
    setFilterMinScore(0);
    wsService.clearSubscriptionFilter();
  };

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "20px" }}>
      {/* Real-Time Feed Header Bar */}
      <div
        className="card"
        style={{
          background: "linear-gradient(135deg, #FAF8F5 0%, #FFFFFF 100%)",
          border: "1px solid var(--border-default)",
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          flexWrap: "wrap",
          gap: "14px",
          padding: "16px 20px",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
          <div
            style={{
              padding: "10px",
              borderRadius: "var(--radius-sm)",
              background:
                connectionStatus === "connected"
                  ? "rgba(16, 168, 120, 0.12)"
                  : "rgba(255, 138, 50, 0.12)",
              color:
                connectionStatus === "connected"
                  ? "var(--status-success)"
                  : "var(--tier-medium)",
              display: "flex",
            }}
          >
            <Radio size={20} />
          </div>
          <div>
            <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
              <h3 style={{ fontSize: "16px", fontWeight: 700, color: "var(--text-primary)" }}>
                Continuous Surveillance Stream
              </h3>
              {connectionStatus === "connected" && <span className="live-dot" />}
            </div>
            <div style={{ fontSize: "12px", color: "var(--text-secondary)" }}>
              Channel: <code className="code-badge">WS /api/v1/ws/surveillance</code> • Status:{" "}
              <strong style={{ color: connectionStatus === "connected" ? "var(--status-success)" : "var(--text-primary)", textTransform: "capitalize" }}>
                {connectionStatus}
              </strong>
            </div>
          </div>
        </div>

        <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
          {connectionStatus !== "connected" && (
            <button onClick={() => wsService.connect()} className="btn btn-primary btn-sm">
              Reconnect Feed
            </button>
          )}
          <button onClick={() => setUpdates([])} className="btn btn-secondary btn-sm">
            Clear Feed
          </button>
        </div>
      </div>

      {/* Subscription Filter Controls */}
      <div
        className="card"
        style={{
          padding: "14px 18px",
          display: "flex",
          alignItems: "center",
          gap: "12px",
          flexWrap: "wrap",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: "6px", color: "var(--brand-primary)", fontSize: "12px", fontWeight: 700 }}>
          <Filter size={14} /> Topic Subscription:
        </div>

        <div style={{ flex: "1 1 160px" }}>
          <input
            type="text"
            placeholder="Subscribe to pathogen (e.g. Nipah)..."
            value={filterPathogen}
            onChange={(e) => setFilterPathogen(e.target.value)}
            className="input"
            style={{ padding: "6px 10px", fontSize: "12px" }}
          />
        </div>

        <div style={{ width: "130px" }}>
          <select
            value={filterTier}
            onChange={(e) => setFilterTier(e.target.value as AlertTier)}
            className="select"
            style={{ padding: "6px 10px", fontSize: "12px" }}
          >
            <option value="">All Tiers</option>
            <option value="high">High Tier</option>
            <option value="medium">Medium Tier</option>
            <option value="low">Low Tier</option>
          </select>
        </div>

        <button onClick={handleApplyFilter} className="btn btn-primary btn-sm">
          Apply Filter
        </button>

        <button onClick={handleResetFilter} className="btn btn-secondary btn-sm" title="Clear Filters">
          <RotateCcw size={12} />
        </button>
      </div>

      {/* Activity Feed */}
      <div className="card">
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "16px" }}>
          <h4 style={{ fontSize: "14px", fontWeight: 700, color: "var(--text-primary)" }}>
            Live Epidemiological Event Log ({updates.length} Received)
          </h4>
          <span style={{ fontSize: "11px", color: "var(--text-muted)" }}>
            Auto-scrolling streaming buffer
          </span>
        </div>

        {updates.length === 0 ? (
          <div
            style={{
              padding: "48px 24px",
              textAlign: "center",
              color: "var(--text-tertiary)",
              display: "flex",
              flexDirection: "column",
              alignItems: "center",
              gap: "8px",
            }}
          >
            <Radio size={28} style={{ color: "var(--text-muted)" }} />
            <div style={{ color: "var(--text-primary)", fontWeight: 600, fontSize: "14px" }}>
              Waiting for incoming surveillance dispatches...
            </div>
            <div style={{ fontSize: "12px", maxWidth: "420px" }}>
              Submit a clinical bulletin via the <strong>Submit Report</strong> view or simulate an ingestion dispatch to observe live event fan-out.
            </div>
          </div>
        ) : (
          <div style={{ display: "flex", flexDirection: "column", gap: "10px" }}>
            {updates.map((up) => {
              const hasAlerts = up.alerts_generated.length > 0;
              return (
                <div
                  key={up.update_id}
                  style={{
                    padding: "14px 18px",
                    borderRadius: "var(--radius-sm)",
                    background: "var(--bg-canvas)",
                    border: "1px solid",
                    borderColor: hasAlerts ? "rgba(240, 68, 98, 0.3)" : "var(--border-subtle)",
                    display: "flex",
                    justifyContent: "space-between",
                    alignItems: "flex-start",
                    flexWrap: "wrap",
                    gap: "12px",
                  }}
                >
                  <div style={{ display: "flex", alignItems: "flex-start", gap: "12px" }}>
                    <div
                      style={{
                        padding: "8px",
                        borderRadius: "var(--radius-sm)",
                        background: hasAlerts ? "rgba(240, 68, 98, 0.12)" : "rgba(112, 71, 245, 0.12)",
                        color: hasAlerts ? "var(--tier-critical)" : "var(--brand-primary)",
                        marginTop: "2px",
                      }}
                    >
                      {hasAlerts ? <AlertOctagon size={18} /> : <CheckCircle2 size={18} />}
                    </div>

                    <div>
                      <div style={{ display: "flex", alignItems: "center", gap: "8px", marginBottom: "4px" }}>
                        <span style={{ fontWeight: 700, color: "var(--text-primary)", fontSize: "13px" }}>
                          {up.message || "Surveillance Update"}
                        </span>
                        <span className={`badge badge-${up.status === "accepted" ? "success" : "medium"}`} style={{ fontSize: "9px" }}>
                          {up.status}
                        </span>
                      </div>

                      <div style={{ fontSize: "12px", color: "var(--text-secondary)", display: "flex", gap: "14px", flexWrap: "wrap" }}>
                        <span>
                          <Layers size={12} style={{ display: "inline", marginRight: "4px" }} />
                          {up.fused_events_affected.length} Fused Incidents
                        </span>
                        <span>
                          <Activity size={12} style={{ display: "inline", marginRight: "4px" }} />
                          {up.signals_generated.length} Signals
                        </span>
                        <span>
                          <AlertOctagon size={12} style={{ display: "inline", marginRight: "4px" }} />
                          {up.alerts_generated.length} Alerts
                        </span>
                      </div>

                      {/* Clickable alerts generated */}
                      {hasAlerts && (
                        <div style={{ display: "flex", gap: "6px", marginTop: "8px", flexWrap: "wrap" }}>
                          {up.alerts_generated.map((aid) => (
                            <button
                              key={aid}
                              onClick={() => setSelectedAlertId(aid)}
                              className="btn btn-secondary btn-sm"
                              style={{ fontSize: "10px", padding: "2px 8px" }}
                            >
                              Inspect Alert: {aid.slice(0, 8)}...
                            </button>
                          ))}
                        </div>
                      )}
                    </div>
                  </div>

                  <div style={{ textAlign: "right", fontSize: "11px", color: "var(--text-tertiary)" }}>
                    <div>{new Date(up.timestamp).toLocaleTimeString()}</div>
                    <div style={{ fontFamily: "var(--font-mono)", fontSize: "10px", marginTop: "2px" }}>
                      ID: {up.update_id.slice(0, 8)}
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>

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

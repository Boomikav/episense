import { Shield } from "lucide-react";
import type { SignalObservation } from "../../types/api";
import { SignalLevelBadge } from "../common/Badge";

interface SignalTableProps {
  signals: SignalObservation[];
}

export const SignalTable = ({ signals }: SignalTableProps) => {
  if (signals.length === 0) {
    return (
      <div className="card" style={{ textAlign: "center", padding: "40px", color: "var(--text-tertiary)" }}>
        No early warning signals found for the current query.
      </div>
    );
  }

  return (
    <div className="card" style={{ padding: "0", overflow: "hidden" }}>
      <div style={{ overflowX: "auto" }}>
        <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "13px", textAlign: "left" }}>
          <thead>
            <tr
              style={{
                borderBottom: "1px solid var(--border-default)",
                background: "var(--bg-canvas)",
                color: "var(--text-secondary)",
                fontSize: "11px",
                textTransform: "uppercase",
                letterSpacing: "0.05em",
              }}
            >
              <th style={{ padding: "12px 16px" }}>Pathogen / Location</th>
              <th style={{ padding: "12px 16px" }}>Signal Classification</th>
              <th style={{ padding: "12px 16px", textAlign: "center" }}>Observed</th>
              <th style={{ padding: "12px 16px", textAlign: "center" }}>Baseline</th>
              <th style={{ padding: "12px 16px", textAlign: "center" }}>Deviation</th>
              <th style={{ padding: "12px 16px" }}>Detection Algorithm</th>
              <th style={{ padding: "12px 16px" }}>Baseline Reliability</th>
              <th style={{ padding: "12px 16px" }}>Surveillance Week</th>
            </tr>
          </thead>
          <tbody>
            {signals.map((s) => {
              const isInsufficient =
                s.reliability_status === "insufficient_history" ||
                s.reliability_status === "insufficient_baseline" ||
                s.reliability_status === "incompatible_granularity" ||
                s.reliability_status === "sparse_history" ||
                s.reliability_status === "not_evaluable" ||
                s.detection_method === "suppressed_insufficient_baseline";

              return (
                <tr
                  key={s.signal_id}
                  style={{
                    borderBottom: "1px solid var(--border-subtle)",
                    transition: "background 0.15s ease",
                  }}
                  onMouseEnter={(el) => (el.currentTarget.style.backgroundColor = "var(--bg-surface-2)")}
                  onMouseLeave={(el) => (el.currentTarget.style.backgroundColor = "transparent")}
                >
                  <td style={{ padding: "14px 16px" }}>
                    <div style={{ fontWeight: 700, color: "var(--text-primary)", textTransform: "capitalize" }}>
                      {s.disease_key}
                    </div>
                    <div style={{ fontSize: "12px", color: "var(--text-secondary)", textTransform: "capitalize" }}>
                      {s.geo_key}
                    </div>
                  </td>

                  <td style={{ padding: "14px 16px" }}>
                    {isInsufficient ? (
                      <span
                        style={{
                          fontSize: "11px",
                          fontWeight: 700,
                          padding: "3px 8px",
                          borderRadius: "6px",
                          background: "#F1F5F9",
                          color: "#64748B",
                          border: "1px solid #CBD5E1",
                        }}
                      >
                        SUPPRESSED
                      </span>
                    ) : (
                      <SignalLevelBadge level={s.signal_level} />
                    )}
                  </td>

                  <td style={{ padding: "14px 16px", textAlign: "center", fontWeight: 700, color: "var(--text-primary)", fontFamily: "var(--font-mono)" }}>
                    {s.observed_value !== null && s.observed_value !== undefined ? (
                      s.observed_value
                    ) : (
                      <span style={{ fontSize: "11.5px", color: "#94a3b8", fontWeight: 500, fontStyle: "italic" }}>
                        Not reported
                      </span>
                    )}
                  </td>

                  <td style={{ padding: "14px 16px", textAlign: "center", color: "var(--text-secondary)", fontFamily: "var(--font-mono)" }}>
                    {isInsufficient ? (
                      <span style={{ color: "var(--text-tertiary)", fontStyle: "italic", fontSize: "11px" }}>— (Absent)</span>
                    ) : (
                      s.expected_value.toFixed(1)
                    )}
                  </td>

                  <td style={{ padding: "14px 16px", textAlign: "center" }}>
                    {isInsufficient ? (
                      <span style={{ color: "var(--text-tertiary)", fontStyle: "italic", fontSize: "11px" }}>— (Suppressed)</span>
                    ) : (
                      <div
                        style={{
                          fontFamily: "var(--font-mono)",
                          fontWeight: 700,
                          color:
                            (s.standardized_score ?? s.deviation) >= 3.0
                              ? "var(--tier-critical)"
                              : (s.standardized_score ?? s.deviation) >= 2.0
                              ? "var(--tier-high)"
                              : "var(--brand-primary)",
                        }}
                      >
                        {s.standardized_score != null
                          ? `${s.standardized_score >= 0 ? "+" : ""}${s.standardized_score.toFixed(2)}σ`
                          : `${s.deviation >= 0 ? "+" : ""}${s.deviation.toFixed(2)}σ`}
                      </div>
                    )}
                  </td>

                  <td style={{ padding: "14px 16px", fontSize: "12px" }}>
                    {isInsufficient ? (
                      <span className="code-badge" style={{ opacity: 0.75, fontSize: "11px" }}>SUPPRESSED</span>
                    ) : (
                      <span className="code-badge">{s.detection_method.toUpperCase()}</span>
                    )}
                  </td>

                <td style={{ padding: "14px 16px" }}>
                  {s.reliability_status === "insufficient_history" ||
                  s.reliability_status === "insufficient_baseline" ||
                  s.reliability_status === "sparse_history" ||
                  s.reliability_status === "incompatible_granularity" ||
                  s.reliability_status === "conflicting_data" ||
                  s.reliability_status === "not_evaluable" ? (
                    <span
                      style={{
                        fontSize: "11px",
                        fontWeight: 600,
                        padding: "3px 8px",
                        borderRadius: "6px",
                        background: "#FEF3C7",
                        color: "#92400E",
                        border: "1px solid #FDE68A",
                        display: "inline-flex",
                        alignItems: "center",
                        gap: "4px",
                      }}
                      title={
                        s.downgraded_reason ||
                        (s.reliability_status === "incompatible_granularity"
                          ? "Incompatible spatial or temporal granularity: Historical units do not match target series."
                          : s.reliability_status === "conflicting_data"
                          ? "Conflicting data: Target period contains discrepant quantities from independent sources."
                          : s.reliability_status === "sparse_history"
                          ? "Sparse baseline: Fewer than 2 non-zero historical periods observed. Quasi-Poisson variance calculation suppressed."
                          : "Insufficient baseline data: Historical series has fewer than 3 periods. Statistical anomaly detection is suppressed to prevent false alarms.")
                      }
                    >
                      <Shield size={12} />
                      {s.reliability_status === "incompatible_granularity"
                        ? "INCOMPATIBLE GRANULARITY"
                        : s.reliability_status === "conflicting_data"
                        ? "CONFLICTING DATA"
                        : s.reliability_status === "sparse_history"
                        ? "SPARSE HISTORY (<2 NON-ZERO)"
                        : "INSUFFICIENT_BASELINE"}
                    </span>
                  ) : (
                    <span
                      style={{
                        fontSize: "12px",
                        color:
                          s.reliability_status === "stable_baseline"
                            ? "var(--status-success)"
                            : "var(--tier-medium)",
                        display: "inline-flex",
                        alignItems: "center",
                        gap: "4px",
                      }}
                    >
                      <Shield size={12} />
                      {s.reliability_status.replace("_", " ").toUpperCase()}
                    </span>
                  )}
                </td>

                <td style={{ padding: "14px 16px", fontSize: "12px", color: "var(--text-secondary)" }}>
                  {new Date(s.target_period_start).toLocaleDateString()}
                </td>
              </tr>
            );
          })}
        </tbody>
        </table>
      </div>
    </div>
  );
};

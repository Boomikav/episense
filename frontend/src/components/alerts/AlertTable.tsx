import { AlertTriangle, ChevronRight } from "lucide-react";
import type { EpidemiologicalAlert } from "../../types/api";
import { AlertTierBadge, RecommendedActionBadge, ThreatTierBadge } from "../common/Badge";

interface AlertTableProps {
  alerts: EpidemiologicalAlert[];
  onSelectAlert: (alertId: string) => void;
}

export const AlertTable = ({ alerts, onSelectAlert }: AlertTableProps) => {
  if (alerts.length === 0) {
    return (
      <div className="card" style={{ textAlign: "center", padding: "48px", color: "#64748B" }}>
        No epidemiological alerts match the current filter criteria.
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
                background: "var(--bg-surface-2)",
                color: "#64748B",
                fontSize: "11px",
                fontWeight: 700,
                textTransform: "uppercase",
                letterSpacing: "0.05em",
              }}
            >
              <th style={{ padding: "14px 18px" }}>Pathogen / Syndrome</th>
              <th style={{ padding: "14px 18px" }}>Location</th>
              <th style={{ padding: "14px 18px" }}>Alert Tier</th>
              <th style={{ padding: "14px 18px" }}>Decision Category</th>
              <th style={{ padding: "14px 18px" }}>Triage Review</th>
              <th style={{ padding: "14px 18px", textAlign: "center" }}>Sources</th>
              <th style={{ padding: "14px 18px" }}>Reporting Window End (IST)</th>
              <th style={{ padding: "14px 18px", textAlign: "right" }}>Inspect</th>
            </tr>
          </thead>
          <tbody>
            {alerts.map((a) => {
              const scoreVal = a.event_triage_score ?? a.composite_score;
              const isHigh = scoreVal >= 0.8;
              const isMedium = scoreVal >= 0.65;
              const scoreColor = isHigh ? "#F04462" : isMedium ? "#FF8A32" : "#12B8B0";

              return (
                <tr
                  key={a.alert_id}
                  onClick={() => onSelectAlert(a.alert_id)}
                  style={{
                    borderBottom: "1px solid var(--border-subtle)",
                    cursor: "pointer",
                    transition: "background 0.15s ease",
                  }}
                  onMouseEnter={(e) => (e.currentTarget.style.backgroundColor = "var(--bg-canvas)")}
                  onMouseLeave={(e) => (e.currentTarget.style.backgroundColor = "transparent")}
                >
                  <td style={{ padding: "14px 18px" }}>
                    <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
                      <div
                        style={{
                          width: "32px",
                          height: "32px",
                          borderRadius: "8px",
                          background:
                            a.alert_tier === "high"
                              ? "#FEECEF"
                              : a.alert_tier === "medium"
                              ? "#FFF2E8"
                              : "#F1EDFD",
                          color:
                            a.alert_tier === "high"
                              ? "#F04462"
                              : a.alert_tier === "medium"
                              ? "#FF8A32"
                              : "#7047F5",
                          display: "flex",
                          alignItems: "center",
                          justifyContent: "center",
                          flexShrink: 0,
                        }}
                      >
                        <AlertTriangle size={16} strokeWidth={2.2} />
                      </div>
                      <div>
                        <div style={{ fontWeight: 700, color: "#0F172A", textTransform: "capitalize", fontSize: "13.5px" }}>
                          {a.disease_key || (a as any).pathogen || "Unknown Pathogen"}
                        </div>
                        <div style={{ fontSize: "11.5px", color: "#64748B", marginTop: "2px" }}>
                          {a.explanation?.summary ? `${a.explanation.summary.slice(0, 48)}...` : "Surveillance anomaly detected"}
                        </div>
                      </div>
                    </div>
                  </td>

                  <td style={{ padding: "14px 18px", fontWeight: 600, color: "#475569", textTransform: "capitalize" }}>
                    {a.geo_key || (a as any).location_name || "Regional Block"}
                  </td>

                  <td style={{ padding: "14px 18px" }}>
                    <AlertTierBadge tier={a.alert_tier} />
                  </td>

                  <td style={{ padding: "14px 18px" }}>
                    {(() => {
                      const cat = ((a as any).decision_category || a.recommended_action || "INFORMATIONAL").toUpperCase();
                      const isReview = cat.includes("REVIEW") || cat.includes("ALERT") || cat.includes("WARNING");
                      const isCorroborated = cat.includes("CORROBORATED");
                      const isAnomaly = cat.includes("ANOMALY") || cat.includes("STATISTICAL");
                      const bg = isReview ? "#FEF3C7" : isCorroborated ? "#DBEAFE" : isAnomaly ? "#FCE7F3" : "#F1F5F9";
                      const fg = isReview ? "#92400E" : isCorroborated ? "#1E40AF" : isAnomaly ? "#9D174D" : "#475569";
                      return (
                        <span
                          style={{
                            display: "inline-flex",
                            alignItems: "center",
                            gap: "4px",
                            padding: "3px 8px",
                            borderRadius: "6px",
                            fontSize: "11.5px",
                            fontWeight: 700,
                            backgroundColor: bg,
                            color: fg,
                            textTransform: "uppercase",
                            letterSpacing: "0.03em",
                          }}
                        >
                          {cat.replace(/_/g, " ")}
                        </span>
                      );
                    })()}
                  </td>

                  <td style={{ padding: "14px 18px" }}>
                    <ThreatTierBadge tier={a.pathogen_threat_tier} />
                  </td>

                  <td style={{ padding: "14px 18px", textAlign: "center", fontWeight: 700, color: "var(--brand-primary)" }}>
                    <span
                      style={{
                        padding: "2px 8px",
                        borderRadius: "9999px",
                        background: "var(--brand-primary-light)",
                        fontSize: "12px",
                      }}
                    >
                      {a.supporting_source_count}
                    </span>
                  </td>

                  <td style={{ padding: "14px 18px", fontSize: "12px", color: "#475569", whiteSpace: "nowrap" }}>
                    <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
                      <span style={{ fontWeight: 700 }}>
                        {new Date(a.period_end).toLocaleDateString("en-US", { timeZone: "UTC", month: "short", day: "numeric", year: "numeric" })}
                      </span>
                      {new Date(a.period_end).getTime() > Date.now() && (
                        <span
                          style={{
                            fontSize: "10px",
                            fontWeight: 700,
                            padding: "1px 5px",
                            borderRadius: "4px",
                            background: "#FEF3C7",
                            color: "#B45309",
                            border: "1px solid #FDE68A",
                          }}
                        >
                          IN PROGRESS
                        </span>
                      )}
                    </div>
                    <div style={{ fontSize: "11px", color: "#64748B", marginTop: "2px" }}>
                      Window: {new Date(a.period_start).toLocaleDateString("en-US", { timeZone: "UTC", month: "short", day: "numeric" })} – {new Date(a.period_end).toLocaleDateString("en-US", { timeZone: "UTC", month: "short", day: "numeric" })} (UTC/IST)
                    </div>
                  </td>

                  <td style={{ padding: "14px 18px", textAlign: "right" }}>
                    <button
                      className="btn btn-secondary btn-sm"
                      style={{ padding: "5px 10px" }}
                      onClick={(e) => {
                        e.stopPropagation();
                        onSelectAlert(a.alert_id);
                      }}
                    >
                      <span>Inspect</span>
                      <ChevronRight size={13} />
                    </button>
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

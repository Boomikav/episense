import React from "react";
import { ArrowRight, HelpCircle, Radio } from "lucide-react";
import type { EpidemiologicalAlert, SignalObservation } from "../../types/api";

interface RecentActivityProps {
  alerts: EpidemiologicalAlert[];
  signals: SignalObservation[];
  onSelectAlert: (alertId: string) => void;
  onViewAllAlerts: () => void;
  onViewAllSignals?: () => void;
}

export const RecentActivity: React.FC<RecentActivityProps> = ({
  alerts,
  onSelectAlert,
  onViewAllAlerts,
}) => {
  const displayAlerts = alerts.slice(0, 5);

  return (
    <div className="card" style={{ padding: "24px 28px", height: "100%", display: "flex", flexDirection: "column" }}>
      {/* Header */}
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "flex-start",
          marginBottom: "14px",
          flexWrap: "wrap",
          gap: "10px",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
          <div
            style={{
              width: "36px",
              height: "36px",
              borderRadius: "10px",
              background: "#FFF2E8",
              color: "#FF8A32",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
            }}
          >
            <Radio size={19} strokeWidth={2.2} />
          </div>
          <div>
            <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
              <h3 style={{ fontSize: "16px", fontWeight: 700, color: "#0F172A", letterSpacing: "-0.01em" }}>
                Narrative Event Reviews
              </h3>
              <span
                style={{
                  display: "inline-flex",
                  alignItems: "center",
                  gap: "5px",
                  padding: "3px 8px",
                  borderRadius: "9999px",
                  background: "#EEF2FF",
                  color: "#4F46E5",
                  fontSize: "11px",
                  fontWeight: 700,
                }}
              >
                <span>Triage Queue</span>
              </span>
            </div>
            <div style={{ fontSize: "11.5px", color: "#64748B", marginTop: "2px" }}>
              Heuristic prioritization index (0.00–1.00) for human field review · Not calibrated outbreak probability
            </div>
          </div>
        </div>

        {/* View All */}
        <button
          onClick={onViewAllAlerts}
          style={{
            display: "inline-flex",
            alignItems: "center",
            gap: "5px",
            background: "none",
            border: "none",
            color: "var(--brand-primary)",
            fontSize: "13px",
            fontWeight: 700,
            cursor: "pointer",
            fontFamily: "var(--font-sans)",
            paddingTop: "4px",
          }}
        >
          <span>View All</span>
          <ArrowRight size={15} />
        </button>
      </div>

      {/* Feed List */}
      <div style={{ display: "flex", flexDirection: "column", gap: "12px", flex: 1 }}>
        {displayAlerts.length === 0 ? (
          <div style={{ padding: "30px 20px", textAlign: "center", color: "#64748B", fontSize: "13px" }}>
            <div style={{ fontWeight: 600, color: "#0F172A", marginBottom: "4px" }}>No Narrative Reviews Pending Triage</div>
            No unverified narrative reports currently require analyst triage across connected public health feeds.
          </div>
        ) : (
          displayAlerts.map((a) => {
            const isHigh = a.alert_tier === "high";
            const isMedium = a.alert_tier === "medium";
            const isLow = a.alert_tier === "low";

            // Determine if publication is recent (>= 2025) or archived (< 2025)
            const dateToEvaluate = a.period_end || a.created_at;
            const evalYear = dateToEvaluate ? new Date(dateToEvaluate).getFullYear() : 2026;
            const isHistoricalPub = evalYear < 2025;

            const timeLabel = a.created_at
              ? new Date(a.created_at).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })
              : new Date(a.period_end).toLocaleDateString([], { month: "short", day: "numeric", year: "numeric" });

            const severityLabel = isHigh ? "Priority Review" : isMedium ? "Routine Review" : isLow ? "Low Priority" : "Informational";
            const severityBg = isHigh ? "#FEECEF" : isMedium ? "#FFF2E8" : isLow ? "#F1EDFD" : "#E8F8F2";
            const severityColor = isHigh ? "#F04462" : isMedium ? "#FF8A32" : isLow ? "#7047F5" : "#10A878";

            return (
              <div
                key={a.alert_id}
                onClick={() => onSelectAlert(a.alert_id)}
                style={{
                  padding: "12px 14px",
                  borderRadius: "12px",
                  background: "var(--bg-canvas)",
                  border: "1px solid var(--border-default)",
                  display: "flex",
                  flexDirection: "column",
                  gap: "6px",
                  cursor: "pointer",
                  transition: "all 0.15s ease",
                }}
                onMouseEnter={(e) => {
                  e.currentTarget.style.borderColor = "var(--brand-primary-border)";
                  e.currentTarget.style.backgroundColor = "#FFFFFF";
                  e.currentTarget.style.boxShadow = "var(--shadow-sm)";
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.borderColor = "var(--border-default)";
                  e.currentTarget.style.backgroundColor = "var(--bg-canvas)";
                  e.currentTarget.style.boxShadow = "none";
                }}
              >
                {/* Meta Row: Time & Severity Tag */}
                <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
                  <div style={{ display: "flex", alignItems: "center", gap: "8px", flexWrap: "wrap" }}>
                    <span style={{ fontSize: "11.5px", fontWeight: 700, color: "#0F172A", fontFamily: "var(--font-mono)" }}>
                      {timeLabel}
                    </span>
                    <span
                      style={{
                        padding: "2px 8px",
                        borderRadius: "9999px",
                        background: severityBg,
                        color: severityColor,
                        fontSize: "10.5px",
                        fontWeight: 700,
                      }}
                    >
                      {severityLabel}
                    </span>
                    {isHistoricalPub && (
                      <span
                        style={{
                          padding: "2px 6px",
                          borderRadius: "4px",
                          background: "#F1F5F9",
                          color: "#64748B",
                          fontSize: "10px",
                          fontWeight: 600,
                        }}
                      >
                        Archived Feed Publication ({evalYear})
                      </span>
                    )}
                  </div>

                  <span
                    style={{
                      fontSize: "11px",
                      fontWeight: 700,
                      color: "var(--brand-primary)",
                      background: "var(--brand-primary-light)",
                      padding: "2px 7px",
                      borderRadius: "6px",
                    }}
                    title="Heuristic multi-criteria prioritization index (not calibrated probability)"
                  >
                    Triage Index: {a.composite_score.toFixed(2)}
                  </span>
                </div>

                {/* Event Headline */}
                <div style={{ fontSize: "13px", fontWeight: 700, color: "#0F172A", textTransform: "capitalize" }}>
                  {a.disease_key} Incident Report — {a.geo_key}
                </div>

                {/* Subtitle / summary */}
                <div
                  style={{
                    fontSize: "11.5px",
                    color: "#64748B",
                    lineHeight: 1.4,
                    display: "-webkit-box",
                    WebkitLineClamp: 2,
                    WebkitBoxOrient: "vertical",
                    overflow: "hidden",
                  }}
                >
                  {a.explanation?.summary || `Cross-verified narrative signal across ${a.supporting_source_count} surveillance source(s).`}
                </div>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
};

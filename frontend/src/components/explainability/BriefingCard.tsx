import React from "react";
import { Clock, HelpCircle, MapPin, Network, User, Zap } from "lucide-react";
import type { Epidemiological5W1H } from "../../types/api";

interface BriefingCardProps {
  briefing: Epidemiological5W1H;
}

export const BriefingCard: React.FC<BriefingCardProps> = ({ briefing }) => {
  const items = [
    { label: "WHO (Pathogen)", val: briefing.who_pathogen, icon: User, color: "var(--brand-primary)", bg: "var(--brand-primary-light)" },
    { label: "WHAT (Incident)", val: briefing.what_event, icon: HelpCircle, color: "#FF8A32", bg: "#FFF2E8" },
    { label: "WHEN (Period)", val: briefing.when_period, icon: Clock, color: "#2563EB", bg: "#EFF6FF" },
    { label: "WHERE (Location)", val: briefing.where_location, icon: MapPin, color: "#10A878", bg: "#E8F8F2" },
    { label: "WHY (Aberration)", val: briefing.why_aberration, icon: Zap, color: "#F04462", bg: "#FEECEF" },
    { label: "HOW (Corroboration)", val: briefing.how_corroboration, icon: Network, color: "#64748B", bg: "#F1F5F9" },
  ];

  return (
    <div className="card" style={{ marginBottom: "20px", background: "#FFFFFF", padding: "20px 24px" }}>
      <h4 style={{ fontSize: "14px", fontWeight: 700, color: "#0F172A", marginBottom: "4px" }}>
        5W1H Epidemiological Intelligence Briefing
      </h4>
      <p style={{ fontSize: "12px", color: "#64748B", marginBottom: "16px" }}>
        Structured public health narrative answering the six foundational surveillance questions
      </p>

      <div className="grid-2" style={{ gap: "12px" }}>
        {items.map((it) => {
          const Icon = it.icon;
          return (
            <div
              key={it.label}
              style={{
                background: "var(--bg-canvas)",
                padding: "12px 14px",
                borderRadius: "10px",
                border: "1px solid var(--border-default)",
              }}
            >
              <div style={{ display: "flex", alignItems: "center", gap: "8px", marginBottom: "4px" }}>
                <div
                  style={{
                    width: "24px",
                    height: "24px",
                    borderRadius: "6px",
                    background: it.bg,
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                  }}
                >
                  <Icon size={13} style={{ color: it.color }} />
                </div>
                <span style={{ fontSize: "11px", fontWeight: 700, color: "#475569", letterSpacing: "0.04em" }}>
                  {it.label}
                </span>
              </div>
              <div style={{ fontSize: "13px", color: "#0F172A", lineHeight: 1.4, fontWeight: 500, paddingLeft: "4px" }}>
                {it.val || "N/A"}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};

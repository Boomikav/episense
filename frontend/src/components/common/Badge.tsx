import React from "react";
import type { AlertTier, AssertionStatus, PathogenThreatTier, RecommendedReviewAction, SignalLevel } from "../../types/api";

interface BadgeProps {
  children: React.ReactNode;
  variant?: "high" | "medium" | "low" | "info" | "success" | "neutral";
  size?: "sm" | "md";
  className?: string;
}

export const Badge: React.FC<BadgeProps> = ({
  children,
  variant = "info",
  size = "md",
  className = "",
}) => {
  return (
    <span
      className={`badge badge-${variant} ${size === "sm" ? "badge-sm" : ""} ${className}`}
      style={size === "sm" ? { padding: "2px 6px", fontSize: "10px" } : {}}
    >
      {children}
    </span>
  );
};

export const AlertTierBadge: React.FC<{ tier: AlertTier }> = ({ tier }) => {
  switch (tier) {
    case "high":
      return <Badge variant="high">High Alert</Badge>;
    case "medium":
      return <Badge variant="medium">Medium Alert</Badge>;
    case "low":
      return <Badge variant="low">Low Alert</Badge>;
    case "informational":
    default:
      return <Badge variant="info">Informational</Badge>;
  }
};

export const ThreatTierBadge: React.FC<{ tier: PathogenThreatTier }> = ({ tier }) => {
  switch (tier) {
    case "tier_4_high_consequence":
    case "tier_3_severe":
      return (
        <span
          title="Operational triage review priority based on configured surveillance indicators. Heuristic score is strictly decoupled from outbreak probability, clinical severity, biological pathogen hazard, and epidemiological confirmation."
          style={{
            display: "inline-flex",
            alignItems: "center",
            padding: "2px 8px",
            borderRadius: "6px",
            background: "#FEE2E2",
            border: "1px solid #FECACA",
            color: "#991B1B",
            fontSize: "11px",
            fontWeight: 700,
            fontFamily: "var(--font-mono)",
          }}
        >
          Priority Review
        </span>
      );
    case "tier_2_moderate":
      return (
        <span
          title="Operational triage review priority based on configured surveillance indicators. Heuristic score is strictly decoupled from outbreak probability, clinical severity, biological pathogen hazard, and epidemiological confirmation."
          style={{
            display: "inline-flex",
            alignItems: "center",
            padding: "2px 8px",
            borderRadius: "6px",
            background: "#FEF3C7",
            border: "1px solid #FDE68A",
            color: "#92400E",
            fontSize: "11px",
            fontWeight: 700,
            fontFamily: "var(--font-mono)",
          }}
        >
          Needs Review
        </span>
      );
    case "tier_1_mild":
    default:
      return (
        <span
          title="Operational triage review priority based on configured surveillance indicators. Heuristic score is strictly decoupled from outbreak probability, clinical severity, biological pathogen hazard, and epidemiological confirmation."
          style={{
            display: "inline-flex",
            alignItems: "center",
            padding: "2px 8px",
            borderRadius: "6px",
            background: "#F1F5F9",
            border: "1px solid #E2E8F0",
            color: "#475569",
            fontSize: "11px",
            fontWeight: 600,
            fontFamily: "var(--font-mono)",
          }}
        >
          Informational
        </span>
      );
  }
};

export const SignalLevelBadge: React.FC<{ level: SignalLevel }> = ({ level }) => {
  switch (level) {
    case "strong_signal":
      return <Badge variant="high">Strong Signal</Badge>;
    case "signal":
      return <Badge variant="medium">Signal</Badge>;
    case "watch":
      return <Badge variant="low">Watch</Badge>;
    case "no_signal":
      return <Badge variant="neutral">Suppressed (No Signal)</Badge>;
    case "noise":
    default:
      return <Badge variant="info">Noise</Badge>;
  }
};

export const AssertionBadge: React.FC<{ status: AssertionStatus }> = ({ status }) => {
  switch (status) {
    case "confirmed":
      return <Badge variant="success">Confirmed</Badge>;
    case "suspected":
      return <Badge variant="medium">Suspected</Badge>;
    case "historical":
      return <Badge variant="info">Historical</Badge>;
    case "negated":
      return <Badge variant="neutral">Negated</Badge>;
    case "hypothetical":
    default:
      return <Badge variant="info">Hypothetical</Badge>;
  }
};

export const RecommendedActionBadge: React.FC<{ action?: RecommendedReviewAction }> = ({ action }) => {
  switch (action) {
    case "investigate":
      return (
        <span
          title="Recommended Operational Action: Immediate human epidemiologist triage and investigation."
          style={{
            display: "inline-flex",
            alignItems: "center",
            padding: "2px 8px",
            borderRadius: "6px",
            background: "#FEE2E2",
            border: "1px solid #FCA5A5",
            color: "#991B1B",
            fontSize: "11px",
            fontWeight: 800,
            textTransform: "uppercase",
            letterSpacing: "0.05em",
          }}
        >
          INVESTIGATE
        </span>
      );
    case "monitor":
      return (
        <span
          title="Recommended Operational Action: Monitor signal for spatial-temporal escalation."
          style={{
            display: "inline-flex",
            alignItems: "center",
            padding: "2px 8px",
            borderRadius: "6px",
            background: "#FEF3C7",
            border: "1px solid #FCD34D",
            color: "#92400E",
            fontSize: "11px",
            fontWeight: 800,
            textTransform: "uppercase",
            letterSpacing: "0.05em",
          }}
        >
          MONITOR
        </span>
      );
    case "discard":
      return (
        <span
          title="Recommended Operational Action: Negated, historical, or non-communicable event; safe to discard."
          style={{
            display: "inline-flex",
            alignItems: "center",
            padding: "2px 8px",
            borderRadius: "6px",
            background: "#F1F5F9",
            border: "1px solid #CBD5E1",
            color: "#64748B",
            fontSize: "11px",
            fontWeight: 700,
            textTransform: "uppercase",
          }}
        >
          DISCARD
        </span>
      );
    case "informational":
    default:
      return (
        <span
          title="Recommended Operational Action: Routine baseline or gated signal for passive surveillance."
          style={{
            display: "inline-flex",
            alignItems: "center",
            padding: "2px 8px",
            borderRadius: "6px",
            background: "#E0F2FE",
            border: "1px solid #BAE6FD",
            color: "#0369A1",
            fontSize: "11px",
            fontWeight: 700,
            textTransform: "uppercase",
          }}
        >
          INFORMATIONAL
        </span>
      );
  }
};

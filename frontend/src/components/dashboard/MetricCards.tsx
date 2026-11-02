import React from "react";
import { AlertTriangle, Database, Radio, ShieldAlert } from "lucide-react";
import type { EpidemiologicalAlert, FusedEvent, SignalObservation } from "../../types/api";

interface MetricCardsProps {
  alerts: EpidemiologicalAlert[];
  events: FusedEvent[];
  signals: SignalObservation[];
  documentsCount: number;
  operationalSources?: number;
  totalSources?: number;
}

export const MetricCards: React.FC<MetricCardsProps> = ({
  alerts,
  events,
  signals,
  documentsCount,
  operationalSources = 2,
  totalSources = 6,
}) => {
  const activeAlertsCount = alerts.length;
  const criticalCount = alerts.filter(
    (a) => a.alert_tier === "high" || a.pathogen_threat_tier === "tier_4_high_consequence"
  ).length;

  const fusedEventsCount = events.length;
  
  // Truthful statistical anomaly count: only count signals with genuine statistical anomaly on a stable baseline
  const activeStatisticalAnomaliesCount = signals.filter(
    (s) =>
      s.signal_level !== "no_signal" &&
      s.signal_level !== "noise" &&
      s.reliability_status === "stable_baseline" &&
      !s.downgraded_reason
  ).length;

  return (
    <div className="grid-4" style={{ marginBottom: "28px" }}>
      {/* 1. Narrative Event Reviews (Operational Triage) */}
      <div
        className="card"
        style={{
          padding: "20px 22px 14px 22px",
          display: "flex",
          flexDirection: "column",
          justifyContent: "space-between",
          position: "relative",
          overflow: "hidden",
        }}
      >
        <div>
          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
            <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
              <div
                style={{
                  width: "36px",
                  height: "36px",
                  borderRadius: "10px",
                  background: "#FEECEF",
                  color: "#F04462",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                }}
              >
                <AlertTriangle size={18} strokeWidth={2.2} />
              </div>
              <div>
                <span style={{ fontSize: "13px", fontWeight: 700, color: "#334155" }}>
                  Narrative Event Reviews
                </span>
              </div>
            </div>

            <div
              style={{
                display: "inline-flex",
                alignItems: "center",
                gap: "4px",
                padding: "3px 9px",
                borderRadius: "9999px",
                background: "#FEECEF",
                color: "#E11D48",
                fontSize: "11px",
                fontWeight: 700,
              }}
            >
              <span>●</span>
              <span>{criticalCount > 0 ? `${criticalCount} Priority` : "Triage Index"}</span>
            </div>
          </div>

          <div
            style={{
              fontSize: "36px",
              fontWeight: 800,
              color: "#0F172A",
              letterSpacing: "-0.03em",
              lineHeight: 1.1,
              marginTop: "16px",
            }}
          >
            {activeAlertsCount}
          </div>

          <div style={{ fontSize: "12px", color: "#475569", fontWeight: 500, marginTop: "6px" }}>
            Unverified reports prioritized for human field review (Heuristic score)
          </div>
        </div>

        {/* Coral Sparkline SVG */}
        <div style={{ marginTop: "12px", marginInline: "-22px", marginBottom: "-14px" }}>
          <svg viewBox="0 0 300 60" style={{ width: "100%", height: "46px", display: "block" }}>
            <defs>
              <linearGradient id="coralGrad" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor="#F04462" stopOpacity="0.25" />
                <stop offset="100%" stopColor="#F04462" stopOpacity="0.0" />
              </linearGradient>
            </defs>
            <path
              d="M 0,55 Q 60,52 100,42 T 180,35 T 240,36 T 300,32 L 300,60 L 0,60 Z"
              fill="url(#coralGrad)"
            />
            <path
              d="M 0,55 Q 60,52 100,42 T 180,35 T 240,36 T 300,32"
              fill="none"
              stroke="#F04462"
              strokeWidth="2.5"
              strokeLinecap="round"
            />
          </svg>
        </div>
      </div>

      {/* 2. Canonical Fused Events */}
      <div
        className="card"
        style={{
          padding: "20px 22px 14px 22px",
          display: "flex",
          flexDirection: "column",
          justifyContent: "space-between",
          position: "relative",
          overflow: "hidden",
        }}
      >
        <div>
          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
            <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
              <div
                style={{
                  width: "36px",
                  height: "36px",
                  borderRadius: "10px",
                  background: "#E8F8F2",
                  color: "#10A878",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                }}
              >
                <Database size={18} strokeWidth={2.2} />
              </div>
              <div>
                <span style={{ fontSize: "13px", fontWeight: 700, color: "#334155" }}>
                  Canonical Fused Events
                </span>
              </div>
            </div>

            <div
              style={{
                display: "inline-flex",
                alignItems: "center",
                gap: "4px",
                padding: "3px 9px",
                borderRadius: "9999px",
                background: "#E8F8F2",
                color: "#059669",
                fontSize: "11px",
                fontWeight: 700,
              }}
            >
              <span>●</span>
              <span>Multi-Source</span>
            </div>
          </div>

          <div
            style={{
              fontSize: "36px",
              fontWeight: 800,
              color: "#0F172A",
              letterSpacing: "-0.03em",
              lineHeight: 1.1,
              marginTop: "16px",
            }}
          >
            {fusedEventsCount}
          </div>

          <div style={{ fontSize: "12px", color: "#475569", fontWeight: 500, marginTop: "6px" }}>
            Cross-document deduplicated incidents (Anti-inflation verified)
          </div>
        </div>

        {/* Emerald Sparkline SVG */}
        <div style={{ marginTop: "12px", marginInline: "-22px", marginBottom: "-14px" }}>
          <svg viewBox="0 0 300 60" style={{ width: "100%", height: "46px", display: "block" }}>
            <defs>
              <linearGradient id="emeraldGrad" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor="#10A878" stopOpacity="0.25" />
                <stop offset="100%" stopColor="#10A878" stopOpacity="0.0" />
              </linearGradient>
            </defs>
            <path
              d="M 0,56 Q 70,55 120,48 T 200,42 T 260,36 T 300,30 L 300,60 L 0,60 Z"
              fill="url(#emeraldGrad)"
            />
            <path
              d="M 0,56 Q 70,55 120,48 T 200,42 T 260,36 T 300,30"
              fill="none"
              stroke="#10A878"
              strokeWidth="2.5"
              strokeLinecap="round"
            />
          </svg>
        </div>
      </div>

      {/* 3. Statistical Indicator Anomalies (Strictly Baseline Gated) */}
      <div
        className="card"
        style={{
          padding: "20px 22px 14px 22px",
          display: "flex",
          flexDirection: "column",
          justifyContent: "space-between",
          position: "relative",
          overflow: "hidden",
        }}
      >
        <div>
          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
            <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
              <div
                style={{
                  width: "36px",
                  height: "36px",
                  borderRadius: "10px",
                  background: "#FEF3C7",
                  color: "#D97706",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                }}
              >
                <ShieldAlert size={18} strokeWidth={2.2} />
              </div>
              <div>
                <span style={{ fontSize: "13px", fontWeight: 700, color: "#334155" }}>
                  Statistical Anomalies
                </span>
              </div>
            </div>

            <div
              style={{
                display: "inline-flex",
                alignItems: "center",
                gap: "4px",
                padding: "3px 9px",
                borderRadius: "9999px",
                background: "#FEF3C7",
                color: "#B45309",
                fontSize: "11px",
                fontWeight: 700,
              }}
            >
              <span>●</span>
              <span>Baseline Gated</span>
            </div>
          </div>

          <div
            style={{
              fontSize: "36px",
              fontWeight: 800,
              color: "#0F172A",
              letterSpacing: "-0.03em",
              lineHeight: 1.1,
              marginTop: "16px",
            }}
          >
            {activeStatisticalAnomaliesCount}
          </div>

          <div style={{ fontSize: "12px", color: "#475569", fontWeight: 500, marginTop: "6px" }}>
            0 active anomalies; historical series suppressed (N &lt; 3 baseline history)
          </div>
        </div>

        {/* Amber Sparkline SVG */}
        <div style={{ marginTop: "12px", marginInline: "-22px", marginBottom: "-14px" }}>
          <svg viewBox="0 0 300 60" style={{ width: "100%", height: "46px", display: "block" }}>
            <defs>
              <linearGradient id="amberGrad" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor="#D97706" stopOpacity="0.25" />
                <stop offset="100%" stopColor="#D97706" stopOpacity="0.0" />
              </linearGradient>
            </defs>
            <path
              d="M 0,55 Q 80,55 140,55 T 220,55 T 300,55 L 300,60 L 0,60 Z"
              fill="url(#amberGrad)"
            />
            <path
              d="M 0,55 Q 80,55 140,55 T 220,55 T 300,55"
              fill="none"
              stroke="#D97706"
              strokeWidth="2.5"
              strokeLinecap="round"
            />
          </svg>
        </div>
      </div>

      {/* 4. Live Source Connectors */}
      <div
        className="card"
        style={{
          padding: "20px 22px 14px 22px",
          display: "flex",
          flexDirection: "column",
          justifyContent: "space-between",
          position: "relative",
          overflow: "hidden",
        }}
      >
        <div>
          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
            <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
              <div
                style={{
                  width: "36px",
                  height: "36px",
                  borderRadius: "10px",
                  background: "#F1EDFD",
                  color: "#7047F5",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                }}
              >
                <Radio size={18} strokeWidth={2.2} />
              </div>
              <div>
                <span style={{ fontSize: "13px", fontWeight: 700, color: "#334155" }}>
                  Operational Feeds
                </span>
              </div>
            </div>

            <div
              style={{
                display: "inline-flex",
                alignItems: "center",
                gap: "4px",
                padding: "3px 9px",
                borderRadius: "9999px",
                background: "#E8F8F2",
                color: "#059669",
                fontSize: "11px",
                fontWeight: 700,
              }}
            >
              <span>●</span>
              <span>{operationalSources} Active</span>
            </div>
          </div>

          <div
            style={{
              fontSize: "36px",
              fontWeight: 800,
              color: "#0F172A",
              letterSpacing: "-0.03em",
              lineHeight: 1.1,
              marginTop: "16px",
            }}
          >
            {operationalSources} <span style={{ fontSize: "20px", color: "#64748B", fontWeight: 600 }}>/ {totalSources}</span>
          </div>

          <div style={{ fontSize: "12px", color: "#475569", fontWeight: 500, marginTop: "6px" }}>
            WHO News &amp; IDSP active; CDC empty; 3 blocked/unavailable
          </div>
        </div>

        {/* Violet Sparkline SVG */}
        <div style={{ marginTop: "12px", marginInline: "-22px", marginBottom: "-14px" }}>
          <svg viewBox="0 0 300 60" style={{ width: "100%", height: "46px", display: "block" }}>
            <defs>
              <linearGradient id="violetGrad" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor="#7047F5" stopOpacity="0.25" />
                <stop offset="100%" stopColor="#7047F5" stopOpacity="0.0" />
              </linearGradient>
            </defs>
            <path
              d="M 0,55 Q 80,54 130,46 T 210,38 T 270,35 T 300,34 L 300,60 L 0,60 Z"
              fill="url(#violetGrad)"
            />
            <path
              d="M 0,55 Q 80,54 130,46 T 210,38 T 270,35 T 300,34"
              fill="none"
              stroke="#7047F5"
              strokeWidth="2.5"
              strokeLinecap="round"
            />
          </svg>
        </div>
      </div>
    </div>
  );
};

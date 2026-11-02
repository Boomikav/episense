import React from "react";
import {
  Activity,
  Binary,
  Layers,
  LayoutDashboard,
  MapPin,
  Scale,
  Radio,
  Database,
} from "lucide-react";
import type { ConnectionStatus } from "../../services/websocket";

export type NavView =
  | "overview"
  | "eight-diseases"
  | "events-signals"
  | "map"
  | "data-evaluation"
  | "sources"
  | "workbench"
  // Legacy aliases mapped gracefully in App.tsx
  | "live"
  | "fusion"
  | "alerts"
  | "events"
  | "signals"
  | "research"
  | "submit"
  | "status"
  | "forecasting";

interface SidebarProps {
  currentView: NavView;
  onNavigate: (view: NavView) => void;
  connectionStatus: ConnectionStatus;
  alertCount?: number;
}

export const Sidebar: React.FC<SidebarProps> = ({
  currentView,
  onNavigate,
  alertCount = 0,
}) => {
  // Normalize alias views to primary destinations + secondary workbench for active styling
  const activeDestination: "overview" | "eight-diseases" | "events-signals" | "map" | "data-evaluation" | "sources" | "workbench" =
    currentView === "overview" || currentView === "live"
      ? "overview"
      : currentView === "eight-diseases"
      ? "eight-diseases"
      : currentView === "events-signals" || currentView === "fusion" || currentView === "alerts" || currentView === "events" || currentView === "signals"
      ? "events-signals"
      : currentView === "map"
      ? "map"
      : currentView === "sources" || currentView === "status"
      ? "sources"
      : currentView === "workbench" || currentView === "submit"
      ? "workbench"
      : "data-evaluation";

  const primaryNavItems = [
    {
      id: "overview" as const,
      label: "Overview",
      icon: LayoutDashboard,
      color: "#7047F5",
    },
    {
      id: "eight-diseases" as const,
      label: "Eight Priority Pathogens",
      icon: Activity,
      color: "#10B981",
    },
    {
      id: "events-signals" as const,
      label: "Event Intelligence",
      icon: Layers,
      color: "#D97706",
      badgeCount: alertCount > 0 ? alertCount : undefined,
    },
    {
      id: "map" as const,
      label: "Geographic View",
      icon: MapPin,
      color: "#059669",
    },
    {
      id: "data-evaluation" as const,
      label: "Forecasting & Model Status",
      icon: Scale,
      color: "#6366F1",
    },
    {
      id: "sources" as const,
      label: "Sources & System Health",
      icon: Radio,
      color: "#0284C7",
    },
  ];

  const secondaryNavItems = [
    {
      id: "workbench" as const,
      label: "NLP Forensic Workbench",
      icon: Binary,
      color: "#2563EB",
    },
  ];

  return (
    <aside
      style={{
        width: "var(--sidebar-width)",
        height: "100vh",
        position: "fixed",
        top: 0,
        left: 0,
        backgroundColor: "#FFFFFF",
        borderRight: "1px solid var(--border-default)",
        display: "flex",
        flexDirection: "column",
        zIndex: 50,
      }}
    >
      {/* Brand Header */}
      <div
        style={{
          padding: "24px 22px 20px 22px",
          borderBottom: "1px solid var(--border-subtle)",
          display: "flex",
          alignItems: "center",
          gap: "12px",
        }}
      >
        <div
          style={{
            width: "38px",
            height: "38px",
            borderRadius: "10px",
            background: "linear-gradient(135deg, #7047F5 0%, #4F28D9 100%)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            color: "#FFFFFF",
            fontWeight: 800,
            fontSize: "17px",
            boxShadow: "0 4px 10px rgba(112, 71, 245, 0.28)",
            letterSpacing: "-0.5px",
          }}
        >
          ES
        </div>
        <div>
          <div
            style={{
              fontSize: "16px",
              fontWeight: 800,
              color: "#0F172A",
              letterSpacing: "-0.3px",
              lineHeight: 1.15,
            }}
          >
            EpiSense
          </div>
          <div
            style={{
              fontSize: "11px",
              color: "var(--text-tertiary)",
              fontWeight: 600,
              letterSpacing: "0.02em",
              marginTop: "2px",
            }}
          >
            Epidemiological Intelligence
          </div>
        </div>
      </div>

      {/* Navigation Links: 5 Primary Surveillance Destinations */}
      <nav
        style={{
          flex: 1,
          padding: "16px 12px",
          overflowY: "auto",
        }}
      >
        <div style={{ display: "flex", flexDirection: "column", gap: "4px" }}>
          <div
            style={{
              padding: "4px 14px 6px 14px",
              fontSize: "10px",
              fontWeight: 800,
              textTransform: "uppercase",
              letterSpacing: "0.08em",
              color: "#94A3B8",
            }}
          >
            Surveillance
          </div>
          {primaryNavItems.map((item) => {
            const Icon = item.icon;
            const isActive = activeDestination === item.id;

            return (
              <button
                key={item.id}
                onClick={() => onNavigate(item.id)}
                style={{
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "space-between",
                  width: "100%",
                  padding: "10px 14px",
                  borderRadius: "10px",
                  border: "none",
                  backgroundColor: isActive ? "var(--brand-primary-light)" : "transparent",
                  color: isActive ? "var(--brand-primary)" : "#475569",
                  fontSize: "13px",
                  fontWeight: isActive ? 700 : 500,
                  cursor: "pointer",
                  transition: "all 0.15s ease",
                  textAlign: "left",
                  boxShadow: isActive ? "inset 0 0 0 1px #DDD6FE" : "none",
                }}
                onMouseEnter={(e) => {
                  if (!isActive) {
                    e.currentTarget.style.backgroundColor = "var(--bg-canvas)";
                    e.currentTarget.style.color = "#0F172A";
                  }
                }}
                onMouseLeave={(e) => {
                  if (!isActive) {
                    e.currentTarget.style.backgroundColor = "transparent";
                    e.currentTarget.style.color = "#475569";
                  }
                }}
              >
                <div style={{ display: "flex", alignItems: "center", gap: "11px" }}>
                  <Icon
                    size={18}
                    strokeWidth={isActive ? 2.2 : 1.8}
                    style={{
                      color: isActive ? "var(--brand-primary)" : item.color,
                      flexShrink: 0,
                    }}
                  />
                  <span>{item.label}</span>
                </div>

                <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                  {"badgeCount" in item && item.badgeCount !== undefined && item.badgeCount > 0 && (
                    <span
                      title="Candidate signals in review queue pending epidemiological triage"
                      style={{
                        padding: "2px 8px",
                        borderRadius: "9999px",
                        background: "#FEF3C7",
                        color: "#B45309",
                        border: "1px solid #FDE68A",
                        fontSize: "10.5px",
                        fontWeight: 700,
                        lineHeight: "16px",
                      }}
                    >
                      {item.badgeCount} review
                    </span>
                  )}
                  {isActive && (
                    <div
                      style={{
                        width: "4px",
                        height: "16px",
                        borderRadius: "4px",
                        background: "var(--brand-primary)",
                      }}
                    />
                  )}
                </div>
              </button>
            );
          })}

          <div
            style={{
              padding: "14px 14px 6px 14px",
              fontSize: "10px",
              fontWeight: 800,
              textTransform: "uppercase",
              letterSpacing: "0.08em",
              color: "#94A3B8",
              marginTop: "8px",
              borderTop: "1px solid var(--border-subtle)",
            }}
          >
            Forensic Tools
          </div>
          {secondaryNavItems.map((item) => {
            const Icon = item.icon;
            const isActive = activeDestination === item.id;

            return (
              <button
                key={item.id}
                onClick={() => onNavigate(item.id)}
                style={{
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "space-between",
                  width: "100%",
                  padding: "10px 14px",
                  borderRadius: "10px",
                  border: "none",
                  backgroundColor: isActive ? "var(--brand-primary-light)" : "transparent",
                  color: isActive ? "var(--brand-primary)" : "#475569",
                  fontSize: "13px",
                  fontWeight: isActive ? 700 : 500,
                  cursor: "pointer",
                  transition: "all 0.15s ease",
                  textAlign: "left",
                  boxShadow: isActive ? "inset 0 0 0 1px #DDD6FE" : "none",
                }}
                onMouseEnter={(e) => {
                  if (!isActive) {
                    e.currentTarget.style.backgroundColor = "var(--bg-canvas)";
                    e.currentTarget.style.color = "#0F172A";
                  }
                }}
                onMouseLeave={(e) => {
                  if (!isActive) {
                    e.currentTarget.style.backgroundColor = "transparent";
                    e.currentTarget.style.color = "#475569";
                  }
                }}
              >
                <div style={{ display: "flex", alignItems: "center", gap: "11px" }}>
                  <Icon
                    size={18}
                    strokeWidth={isActive ? 2.2 : 1.8}
                    style={{
                      color: isActive ? "var(--brand-primary)" : item.color,
                      flexShrink: 0,
                    }}
                  />
                  <span>{item.label}</span>
                </div>

                {isActive && (
                  <div
                    style={{
                      width: "4px",
                      height: "16px",
                      borderRadius: "4px",
                      background: "var(--brand-primary)",
                    }}
                  />
                )}
              </button>
            );
          })}
        </div>
      </nav>

      {/* Footer Info Badge */}
      <div style={{ padding: "16px 14px 20px 14px", borderTop: "1px solid var(--border-subtle)" }}>
        <div
          style={{
            padding: "10px 12px",
            borderRadius: "10px",
            background: "var(--bg-canvas)",
            border: "1px solid var(--border-default)",
            display: "flex",
            alignItems: "center",
            gap: "10px",
          }}
        >
          <Database size={15} style={{ color: "#7047F5", flexShrink: 0 }} />
          <div>
            <div style={{ fontSize: "11px", fontWeight: 700, color: "#0F172A" }}>
              SQLite WAL Active
            </div>
            <div style={{ fontSize: "10px", color: "#64748B" }}>
              Deterministic State Store
            </div>
          </div>
        </div>
      </div>
    </aside>
  );
};

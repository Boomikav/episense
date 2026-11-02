import React from "react";
import { Bell, ChevronDown, RefreshCw, Search } from "lucide-react";
import type { ConnectionStatus } from "../../services/websocket";

interface HeaderProps {
  viewTitle?: string;
  viewSubtitle?: string;
  connectionStatus: ConnectionStatus;
  onRefresh?: () => void;
  isRefreshing?: boolean;
}

export const Header: React.FC<HeaderProps> = ({
  connectionStatus,
  onRefresh,
  isRefreshing,
}) => {
  return (
    <header
      style={{
        height: "var(--header-height)",
        background: "#FFFFFF",
        borderBottom: "1px solid var(--border-default)",
        display: "flex",
        alignItems: "center",
        justifyContent: "space-between",
        padding: "0 36px",
        position: "sticky",
        top: 0,
        zIndex: 40,
      }}
    >
      {/* Search Input Bar (from Stitch reference) */}
      <div
        style={{
          display: "flex",
          alignItems: "center",
          gap: "10px",
          background: "var(--bg-canvas)",
          border: "1px solid var(--border-default)",
          borderRadius: "9999px",
          padding: "8px 16px",
          width: "480px",
          maxWidth: "100%",
          transition: "border-color 0.18s ease, box-shadow 0.18s ease",
        }}
      >
        <Search size={16} style={{ color: "#94A3B8", flexShrink: 0 }} />
        <input
          type="text"
          placeholder="Search locations, pathogens, events, or keywords..."
          style={{
            border: "none",
            background: "transparent",
            outline: "none",
            fontSize: "13px",
            color: "#0F172A",
            width: "100%",
            fontFamily: "var(--font-sans)",
          }}
        />
        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: "2px",
            padding: "2px 7px",
            borderRadius: "6px",
            background: "#FFFFFF",
            border: "1px solid #E2DFD8",
            fontSize: "11px",
            fontWeight: 600,
            color: "#64748B",
            fontFamily: "var(--font-sans)",
            flexShrink: 0,
            boxShadow: "0 1px 2px rgba(0,0,0,0.03)",
          }}
        >
          <span>⌘</span>
          <span>K</span>
        </div>
      </div>

      {/* Right Controls */}
      <div style={{ display: "flex", alignItems: "center", gap: "16px" }}>
        {/* Connection status indicator */}
        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: "6px",
            padding: "5px 11px",
            borderRadius: "var(--radius-full)",
            background: "var(--bg-canvas)",
            border: "1px solid var(--border-default)",
            fontSize: "11px",
            fontWeight: 600,
            color:
              connectionStatus === "connected"
                ? "var(--status-success)"
                : connectionStatus === "reconnecting"
                ? "var(--tier-medium)"
                : "var(--text-tertiary)",
          }}
        >
          <span
            style={{
              width: "7px",
              height: "7px",
              borderRadius: "50%",
              backgroundColor:
                connectionStatus === "connected"
                  ? "var(--status-success)"
                  : connectionStatus === "reconnecting"
                  ? "var(--tier-medium)"
                  : "#94A3B8",
            }}
          />
          <span style={{ textTransform: "capitalize" }}>WS {connectionStatus}</span>
        </div>

        {/* Refresh button */}
        {onRefresh && (
          <button
            onClick={onRefresh}
            disabled={isRefreshing}
            className="btn btn-secondary btn-sm"
            style={{ padding: "7px 12px" }}
            title="Refresh Surveillance Data"
          >
            <RefreshCw
              size={13}
              style={{
                animation: isRefreshing ? "spin 1s linear infinite" : "none",
              }}
            />
            <span>Refresh</span>
          </button>
        )}

        {/* Notifications Icon with red dot badge */}
        <div style={{ position: "relative" }}>
          <button
            className="btn btn-secondary btn-icon"
            style={{ width: "38px", height: "38px", position: "relative" }}
            title="Surveillance Notifications"
          >
            <Bell size={17} style={{ color: "#475569" }} />
            <span
              style={{
                position: "absolute",
                top: "8px",
                right: "8px",
                width: "8px",
                height: "8px",
                borderRadius: "50%",
                background: "#F04462",
                border: "2px solid #FFFFFF",
              }}
            />
          </button>
        </div>

        {/* User Profile Card */}
        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: "10px",
            padding: "4px 8px 4px 4px",
            borderRadius: "var(--radius-full)",
            cursor: "pointer",
            transition: "background 0.15s ease",
          }}
        >
          <div
            style={{
              width: "34px",
              height: "34px",
              borderRadius: "50%",
              background: "var(--brand-primary)",
              color: "#FFFFFF",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              fontWeight: 700,
              fontSize: "13px",
            }}
          >
            A
          </div>
          <div style={{ textAlign: "left" }}>
            <div style={{ fontSize: "13px", fontWeight: 700, color: "#0F172A", lineHeight: 1.2 }}>
              Dr. Ananya
            </div>
            <div style={{ fontSize: "11px", color: "#64748B" }}>Analyst</div>
          </div>
          <ChevronDown size={14} style={{ color: "#64748B", marginLeft: "2px" }} />
        </div>
      </div>
    </header>
  );
};

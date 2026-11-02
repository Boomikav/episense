import React, { useState } from "react";
import { Radio, Server, ShieldCheck } from "lucide-react";
import { SourceConnectorsView } from "./SourceConnectorsView";
import { StatusView } from "./StatusView";

export type SourcesHealthTab = "connectors" | "health";

interface SourcesSystemHealthViewProps {
  initialTab?: SourcesHealthTab;
}

export const SourcesSystemHealthView: React.FC<SourcesSystemHealthViewProps> = ({
  initialTab = "connectors",
}) => {
  const [activeTab, setActiveTab] = useState<SourcesHealthTab>(initialTab);

  const tabs: { id: SourcesHealthTab; label: string; icon: React.ElementType; description: string }[] = [
    {
      id: "connectors",
      label: "Source Connectors & Telemetry",
      icon: Radio,
      description: "External public-health feed adapters, HTTP polling telemetry, and deduplication status",
    },
    {
      id: "health",
      label: "System Health & Persistence",
      icon: Server,
      description: "SQLite WAL persistence, memory utilization, API probes, and background task diagnostics",
    },
  ];

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "20px" }}>
      {/* Tab Navigation Header */}
      <div
        className="card"
        style={{
          padding: "8px 12px",
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          flexWrap: "wrap",
          gap: "12px",
          background: "#FFFFFF",
          border: "1px solid var(--border-default)",
          borderRadius: "14px",
          boxShadow: "var(--shadow-xs)",
        }}
      >
        <div style={{ display: "flex", gap: "8px", flexWrap: "wrap" }}>
          {tabs.map((tab) => {
            const Icon = tab.icon;
            const isActive = activeTab === tab.id;
            return (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: "8px",
                  padding: "9px 18px",
                  borderRadius: "10px",
                  border: isActive ? "1px solid #7047F5" : "1px solid transparent",
                  background: isActive ? "#F1EDFD" : "transparent",
                  color: isActive ? "#7047F5" : "var(--text-secondary)",
                  fontWeight: isActive ? 700 : 500,
                  fontSize: "13px",
                  cursor: "pointer",
                  transition: "all 0.15s ease",
                }}
              >
                <Icon size={16} />
                <span>{tab.label}</span>
              </button>
            );
          })}
        </div>

        <div style={{ display: "flex", alignItems: "center", gap: "6px", fontSize: "12px", color: "var(--text-secondary)", paddingRight: "8px" }}>
          <ShieldCheck size={14} color="#059669" />
          <span>Operational Feeds & Persistent WAL Architecture</span>
        </div>
      </div>

      {/* Tab Content */}
      <div>
        {activeTab === "connectors" && <SourceConnectorsView />}
        {activeTab === "health" && <StatusView />}
      </div>
    </div>
  );
};

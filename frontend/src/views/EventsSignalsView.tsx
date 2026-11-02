import React, { useState } from "react";
import { Layers, Activity, Bell, ShieldCheck } from "lucide-react";
import { FusionInspectionView } from "./FusionInspectionView";
import { SignalsView } from "./SignalsView";
import { AlertsView } from "./AlertsView";

export type EventsSignalsTab = "fusion" | "signals" | "alerts";

interface EventsSignalsViewProps {
  initialTab?: EventsSignalsTab;
}

export const EventsSignalsView: React.FC<EventsSignalsViewProps> = ({
  initialTab = "fusion",
}) => {
  const [activeTab, setActiveTab] = useState<EventsSignalsTab>(initialTab);

  const tabs: { id: EventsSignalsTab; label: string; icon: React.ElementType; description: string }[] = [
    {
      id: "fusion",
      label: "Validated Events & Fusion",
      icon: Layers,
      description: "Canonical cross-document event clustering with multi-criteria resolution and anti-inflation deduplication",
    },
    {
      id: "signals",
      label: "Early Signals",
      icon: Activity,
      description: "Statistical aberration detection via EARS C1/C2/C3 and Farrington with baseline reliability gating",
    },
    {
      id: "alerts",
      label: "Explainable Alerts",
      icon: Bell,
      description: "Prioritized public health risk alerts with multi-criteria scores, safety ceilings, and audit dossiers",
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
                  border: isActive ? "1px solid var(--brand-primary)" : "1px solid transparent",
                  background: isActive ? "var(--brand-surface, #F1EDFD)" : "transparent",
                  color: isActive ? "var(--brand-primary, #7047F5)" : "var(--text-secondary)",
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
          <span>Downstream Epidemiological Analytics (Optional Layer)</span>
        </div>
      </div>

      {/* Tab Content */}
      <div>
        {activeTab === "fusion" && <FusionInspectionView />}
        {activeTab === "signals" && <SignalsView />}
        {activeTab === "alerts" && <AlertsView />}
      </div>
    </div>
  );
};

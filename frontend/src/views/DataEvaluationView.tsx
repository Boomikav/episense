import React, { useState } from "react";
import { Radio, Scale, Server, ShieldCheck, TrendingUp } from "lucide-react";
import { SourceConnectorsView } from "./SourceConnectorsView";
import { ResearchValidationView } from "./ResearchValidationView";
import { StatusView } from "./StatusView";
import { ForecastingView } from "./ForecastingView";

export type DataEvaluationTab = "sources" | "forecasting" | "benchmark" | "health";

interface DataEvaluationViewProps {
  initialTab?: DataEvaluationTab;
}

export const DataEvaluationView: React.FC<DataEvaluationViewProps> = ({
  initialTab = "forecasting",
}) => {
  const [activeTab, setActiveTab] = useState<DataEvaluationTab>(initialTab);

  const tabs: { id: DataEvaluationTab; label: string; icon: React.ElementType; description: string }[] = [
    {
      id: "forecasting",
      label: "Forecasting & Baseline Sufficiency",
      icon: TrendingUp,
      description: "Baseline data-sufficiency gating, multi-step count models, and prediction intervals",
    },
    {
      id: "benchmark",
      label: "Gold Benchmark Evaluation",
      icon: Scale,
      description: "Empirical evaluation on gold-annotated corpus (v1), token/span F1 metrics, and error analysis",
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
                  border: isActive ? "1px solid #6366F1" : "1px solid transparent",
                  background: isActive ? "#EEF2FF" : "transparent",
                  color: isActive ? "#4F46E5" : "var(--text-secondary)",
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
          <span>Verified Backend Infrastructure & Evaluation Layer</span>
        </div>
      </div>

      {/* Tab Content */}
      <div>
        {activeTab === "sources" && <SourceConnectorsView />}
        {activeTab === "forecasting" && <ForecastingView />}
        {activeTab === "benchmark" && <ResearchValidationView />}
        {activeTab === "health" && <StatusView />}
      </div>
    </div>
  );
};

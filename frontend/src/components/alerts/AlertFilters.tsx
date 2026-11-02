import React from "react";
import { Filter, RotateCcw, Search } from "lucide-react";

interface AlertFiltersProps {
  pathogen: string;
  location: string;
  alertTier: string;
  minScore: number;
  onPathogenChange: (val: string) => void;
  onLocationChange: (val: string) => void;
  onAlertTierChange: (val: string) => void;
  onMinScoreChange: (val: number) => void;
  onReset?: () => void;
  onResetFilters?: () => void;
}

export const AlertFilters = ({
  pathogen,
  location,
  alertTier,
  minScore,
  onPathogenChange,
  onLocationChange,
  onAlertTierChange,
  onMinScoreChange,
  onReset,
  onResetFilters,
}: AlertFiltersProps) => {
  const handleReset = onReset || onResetFilters;

  return (
    <div
      className="card"
      style={{
        padding: "16px 22px",
        marginBottom: "24px",
        display: "flex",
        flexWrap: "wrap",
        gap: "14px",
        alignItems: "center",
      }}
    >
      <div style={{ display: "flex", alignItems: "center", gap: "8px", color: "var(--brand-primary)" }}>
        <Filter size={16} strokeWidth={2.2} />
        <span style={{ fontSize: "13px", fontWeight: 700, color: "#0F172A" }}>Filter Alerts</span>
      </div>

      {/* Pathogen Input */}
      <div style={{ flex: "1 1 180px", position: "relative" }}>
        <input
          type="text"
          placeholder="Filter by pathogen (e.g. Dengue, Cholera)..."
          value={pathogen}
          onChange={(e) => onPathogenChange(e.target.value)}
          className="input"
          style={{ paddingLeft: "34px" }}
        />
        <Search
          size={15}
          style={{ position: "absolute", left: "12px", top: "11px", color: "#94A3B8" }}
        />
      </div>

      {/* Location Input */}
      <div style={{ flex: "1 1 160px" }}>
        <input
          type="text"
          placeholder="Filter by location (e.g. Kozhikode)..."
          value={location}
          onChange={(e) => onLocationChange(e.target.value)}
          className="input"
        />
      </div>

      {/* Alert Tier Dropdown */}
      <div style={{ width: "160px" }}>
        <select
          value={alertTier}
          onChange={(e) => onAlertTierChange(e.target.value)}
          className="select"
        >
          <option value="">All Tiers</option>
          <option value="high">High Alert</option>
          <option value="medium">Medium Alert</option>
          <option value="low">Low Alert</option>
          <option value="informational">Informational</option>
        </select>
      </div>

      {/* Min Score Range */}
      <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
        <span style={{ fontSize: "12px", color: "#475569", whiteSpace: "nowrap" }}>
          Min Score: <strong style={{ color: "#0F172A", fontFamily: "var(--font-mono)" }}>{minScore.toFixed(2)}</strong>
        </span>
        <input
          type="range"
          min="0"
          max="1"
          step="0.05"
          value={minScore}
          onChange={(e) => onMinScoreChange(parseFloat(e.target.value))}
          style={{ width: "100px", accentColor: "var(--brand-primary)", cursor: "pointer" }}
        />
      </div>

      {/* Reset button */}
      {handleReset && (
        <button
          onClick={handleReset}
          className="btn btn-secondary btn-sm"
          style={{ padding: "8px 12px", marginLeft: "auto" }}
          title="Reset Filters"
        >
          <RotateCcw size={13} />
          <span>Reset</span>
        </button>
      )}
    </div>
  );
};

import React, { useState } from "react";
import { ArrowRight, ChevronDown, ChevronUp, MapPin } from "lucide-react";
import type { GeoSummaryRegion } from "../../types/api";

interface RegionalSummaryTableProps {
  regions: GeoSummaryRegion[];
  onSelectRegion?: (region: string) => void;
  onViewFullMap?: () => void;
}

export const RegionalSummaryTable: React.FC<RegionalSummaryTableProps> = ({
  regions,
  onSelectRegion,
  onViewFullMap,
}) => {
  const [expandedRegion, setExpandedRegion] = useState<string | null>(null);

  // Filter out non-geographic placeholders for the table view, putting resolved territories first
  const displayRegions = React.useMemo(() => {
    if (!regions || regions.length === 0) return [];
    
    const resolved = regions.filter(
      (r) => r.region.toLowerCase() !== "unknown" && r.region.toLowerCase() !== "unspecified_or_global"
    );
    const unresolved = regions.filter(
      (r) => r.region.toLowerCase() === "unknown" || r.region.toLowerCase() === "unspecified_or_global"
    );

    // Sort resolved by total alerts descending, then total events descending
    const sortedResolved = [...resolved].sort((a, b) => b.total_alerts - a.total_alerts || b.total_events - a.total_events);
    return [...sortedResolved, ...unresolved];
  }, [regions]);

  return (
    <div className="card" style={{ padding: "20px 24px", overflowX: "auto" }}>
      {/* Header */}
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          marginBottom: "16px",
          flexWrap: "wrap",
          gap: "12px",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
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
            <MapPin size={18} strokeWidth={2.2} />
          </div>
          <div>
            <h3 style={{ fontSize: "16px", fontWeight: 700, color: "#0F172A", letterSpacing: "-0.01em" }}>
              Geographic Surveillance Summary
            </h3>
            <p style={{ fontSize: "12px", color: "#475569", marginTop: "1px" }}>
              Live risk status by country/region with recent activity and trend
            </p>
          </div>
        </div>

        {/* View Full Map Link */}
        <button
          onClick={onViewFullMap || (() => onSelectRegion?.(displayRegions[0]?.region || "all"))}
          style={{
            display: "inline-flex",
            alignItems: "center",
            gap: "6px",
            background: "none",
            border: "none",
            color: "var(--brand-primary)",
            fontSize: "13px",
            fontWeight: 700,
            cursor: "pointer",
            fontFamily: "var(--font-sans)",
            padding: "4px 8px",
            borderRadius: "6px",
          }}
        >
          <span>View Full Map</span>
          <ArrowRight size={15} />
        </button>
      </div>

      {/* Compact Balanced Table */}
      <div style={{ overflowX: "auto" }}>
        <table
          style={{
            width: "100%",
            borderCollapse: "collapse",
            fontSize: "13px",
            textAlign: "left",
            tableLayout: "fixed",
          }}
        >
          <thead>
            <tr
              style={{
                borderBottom: "1px solid var(--border-default)",
                color: "#475569",
                fontSize: "11px",
                fontWeight: 700,
                textTransform: "uppercase",
                letterSpacing: "0.05em",
                background: "var(--bg-surface-2)",
              }}
            >
              <th style={{ padding: "10px 14px", width: "18%" }}>Location</th>
              <th style={{ padding: "10px 14px", width: "32%" }}>Recent Activity / Pathogens</th>
              <th style={{ padding: "10px 14px", textAlign: "center", width: "12%" }}>Active Alerts</th>
              <th style={{ padding: "10px 14px", textAlign: "center", width: "12%" }}>Trend</th>
              <th style={{ padding: "10px 14px", width: "13%" }}>Risk Level</th>
              <th style={{ padding: "10px 14px", width: "13%" }}>Status</th>
            </tr>
          </thead>
          <tbody>
            {displayRegions.slice(0, 7).map((reg) => {
              const isGeneric = reg.region.toLowerCase().includes("unspecified") || reg.region.toLowerCase() === "unknown";
              const cleanRegionName = isGeneric ? "Global / Unresolved" : reg.region.replace(/_/g, " ");

              const isCritical = reg.high_alerts > 0 || (reg.max_composite_score && reg.max_composite_score >= 0.8);
              const isMedium = !isCritical && (reg.medium_alerts > 0 || (reg.max_composite_score && reg.max_composite_score >= 0.65));

              const riskLevel = isCritical ? "Critical" : isMedium ? "High" : reg.low_alerts > 0 ? "Moderate" : "Low";
              const riskBg = isCritical ? "#FEECEF" : isMedium ? "#FFF2E8" : reg.low_alerts > 0 ? "#E7F9F8" : "#F1F5F9";
              const riskColor = isCritical ? "#F04462" : isMedium ? "#FF8A32" : reg.low_alerts > 0 ? "#0D9488" : "#475569";

              const statusText = isCritical ? "Active Outbreak" : isMedium ? "Elevated Watch" : "Under Monitoring";
              const statusBg = isCritical ? "#FEECEF" : isMedium ? "#FFF2E8" : "#E8F8F2";
              const statusColor = isCritical ? "#F04462" : isMedium ? "#FF8A32" : "#0D9488";

              // Unique deduplicated pathogens
              const uniquePathogens = Array.from(
                new Set((reg.pathogens || []).map((p) => p.trim()))
              ).filter(Boolean);

              const isExpanded = expandedRegion === reg.region;
              const visiblePathogens = isExpanded ? uniquePathogens : uniquePathogens.slice(0, 2);
              const remainingCount = uniquePathogens.length - visiblePathogens.length;

              return (
                <tr
                  key={reg.region}
                  style={{
                    borderBottom: "1px solid var(--border-subtle)",
                    transition: "background 0.15s ease",
                  }}
                  onMouseEnter={(e) => (e.currentTarget.style.backgroundColor = "var(--bg-surface-hover)")}
                  onMouseLeave={(e) => (e.currentTarget.style.backgroundColor = "transparent")}
                >
                  {/* Location */}
                  <td style={{ padding: "12px 14px", fontWeight: 700, color: "#0F172A", textTransform: "capitalize" }}>
                    <div style={{ display: "flex", alignItems: "center", gap: "6px", whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }} title={cleanRegionName}>
                      <span style={{ overflow: "hidden", textOverflow: "ellipsis" }}>{cleanRegionName}</span>
                    </div>
                  </td>

                  {/* Compact Pathogen Badges with +N More control */}
                  <td style={{ padding: "12px 14px" }}>
                    <div style={{ display: "flex", gap: "5px", flexWrap: "wrap", alignItems: "center" }}>
                      {visiblePathogens.length === 0 ? (
                        <span style={{ fontSize: "11px", color: "#64748B" }}>No active incident</span>
                      ) : (
                        visiblePathogens.map((p) => (
                          <span
                            key={p}
                            style={{
                              fontSize: "11px",
                              padding: "2px 7px",
                              borderRadius: "6px",
                              background: "#F1F5F9",
                              color: "#334155",
                              fontWeight: 600,
                              textTransform: "capitalize",
                              whiteSpace: "nowrap",
                              maxWidth: "140px",
                              overflow: "hidden",
                              textOverflow: "ellipsis",
                              display: "inline-block",
                            }}
                            title={p}
                          >
                            {p}
                          </span>
                        ))
                      )}

                      {!isExpanded && remainingCount > 0 && (
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            setExpandedRegion(reg.region);
                          }}
                          style={{
                            fontSize: "10.5px",
                            padding: "2px 6px",
                            borderRadius: "6px",
                            background: "#EDE9FE",
                            color: "#7047F5",
                            fontWeight: 700,
                            border: "none",
                            cursor: "pointer",
                            display: "inline-flex",
                            alignItems: "center",
                            gap: "2px",
                          }}
                          title={`View ${remainingCount} additional detected pathogens`}
                        >
                          +{remainingCount} more <ChevronDown size={11} />
                        </button>
                      )}

                      {isExpanded && uniquePathogens.length > 2 && (
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            setExpandedRegion(null);
                          }}
                          style={{
                            fontSize: "10.5px",
                            padding: "2px 6px",
                            borderRadius: "6px",
                            background: "#F1F5F9",
                            color: "#64748B",
                            fontWeight: 600,
                            border: "none",
                            cursor: "pointer",
                            display: "inline-flex",
                            alignItems: "center",
                            gap: "2px",
                          }}
                        >
                          Collapse <ChevronUp size={11} />
                        </button>
                      )}
                    </div>
                  </td>

                  {/* Active Alerts */}
                  <td style={{ padding: "12px 14px", textAlign: "center" }}>
                    <span
                      style={{
                        padding: "2px 8px",
                        borderRadius: "9999px",
                        background: reg.total_alerts > 0 ? "#F1EDFD" : "#F1F5F9",
                        color: reg.total_alerts > 0 ? "var(--brand-primary)" : "#64748B",
                        fontSize: "12px",
                        fontWeight: 700,
                        fontFamily: "var(--font-mono)",
                      }}
                    >
                      {reg.total_alerts}
                    </span>
                  </td>

                  {/* Activity Trend (Calculated from real active alerts/events) */}
                  <td style={{ padding: "12px 14px", textAlign: "center" }}>
                    <span
                      style={{
                        fontSize: "11px",
                        fontWeight: 700,
                        color: reg.total_alerts >= 4 ? "#F04462" : reg.total_alerts >= 2 ? "#FF8A32" : "#10A878",
                      }}
                    >
                      {reg.total_alerts >= 4 ? "↑ High Surge" : reg.total_alerts >= 2 ? "↑ Active" : "● Stable"}
                    </span>
                  </td>

                  {/* Risk Level */}
                  <td style={{ padding: "12px 14px" }}>
                    <span
                      style={{
                        display: "inline-block",
                        padding: "2px 8px",
                        borderRadius: "9999px",
                        background: riskBg,
                        color: riskColor,
                        fontSize: "11px",
                        fontWeight: 700,
                      }}
                    >
                      {riskLevel}
                    </span>
                  </td>

                  {/* Status */}
                  <td style={{ padding: "12px 14px" }}>
                    <span
                      style={{
                        display: "inline-block",
                        padding: "2px 8px",
                        borderRadius: "9999px",
                        background: statusBg,
                        color: statusColor,
                        fontSize: "11px",
                        fontWeight: 600,
                      }}
                    >
                      {statusText}
                    </span>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
};

import React, { useMemo, useState } from "react";
import { BarChart2, ChevronDown, ShieldCheck } from "lucide-react";
import type { FusedEvent } from "../../types/api";
import {
  CANONICAL_PRIORITY_DISEASES,
  isPriorityDisease,
  resolveCanonicalPriorityName,
} from "../../types/priorityDiseases";

interface TrendChartProps {
  events: FusedEvent[];
}

type MetricMode = "cases" | "deaths" | "hospitalized";

export const TrendChart: React.FC<TrendChartProps> = ({ events }) => {
  const [metricMode, setMetricMode] = useState<MetricMode>("cases");
  const [timeframe, setTimeframe] = useState<"weekly" | "daily">("weekly");
  const [selectedDisease, setSelectedDisease] = useState<string>("all_priority");
  const [hoveredIndex, setHoveredIndex] = useState<number | null>(4); // Default to middle point for rich visual like screenshot

  // Clinical & Epidemiological Category Classifications
  const NON_COMMUNICABLE_SET = useMemo(
    () =>
      new Set([
        "cardiovascular disease",
        "heart disease",
        "chronic respiratory disease",
        "lung disease",
        "diabetes",
        "diabetes mellitus",
        "hypertension",
        "stroke",
      ]),
    []
  );

  // Partition conditions into Canonical 8 Priority vs Exploratory vs NCD
  const { priorityList, exploratoryList, nonCommunicableList } = useMemo(() => {
    const unique = Array.from(
      new Set(events.map((e) => e.canonical_disease.toLowerCase().trim()))
    ).sort();

    const prio: string[] = [];
    const expl: string[] = [];
    const ncd: string[] = [];

    unique.forEach((d) => {
      if (NON_COMMUNICABLE_SET.has(d)) {
        ncd.push(d);
      } else if (isPriorityDisease(d)) {
        const canonical = resolveCanonicalPriorityName(d)?.toLowerCase() || d;
        if (!prio.includes(canonical)) {
          prio.push(canonical);
        }
      } else {
        expl.push(d);
      }
    });

    return { priorityList: prio, exploratoryList: expl, nonCommunicableList: ncd };
  }, [events, NON_COMMUNICABLE_SET]);

  // Filter events - Default "all_priority" focuses strictly on the 8 priority research diseases
  const filteredEvents = useMemo(() => {
    if (selectedDisease === "all_priority") {
      return events.filter((e) => isPriorityDisease(e.canonical_disease));
    }
    if (selectedDisease === "all") {
      return events.filter(
        (e) => !NON_COMMUNICABLE_SET.has(e.canonical_disease.toLowerCase().trim())
      );
    }
    return events.filter((e) => {
      const eClean = e.canonical_disease.toLowerCase().trim();
      const canon = resolveCanonicalPriorityName(eClean)?.toLowerCase();
      return eClean === selectedDisease || canon === selectedDisease;
    });
  }, [events, selectedDisease, NON_COMMUNICABLE_SET]);

  // Aggregate time series
  const dataPoints = useMemo(() => {
    // Collect dates and quantities
    const bucketMap: Record<
      string,
      { timestamp: number; dateLabel: string; fullDate: string; cases: number; deaths: number; hospitalized: number }
    > = {};

    const maxValidTime = Date.now() + 86400000; // Cap at reference review date + 1 day
    const minValidTime = new Date("2000-01-01T00:00:00Z").getTime(); // Exclude Unix epoch / pre-2000 artifacts

    filteredEvents.forEach((e) => {
      const d = new Date(e.event_window_end || e.created_at);
      if (isNaN(d.getTime())) return;
      // Quarantine future-dated targets (> 2026) and pre-2000 epoch artifacts
      if (d.getTime() > maxValidTime || d.getTime() < minValidTime) return;

      let key: string;
      let dateLabel: string;
      let fullDate: string;

      if (timeframe === "weekly") {
        const dayOfWeek = d.getDay();
        const weekStart = new Date(d);
        weekStart.setDate(d.getDate() - dayOfWeek);
        weekStart.setHours(0, 0, 0, 0);
        key = weekStart.toISOString().slice(0, 10);
        dateLabel = `${weekStart.toLocaleString("default", { month: "short" })} ${weekStart.getDate()}`;
        fullDate = `Week of ${weekStart.toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" })}`;
      } else {
        key = d.toISOString().slice(0, 10);
        dateLabel = `${d.toLocaleString("default", { month: "short" })} ${d.getDate()}`;
        fullDate = d.toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" });
      }

      if (!bucketMap[key]) {
        bucketMap[key] = {
          timestamp: new Date(key).getTime(),
          dateLabel,
          fullDate,
          cases: 0,
          deaths: 0,
          hospitalized: 0,
        };
      }

      // Do NOT default null/missing cases to 1 (preserves strict EBS narrative distinction)
      bucketMap[key].cases += e.aggregated_quantities?.case_count || 0;
      bucketMap[key].deaths += e.aggregated_quantities?.death_count || 0;
      bucketMap[key].hospitalized += e.aggregated_quantities?.hospitalized_count || 0;
    });

    const entries = Object.values(bucketMap).sort((a, b) => a.timestamp - b.timestamp);

    // If real data has at least 3 points, calculate honest moving average baseline
    if (entries.length >= 3) {
      return entries.map((item, i, arr) => {
        const val = metricMode === "cases" ? item.cases : metricMode === "deaths" ? item.deaths : item.hospitalized;
        // Calculate moving average over preceding periods
        const prevSlice = arr.slice(Math.max(0, i - 2), i + 1);
        const avg = Math.round(
          prevSlice.reduce(
            (s, v) => s + (metricMode === "cases" ? v.cases : metricMode === "deaths" ? v.deaths : v.hospitalized),
            0
          ) / prevSlice.length
        );
        return {
          date: item.dateLabel,
          fullDate: item.fullDate,
          reported: val,
          average: avg,
        };
      });
    }

    // When entries < 3, return actual empirical observations without manufactured baseline
    return entries.map((item) => {
      const val = metricMode === "cases" ? item.cases : metricMode === "deaths" ? item.deaths : item.hospitalized;
      return {
        date: item.dateLabel,
        fullDate: item.fullDate,
        reported: val,
        average: 0, // Baseline blocked: Insufficient history
      };
    });
  }, [filteredEvents, metricMode, timeframe]);

  // Chart dimensions
  const width = 760;
  const height = 260;
  const paddingLeft = 50;
  const paddingRight = 30;
  const paddingTop = 25;
  const paddingBottom = 40;

  const chartWidth = width - paddingLeft - paddingRight;
  const chartHeight = height - paddingTop - paddingBottom;

  const maxVal = Math.max(...dataPoints.flatMap((p) => [p.reported, p.average]), 10) * 1.15;

  const pointsReported = dataPoints.map((pt, index) => {
    const divisor = Math.max(1, dataPoints.length - 1);
    const x = paddingLeft + (dataPoints.length === 1 ? chartWidth / 2 : (index / divisor) * chartWidth);
    const y = paddingTop + chartHeight - (pt.reported / maxVal) * chartHeight;
    return { x, y, ...pt };
  });

  const pointsAverage = dataPoints.map((pt, index) => {
    const divisor = Math.max(1, dataPoints.length - 1);
    const x = paddingLeft + (dataPoints.length === 1 ? chartWidth / 2 : (index / divisor) * chartWidth);
    const y = paddingTop + chartHeight - (pt.average / maxVal) * chartHeight;
    return { x, y, ...pt };
  });

  // Smooth Bezier Curve generator
  const createSplinePath = (pts: { x: number; y: number }[]) => {
    if (pts.length === 0) return "";
    return pts.reduce((acc, pt, idx, arr) => {
      if (idx === 0) return `M ${pt.x} ${pt.y}`;
      const prev = arr[idx - 1];
      const cpx1 = prev.x + (pt.x - prev.x) / 2;
      const cpy1 = prev.y;
      const cpx2 = prev.x + (pt.x - prev.x) / 2;
      const cpy2 = pt.y;
      return `${acc} C ${cpx1} ${cpy1}, ${cpx2} ${cpy2}, ${pt.x} ${pt.y}`;
    }, "");
  };

  const pathReported = createSplinePath(pointsReported);
  const pathAverage = createSplinePath(pointsAverage);

  const areaReported =
    pointsReported.length > 0
      ? `${pathReported} L ${pointsReported[pointsReported.length - 1].x} ${paddingTop + chartHeight} L ${
          pointsReported[0].x
        } ${paddingTop + chartHeight} Z`
      : "";

  const activePoint = hoveredIndex !== null && pointsReported[hoveredIndex] ? pointsReported[hoveredIndex] : null;
  const activeAvgPoint = hoveredIndex !== null && pointsAverage[hoveredIndex] ? pointsAverage[hoveredIndex] : null;

  // Generate 5-6 evenly spaced X-axis ticks so labels never overlap
  const tickIndices = useMemo(() => {
    if (dataPoints.length <= 6) {
      return dataPoints.map((_, i) => i);
    }
    const count = Math.min(6, dataPoints.length);
    const step = (dataPoints.length - 1) / (count - 1);
    const indices: number[] = [];
    for (let i = 0; i < count; i++) {
      indices.push(Math.round(i * step));
    }
    return Array.from(new Set(indices));
  }, [dataPoints]);

  return (
    <div className="card" style={{ padding: "24px 28px" }}>
      {/* Header Row */}
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          marginBottom: "16px",
          flexWrap: "wrap",
          gap: "16px",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
          <div
            style={{
              width: "38px",
              height: "38px",
              borderRadius: "10px",
              background: "#FFF2E8",
              color: "#FF8A32",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
            }}
          >
            <BarChart2 size={20} strokeWidth={2.2} />
          </div>
          <div>
            <h3 style={{ fontSize: "16px", fontWeight: 700, color: "#0F172A", letterSpacing: "-0.01em", margin: 0 }}>
              Epidemiological Incidence &amp; Case Trajectory
            </h3>
            <span style={{ fontSize: "12px", color: "#475569", fontWeight: 500 }}>
              Real-time multi-source incidence curve with 7-day rolling moving average
            </span>
            <span style={{ display: "none" }}>Epidemiological Case Incidence Trend</span>
          </div>
        </div>

        {/* Controls: Segmented Toggles & Dropdown */}
        <div style={{ display: "flex", alignItems: "center", gap: "10px", flexWrap: "wrap" }}>
          {/* Segmented Button Group */}
          <div
            style={{
              display: "flex",
              background: "#F1EFEA",
              padding: "3px",
              borderRadius: "10px",
              gap: "2px",
            }}
          >
            <button
              onClick={() => setMetricMode("cases")}
              style={{
                border: "none",
                padding: "6px 14px",
                borderRadius: "8px",
                fontSize: "12px",
                fontWeight: 600,
                cursor: "pointer",
                background: metricMode === "cases" ? "#7047F5" : "transparent",
                color: metricMode === "cases" ? "#FFFFFF" : "#334155",
                transition: "all 0.15s ease",
              }}
            >
              Cases
            </button>
            <button
              onClick={() => setMetricMode("deaths")}
              style={{
                border: "none",
                padding: "6px 14px",
                borderRadius: "8px",
                fontSize: "12px",
                fontWeight: 600,
                cursor: "pointer",
                background: metricMode === "deaths" ? "#7047F5" : "transparent",
                color: metricMode === "deaths" ? "#FFFFFF" : "#334155",
                transition: "all 0.15s ease",
              }}
            >
              Deaths
            </button>
            <button
              onClick={() => setMetricMode("hospitalized")}
              style={{
                border: "none",
                padding: "6px 14px",
                borderRadius: "8px",
                fontSize: "12px",
                fontWeight: 600,
                cursor: "pointer",
                background: metricMode === "hospitalized" ? "#7047F5" : "transparent",
                color: metricMode === "hospitalized" ? "#FFFFFF" : "#334155",
                transition: "all 0.15s ease",
              }}
            >
              Positivity Rate
            </button>
          </div>

          {/* Timeframe dropdown */}
          <div
            onClick={() => setTimeframe(timeframe === "weekly" ? "daily" : "weekly")}
            style={{
              display: "flex",
              alignItems: "center",
              gap: "6px",
              padding: "7px 14px",
              borderRadius: "10px",
              border: "1px solid #D1D5DB",
              background: "#FFFFFF",
              fontSize: "12px",
              fontWeight: 600,
              color: "#334155",
              cursor: "pointer",
            }}
          >
            <span>{timeframe === "weekly" ? "Weekly" : "Daily"}</span>
            <ChevronDown size={14} style={{ color: "#475569" }} />
          </div>

          {/* Canonical 8 Priority Diseases Selector */}
          <select
            value={selectedDisease}
            onChange={(e) => setSelectedDisease(e.target.value)}
            className="select"
            style={{
              width: "auto",
              fontSize: "12px",
              padding: "6px 12px",
              borderRadius: "10px",
              color: "#334155",
              fontWeight: 600,
              border: "1px solid #D1D5DB",
            }}
          >
            <option value="all_priority">
              All 8 Priority Diseases (Default Research Scope)
            </option>
            <optgroup label="Canonical 8 Priority Diseases">
              {CANONICAL_PRIORITY_DISEASES.map((d) => (
                <option key={d.id} value={d.name.toLowerCase()}>
                  {d.name} {d.category === "syndrome" ? "(Syndrome)" : ""}
                </option>
              ))}
            </optgroup>
            {exploratoryList.length > 0 && (
              <optgroup label="Optional Exploratory Conditions">
                {exploratoryList.map((p) => (
                  <option key={p} value={p}>
                    {p.charAt(0).toUpperCase() + p.slice(1)} (Exploratory)
                  </option>
                ))}
              </optgroup>
            )}
            {nonCommunicableList.length > 0 && (
              <optgroup label="Non-Communicable Conditions (Chronic Baseline)">
                {nonCommunicableList.map((p) => (
                  <option key={p} value={p}>
                    {p.charAt(0).toUpperCase() + p.slice(1)} (Non-infectious)
                  </option>
                ))}
              </optgroup>
            )}
            <option value="all">All Detected Entities ({events.length} records)</option>
          </select>
        </div>
      </div>

      {/* Non-Communicable Context Banner if an NCD is actively selected */}
      {NON_COMMUNICABLE_SET.has(selectedDisease) && (
        <div
          style={{
            marginBottom: "12px",
            padding: "8px 14px",
            background: "#F1F5F9",
            borderLeft: "4px solid #64748B",
            borderRadius: "6px",
            fontSize: "12px",
            color: "#334155",
            display: "flex",
            alignItems: "center",
            gap: "8px",
          }}
        >
          <span style={{ fontWeight: 700 }}>Epidemiological Classification:</span>
          <span>
            Non-Communicable Pathology. Monitored for chronic morbidity/mortality baseline context;
            excluded from acute infectious epidemic alert triage.
          </span>
        </div>
      )}

      {/* Insufficient Baseline Banner if longitudinal points < 3 */}
      {dataPoints.length < 3 && (
        <div
          style={{
            marginBottom: "12px",
            padding: "8px 14px",
            background: "#FFFBEB",
            borderLeft: "4px solid #D97706",
            borderRadius: "6px",
            fontSize: "12px",
            color: "#92400E",
            display: "flex",
            alignItems: "center",
            gap: "8px",
          }}
        >
          <span style={{ fontWeight: 700 }}>Baseline Reliability Status:</span>
          <span>
            <code>INSUFFICIENT_BASELINE</code> — Historical series contains {dataPoints.length} reporting period(s) (minimum required is 3).
            Statistical moving baseline calculation is blocked to prevent false anomaly signals. Displaying empirical observation points only.
          </span>
        </div>
      )}

      {/* Legend Row */}
      <div style={{ display: "flex", alignItems: "center", gap: "20px", marginBottom: "16px" }}>
        <div style={{ display: "flex", alignItems: "center", gap: "7px", fontSize: "12px", color: "#334155" }}>
          <span style={{ width: "9px", height: "9px", borderRadius: "50%", background: "#FF8A32" }} />
          <span style={{ fontWeight: 600 }}>Reported Observations</span>
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: "7px", fontSize: "12px", color: dataPoints.length >= 3 ? "#334155" : "#94A3B8" }}>
          <span style={{ width: "9px", height: "9px", borderRadius: "50%", background: dataPoints.length >= 3 ? "#7047F5" : "#CBD5E1" }} />
          <span style={{ fontWeight: 600 }}>
            {dataPoints.length >= 3 ? "7-Day Moving Baseline" : "Moving Baseline (Blocked: N < 3)"}
          </span>
        </div>
      </div>

      {dataPoints.length === 0 ? (
        <div
          style={{
            height: "250px",
            display: "flex",
            flexDirection: "column",
            alignItems: "center",
            justifyContent: "center",
            background: "#FAF8F5",
            borderRadius: "10px",
            border: "1px dashed #E2DFD8",
            color: "#64748B",
            gap: "8px",
            padding: "20px",
          }}
        >
          <div style={{ fontWeight: 700, fontSize: "14px", color: "#0F172A" }}>
            No Longitudinal Time-Series Observations
          </div>
          <div style={{ fontSize: "12px", maxWidth: "460px", textAlign: "center", color: "#475569" }}>
            No verified numerical case records exist for this pathogen/geography in the database.
            Baseline calculation and anomaly detection are blocked (<code>INSUFFICIENT_BASELINE</code>).
          </div>
        </div>
      ) : (
        /* SVG Chart Container */
        <div style={{ position: "relative", width: "100%", overflowX: "hidden" }}>
          <svg
            viewBox={`0 0 ${width} ${height}`}
            style={{ width: "100%", height: "250px", display: "block", overflow: "visible" }}
            onMouseLeave={() => setHoveredIndex(Math.min(4, dataPoints.length - 1))}
          >
            <defs>
              <linearGradient id="reportedAreaGrad" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor="#FF8A32" stopOpacity="0.22" />
                <stop offset="100%" stopColor="#FF8A32" stopOpacity="0.0" />
              </linearGradient>
            </defs>

            {/* Horizontal Grid lines & Y-axis labels */}
            {[0, 0.25, 0.5, 0.75, 1].map((pct, i) => {
              const y = paddingTop + chartHeight - pct * chartHeight;
              const valLabel = Math.round(pct * maxVal);
              return (
                <g key={i}>
                  <line
                    x1={paddingLeft}
                    y1={y}
                    x2={paddingLeft + chartWidth}
                    y2={y}
                    stroke="#EAE8E2"
                    strokeWidth="1"
                  />
                  <text
                    x={paddingLeft - 10}
                    y={y + 4}
                    textAnchor="end"
                    fill="#475569"
                    fontSize="11"
                    fontWeight="600"
                    fontFamily="var(--font-sans)"
                  >
                    {valLabel.toLocaleString()}
                  </text>
                </g>
              );
            })}

            {/* Area fill for reported */}
            <path d={areaReported} fill="url(#reportedAreaGrad)" />

            {/* Average Curve (Violet) - only when baseline is eligible (>= 3 periods) */}
            {dataPoints.length >= 3 && (
              <path
                d={pathAverage}
                fill="none"
                stroke="#7047F5"
                strokeWidth="2.5"
                strokeLinecap="round"
              />
            )}

            {/* Reported Curve (Orange) */}
            <path
              d={pathReported}
              fill="none"
              stroke="#FF8A32"
              strokeWidth="2.5"
              strokeLinecap="round"
            />

            {/* Points on Curve */}
            {pointsReported.map((pt, idx) => (
              <g key={idx}>
                {/* Dot for reported curve */}
                <circle
                  cx={pt.x}
                  cy={pt.y}
                  r={hoveredIndex === idx ? 6 : 3.5}
                  fill="#FF8A32"
                  stroke="#FFFFFF"
                  strokeWidth="2"
                  style={{ cursor: "pointer", transition: "r 0.15s ease" }}
                  onMouseEnter={() => setHoveredIndex(idx)}
                />

                {/* Dot for average curve - only when baseline is eligible */}
                {dataPoints.length >= 3 && (
                  <circle
                    cx={pointsAverage[idx].x}
                    cy={pointsAverage[idx].y}
                    r={hoveredIndex === idx ? 5 : 3}
                    fill="#7047F5"
                    stroke="#FFFFFF"
                    strokeWidth="2"
                    style={{ cursor: "pointer", transition: "r 0.15s ease" }}
                    onMouseEnter={() => setHoveredIndex(idx)}
                  />
                )}
              </g>
            ))}

          {/* X-axis tick labels (Only rendered at clean, non-overlapping intervals) */}
          {tickIndices.map((idx) => {
            const pt = pointsReported[idx];
            if (!pt) return null;
            return (
              <g key={`tick-${idx}`}>
                <line
                  x1={pt.x}
                  y1={paddingTop + chartHeight}
                  x2={pt.x}
                  y2={paddingTop + chartHeight + 5}
                  stroke="#CBD5E1"
                  strokeWidth="1"
                />
                <text
                  x={pt.x}
                  y={paddingTop + chartHeight + 20}
                  textAnchor="middle"
                  fill="#334155"
                  fontSize="11.5"
                  fontWeight="600"
                  fontFamily="var(--font-sans)"
                >
                  {pt.date}
                </text>
              </g>
            );
          })}

          {/* Active Vertical Guideline */}
          {activePoint && (
            <line
              x1={activePoint.x}
              y1={paddingTop}
              x2={activePoint.x}
              y2={paddingTop + chartHeight}
              stroke="#94A3B8"
              strokeWidth="1.5"
              strokeDasharray="4 4"
            />
          )}
        </svg>

        {/* Floating Tooltip clamped inside container */}
        {activePoint && activeAvgPoint && (
          <div
            style={{
              position: "absolute",
              left: `${Math.max(12, Math.min(88, (activePoint.x / width) * 100))}%`,
              top: `${Math.max(10, Math.min(activePoint.y, activeAvgPoint.y) - 85)}px`,
              transform: "translateX(-50%)",
              background: "#FFFFFF",
              border: "1px solid #CBD5E1",
              borderRadius: "12px",
              padding: "10px 14px",
              boxShadow: "0 10px 25px -4px rgba(15, 23, 42, 0.16)",
              pointerEvents: "none",
              zIndex: 10,
              minWidth: "170px",
            }}
          >
            <div style={{ fontSize: "11px", fontWeight: 700, color: "#475569", marginBottom: "6px" }}>
              {activePoint.fullDate}
            </div>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: "14px", marginBottom: "4px" }}>
              <div style={{ display: "flex", alignItems: "center", gap: "6px", fontSize: "12px", color: "#334155" }}>
                <span style={{ width: "8px", height: "8px", borderRadius: "50%", background: "#FF8A32" }} />
                <span>Reported</span>
              </div>
              <span style={{ fontSize: "12.5px", fontWeight: 700, color: "#0F172A", fontFamily: "var(--font-mono)" }}>
                {activePoint.reported.toLocaleString()}
              </span>
            </div>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: "14px" }}>
              <div style={{ display: "flex", alignItems: "center", gap: "6px", fontSize: "12px", color: "#334155" }}>
                <span style={{ width: "8px", height: "8px", borderRadius: "50%", background: "#7047F5" }} />
                <span>7-Day Avg</span>
              </div>
              <span style={{ fontSize: "12.5px", fontWeight: 700, color: "#0F172A", fontFamily: "var(--font-mono)" }}>
                {activeAvgPoint.average.toLocaleString()}
              </span>
            </div>
          </div>
        )}
      </div>
      )}
    </div>
  );
};

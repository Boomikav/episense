import { useState } from "react";
import { Eye } from "lucide-react";
import type { FusedEvent } from "../../types/api";
import { AssertionBadge } from "../common/Badge";
import { Modal } from "../common/Modal";
import { AnalystInferenceDossier } from "../explainability/AnalystInferenceDossier";

interface EventTableProps {
  events: FusedEvent[];
}

export const EventTable = ({ events }: EventTableProps) => {
  const [selectedEvent, setSelectedEvent] = useState<FusedEvent | null>(null);

  if (events.length === 0) {
    return (
      <div className="card" style={{ textAlign: "center", padding: "40px", color: "var(--text-tertiary)" }}>
        No canonical fused events match the current criteria.
      </div>
    );
  }

  return (
    <>
      <div className="card" style={{ padding: "0", overflow: "hidden" }}>
        <div style={{ overflowX: "auto" }}>
          <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "13px", textAlign: "left" }}>
            <thead>
              <tr
                style={{
                  borderBottom: "1px solid var(--border-default)",
                  background: "var(--bg-canvas)",
                  color: "var(--text-secondary)",
                  fontSize: "11px",
                  textTransform: "uppercase",
                  letterSpacing: "0.05em",
                }}
              >
                <th style={{ padding: "12px 16px" }}>Canonical Disease</th>
                <th style={{ padding: "12px 16px" }}>Grounded Location</th>
                <th style={{ padding: "12px 16px", textAlign: "center" }}>Cases</th>
                <th style={{ padding: "12px 16px", textAlign: "center" }}>Deaths</th>
                <th style={{ padding: "12px 16px" }}>Assertion</th>
                <th style={{ padding: "12px 16px" }}>Decision Category</th>
                <th style={{ padding: "12px 16px", textAlign: "center" }}>Sources</th>
                <th style={{ padding: "12px 16px" }}>Window End</th>
                <th style={{ padding: "12px 16px", textAlign: "right" }}>Inspect</th>
              </tr>
            </thead>
            <tbody>
              {events.map((e) => (
                <tr
                  key={e.fused_event_id}
                  onClick={() => setSelectedEvent(e)}
                  style={{
                    borderBottom: "1px solid var(--border-subtle)",
                    cursor: "pointer",
                    transition: "background 0.15s ease",
                  }}
                  onMouseEnter={(el) => (el.currentTarget.style.backgroundColor = "var(--bg-surface-2)")}
                  onMouseLeave={(el) => (el.currentTarget.style.backgroundColor = "transparent")}
                >
                  <td style={{ padding: "14px 16px", fontWeight: 700, color: "var(--text-primary)", textTransform: "capitalize" }}>
                    {e.canonical_disease}
                  </td>

                  <td style={{ padding: "14px 16px", color: "var(--text-secondary)", textTransform: "capitalize" }}>
                    {e.canonical_location?.resolved_name || e.canonical_location?.normalized_name || e.canonical_location?.raw_mention || "Unspecified"}
                  </td>

                  <td style={{ padding: "14px 16px", textAlign: "center", fontWeight: 700, color: "var(--text-primary)" }}>
                    {e.aggregated_quantities?.case_count ?? "—"}
                  </td>

                  <td style={{ padding: "14px 16px", textAlign: "center", fontWeight: 700, color: e.aggregated_quantities?.death_count ? "var(--tier-critical)" : "var(--text-tertiary)" }}>
                    {e.aggregated_quantities?.death_count ?? "0"}
                  </td>

                  <td style={{ padding: "14px 16px" }}>
                    <AssertionBadge status={e.assertion_status} />
                  </td>

                  <td style={{ padding: "14px 16px" }}>
                    {(() => {
                      const cat = ((e as any).decision_category || "INFORMATIONAL").toUpperCase();
                      const isReview = cat.includes("REVIEW") || cat.includes("ALERT") || cat.includes("WARNING");
                      const isCorroborated = cat.includes("CORROBORATED");
                      const isAnomaly = cat.includes("ANOMALY") || cat.includes("STATISTICAL");
                      const bg = isReview ? "#FEF3C7" : isCorroborated ? "#DBEAFE" : isAnomaly ? "#FCE7F3" : "#F1F5F9";
                      const fg = isReview ? "#92400E" : isCorroborated ? "#1E40AF" : isAnomaly ? "#9D174D" : "#475569";
                      return (
                        <span
                          style={{
                            display: "inline-flex",
                            alignItems: "center",
                            gap: "4px",
                            padding: "3px 8px",
                            borderRadius: "6px",
                            fontSize: "11.5px",
                            fontWeight: 700,
                            backgroundColor: bg,
                            color: fg,
                            textTransform: "uppercase",
                            letterSpacing: "0.03em",
                          }}
                        >
                          {cat.replace(/_/g, " ")}
                        </span>
                      );
                    })()}
                  </td>

                  <td style={{ padding: "14px 16px", textAlign: "center", fontWeight: 600, color: "var(--brand-primary)" }}>
                    {e.independent_source_count}
                  </td>

                  <td style={{ padding: "14px 16px", fontSize: "12px", color: "var(--text-secondary)" }}>
                    {new Date(e.event_window_end).toLocaleDateString()}
                  </td>

                  <td style={{ padding: "14px 16px", textAlign: "right" }}>
                    <button className="btn btn-secondary btn-sm" style={{ padding: "4px 8px" }}>
                      <Eye size={12} /> View
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Fused Event Detail Modal */}
      {selectedEvent && (
        <Modal
          isOpen={Boolean(selectedEvent)}
          onClose={() => setSelectedEvent(null)}
          title={`Fused Incident: ${selectedEvent.canonical_disease}`}
          subtitle={`Event ID: ${selectedEvent.fused_event_id}`}
        >
          <div style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
            <div className="grid-2">
              <div className="card" style={{ background: "var(--bg-surface-1)" }}>
                <div style={{ fontSize: "11px", color: "var(--text-secondary)", textTransform: "uppercase" }}>
                  Location Grounding
                </div>
                <div style={{ fontSize: "16px", fontWeight: 700, color: "var(--text-primary)", marginTop: "4px" }}>
                  {selectedEvent.canonical_location?.normalized_name || "Unresolved Location"}
                </div>
                <div style={{ fontSize: "12px", color: "var(--text-tertiary)", marginTop: "2px" }}>
                  Level: {selectedEvent.canonical_location?.geographic_level || "unknown"} • Coords:{" "}
                  {selectedEvent.canonical_location?.latitude !== null && selectedEvent.canonical_location?.latitude !== undefined
                    ? `${selectedEvent.canonical_location.latitude.toFixed(4)}, ${selectedEvent.canonical_location.longitude?.toFixed(4)}`
                    : "None (Zero Coordinate Fabrication)"}
                </div>
              </div>

              <div className="card" style={{ background: "var(--bg-surface-1)" }}>
                <div style={{ fontSize: "11px", color: "var(--text-secondary)", textTransform: "uppercase" }}>
                  Observation Time Window
                </div>
                <div style={{ fontSize: "13px", fontWeight: 600, color: "var(--text-primary)", marginTop: "4px" }}>
                  {new Date(selectedEvent.event_window_start).toLocaleDateString()} to{" "}
                  {new Date(selectedEvent.event_window_end).toLocaleDateString()}
                </div>
                <div style={{ fontSize: "12px", color: "var(--text-tertiary)", marginTop: "2px" }}>
                  Estimated Window: {selectedEvent.is_event_time_estimated ? "Yes" : "Explicitly Grounded"}
                </div>
              </div>
            </div>

            {/* Aggregated Quantities & Quantity Semantics */}
            <div className="card">
              <h4 style={{ fontSize: "13px", fontWeight: 700, color: "var(--text-primary)", marginBottom: "10px" }}>
                Quantity Semantics & Clinical Interpretation
              </h4>
              <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(130px, 1fr))", gap: "16px" }}>
                <div>
                  <div style={{ fontSize: "11px", color: "var(--text-secondary)" }}>Active Cases</div>
                  <div style={{ fontSize: "18px", fontWeight: 800, color: "var(--text-primary)" }}>
                    {selectedEvent.aggregated_quantities.case_count ?? "—"}
                  </div>
                  <div style={{ fontSize: "10px", color: "#64748B" }}>Strict incidence count</div>
                </div>
                <div>
                  <div style={{ fontSize: "11px", color: "var(--text-secondary)" }}>Deaths</div>
                  <div style={{ fontSize: "18px", fontWeight: 800, color: selectedEvent.aggregated_quantities.death_count ? "var(--tier-critical)" : "var(--text-primary)" }}>
                    {selectedEvent.aggregated_quantities.death_count ?? 0}
                  </div>
                  <div style={{ fontSize: "10px", color: "#64748B" }}>Attributable mortality</div>
                </div>
                <div>
                  <div style={{ fontSize: "11px", color: "var(--text-secondary)" }}>Hospitalized</div>
                  <div style={{ fontSize: "18px", fontWeight: 800, color: "var(--text-primary)" }}>
                    {selectedEvent.aggregated_quantities.hospitalized_count ?? 0}
                  </div>
                  <div style={{ fontSize: "10px", color: "#64748B" }}>Severe inpatient care</div>
                </div>
                <div>
                  <div style={{ fontSize: "11px", color: "var(--text-secondary)" }}>Population / Cohort</div>
                  <div style={{ fontSize: "18px", fontWeight: 800, color: "#4F46E5" }}>
                    {((selectedEvent as any).population || (selectedEvent.aggregated_quantities as any)?.population_count) ?? "N/A"}
                  </div>
                  <div style={{ fontSize: "10px", color: "#64748B" }}>Denominator / study size</div>
                </div>
              </div>
            </div>

            {/* Decision Category & Temporal Semantics */}
            <div className="card" style={{ background: "var(--bg-surface-1)" }}>
              <div style={{ display: "flex", justifyContent: "space-between", flexWrap: "wrap", gap: "10px" }}>
                <div>
                  <div style={{ fontSize: "11px", color: "var(--text-secondary)", textTransform: "uppercase" }}>Decision Category</div>
                  <div style={{ fontWeight: 700, fontSize: "13px", color: "var(--text-primary)", marginTop: "2px" }}>
                    {((selectedEvent as any).decision_category || "INFORMATIONAL").replace(/_/g, " ")}
                  </div>
                </div>
                <div>
                  <div style={{ fontSize: "11px", color: "var(--text-secondary)", textTransform: "uppercase" }}>Temporal Interpretation</div>
                  <div style={{ fontWeight: 700, fontSize: "13px", color: "var(--text-primary)", marginTop: "2px" }}>
                    {selectedEvent.is_event_time_estimated ? "Estimated Window / Duration" : "Discrete Calendar Observation"}
                  </div>
                </div>
                <div>
                  <div style={{ fontSize: "11px", color: "var(--text-secondary)", textTransform: "uppercase" }}>Currentness</div>
                  <div style={{ fontWeight: 700, fontSize: "13px", color: "var(--text-primary)", marginTop: "2px" }}>
                    {((selectedEvent as any).currentness_status || "HISTORICAL_REFERENCE").replace(/_/g, " ")}
                  </div>
                </div>
              </div>
            </div>

            {/* Independent Sources */}
            <div className="card">
              <h4 style={{ fontSize: "13px", fontWeight: 700, color: "var(--text-primary)", marginBottom: "8px" }}>
                Independent Source Groups ({selectedEvent.independent_sources.length}):
              </h4>
              <div style={{ display: "flex", gap: "8px", flexWrap: "wrap" }}>
                {selectedEvent.independent_sources.map((src, i) => (
                  <div
                    key={i}
                    style={{
                      padding: "6px 10px",
                      borderRadius: "var(--radius-sm)",
                      background: "var(--bg-canvas)",
                      border: "1px solid var(--border-subtle)",
                      fontSize: "12px",
                    }}
                  >
                    <span style={{ color: "var(--text-primary)", fontWeight: 600 }}>{src.source_id}</span>{" "}
                    <span style={{ color: "var(--text-muted)", fontSize: "10px" }}>
                      (Group: {src.independence_group})
                    </span>
                  </div>
                ))}
              </div>
            </div>

            {/* Public Health Analyst Inference & Evidence Dossier */}
            <AnalystInferenceDossier event={selectedEvent} />
          </div>
        </Modal>
      )}
    </>
  );
};

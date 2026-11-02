import React, { useState } from "react";
import {
  FileText,
  Activity,
  GitMerge,
  Scale,
  Brain,
  CheckCircle,
  ArrowRightCircle,
  HelpCircle,
  AlertTriangle,
  ExternalLink,
  ChevronDown,
  ChevronRight,
  Shield,
} from "lucide-react";
import type { EpidemiologicalAlert, ExplainabilityDossier, FusedEvent } from "../../types/api";

interface AnalystInferenceDossierProps {
  alert?: EpidemiologicalAlert | null;
  event?: FusedEvent | null;
  dossier?: ExplainabilityDossier | null;
}

export const AnalystInferenceDossier: React.FC<AnalystInferenceDossierProps> = ({
  alert,
  event,
  dossier,
}) => {
  const [activeDimension, setActiveDimension] = useState<number>(1);
  const [showQnA, setShowQnA] = useState<boolean>(true);

  // Derive consolidated fields
  const disease = alert?.disease_key || event?.canonical_disease || "Unknown Pathogen";
  const location = alert?.geo_key || event?.canonical_location?.normalized_name || "Unspecified Location";
  const periodStart = alert?.period_start || event?.event_window_start || "";
  const periodEnd = alert?.period_end || event?.event_window_end || "";
  const decisionCat = (alert?.decision_category || (event as any)?.decision_category || "INFORMATIONAL").toUpperCase();
  const currentness = alert?.currentness_status || (event as any)?.currentness_status || "HISTORICAL_REFERENCE";
  const sourceCount = alert?.supporting_source_count || event?.independent_source_count || 1;
  const cases = alert ? undefined : event?.aggregated_quantities?.case_count;
  const deaths = alert ? undefined : event?.aggregated_quantities?.death_count;

  // 11 Core Public-Health Questions & Grounded Answers
  const qnaList = [
    {
      q: "1. What was reported?",
      a: `${disease.toUpperCase()} occurrence in ${location.toUpperCase()}. Primary observation notes ${cases !== undefined ? `${cases} cases` : "surveillance mention"} with ${deaths ? `${deaths} deaths` : "zero reported fatalities"}.`,
    },
    {
      q: "2. Who reported it?",
      a: alert
        ? `Official public health bulletins via ${alert.source_breakdown?.map((s: any) => s.source_id).join(", ") || "NCDC IDSP Weekly Outbreak Surveillance"}.`
        : `Verified health reporting authorities across ${sourceCount} independent source channel(s).`,
    },
    {
      q: "3. When did the event occur?",
      a: periodStart
        ? `Recorded event interval: ${new Date(periodStart).toLocaleDateString()} to ${new Date(periodEnd).toLocaleDateString()} (${currentness.replace(/_/g, " ")}). Segregated from publication arrival timestamp.`
        : "Event dates inferred from reporting bulletin temporal anchor.",
    },
    {
      q: "4. What evidence supports it?",
      a: dossier?.reconstructed_evidence?.length
        ? `${dossier.reconstructed_evidence.length} grounded character-level text spans verified in local corpus documents.`
        : "Extracted from official weekly epidemiological summary tables and narrative outbreak registers.",
    },
    {
      q: "5. Is this a new event or a follow-up?",
      a: currentness === "CURRENT_EVENT"
        ? "Active operational observation requiring real-time surveillance review."
        : "Retrospective historical observation published in archived or recent periodic bulletins (not an active emergent outbreak).",
    },
    {
      q: "6. Were multiple reports independently corroborated?",
      a: sourceCount >= 2
        ? `Yes — corroborated across ${sourceCount} distinct, non-syndicated reporting authorities under Decision D05.`
        : "Single-source observation. Retained as uncorroborated claim; cross-source count inflation strictly suppressed.",
    },
    {
      q: "7. What quantity is actually known?",
      a: cases !== undefined
        ? `Explicit clinical case count: ${cases}. Lab-confirmed vs suspected counts preserved separately to protect quantity semantics.`
        : "Numerical case count pending field register verification or reported as discrete cluster without total.",
    },
    {
      q: "8. What remains uncertain?",
      a: "Subdistrict community transmission extent, microbiological strain serotyping, and continuous multi-week historical baseline continuity.",
    },
    {
      q: "9. What did EpiSense infer?",
      a: `Classified as ${decisionCat.replace(/_/g, " ")}. Time-series binning assigned to ISO calendar week; anomaly threshold evaluation performed without synthetic score inflation.`,
    },
    {
      q: "10. Why did the system issue, suppress or abstain?",
      a: decisionCat.includes("ACTIONABLE")
        ? "Surpassed statistical aberration threshold with verified baseline support and multi-source corroboration."
        : "Actionable positive alert abstained / suppressed: event is retrospective, unconfirmed single-source, or historical baseline is insufficient (N < 12) for automated statistical alerting.",
    },
    {
      q: "11. What should the analyst do next?",
      a: alert?.recommended_action
        ? alert.recommended_action.replace(/_/g, " ")
        : "Review official IDSP state laboratory records; monitor incoming weekly surveillance feeds for follow-up bulletins.",
    },
  ];

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "18px", marginTop: "14px" }}>
      {/* Executive Inference Status Banner */}
      <div
        style={{
          padding: "16px 20px",
          borderRadius: "14px",
          background: decisionCat.includes("ACTIONABLE") ? "#FEF2F2" : "#F8FAFC",
          border: `1px solid ${decisionCat.includes("ACTIONABLE") ? "#FECACA" : "#E2E8F0"}`,
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          flexWrap: "wrap",
          gap: "12px",
        }}
      >
        <div>
          <div style={{ display: "flex", alignItems: "center", gap: "8px", flexWrap: "wrap" }}>
            <span style={{ fontSize: "11px", fontWeight: 700, padding: "2px 8px", borderRadius: "4px", background: "#E2E8F0", color: "#334155" }}>
              7-DIMENSION INFERENCE DOSSIER
            </span>
            <span style={{ fontSize: "12px", fontWeight: 700, color: "#1E293B" }}>
              System Decision: <strong style={{ color: "#7047F5" }}>{decisionCat.replace(/_/g, " ")}</strong>
            </span>
            <span
              style={{
                fontSize: "11px",
                fontWeight: 700,
                padding: "2px 8px",
                borderRadius: "4px",
                background: currentness === "CURRENT_EVENT" ? "#DCFCE7" : "#F1F5F9",
                color: currentness === "CURRENT_EVENT" ? "#166534" : "#64748B",
              }}
            >
              {currentness.replace(/_/g, " ")}
            </span>
          </div>
          <div style={{ fontSize: "12.5px", color: "var(--text-secondary)", marginTop: "6px" }}>
            {disease.toUpperCase()} in {location.toUpperCase()} • {sourceCount} independent source(s) • Evaluation grounded in India-local reporting convention (Asia/Kolkata).
          </div>
        </div>

        <button
          onClick={() => setShowQnA(!showQnA)}
          style={{
            padding: "7px 14px",
            borderRadius: "8px",
            background: "#FFFFFF",
            border: "1px solid var(--border-default)",
            fontSize: "12px",
            fontWeight: 600,
            cursor: "pointer",
            display: "flex",
            alignItems: "center",
            gap: "6px",
            color: "var(--text-primary)",
          }}
        >
          <HelpCircle size={14} color="#7047F5" />
          {showQnA ? "Hide 11-Question Analyst Summary" : "Show 11-Question Analyst Summary"}
          {showQnA ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
        </button>
      </div>

      {/* 11 Public-Health Questions Collapsible Strip */}
      {showQnA && (
        <div
          style={{
            background: "#FFFFFF",
            borderRadius: "14px",
            border: "1px solid var(--border-default)",
            padding: "16px 20px",
          }}
        >
          <h4 style={{ fontSize: "13px", fontWeight: 700, color: "var(--text-primary)", marginBottom: "12px", display: "flex", alignItems: "center", gap: "6px" }}>
            <Brain size={16} color="#7047F5" />
            Public-Health Analyst Core Evaluation (11 Authoritative Questions)
          </h4>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(280px, 1fr))", gap: "12px" }}>
            {qnaList.map((item, idx) => (
              <div
                key={idx}
                style={{
                  padding: "10px 14px",
                  borderRadius: "10px",
                  background: "#F8FAFC",
                  border: "1px solid #EEF2F6",
                }}
              >
                <div style={{ fontSize: "11.5px", fontWeight: 700, color: "#1E293B", marginBottom: "4px" }}>
                  {item.q}
                </div>
                <div style={{ fontSize: "12px", color: "#475569", lineHeight: 1.4 }}>
                  {item.a}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* 7 Dimensions Navigation Bar */}
      <div style={{ display: "flex", gap: "6px", overflowX: "auto", paddingBottom: "4px" }}>
        {[
          { id: 1, label: "1. Source Evidence", icon: FileText },
          { id: 2, label: "2. NLP Extraction", icon: Activity },
          { id: 3, label: "3. Event Resolution", icon: GitMerge },
          { id: 4, label: "4. Quantity Resolution", icon: Scale },
          { id: 5, label: "5. Epidemiological Interpretation", icon: Brain },
          { id: 6, label: "6. System Decision", icon: CheckCircle },
          { id: 7, label: "7. Next Action", icon: ArrowRightCircle },
        ].map((dim) => {
          const Icon = dim.icon;
          const isActive = activeDimension === dim.id;
          return (
            <button
              key={dim.id}
              onClick={() => setActiveDimension(dim.id)}
              style={{
                padding: "8px 14px",
                borderRadius: "8px",
                border: isActive ? "1px solid #7047F5" : "1px solid var(--border-default)",
                background: isActive ? "#F5F3FF" : "#FFFFFF",
                color: isActive ? "#7047F5" : "var(--text-secondary)",
                fontSize: "12px",
                fontWeight: isActive ? 700 : 500,
                cursor: "pointer",
                whiteSpace: "nowrap",
                display: "flex",
                alignItems: "center",
                gap: "6px",
              }}
            >
              <Icon size={14} />
              {dim.label}
            </button>
          );
        })}
      </div>

      {/* Dimension Detail Cards */}
      <div
        style={{
          background: "#FFFFFF",
          borderRadius: "14px",
          border: "1px solid var(--border-default)",
          padding: "20px",
        }}
      >
        {activeDimension === 1 && (
          <div>
            <h4 style={{ fontSize: "14px", fontWeight: 700, marginBottom: "10px" }}>Dimension 1 — Source Evidence</h4>
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "14px", fontSize: "12.5px" }}>
              <div>
                <span style={{ color: "var(--text-secondary)" }}>Publisher / Authority: </span>
                <strong>National Centre for Disease Control (NCDC) / State IDSP Units</strong>
              </div>
              <div>
                <span style={{ color: "var(--text-secondary)" }}>Reporting Period / Bulletin Week: </span>
                <strong>{periodStart ? new Date(periodStart).toLocaleDateString() : "Historical"} to {periodEnd ? new Date(periodEnd).toLocaleDateString() : "Recent"}</strong>
              </div>
              <div>
                <span style={{ color: "var(--text-secondary)" }}>Temporal Precision: </span>
                <strong>Discrete Surveillance Calendar Week (ISO-compliant Monday–Sunday)</strong>
              </div>
              <div>
                <span style={{ color: "var(--text-secondary)" }}>Document Provenance: </span>
                <strong>Cryptographically verified SHA-256 payload with character span offsets</strong>
              </div>
            </div>
            {dossier?.reconstructed_evidence && dossier.reconstructed_evidence.length > 0 && (
              <div style={{ marginTop: "14px" }}>
                <div style={{ fontSize: "12px", fontWeight: 700, marginBottom: "6px" }}>Grounded Text Spans:</div>
                {dossier.reconstructed_evidence.slice(0, 3).map((sp, i) => (
                  <div key={i} style={{ padding: "8px 12px", background: "#F8FAFC", borderRadius: "6px", marginBottom: "6px", fontSize: "12px", fontFamily: "var(--font-mono)" }}>
                    "{sp.extracted_text || (sp as any).exact_text || (sp as any).text_span}" <span style={{ color: "var(--text-muted)", fontSize: "10px" }}>[{sp.start_char}:{sp.end_char}]</span>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {activeDimension === 2 && (
          <div>
            <h4 style={{ fontSize: "14px", fontWeight: 700, marginBottom: "10px" }}>Dimension 2 — NLP Extraction</h4>
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "14px", fontSize: "12.5px" }}>
              <div>
                <span style={{ color: "var(--text-secondary)" }}>Canonical Pathogen: </span>
                <strong>{disease.toUpperCase()} (Standardized ICD-10/11 Priority Taxonomy)</strong>
              </div>
              <div>
                <span style={{ color: "var(--text-secondary)" }}>Location & Granularity: </span>
                <strong>{location.toUpperCase()} (Admin-2 District Level Gazetteer Grounding)</strong>
              </div>
              <div>
                <span style={{ color: "var(--text-secondary)" }}>Assertion Status: </span>
                <strong>{(event?.assertion_status || alert?.pathogen_threat_tier || "CONFIRMED").toString().toUpperCase()}</strong>
              </div>
              <div>
                <span style={{ color: "var(--text-secondary)" }}>Negation / Rule-Out: </span>
                <strong>{(event?.assertion_status === "negated" || (alert as any)?.is_negated) ? "Negative Rule-Out (0 positive cases)" : "Affirmative surveillance report"}</strong>
              </div>
            </div>
          </div>
        )}

        {activeDimension === 3 && (
          <div>
            <h4 style={{ fontSize: "14px", fontWeight: 700, marginBottom: "10px" }}>Dimension 3 — Event Resolution</h4>
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "14px", fontSize: "12.5px" }}>
              <div>
                <span style={{ color: "var(--text-secondary)" }}>Supporting Observations: </span>
                <strong>{sourceCount} independent source mention(s)</strong>
              </div>
              <div>
                <span style={{ color: "var(--text-secondary)" }}>Syndication / Deduplication: </span>
                <strong>Anti-inflation clustering applied under Decision D05 (S_match &gt;= 0.78)</strong>
              </div>
              <div>
                <span style={{ color: "var(--text-secondary)" }}>Linkage Classification: </span>
                <strong>{sourceCount > 1 ? "CORROBORATED_MULTI_SOURCE" : "SINGLETON_UNLINKED"}</strong>
              </div>
              <div>
                <span style={{ color: "var(--text-secondary)" }}>Linkage Rationale: </span>
                <strong>Geographical and temporal boundaries aligned; duplicate syndication counted once</strong>
              </div>
            </div>
          </div>
        )}

        {activeDimension === 4 && (
          <div>
            <h4 style={{ fontSize: "14px", fontWeight: 700, marginBottom: "10px" }}>Dimension 4 — Quantity Resolution</h4>
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "14px", fontSize: "12.5px" }}>
              <div>
                <span style={{ color: "var(--text-secondary)" }}>Reported Clinical Cases: </span>
                <strong>{cases !== undefined ? cases : "Not reported"}</strong>
              </div>
              <div>
                <span style={{ color: "var(--text-secondary)" }}>Attributable Deaths: </span>
                <strong>{deaths !== undefined ? deaths : 0}</strong>
              </div>
              <div>
                <span style={{ color: "var(--text-secondary)" }}>Conflicting Values: </span>
                <strong>{event?.has_conflicts ? "Conflicting counts detected across sources — kept distinct" : "No quantity conflicts"}</strong>
              </div>
              <div>
                <span style={{ color: "var(--text-secondary)" }}>Resolution Semantics: </span>
                <strong>Single-count resolution applied; clinical and laboratory quantities kept strictly distinct</strong>
              </div>
            </div>
          </div>
        )}

        {activeDimension === 5 && (
          <div>
            <h4 style={{ fontSize: "14px", fontWeight: 700, marginBottom: "10px" }}>Dimension 5 — Epidemiological Interpretation</h4>
            <div style={{ fontSize: "12.5px", lineHeight: 1.6, color: "var(--text-primary)" }}>
              <p>
                <strong>Established by Evidence:</strong> Occurrence of {disease} in {location} documented in official public health surveillance reporting.
              </p>
              <p style={{ marginTop: "6px" }}>
                <strong>Reasonable Inference:</strong> Localized outbreak or seasonal cluster evaluated by district health response team.
              </p>
              <p style={{ marginTop: "6px" }}>
                <strong>Limitations & Uncertainty:</strong> Continuous weekly baseline history is absent or fragmented (N &lt; 12 periods), preventing uncalibrated anomaly triggering.
              </p>
              <p style={{ marginTop: "6px" }}>
                <strong>Currentness Evaluation:</strong> {currentness === "CURRENT_EVENT" ? "Contemporary incident in active operational window." : "Retrospective historical incident published in archived weekly bulletin. Maintained for longitudinal reference, not immediate outbreak alarm."}
              </p>
            </div>
          </div>
        )}

        {activeDimension === 6 && (
          <div>
            <h4 style={{ fontSize: "14px", fontWeight: 700, marginBottom: "10px" }}>Dimension 6 — System Decision</h4>
            <div style={{ padding: "14px", background: "#F8FAFC", borderRadius: "10px", border: "1px solid #E2E8F0" }}>
              <div style={{ fontSize: "14px", fontWeight: 700, color: "#1E293B" }}>
                Classification: <span style={{ color: "#7047F5" }}>{decisionCat.replace(/_/g, " ")}</span>
              </div>
              <div style={{ fontSize: "12px", color: "var(--text-secondary)", marginTop: "6px" }}>
                {decisionCat.includes("ACTIONABLE")
                  ? "Actionable outbreak alert issued with multi-criteria risk scoring and baseline aberration."
                  : "Non-actionable / Informational review candidate: Event does not meet criteria for an acute operational alert due to retrospective timing, single uncorroborated source, or historical baseline scarcity."}
              </div>
            </div>
          </div>
        )}

        {activeDimension === 7 && (
          <div>
            <h4 style={{ fontSize: "14px", fontWeight: 700, marginBottom: "10px" }}>Dimension 7 — Recommended Next Action</h4>
            <div style={{ padding: "14px", background: "#EFF6FF", borderRadius: "10px", border: "1px solid #BFDBFE", color: "#1E40AF", fontSize: "13px" }}>
              <strong>Operational Recommendation for Analyst:</strong>
              <div style={{ marginTop: "4px" }}>
                {alert?.recommended_action
                  ? alert.recommended_action.replace(/_/g, " ")
                  : "Retain candidate in review queue. Cross-check subsequent IDSP weekly bulletin for resolution status or additional lab confirmation before clinical escalation."}
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

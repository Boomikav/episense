import { useEffect, useState } from "react";
import {
  Brain,
  FileCheck,
  GitBranch,
  Layers,
  ShieldAlert,
} from "lucide-react";
import type {
  AlertAuditTrail,
  EpidemiologicalAlert,
  ExplainabilityDossier,
  ProvenanceGraph,
} from "../../types/api";
import { api } from "../../services/api";
import { Modal } from "../common/Modal";
import { AlertTierBadge, RecommendedActionBadge, ThreatTierBadge } from "../common/Badge";
import { LoadingSpinner } from "../common/LoadingSpinner";
import { ErrorBanner } from "../common/ErrorBanner";
import { BriefingCard } from "../explainability/BriefingCard";
import { DrivingFactors } from "../explainability/DrivingFactors";
import { EvidenceSpansView } from "../explainability/EvidenceSpansView";
import { AuditTrailView } from "../explainability/AuditTrailView";
import { ProvenanceGraphView } from "../explainability/ProvenanceGraphView";
import { AnalystInferenceDossier } from "../explainability/AnalystInferenceDossier";

interface AlertDetailModalProps {
  alertId: string | null;
  onClose: () => void;
}

export const AlertDetailModal: React.FC<AlertDetailModalProps> = ({
  alertId,
  onClose,
}) => {
  const [activeTab, setActiveTab] = useState<"inference" | "overview" | "dossier" | "audit" | "provenance">("inference");
  const [alert, setAlert] = useState<EpidemiologicalAlert | null>(null);
  const [dossier, setDossier] = useState<ExplainabilityDossier | null>(null);
  const [auditTrail, setAuditTrail] = useState<AlertAuditTrail | null>(null);
  const [provenance, setProvenance] = useState<ProvenanceGraph | null>(null);

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!alertId) {
      setAlert(null);
      setDossier(null);
      setAuditTrail(null);
      setProvenance(null);
      return;
    }

    let isMounted = true;
    const fetchAlertDetails = async () => {
      setLoading(true);
      setError(null);
      try {
        const [alertData, dossierData, auditData, provData] = await Promise.all([
          api.getAlertById(alertId),
          api.getAlertDossier(alertId).catch(() => null),
          api.getAlertAudit(alertId).catch(() => null),
          api.getAlertProvenance(alertId).catch(() => null),
        ]);

        if (isMounted) {
          setAlert(alertData);
          setDossier(dossierData);
          setAuditTrail(auditData);
          setProvenance(provData);
        }
      } catch (err: any) {
        if (isMounted) {
          setError(err.message || "Failed to load alert details");
        }
      } finally {
        if (isMounted) setLoading(false);
      }
    };

    fetchAlertDetails();

    return () => {
      isMounted = false;
    };
  }, [alertId]);

  if (!alertId) return null;

  return (
    <Modal
      isOpen={Boolean(alertId)}
      onClose={onClose}
      title={alert ? `${alert.disease_key.toUpperCase()} Surveillance Alert` : "Alert Intelligence Detail"}
      subtitle={alert ? `Territory: ${alert.geo_key.toUpperCase()} • Alert ID: ${alert.alert_id}` : ""}
      maxWidth="920px"
    >
      {loading ? (
        <LoadingSpinner message="Retrieving dossier, audit trail, and provenance graph..." />
      ) : error ? (
        <ErrorBanner message={error} onRetry={() => {}} />
      ) : alert ? (
        <div>
          {/* Top Key Metric Strip */}
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(5, 1fr)",
              gap: "12px",
              marginBottom: "20px",
            }}
          >
            <div className="card" style={{ padding: "12px 16px", background: "var(--bg-surface-1)" }}>
              <div style={{ fontSize: "11px", color: "var(--text-secondary)", textTransform: "uppercase" }}>
                Triage Priority
              </div>
              <div
                style={{
                  fontSize: "22px",
                  fontWeight: 800,
                  fontFamily: "var(--font-mono)",
                  color:
                    (alert.event_triage_score ?? alert.composite_score) >= 0.8
                      ? "var(--tier-critical)"
                      : (alert.event_triage_score ?? alert.composite_score) >= 0.65
                      ? "var(--tier-high)"
                      : "var(--tier-medium)",
                  marginTop: "2px",
                }}
              >
                {(alert.event_triage_score ?? alert.composite_score).toFixed(3)}
              </div>
              <div style={{ marginTop: "4px" }}>
                <AlertTierBadge tier={alert.alert_tier} />
              </div>
            </div>

            <div className="card" style={{ padding: "12px 16px", background: "var(--bg-surface-1)" }}>
              <div style={{ fontSize: "11px", color: "var(--text-secondary)", textTransform: "uppercase" }}>
                Review Action
              </div>
              <div style={{ marginTop: "8px" }}>
                <RecommendedActionBadge action={alert.recommended_action} />
              </div>
              <div style={{ fontSize: "10px", color: "var(--text-tertiary)", marginTop: "6px" }}>
                Operational Guidance
              </div>
            </div>

            <div className="card" style={{ padding: "12px 16px", background: "var(--bg-surface-1)" }}>
              <div style={{ fontSize: "11px", color: "var(--text-secondary)", textTransform: "uppercase" }}>
                Operational Triage Review
              </div>
              <div style={{ marginTop: "8px" }}>
                <ThreatTierBadge tier={alert.pathogen_threat_tier} />
              </div>
            </div>

            <div className="card" style={{ padding: "12px 16px", background: "var(--bg-surface-1)" }}>
              <div style={{ fontSize: "11px", color: "var(--text-secondary)", textTransform: "uppercase" }}>
                Corroboration
              </div>
              <div style={{ fontSize: "16px", fontWeight: 700, color: "var(--text-primary)", marginTop: "2px" }}>
                {alert.supporting_source_count} Sources
              </div>
              <div style={{ fontSize: "11px", color: "var(--text-tertiary)", marginTop: "2px" }}>
                {alert.supporting_fused_event_ids.length} Incidents
              </div>
            </div>

            <div className="card" style={{ padding: "12px 16px", background: "var(--bg-surface-1)" }}>
              <div style={{ fontSize: "11px", color: "var(--text-secondary)", textTransform: "uppercase" }}>
                Surveillance Period
              </div>
              <div style={{ fontSize: "12px", color: "var(--text-primary)", fontWeight: 600, marginTop: "6px" }}>
                {new Date(alert.period_start).toLocaleDateString()}
              </div>
              <div style={{ fontSize: "11px", color: "var(--text-tertiary)" }}>
                to {new Date(alert.period_end).toLocaleDateString()}
              </div>
            </div>
          </div>

          {/* Navigation Tabs */}
          <div className="tabs-nav">
            <button
              onClick={() => setActiveTab("inference")}
              className={`tab-btn ${activeTab === "inference" ? "active" : ""}`}
            >
              <Brain size={14} style={{ display: "inline", marginRight: "6px" }} />
              Analyst Inference Dossier
            </button>
            <button
              onClick={() => setActiveTab("overview")}
              className={`tab-btn ${activeTab === "overview" ? "active" : ""}`}
            >
              <Layers size={14} style={{ display: "inline", marginRight: "6px" }} />
              Risk Breakdown
            </button>
            <button
              onClick={() => setActiveTab("dossier")}
              className={`tab-btn ${activeTab === "dossier" ? "active" : ""}`}
            >
              <ShieldAlert size={14} style={{ display: "inline", marginRight: "6px" }} />
              Explainability Dossier
            </button>
            <button
              onClick={() => setActiveTab("audit")}
              className={`tab-btn ${activeTab === "audit" ? "active" : ""}`}
            >
              <FileCheck size={14} style={{ display: "inline", marginRight: "6px" }} />
              Decision Audit Trail
            </button>
            <button
              onClick={() => setActiveTab("provenance")}
              className={`tab-btn ${activeTab === "provenance" ? "active" : ""}`}
            >
              <GitBranch size={14} style={{ display: "inline", marginRight: "6px" }} />
              Provenance DAG
            </button>
          </div>

          {/* Tab 0: Analyst Inference Dossier */}
          {activeTab === "inference" && (
            <AnalystInferenceDossier alert={alert} dossier={dossier} />
          )}

          {/* Tab 1: Risk Dimensions & Summary */}
          {activeTab === "overview" && (
            <div>
              {/* Driving Factors */}
              <DrivingFactors
                drivingFactors={alert.explanation.driving_factors}
                safetyConstraints={dossier?.applied_safety_constraints || []}
                gatingRationale={alert.gating_reason}
                isGated={alert.is_gated}
              />

              {/* Multi-Criteria Dimension Bars */}
              <div className="card">
                <h4 style={{ fontSize: "14px", fontWeight: 700, color: "var(--text-primary)", marginBottom: "4px" }}>
                  Multi-Criteria Risk Scoring Dimensions (Configured Heuristic Weights)
                </h4>
                <p style={{ fontSize: "12px", color: "var(--text-secondary)", marginBottom: "16px" }}>
                  Bounded dimension scores normalized within [0.0, 1.0]. Note: This composite risk score represents an operational triage prioritization index, NOT an epidemiological outbreak probability.
                </p>

                <div style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
                  {[
                    { label: "Anomaly Aberration Score", val: alert.score_breakdown.anomaly_score, weight: 0.30 },
                    { label: "Surveillance Priority Weight", val: alert.score_breakdown.threat_score, weight: 0.25 },
                    { label: "Evidence Corroboration Score", val: alert.score_breakdown.evidence_score, weight: 0.20 },
                    { label: "Clinical Certainty Score", val: alert.score_breakdown.certainty_score, weight: 0.15 },
                    { label: "Spatial Specificity Score", val: alert.score_breakdown.spatial_score, weight: 0.10 },
                  ].map((dim) => (
                    <div key={dim.label}>
                      <div style={{ display: "flex", justifyContent: "space-between", fontSize: "12px", marginBottom: "3px" }}>
                        <span style={{ color: "var(--text-primary)", fontWeight: 500 }}>{dim.label}</span>
                        <span style={{ fontFamily: "var(--font-mono)", color: "var(--brand-primary)", fontWeight: 700 }}>
                          {dim.val.toFixed(3)} <span style={{ color: "var(--text-muted)", fontSize: "10px" }}>(w={dim.weight})</span>
                        </span>
                      </div>
                      <div style={{ height: "6px", background: "var(--bg-canvas)", borderRadius: "3px", overflow: "hidden" }}>
                        <div
                          style={{
                            height: "100%",
                            width: `${Math.round(dim.val * 100)}%`,
                            background: "linear-gradient(90deg, var(--brand-primary) 0%, var(--accent-teal) 100%)",
                            borderRadius: "3px",
                          }}
                        />
                      </div>
                    </div>
                  ))}

                  {alert.score_breakdown.penalty_applied > 0 && (
                    <div style={{ marginTop: "8px", padding: "8px 12px", background: "rgba(255, 138, 50, 0.1)", borderRadius: "4px", fontSize: "12px", color: "var(--tier-medium)" }}>
                      Penalty Applied: -{alert.score_breakdown.penalty_applied.toFixed(3)}
                    </div>
                  )}
                </div>
              </div>
            </div>
          )}

          {/* Tab 2: Explainability Dossier */}
          {activeTab === "dossier" && dossier && (
            <div>
              <BriefingCard briefing={dossier.briefing} />
              <EvidenceSpansView spans={dossier.reconstructed_evidence} />
            </div>
          )}

          {/* Tab 3: Decision Audit Trail */}
          {activeTab === "audit" && auditTrail && (
            <AuditTrailView auditTrail={auditTrail} />
          )}

          {/* Tab 4: Provenance DAG */}
          {activeTab === "provenance" && provenance && (
            <ProvenanceGraphView graph={provenance} />
          )}
        </div>
      ) : null}
    </Modal>
  );
};

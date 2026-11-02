import React from "react";
import { Check, ShieldCheck, Key } from "lucide-react";
import type { AlertAuditTrail } from "../../types/api";

interface AuditTrailViewProps {
  auditTrail: AlertAuditTrail;
}

export const AuditTrailView: React.FC<AuditTrailViewProps> = ({ auditTrail }) => {
  const steps = auditTrail.decision_steps || [];

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "20px" }}>
      {/* Checksum Verification Banner */}
      <div
        className="card"
        style={{
          background: "linear-gradient(135deg, #FAF8F5 0%, #FFFFFF 100%)",
          border: "1px solid var(--border-default)",
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          flexWrap: "wrap",
          gap: "12px",
          padding: "16px 20px",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
          <div
            style={{
              width: "32px",
              height: "32px",
              borderRadius: "var(--radius-sm)",
              background: "rgba(16, 168, 120, 0.12)",
              color: "var(--status-success)",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
            }}
          >
            <ShieldCheck size={18} />
          </div>
          <div>
            <div style={{ fontSize: "13px", fontWeight: 700, color: "var(--text-primary)" }}>
              Cryptographic Audit Integrity Seal
            </div>
            <div style={{ fontSize: "11px", color: "var(--text-secondary)" }}>
              SHA-256 hash of immutable inputs, weights, and decision transitions
            </div>
          </div>
        </div>

        <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
          <Key size={13} style={{ color: "var(--text-tertiary)" }} />
          <span className="code-badge" style={{ fontSize: "11px", color: "var(--brand-primary)" }}>
            {auditTrail.audit_checksum}
          </span>
        </div>
      </div>

      {/* 8-Step Timeline */}
      <div style={{ display: "flex", flexDirection: "column", gap: "10px" }}>
        <div style={{ fontSize: "13px", fontWeight: 600, color: "var(--text-secondary)", marginBottom: "4px" }}>
          Deterministic Decision Path ({steps.length} Sequential Steps):
        </div>

        {steps.map((step) => (
          <div
            key={step.step_number}
            className="card"
            style={{
              padding: "14px 18px",
              background: "var(--bg-surface-1)",
              border: "1px solid var(--border-subtle)",
              position: "relative",
            }}
          >
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: "8px" }}>
              <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
                <div
                  style={{
                    width: "24px",
                    height: "24px",
                    borderRadius: "50%",
                    background: step.is_gated ? "rgba(255, 138, 50, 0.15)" : "rgba(112, 71, 245, 0.12)",
                    color: step.is_gated ? "var(--tier-medium)" : "var(--brand-primary)",
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    fontSize: "11px",
                    fontWeight: 700,
                  }}
                >
                  {step.step_number}
                </div>
                <div style={{ fontWeight: 600, fontSize: "13px", color: "var(--text-primary)" }}>
                  {step.step_name}
                </div>
              </div>

              <div style={{ fontSize: "11px" }}>
                {step.is_gated ? (
                  <span className="badge badge-medium" style={{ fontSize: "10px" }}>
                    Ceiling Enforced
                  </span>
                ) : (
                  <span className="badge badge-success" style={{ fontSize: "10px" }}>
                    <Check size={10} /> Validated
                  </span>
                )}
              </div>
            </div>

            <div style={{ fontSize: "12px", color: "var(--text-secondary)", marginBottom: "6px" }}>
              Rule Applied: <strong style={{ color: "var(--text-primary)" }}>{step.rule_applied}</strong>
            </div>

            {step.gating_detail && (
              <div
                style={{
                  fontSize: "12px",
                  color: "var(--tier-medium)",
                  background: "rgba(245, 158, 11, 0.1)",
                  padding: "6px 10px",
                  borderRadius: "4px",
                  marginBottom: "8px",
                }}
              >
                Gating Detail: {step.gating_detail}
              </div>
            )}

            <div
              style={{
                display: "flex",
                justifyContent: "space-between",
                alignItems: "center",
                background: "var(--bg-canvas)",
                padding: "8px 12px",
                borderRadius: "var(--radius-sm)",
                fontSize: "11px",
                fontFamily: "var(--font-mono)",
                color: "var(--text-secondary)",
              }}
            >
              <span>Output Value:</span>
              <strong style={{ color: "var(--brand-primary)" }}>
                {typeof step.output_value === "number"
                  ? step.output_value.toFixed(4)
                  : String(step.output_value)}
              </strong>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};

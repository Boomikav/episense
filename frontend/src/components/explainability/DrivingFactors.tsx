import React from "react";
import { CheckCircle2, ShieldCheck, AlertCircle } from "lucide-react";

interface DrivingFactorsProps {
  drivingFactors: string[];
  safetyConstraints: string[];
  gatingRationale?: string | null;
  isGated?: boolean;
}

export const DrivingFactors: React.FC<DrivingFactorsProps> = ({
  drivingFactors,
  safetyConstraints,
  gatingRationale,
  isGated,
}) => {
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "16px", marginBottom: "20px" }}>
      {/* Driving Factors */}
      <div className="card">
        <div style={{ display: "flex", alignItems: "center", gap: "8px", marginBottom: "12px" }}>
          <CheckCircle2 size={16} style={{ color: "var(--brand-primary)" }} />
            <h4 style={{ fontSize: "14px", fontWeight: 700, color: "var(--text-primary)" }}>
            Primary Driving Risk Factors
          </h4>
        </div>
        <ul style={{ listStyle: "none", display: "flex", flexDirection: "column", gap: "6px" }}>
          {drivingFactors.length === 0 ? (
            <li style={{ fontSize: "12px", color: "var(--text-tertiary)" }}>
              No specific primary driving factors isolated.
            </li>
          ) : (
            drivingFactors.map((f, i) => (
              <li
                key={i}
                style={{
                  display: "flex",
                  alignItems: "flex-start",
                  gap: "8px",
                  fontSize: "13px",
                  color: "var(--text-secondary)",
                }}
              >
                <span style={{ color: "var(--brand-primary)", marginTop: "2px" }}>•</span>
                <span>{f}</span>
              </li>
            ))
          )}
        </ul>
      </div>

      {/* Safety Ceilings & Reliability Gating */}
      {(safetyConstraints.length > 0 || isGated) && (
        <div
          className="card"
          style={{
            borderColor: isGated ? "rgba(255, 138, 50, 0.4)" : "var(--border-default)",
            background: isGated ? "rgba(255, 138, 50, 0.06)" : "var(--bg-surface-1)",
          }}
        >
          <div style={{ display: "flex", alignItems: "center", gap: "8px", marginBottom: "10px" }}>
            {isGated ? (
              <AlertCircle size={16} style={{ color: "var(--tier-medium)" }} />
            ) : (
              <ShieldCheck size={16} style={{ color: "var(--status-success)" }} />
            )}
            <h4 style={{ fontSize: "14px", fontWeight: 700, color: isGated ? "var(--tier-medium)" : "var(--text-primary)" }}>
              {isGated ? "Safety Ceiling & Reliability Gating Enforced" : "Applied Safety Constraints"}
            </h4>
          </div>

          {gatingRationale && (
            <div style={{ fontSize: "13px", color: "var(--text-primary)", marginBottom: "10px", fontWeight: 500 }}>
              {gatingRationale}
            </div>
          )}

          <ul style={{ listStyle: "none", display: "flex", flexDirection: "column", gap: "6px" }}>
            {safetyConstraints.map((sc, idx) => (
              <li
                key={idx}
                style={{
                  display: "flex",
                  alignItems: "flex-start",
                  gap: "8px",
                  fontSize: "12px",
                  color: "var(--text-secondary)",
                }}
              >
                <span style={{ color: isGated ? "var(--tier-medium)" : "var(--status-success)" }}>✓</span>
                <span>{sc}</span>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
};

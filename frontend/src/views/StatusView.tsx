import React from "react";
import { SystemHealthCard } from "../components/status/SystemHealthCard";

export const StatusView: React.FC = () => {
  return (
    <div style={{ maxWidth: "900px", margin: "0 auto" }}>
      <div style={{ marginBottom: "24px" }}>
        <h2 style={{ fontSize: "20px", fontWeight: 800, color: "var(--text-primary)" }}>
          System Health & Infrastructure Telemetry
        </h2>
        <p style={{ fontSize: "13px", color: "var(--text-secondary)", marginTop: "4px" }}>
          Operational status, Kubernetes liveness/readiness probes, and pipeline state store availability.
        </p>
      </div>

      <SystemHealthCard />
    </div>
  );
};

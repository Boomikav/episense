import React from "react";
import { Inbox } from "lucide-react";

interface EmptyStateProps {
  title?: string;
  description?: string;
  icon?: React.ReactNode;
  action?: React.ReactNode;
}

export const EmptyState: React.FC<EmptyStateProps> = ({
  title = "No surveillance records found",
  description = "Try adjusting your query filters or criteria.",
  icon,
  action,
}) => {
  return (
    <div
      className="card"
      style={{
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        padding: "48px 24px",
        textAlign: "center",
        color: "var(--text-secondary)",
      }}
    >
      <div
        style={{
          width: "48px",
          height: "48px",
          borderRadius: "50%",
          background: "var(--bg-surface-3)",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          marginBottom: "16px",
          color: "var(--text-tertiary)",
        }}
      >
        {icon || <Inbox size={24} />}
      </div>
      <div style={{ color: "var(--text-primary)", fontWeight: 600, fontSize: "16px", marginBottom: "6px" }}>
        {title}
      </div>
      <div style={{ fontSize: "13px", maxWidth: "380px", marginBottom: action ? "18px" : "0" }}>
        {description}
      </div>
      {action && <div>{action}</div>}
    </div>
  );
};

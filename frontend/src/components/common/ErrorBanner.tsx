import React from "react";
import { AlertTriangle, RefreshCw } from "lucide-react";

interface ErrorBannerProps {
  message: string;
  code?: string;
  onRetry?: () => void;
  className?: string;
}

export const ErrorBanner: React.FC<ErrorBannerProps> = ({
  message,
  code,
  onRetry,
  className = "",
}) => {
  return (
    <div
      className={`card ${className}`}
      style={{
        backgroundColor: "rgba(239, 68, 68, 0.08)",
        borderColor: "rgba(239, 68, 68, 0.3)",
        display: "flex",
        alignItems: "center",
        justifyContent: "space-between",
        gap: "16px",
        padding: "16px 20px",
      }}
    >
      <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
        <div
          style={{
            padding: "8px",
            background: "rgba(239, 68, 68, 0.15)",
            borderRadius: "var(--radius-sm)",
            color: "var(--tier-high)",
            display: "flex",
          }}
        >
          <AlertTriangle size={20} />
        </div>
        <div>
          <div style={{ fontWeight: 600, color: "var(--text-primary)", fontSize: "14px" }}>
            {message}
          </div>
          {code && (
            <div style={{ fontSize: "12px", color: "var(--text-secondary)", marginTop: "2px" }}>
              Code: <span className="code-badge">{code}</span>
            </div>
          )}
        </div>
      </div>
      {onRetry && (
        <button
          onClick={onRetry}
          className="btn btn-secondary btn-sm"
          style={{ borderColor: "rgba(240, 68, 98, 0.4)", color: "var(--text-primary)" }}
        >
          <RefreshCw size={14} /> Retry
        </button>
      )}
    </div>
  );
};

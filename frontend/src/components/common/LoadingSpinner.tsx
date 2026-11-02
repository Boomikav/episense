import React from "react";
import { Loader2 } from "lucide-react";

interface LoadingSpinnerProps {
  message?: string;
  size?: number;
  height?: string;
}

export const LoadingSpinner: React.FC<LoadingSpinnerProps> = ({
  message = "Loading surveillance intelligence...",
  size = 28,
  height = "240px",
}) => {
  return (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        height,
        gap: "12px",
        color: "var(--text-secondary)",
      }}
    >
      <Loader2
        size={size}
        style={{
          animation: "spin 1s linear infinite",
          color: "var(--brand-primary)",
        }}
      />
      <span style={{ fontSize: "13px", fontWeight: 500 }}>{message}</span>
      <style>{`
        @keyframes spin {
          from { transform: rotate(0deg); }
          to { transform: rotate(360deg); }
        }
      `}</style>
    </div>
  );
};

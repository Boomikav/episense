import React from "react";
import { ChevronLeft, ChevronRight } from "lucide-react";

interface PaginationProps {
  page: number;
  total: number;
  pageSize: number;
  onPageChange: (newPage: number) => void;
}

export const Pagination: React.FC<PaginationProps> = ({
  page,
  total,
  pageSize,
  onPageChange,
}) => {
  const totalPages = Math.max(1, Math.ceil(total / pageSize));

  if (totalPages <= 1 && total === 0) {
    return null;
  }

  const start = (page - 1) * pageSize + 1;
  const end = Math.min(page * pageSize, total);

  return (
    <div
      style={{
        display: "flex",
        alignItems: "center",
        justifyContent: "space-between",
        padding: "12px 16px",
        background: "var(--bg-surface-1)",
        border: "1px solid var(--border-default)",
        borderRadius: "var(--radius-sm)",
        marginTop: "16px",
        flexWrap: "wrap",
        gap: "12px",
      }}
    >
      <div style={{ fontSize: "12px", color: "var(--text-secondary)" }}>
        Showing <span style={{ color: "var(--text-primary)", fontWeight: 600 }}>{total > 0 ? start : 0}</span> to{" "}
        <span style={{ color: "var(--text-primary)", fontWeight: 600 }}>{end}</span> of{" "}
        <span style={{ color: "var(--text-primary)", fontWeight: 600 }}>{total}</span> entries
      </div>

      <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
        <button
          onClick={() => onPageChange(page - 1)}
          disabled={page <= 1}
          className="btn btn-secondary btn-sm"
          title="Previous Page"
        >
          <ChevronLeft size={14} /> Previous
        </button>

        <span style={{ fontSize: "12px", color: "var(--text-secondary)", margin: "0 4px" }}>
          Page <strong style={{ color: "var(--text-primary)" }}>{page}</strong> of{" "}
          <strong style={{ color: "var(--text-primary)" }}>{totalPages}</strong>
        </span>

        <button
          onClick={() => onPageChange(page + 1)}
          disabled={page >= totalPages}
          className="btn btn-secondary btn-sm"
          title="Next Page"
        >
          Next <ChevronRight size={14} />
        </button>
      </div>
    </div>
  );
};

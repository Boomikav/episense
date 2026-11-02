import React, { useState } from "react";
import { GitCommit, ArrowDown, Info } from "lucide-react";
import type { ProvenanceGraph, ProvenanceNode } from "../../types/api";

interface ProvenanceGraphViewProps {
  graph: ProvenanceGraph;
}

export const ProvenanceGraphView: React.FC<ProvenanceGraphViewProps> = ({ graph }) => {
  const [selectedNode, setSelectedNode] = useState<ProvenanceNode | null>(null);

  const nodes = graph.nodes || [];
  const edges = graph.edges || [];

  // Group nodes by type for layered DAG presentation
  const nodeLayers: Record<string, ProvenanceNode[]> = {
    alert: [],
    signal: [],
    baseline: [],
    time_bin: [],
    fused_event: [],
    document: [],
    evidence_span: [],
  };

  nodes.forEach((n) => {
    if (nodeLayers[n.node_type]) {
      nodeLayers[n.node_type].push(n);
    }
  });

  const getNodeColor = (type: string) => {
    switch (type) {
      case "alert":
        return "var(--tier-high)";
      case "signal":
        return "var(--tier-medium)";
      case "baseline":
      case "time_bin":
        return "var(--brand-secondary)";
      case "fused_event":
        return "var(--brand-primary)";
      case "document":
        return "var(--status-success)";
      case "evidence_span":
      default:
        return "var(--text-secondary)";
    }
  };

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "20px" }}>
      {/* DAG Integrity Header */}
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          background: "var(--bg-surface-2)",
          padding: "12px 18px",
          borderRadius: "var(--radius-sm)",
          border: "1px solid var(--border-subtle)",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
          <GitCommit size={16} style={{ color: "var(--brand-primary)" }} />
          <span style={{ fontSize: "13px", fontWeight: 700, color: "var(--text-primary)" }}>
            Provenance DAG Traversal
          </span>
          <span className="badge badge-info" style={{ fontSize: "10px" }}>
            {nodes.length} Nodes • {edges.length} Edges
          </span>
        </div>

        <div style={{ fontSize: "11px", color: "var(--text-secondary)" }}>
          Acyclic Guarantee: <strong style={{ color: graph.is_acyclic ? "var(--status-success)" : "var(--tier-high)" }}>{graph.is_acyclic ? "Verified (DAG)" : "Cyclic"}</strong> • Completeness:{" "}
          <strong style={{ color: "var(--brand-primary)" }}>{Math.round(graph.completeness_ratio * 100)}%</strong>
        </div>
      </div>

      {/* Interactive Layered Graph View */}
      <div
        className="card"
        style={{
          background: "var(--bg-canvas)",
          border: "1px solid var(--border-default)",
          padding: "24px",
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          gap: "18px",
        }}
      >
        {Object.entries(nodeLayers).map(([layerKey, layerNodes], layerIdx) => {
          if (layerNodes.length === 0) return null;
          return (
            <React.Fragment key={layerKey}>
              {layerIdx > 0 && (
                <div style={{ display: "flex", alignItems: "center", color: "var(--text-tertiary)" }}>
                  <ArrowDown size={18} />
                </div>
              )}

              <div style={{ display: "flex", flexDirection: "column", alignItems: "center", width: "100%" }}>
                <div
                  style={{
                    fontSize: "10px",
                    fontWeight: 700,
                    textTransform: "uppercase",
                    letterSpacing: "0.08em",
                    color: "var(--text-tertiary)",
                    marginBottom: "8px",
                  }}
                >
                  Layer: {layerKey.replace("_", " ")}
                </div>

                <div style={{ display: "flex", gap: "10px", flexWrap: "wrap", justifyContent: "center" }}>
                  {layerNodes.map((n) => {
                    const isSelected = selectedNode?.node_id === n.node_id;
                    const color = getNodeColor(n.node_type);
                    return (
                      <div
                        key={n.node_id}
                        onClick={() => setSelectedNode(n)}
                        style={{
                          padding: "8px 14px",
                          borderRadius: "var(--radius-sm)",
                          background: isSelected ? "var(--bg-elevated)" : "var(--bg-surface-2)",
                          border: `1px solid ${isSelected ? color : "var(--border-subtle)"}`,
                          boxShadow: isSelected ? `0 0 12px ${color}40` : "none",
                          cursor: "pointer",
                          transition: "all 0.15s ease",
                          display: "flex",
                          alignItems: "center",
                          gap: "8px",
                        }}
                      >
                        <span
                          style={{
                            width: "8px",
                            height: "8px",
                            borderRadius: "50%",
                            backgroundColor: color,
                          }}
                        />
                        <div>
                          <div style={{ fontSize: "12px", fontWeight: 600, color: "var(--text-primary)" }}>
                            {n.label}
                          </div>
                          <div style={{ fontSize: "10px", color: "var(--text-tertiary)", fontFamily: "var(--font-mono)" }}>
                            {n.node_id.slice(0, 16)}...
                          </div>
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>
            </React.Fragment>
          );
        })}
      </div>

      {/* Node Inspector Modal / Drawer */}
      {selectedNode && (
        <div
          className="card"
          style={{
            background: "var(--bg-surface-2)",
            border: "1px solid var(--border-highlight)",
            padding: "16px",
          }}
        >
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "8px" }}>
            <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
              <Info size={16} style={{ color: "var(--brand-primary)" }} />
              <span style={{ fontWeight: 700, color: "var(--text-primary)", fontSize: "13px" }}>
                Node Inspector: {selectedNode.label}
              </span>
            </div>
            <button
              onClick={() => setSelectedNode(null)}
              className="btn btn-secondary btn-sm"
              style={{ fontSize: "10px", padding: "2px 8px" }}
            >
              Close
            </button>
          </div>

          <div style={{ display: "grid", gridTemplateColumns: "repeat(2, 1fr)", gap: "10px", fontSize: "12px" }}>
            <div>
              <span style={{ color: "var(--text-secondary)" }}>Node ID:</span>{" "}
              <span className="code-badge">{selectedNode.node_id}</span>
            </div>
            <div>
              <span style={{ color: "var(--text-secondary)" }}>Entity Type:</span>{" "}
              <strong style={{ color: "var(--text-primary)", textTransform: "capitalize" }}>{selectedNode.node_type}</strong>
            </div>
            <div>
              <span style={{ color: "var(--text-secondary)" }}>Entity ID:</span>{" "}
              <span className="code-badge">{selectedNode.entity_id}</span>
            </div>
          </div>

          {selectedNode.metadata && Object.keys(selectedNode.metadata).length > 0 && (
            <div style={{ marginTop: "10px" }}>
              <div style={{ fontSize: "11px", fontWeight: 600, color: "var(--text-tertiary)", marginBottom: "4px" }}>
                METADATA ATTRIBUTES:
              </div>
              <pre
                style={{
                  background: "var(--bg-canvas)",
                  padding: "8px 12px",
                  borderRadius: "4px",
                  fontSize: "11px",
                  fontFamily: "var(--font-mono)",
                  color: "var(--text-secondary)",
                  overflowX: "auto",
                }}
              >
                {JSON.stringify(selectedNode.metadata, null, 2)}
              </pre>
            </div>
          )}
        </div>
      )}
    </div>
  );
};

"""
Provenance Lineage Graph Builder and Traversal Engine for EpiSense (Phase 10).
Constructs deterministic directed acyclic provenance graphs linking alerts,
signals, baselines, time bins, fused events, documents, and evidence spans.
"""

from collections import defaultdict, deque
from typing import Dict, List, Optional, Set
from uuid import UUID, NAMESPACE_DNS, uuid5

from episense.schemas.alert import EpidemiologicalAlert
from episense.schemas.event import FusedEvent
from episense.schemas.explainability import (
    ProvenanceEdge,
    ProvenanceEdgeType,
    ProvenanceGraph,
    ProvenanceNode,
    ProvenanceNodeType,
)
from episense.schemas.signal import BaselineEstimate, EpidemiologicalTimeBin, SignalObservation


class ProvenanceGraphBuilder:
    """
    Constructs and traverses immutable, acyclic provenance graphs for epidemiological alerts.
    """

    def build_graph(
        self,
        alert: EpidemiologicalAlert,
        signal: Optional[SignalObservation] = None,
        fused_events: Optional[List[FusedEvent]] = None,
        time_bin: Optional[EpidemiologicalTimeBin] = None,
        baseline: Optional[BaselineEstimate] = None,
        available_document_ids: Optional[Set[UUID]] = None,
    ) -> ProvenanceGraph:
        """
        Builds a complete, deterministic lineage DAG for an alert.
        """
        nodes: List[ProvenanceNode] = []
        edges: List[ProvenanceEdge] = []
        seen_nodes: Set[str] = set()
        seen_edges: Set[tuple] = set()
        missing_nodes: List[str] = []

        # 1. Alert Node
        alert_node_id = f"alert:{alert.alert_id}"
        nodes.append(
            ProvenanceNode(
                node_id=alert_node_id,
                node_type=ProvenanceNodeType.ALERT,
                entity_id=alert.alert_id,
                label=f"Alert [{alert.alert_tier.value.upper()}]: {alert.disease_key} ({alert.composite_score:.2f})",
                metadata={
                    "tier": alert.alert_tier.value,
                    "score": alert.composite_score,
                    "disease": alert.disease_key,
                    "geo": alert.geo_key,
                },
            )
        )
        seen_nodes.add(alert_node_id)

        # 2. Signal Node
        if signal:
            sig_node_id = f"signal:{signal.signal_id}"
            nodes.append(
                ProvenanceNode(
                    node_id=sig_node_id,
                    node_type=ProvenanceNodeType.SIGNAL,
                    entity_id=signal.signal_id,
                    label=f"Signal [{signal.signal_level.value.upper()}]: {signal.detection_method.value}",
                    metadata={
                        "level": signal.signal_level.value,
                        "method": signal.detection_method.value,
                        "z_score": signal.standardized_score,
                        "obs": signal.observed_value,
                        "exp": signal.expected_value,
                    },
                )
            )
            seen_nodes.add(sig_node_id)

            edges.append(
                ProvenanceEdge(
                    source_node_id=alert_node_id,
                    target_node_id=sig_node_id,
                    edge_type=ProvenanceEdgeType.SCORED_FROM,
                    description="Alert composite score derived from statistical signal",
                )
            )

            # 3. Baseline Node
            if baseline:
                base_node_id = f"baseline:{baseline.baseline_id}"
                nodes.append(
                    ProvenanceNode(
                        node_id=base_node_id,
                        node_type=ProvenanceNodeType.BASELINE,
                        entity_id=baseline.baseline_id,
                        label=f"Baseline: mean={baseline.baseline_mean:.2f}, std={baseline.baseline_std:.2f} ({baseline.reliability_status.value})",
                        metadata={
                            "mean": baseline.baseline_mean,
                            "median": baseline.baseline_median,
                            "std": baseline.baseline_std,
                            "weeks": baseline.baseline_window_weeks,
                            "reliability": baseline.reliability_status.value,
                        },
                    )
                )
                seen_nodes.add(base_node_id)

                edges.append(
                    ProvenanceEdge(
                        source_node_id=sig_node_id,
                        target_node_id=base_node_id,
                        edge_type=ProvenanceEdgeType.BASELINE_FOR,
                        description="Historical expectation reference for signal detection",
                    )
                )

            # 4. TimeBin Node
            if time_bin:
                bin_node_id = f"time_bin:{time_bin.bin_id}"
                nodes.append(
                    ProvenanceNode(
                        node_id=bin_node_id,
                        node_type=ProvenanceNodeType.TIME_BIN,
                        entity_id=time_bin.bin_id,
                        label=f"TimeBin: ISO {time_bin.iso_year}-W{time_bin.iso_week} (events={time_bin.fused_event_count})",
                        metadata={
                            "iso_year": time_bin.iso_year,
                            "iso_week": time_bin.iso_week,
                            "cases": time_bin.observed_case_count,
                            "deaths": time_bin.observed_death_count,
                            "sources": time_bin.independent_source_count,
                        },
                    )
                )
                seen_nodes.add(bin_node_id)

                edges.append(
                    ProvenanceEdge(
                        source_node_id=bin_node_id,
                        target_node_id=sig_node_id,
                        edge_type=ProvenanceEdgeType.AGGREGATED_INTO,
                        description="Time bin evaluated for statistical aberration",
                    )
                )

        # 5. Fused Event Nodes
        fused_events = fused_events or []
        for fe in fused_events:
            fe_node_id = f"fused_event:{fe.fused_event_id}"
            if fe_node_id not in seen_nodes:
                nodes.append(
                    ProvenanceNode(
                        node_id=fe_node_id,
                        node_type=ProvenanceNodeType.FUSED_EVENT,
                        entity_id=fe.fused_event_id,
                        label=f"FusedEvent: {fe.canonical_disease} ({fe.assertion_status.value})",
                        metadata={
                            "status": fe.assertion_status.value,
                            "certainty": fe.certainty.value,
                            "sources": [s.source_id for s in fe.independent_sources],
                            "has_conflicts": fe.has_conflicts,
                        },
                    )
                )
                seen_nodes.add(fe_node_id)

            if time_bin and f"time_bin:{time_bin.bin_id}" in seen_nodes:
                edge_key = (f"time_bin:{time_bin.bin_id}", fe_node_id)
                if edge_key not in seen_edges:
                    seen_edges.add(edge_key)
                    edges.append(
                        ProvenanceEdge(
                            source_node_id=f"time_bin:{time_bin.bin_id}",
                            target_node_id=fe_node_id,
                            edge_type=ProvenanceEdgeType.COMPOSED_OF,
                            description="TimeBin aggregates canonical fused event",
                        )
                    )
            elif signal:
                edge_key = (f"signal:{signal.signal_id}", fe_node_id)
                if edge_key not in seen_edges:
                    seen_edges.add(edge_key)
                    edges.append(
                        ProvenanceEdge(
                            source_node_id=f"signal:{signal.signal_id}",
                            target_node_id=fe_node_id,
                            edge_type=ProvenanceEdgeType.COMPOSED_OF,
                            description="Signal supported by fused event",
                        )
                    )

        # 6. Evidence Spans and Source Documents
        all_refs = list(alert.provenance_references)
        for fe in fused_events:
            all_refs.extend(fe.evidence_references)

        # Deduplicate references deterministically
        seen_ref_keys = set()
        for ref in all_refs:
            ref_key = (str(ref.document_id), ref.start_char, ref.end_char)
            if ref_key in seen_ref_keys:
                continue
            seen_ref_keys.add(ref_key)

            doc_node_id = f"document:{ref.document_id}"
            span_node_id = f"evidence_span:{ref.document_id}:{ref.start_char}:{ref.end_char}"

            # Evidence Span Node
            if span_node_id not in seen_nodes:
                nodes.append(
                    ProvenanceNode(
                        node_id=span_node_id,
                        node_type=ProvenanceNodeType.EVIDENCE_SPAN,
                        entity_id=ref.document_id,
                        label=f"Span [{ref.start_char}:{ref.end_char}]: '{ref.span_text}' ({ref.attribute_role})",
                        metadata={
                            "start": ref.start_char,
                            "end": ref.end_char,
                            "text": ref.span_text,
                            "role": ref.attribute_role,
                            "method": ref.extraction_method,
                            "source_id": ref.source_id,
                        },
                    )
                )
                seen_nodes.add(span_node_id)

            # Document Node
            if doc_node_id not in seen_nodes:
                is_available = (
                    available_document_ids is None or ref.document_id in available_document_ids
                )
                if not is_available:
                    missing_nodes.append(f"Document {ref.document_id} missing from local store")

                nodes.append(
                    ProvenanceNode(
                        node_id=doc_node_id,
                        node_type=ProvenanceNodeType.DOCUMENT,
                        entity_id=ref.document_id,
                        label=f"Document: {ref.source_id} ({str(ref.document_id)[:8]}...)",
                        metadata={
                            "source_id": ref.source_id,
                            "is_available": is_available,
                        },
                    )
                )
                seen_nodes.add(doc_node_id)

            # Connect span -> document
            span_doc_edge = (span_node_id, doc_node_id)
            if span_doc_edge not in seen_edges:
                seen_edges.add(span_doc_edge)
                edges.append(
                    ProvenanceEdge(
                        source_node_id=span_node_id,
                        target_node_id=doc_node_id,
                        edge_type=ProvenanceEdgeType.SPAN_OF,
                        description="Character span offset within document text",
                    )
                )

            # Connect alert or fused events -> span
            alert_span_edge = (alert_node_id, span_node_id)
            if alert_span_edge not in seen_edges:
                seen_edges.add(alert_span_edge)
                edges.append(
                    ProvenanceEdge(
                        source_node_id=alert_node_id,
                        target_node_id=span_node_id,
                        edge_type=ProvenanceEdgeType.EVIDENCED_BY,
                        description="Underlying linguistic evidence supporting alert",
                    )
                )

        # 7. Check Acyclicity using Kahn's algorithm
        is_acyclic = self._check_acyclicity(nodes, edges)

        # 8. Completeness Ratio
        total_expected = len(nodes) + len(missing_nodes)
        completeness = len(nodes) / total_expected if total_expected > 0 else 1.0

        deterministic_graph_id = uuid5(
            NAMESPACE_DNS, f"{alert.alert_id}:provenance_graph"
        )

        return ProvenanceGraph(
            graph_id=deterministic_graph_id,
            alert_id=alert.alert_id,
            nodes=nodes,
            edges=edges,
            is_acyclic=is_acyclic,
            completeness_ratio=round(completeness, 3),
            missing_nodes=missing_nodes,
        )

    def _check_acyclicity(
        self, nodes: List[ProvenanceNode], edges: List[ProvenanceEdge]
    ) -> bool:
        """
        Verifies that the provenance graph is a directed acyclic graph (DAG).
        """
        in_degree: Dict[str, int] = {n.node_id: 0 for n in nodes}
        adj: Dict[str, List[str]] = defaultdict(list)

        for e in edges:
            adj[e.source_node_id].append(e.target_node_id)
            in_degree[e.target_node_id] = in_degree.get(e.target_node_id, 0) + 1

        queue = deque([nid for nid, deg in in_degree.items() if deg == 0])
        visited_count = 0

        while queue:
            curr = queue.popleft()
            visited_count += 1
            for nxt in adj[curr]:
                in_degree[nxt] -= 1
                if in_degree[nxt] == 0:
                    queue.append(nxt)

        return visited_count == len(nodes)

    # ----------------------------------------------------------------------
    # Traversal Queries
    # ----------------------------------------------------------------------

    @staticmethod
    def traverse_alert_to_documents(graph: ProvenanceGraph) -> List[UUID]:
        """
        Traverses provenance graph to return all source document UUIDs in deterministic order.
        """
        doc_ids: List[UUID] = []
        for n in graph.nodes:
            if n.node_type == ProvenanceNodeType.DOCUMENT:
                doc_ids.append(n.entity_id)
        return sorted(list(set(doc_ids)), key=lambda u: str(u))

    @staticmethod
    def traverse_alert_to_fused_events(graph: ProvenanceGraph) -> List[UUID]:
        """
        Traverses provenance graph to return all supporting FusedEvent UUIDs in deterministic order.
        """
        fe_ids: List[UUID] = []
        for n in graph.nodes:
            if n.node_type == ProvenanceNodeType.FUSED_EVENT:
                fe_ids.append(n.entity_id)
        return sorted(list(set(fe_ids)), key=lambda u: str(u))

    @staticmethod
    def traverse_alert_to_evidence(graph: ProvenanceGraph) -> List[ProvenanceNode]:
        """
        Traverses provenance graph to return all EVIDENCE_SPAN nodes in deterministic order.
        """
        spans = [n for n in graph.nodes if n.node_type == ProvenanceNodeType.EVIDENCE_SPAN]
        return sorted(spans, key=lambda n: (str(n.entity_id), n.metadata.get("start", 0)))

    @staticmethod
    def traverse_alert_to_signals(graph: ProvenanceGraph) -> List[UUID]:
        """
        Traverses provenance graph to return the primary and supporting signal UUIDs.
        """
        sig_ids = [n.entity_id for n in graph.nodes if n.node_type == ProvenanceNodeType.SIGNAL]
        return sorted(list(set(sig_ids)), key=lambda u: str(u))

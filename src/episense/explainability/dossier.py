"""
Explainability Dossier Generator for EpiSense (Phase 10).
Synthesizes comprehensive, human-reviewable dossiers combining epidemiological 5W1H,
reconstructed evidence spans, audit trails, and provenance graphs.
Implements the abstract EvidenceProvider interface.
"""

from typing import Any, Dict, List, Optional, Set, Union
from uuid import NAMESPACE_DNS, UUID, uuid5

from episense.interfaces.explainability import EvidenceProvider
from episense.schemas.alert import AlertTier, EpidemiologicalAlert, PathogenThreatTier
from episense.schemas.document import Document
from episense.schemas.event import FusedEvent
from episense.schemas.explainability import (
    Epidemiological5W1H,
    ExplainabilityDossier,
    ReconstructedEvidenceSpan,
)
from episense.schemas.signal import BaselineEstimate, EpidemiologicalTimeBin, SignalObservation
from episense.explainability.auditor import AuditTrailEngine
from episense.explainability.graph import ProvenanceGraphBuilder
from episense.explainability.reconstructor import EvidenceSpanReconstructor


class DossierGenerator(EvidenceProvider):
    """
    Generates structured, provenance-preserving explainability dossiers for public health alerts.
    """

    def __init__(
        self,
        reconstructor: Optional[EvidenceSpanReconstructor] = None,
        graph_builder: Optional[ProvenanceGraphBuilder] = None,
        auditor: Optional[AuditTrailEngine] = None,
        documents_map: Optional[Dict[UUID, Union[Document, str]]] = None,
        alert_registry: Optional[Dict[UUID, EpidemiologicalAlert]] = None,
    ):
        self.reconstructor = reconstructor or EvidenceSpanReconstructor()
        self.graph_builder = graph_builder or ProvenanceGraphBuilder()
        self.auditor = auditor or AuditTrailEngine()
        self.documents_map = documents_map or {}
        self.alert_registry = alert_registry or {}

    def register_documents(self, documents: List[Document]):
        """Registers source documents for evidence span reconstruction."""
        for doc in documents:
            self.documents_map[doc.document_id] = doc

    def register_alerts(self, alerts: List[EpidemiologicalAlert]):
        """Registers alerts for interface query resolution."""
        for a in alerts:
            self.alert_registry[a.alert_id] = a

    def generate_dossier(self, alert_id: UUID) -> Dict[str, Any]:
        """
        Implementation of the abstract EvidenceProvider interface.
        Traverses provenance graph from Alert down to source text character spans.
        """
        alert = self.alert_registry.get(alert_id)
        if not alert:
            raise KeyError(f"Alert ID {alert_id} not found in dossier registry")

        dossier = self.create_dossier(alert=alert)
        return dossier.model_dump(mode="json")

    def create_dossier(
        self,
        alert: EpidemiologicalAlert,
        signal: Optional[SignalObservation] = None,
        fused_events: Optional[List[FusedEvent]] = None,
        time_bin: Optional[EpidemiologicalTimeBin] = None,
        baseline: Optional[BaselineEstimate] = None,
        documents_map: Optional[Dict[UUID, Union[Document, str]]] = None,
    ) -> ExplainabilityDossier:
        """
        Creates a strongly-typed, complete ExplainabilityDossier for an EpidemiologicalAlert.
        """
        docs = documents_map if documents_map is not None else self.documents_map
        available_doc_ids = set(docs.keys())

        # 1. Epidemiological 5W1H Synthesis
        who = f"{alert.disease_key.title()} ({alert.pathogen_threat_tier.value.upper()})"
        obs_val = signal.observed_value if (signal and signal.observed_value is not None) else None
        exp_val = signal.expected_value if signal else 0.0
        obs_disp = f"{obs_val:.1f}" if obs_val is not None else "Not reported"
        what = f"{obs_disp} observed cases/reports across {len(alert.supporting_fused_event_ids)} fused events"
        
        event_dates = []
        if fused_events:
            for fe in fused_events:
                if getattr(fe, "event_window_start", None):
                    event_dates.append(fe.event_window_start.strftime("%Y-%m-%d"))
                elif getattr(fe, "event_window_end", None):
                    event_dates.append(fe.event_window_end.strftime("%Y-%m-%d"))
        event_dates_str = ", ".join(sorted(set(event_dates))) if event_dates else None
        surveillance_window_str = f"{alert.period_start.strftime('%Y-%m-%d')} to {alert.period_end.strftime('%Y-%m-%d')}"
        when = f"{surveillance_window_str} (Event Date: {event_dates_str})" if event_dates_str else surveillance_window_str

        # Reporting / publication dates
        reporting_dates = []
        if fused_events:
            for fe in fused_events:
                for ref in fe.evidence_references:
                    doc_obj = docs.get(ref.document_id)
                    if doc_obj and hasattr(doc_obj, "provenance_metadata") and doc_obj.provenance_metadata:
                        rep = doc_obj.provenance_metadata.get("reporting_date")
                        if rep:
                            reporting_dates.append(rep)
                    elif doc_obj and hasattr(doc_obj, "publication_timestamp") and doc_obj.publication_timestamp:
                        reporting_dates.append(doc_obj.publication_timestamp.strftime("%Y-%m-%d"))
        reporting_dates_str = ", ".join(sorted(set(reporting_dates))) if reporting_dates else None

        # Defensible aligned historical baseline window
        baseline_window_str = None
        if time_bin:
            from episense.baseline.timeseries import TimeSeriesBuilder
            prev_start, prev_end = TimeSeriesBuilder()._get_iso_week_bounds(time_bin.iso_year - 1, time_bin.iso_week)
            baseline_window_str = (
                f"{prev_start.strftime('%Y-%m-%d')} to {prev_end.strftime('%Y-%m-%d')} "
                f"(ISO Week {time_bin.iso_week}, Year {time_bin.iso_year - 1})"
            )
        elif baseline and baseline.baseline_window_weeks > 0:
            baseline_window_str = f"Rolling {baseline.baseline_window_weeks} preceding weeks (Mean: {baseline.baseline_mean:.2f})"

        where = f"{alert.geo_key.title()}"
        z_str = f"+{signal.standardized_score:.2f}" if (signal and signal.standardized_score is not None) else "N/A"
        method_str = signal.detection_method.value if signal else "statistical aberration"
        why = f"{method_str.upper()} triggered (Z-score: {z_str}, baseline expected: {exp_val:.2f})"
        how = f"{alert.supporting_source_count} independent source group(s) reporting"

        # Actionable next step based on pathogen threat and operational alert tier
        if alert.alert_tier == AlertTier.HIGH or alert.pathogen_threat_tier == PathogenThreatTier.TIER_4_HIGH_CONSEQUENCE:
            action = "Deploy district rapid response team for contact tracing; verify lab RT-PCR confirmation with NIV/reference lab before escalation."
        elif alert.alert_tier == AlertTier.MEDIUM or alert.pathogen_threat_tier == PathogenThreatTier.TIER_3_SEVERE:
            action = "Cross-check district hospital admission registers and verify active surveillance data with adjacent subdistricts."
        else:
            action = "Maintain routine syndromic surveillance; verify next periodic reporting bulletin without clinical escalation."

        date_context = f"Observed event date: {event_dates_str}. Active surveillance window: {surveillance_window_str}." if event_dates_str else f"Active surveillance window: {surveillance_window_str}."
        cases_disp = f"{obs_val:.0f} cases" if obs_val is not None else "Case count not reported"
        playbook = (
            f"Review required — suspected activity in {alert.disease_key.title()} in {alert.geo_key.title()}. "
            f"{date_context} "
            f"{cases_disp} reported across {alert.supporting_source_count} independent source group(s), compared with an expected baseline of {exp_val:.1f}. "
            f"Corroboration: {alert.supporting_source_count} source(s). "
            f"Statistical status: {method_str} ({'active aberration' if alert.alert_tier in (AlertTier.HIGH, AlertTier.MEDIUM) else 'monitored / stable baseline'}). "
            f"Recommended analyst action: {action}"
        )

        briefing = Epidemiological5W1H(
            who_pathogen=who,
            what_event=what,
            when_period=when,
            where_location=where,
            why_aberration=why,
            how_corroboration=how,
            recommended_action=action,
            event_date=event_dates_str,
            reporting_date=reporting_dates_str,
            active_surveillance_window=surveillance_window_str,
            historical_baseline_window=baseline_window_str,
        )

        # 2. Evidence Span Reconstruction
        all_refs = list(alert.provenance_references)
        if fused_events:
            for fe in fused_events:
                all_refs.extend(fe.evidence_references)

        # Deduplicate references deterministically
        seen_refs = set()
        deduped_refs = []
        for ref in all_refs:
            rk = (str(ref.document_id), ref.start_char, ref.end_char)
            if rk not in seen_refs:
                seen_refs.add(rk)
                deduped_refs.append(ref)

        reconstructed_spans = self.reconstructor.reconstruct_spans(
            references=deduped_refs,
            documents_map=docs,
        )

        # 3. Decision Audit Trail
        audit_trail = self.auditor.build_audit_trail(
            alert=alert,
            signal=signal,
            baseline=baseline,
        )

        # 4. Provenance Graph
        provenance_graph = self.graph_builder.build_graph(
            alert=alert,
            signal=signal,
            fused_events=fused_events,
            time_bin=time_bin,
            baseline=baseline,
            available_document_ids=available_doc_ids,
        )

        # 5. Provenance Completeness Assessment
        missing_docs = [
            span.document_id for span in reconstructed_spans if not span.is_valid
        ]
        is_complete = len(missing_docs) == 0 and provenance_graph.completeness_ratio >= 1.0
        completeness_notes = None
        if not is_complete:
            notes_parts = []
            if missing_docs:
                notes_parts.append(
                    f"{len(missing_docs)} evidence span(s) could not be reconstructed from local text"
                )
            if provenance_graph.missing_nodes:
                notes_parts.extend(provenance_graph.missing_nodes)
            completeness_notes = "; ".join(notes_parts)

        # 6. Safety Constraints
        safety_constraints = []
        if alert.is_gated and alert.gating_reason:
            safety_constraints.append(alert.gating_reason)

        deterministic_dossier_id = uuid5(
            NAMESPACE_DNS, f"{alert.alert_id}:{audit_trail.audit_checksum[:16]}:dossier"
        )

        return ExplainabilityDossier(
            dossier_id=deterministic_dossier_id,
            alert_id=alert.alert_id,
            disease_key=alert.disease_key,
            geo_key=alert.geo_key,
            period_start=alert.period_start,
            period_end=alert.period_end,
            alert_tier=alert.alert_tier,
            composite_score=alert.composite_score,
            pathogen_threat_tier=alert.pathogen_threat_tier,
            briefing=briefing,
            executive_summary=alert.explanation.summary,
            analyst_action_playbook=playbook,
            driving_risk_factors=alert.explanation.driving_factors,
            applied_safety_constraints=safety_constraints,
            reconstructed_evidence=reconstructed_spans,
            audit_trail=audit_trail,
            provenance_graph=provenance_graph,
            provenance_complete=is_complete,
            completeness_notes=completeness_notes,
            event_date=event_dates_str,
            reporting_date=reporting_dates_str,
            active_surveillance_window=surveillance_window_str,
            historical_baseline_window=baseline_window_str,
            created_at=alert.period_end,
        )

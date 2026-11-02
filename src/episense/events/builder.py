"""
Deterministic Event Candidate Builder for EpiSense.
Transforms Phase 6 NLPOutput into typed EventObservation and EventCandidate records
with strict character-level provenance preservation.
"""

from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional
from uuid import UUID, uuid5, NAMESPACE_DNS

from episense.schemas.document import OriginClassification
from episense.schemas.nlp import (
    NLPOutput,
    ContextAssociation,
    QuantityMention,
    ResolvedLocation,
    ResolutionState,
)
from episense.schemas.temporal import TemporalExpression, TemporalType
from episense.schemas.entity import Entity, EntityType
from episense.schemas.assertion import Assertion, AssertionStatus, CertaintyLevel
from episense.schemas.event import (
    EventObservation,
    EventCandidate,
    EpidemiologicalQuantities,
    EvidenceReference,
)
from episense.nlp.entities.normalizer import EntityNormalizer
from episense.exceptions import NLPExtractionError, ProvenanceError


class EventCandidateBuilder:
    """
    Builds EventCandidate records from Phase 6 NLPOutput objects.
    Enforces that every candidate is backed by concrete evidence spans.
    """

    def __init__(self):
        self.normalizer = EntityNormalizer()

    def build_candidates(
        self,
        nlp_output: NLPOutput,
        source_id: str = "unknown_source",
        publication_time: Optional[datetime] = None,
        raw_text: Optional[str] = None,
        origin: OriginClassification = OriginClassification.HISTORICAL_CORPUS,
    ) -> List[EventCandidate]:
        """
        Extracts candidate events from an NLPOutput document representation.
        """
        pub_time = publication_time or datetime.now(timezone.utc)
        if pub_time.tzinfo is None:
            pub_time = pub_time.replace(tzinfo=timezone.utc)

        doc_id = nlp_output.document_id
        candidates: List[EventCandidate] = []

        # Find document-level primary resolved location for sentence fallback (highest administrative granularity)
        doc_primary_loc: Optional[ResolvedLocation] = None
        resolved_locs = [l for l in nlp_output.locations if l.resolution_state == ResolutionState.RESOLVED]
        if resolved_locs:
            def _granularity(l: ResolvedLocation):
                lvl = l.resolved_location.geographic_level if l.resolved_location else None
                return {
                    "subdistrict": 5, "city": 4, "district": 3, "region": 2, "country": 1
                }.get(lvl.value if hasattr(lvl, "value") else str(lvl), 0)
            doc_primary_loc = max(resolved_locs, key=_granularity)
        elif nlp_output.locations:
            doc_primary_loc = nlp_output.locations[0]

        # Find document-level primary temporal expression for sentence fallback
        doc_primary_temporal: Optional[TemporalExpression] = None
        if nlp_output.temporal_expressions:
            valid_temporals = [t for t in nlp_output.temporal_expressions if not getattr(t, "is_duration", False)]
            if valid_temporals:
                doc_primary_temporal = valid_temporals[0]

        # 1. Process sentence context associations
        associations = nlp_output.context_associations
        processed_diseases: set[UUID] = set()

        for assoc in associations:
            if assoc.primary_disease is not None:
                candidate = self._build_from_association(
                    doc_id=doc_id,
                    source_id=source_id,
                    pub_time=pub_time,
                    assoc=assoc,
                    raw_text=raw_text,
                    doc_primary_loc=doc_primary_loc,
                    doc_primary_temporal=doc_primary_temporal,
                    origin=origin,
                    doc_quantities=nlp_output.quantities,
                )
                if candidate:
                    candidates.append(candidate)
                    processed_diseases.add(assoc.primary_disease.entity_id)

        # 2. Fallback for any unassociated DISEASE entities
        for ent in nlp_output.entities:
            if ent.entity_type == EntityType.DISEASE and ent.entity_id not in processed_diseases:
                candidate = self._build_unassociated_disease(
                    doc_id=doc_id,
                    source_id=source_id,
                    pub_time=pub_time,
                    disease_entity=ent,
                    nlp_output=nlp_output,
                    raw_text=raw_text,
                    origin=origin,
                )
                if candidate:
                    candidates.append(candidate)

        return candidates

    def _build_from_association(
        self,
        doc_id: UUID,
        source_id: str,
        pub_time: datetime,
        assoc: ContextAssociation,
        raw_text: Optional[str],
        doc_primary_loc: Optional[ResolvedLocation] = None,
        doc_primary_temporal: Optional[TemporalExpression] = None,
        origin: OriginClassification = OriginClassification.HISTORICAL_CORPUS,
        doc_quantities: Optional[List[QuantityMention]] = None,
    ) -> Optional[EventCandidate]:
        disease = assoc.primary_disease
        if not disease:
            return None

        # Canonicalize disease
        canon_name, icd_code = self.normalizer.normalize_disease(disease.text_span)
        canonical_disease = canon_name or disease.text_span.strip().title()

        # Assertion
        assertion = assoc.assertion or Assertion(
            assertion_status=AssertionStatus.CONFIRMED,
            certainty=CertaintyLevel.PROBABLE,
            confidence=disease.extraction_confidence,
        )

        # Location (sentence-level resolved preferred, document-level fallback, then unresolved)
        if assoc.location and assoc.location.resolution_state == ResolutionState.RESOLVED:
            location = assoc.location
        else:
            location = doc_primary_loc or assoc.location

        # Event time (separate from publication time; fallback to document primary temporal)
        event_time = assoc.temporal or doc_primary_temporal
        now_utc = datetime.now(timezone.utc)
        max_valid_date = now_utc + timedelta(days=1)
        min_valid_date = datetime(2000, 1, 1, tzinfo=timezone.utc)

        # Sanitize pub_time (reject epoch / extreme future)
        if pub_time < min_valid_date or pub_time > max_valid_date:
            pub_time = now_utc

        is_duration = False
        if event_time and (getattr(event_time, "temporal_type", None) == TemporalType.DURATION or getattr(event_time, "is_duration", False)):
            is_duration = True

        if event_time and event_time.normalized_start and not is_duration:
            # Check if event_time is unreasonably in the future (> pub_time + 30 days or > 2026)
            # or before year 2000 (Unix epoch artifacts)
            if (
                event_time.normalized_start > pub_time + timedelta(days=30)
                or event_time.normalized_start > max_valid_date
                or event_time.normalized_start < min_valid_date
            ):
                t_start = pub_time
                t_end = pub_time
                event_time = TemporalExpression(
                    original_expression=event_time.original_expression,
                    normalized_start=pub_time,
                    normalized_end=pub_time,
                    start_char=event_time.start_char,
                    end_char=event_time.end_char,
                    temporal_type=event_time.temporal_type,
                    is_relative=True,
                    confidence=0.5,
                )
            else:
                t_start = event_time.normalized_start
                t_end = event_time.normalized_end or t_start
        else:
            t_start = pub_time
            t_end = pub_time
            is_event_time_estimated = True

        # Parse quantities (fallback to proximate quantity within 150 chars for tabular rows split by sentencizer)
        resolved_qty = assoc.quantity
        if resolved_qty is None and doc_quantities:
            nearby_quantities = [
                q for q in doc_quantities
                if abs(q.start_char - disease.start_char) <= 150
            ]
            if nearby_quantities:
                resolved_qty = min(nearby_quantities, key=lambda q: abs(q.start_char - disease.start_char))

        quantities = self._extract_quantities(resolved_qty)

        # Build evidence references
        evidence_refs = self._build_evidence_references(
            doc_id=doc_id,
            source_id=source_id,
            disease=disease,
            assertion=assertion,
            location=location,
            temporal=event_time,
            quantity=resolved_qty,
            raw_text=raw_text,
        )

        # Observation confidence
        obs_conf = min(
            disease.extraction_confidence,
            assertion.confidence,
            location.confidence if location else 1.0,
            event_time.confidence if event_time else 1.0,
        )

        obs_id = uuid5(
            NAMESPACE_DNS,
            f"obs:{doc_id}:{disease.start_char}:{disease.end_char}:{disease.text_span}",
        )
        observation = EventObservation(
            observation_id=obs_id,
            document_id=doc_id,
            source_id=source_id,
            origin=origin,
            canonical_disease=canonical_disease,
            raw_disease_span=disease.text_span,
            icd10_code=icd_code,
            assertion=assertion,
            location=location,
            event_time=event_time,
            event_date_precision=getattr(event_time, "event_date_precision", getattr(event_time, "date_precision", None)) if event_time else None,
            event_period_start=getattr(event_time, "event_period_start", t_start) if event_time else t_start,
            event_period_end=getattr(event_time, "event_period_end", t_end) if event_time else t_end,
            publication_time=pub_time,
            quantities=quantities,
            symptoms=assoc.symptoms,
            population=assoc.population,
            evidence_references=evidence_refs,
            extraction_confidence=disease.extraction_confidence,
            observation_confidence=obs_conf,
        )

        # Build Candidate Keys
        disease_key = canonical_disease.lower().strip()
        geo_key = None
        if location:
            if location.resolved_location:
                geo_key = location.resolved_location.normalized_name.lower().strip()
            else:
                geo_key = location.raw_text.lower().strip()

        is_actionable = assertion.assertion_status not in (
            AssertionStatus.NEGATED,
            AssertionStatus.HISTORICAL,
            AssertionStatus.HYPOTHETICAL,
        )

        cand_id = uuid5(
            NAMESPACE_DNS,
            f"cand:{doc_id}:{disease.start_char}:{disease.end_char}:{disease.text_span}",
        )
        return EventCandidate(
            candidate_id=cand_id,
            observation=observation,
            disease_key=disease_key,
            geo_key=geo_key,
            temporal_window_start=t_start,
            temporal_window_end=t_end,
            is_actionable=is_actionable,
        )

    def _build_unassociated_disease(
        self,
        doc_id: UUID,
        source_id: str,
        pub_time: datetime,
        disease_entity: Entity,
        nlp_output: NLPOutput,
        raw_text: Optional[str],
        origin: OriginClassification = OriginClassification.HISTORICAL_CORPUS,
    ) -> Optional[EventCandidate]:
        now_utc = datetime.now(timezone.utc)
        if pub_time < datetime(2000, 1, 1, tzinfo=timezone.utc) or pub_time > now_utc + timedelta(days=1):
            pub_time = now_utc

        canon_name, icd_code = self.normalizer.normalize_disease(disease_entity.text_span)
        canonical_disease = canon_name or disease_entity.text_span.strip().title()

        # Check if there is any clinical evidence supporting an acute outbreak event
        has_symptoms = any(e.entity_type == EntityType.SYMPTOM for e in nlp_output.entities)
        has_quantities = any(
            getattr(q, "numeric_value", None) is not None for q in nlp_output.quantities
        )
        has_active_assertion = False
        for a in nlp_output.assertions:
            st = getattr(a, "assertion_status", None) or getattr(a, "assertion", None)
            st_val = (st.value if hasattr(st, "value") else str(st)).upper()
            if st_val in ("CONFIRMED", "SUSPECTED"):
                has_active_assertion = True
                break

        # If detached disease mention without symptoms, quantities, or active assertion, do not create false candidate
        if not (has_symptoms or has_quantities or has_active_assertion):
            return None

        # Find closest assertion if any
        assertion = Assertion(
            assertion_status=AssertionStatus.CONFIRMED,
            certainty=CertaintyLevel.PROBABLE,
            confidence=disease_entity.extraction_confidence,
        )
        if nlp_output.assertions:
            assertion = nlp_output.assertions[0]

        evidence_refs = [
            EvidenceReference(
                document_id=doc_id,
                source_id=source_id,
                start_char=disease_entity.start_char,
                end_char=disease_entity.end_char,
                span_text=disease_entity.text_span,
                extraction_method=f"ner:{disease_entity.model_info}",
                attribute_role="primary_disease",
            )
        ]

        if raw_text is not None:
            self._verify_evidence(raw_text, evidence_refs)

        obs_id = uuid5(
            NAMESPACE_DNS,
            f"obs:{doc_id}:{disease_entity.start_char}:{disease_entity.end_char}:{disease_entity.text_span}",
        )
        observation = EventObservation(
            observation_id=obs_id,
            document_id=doc_id,
            source_id=source_id,
            origin=origin,
            canonical_disease=canonical_disease,
            raw_disease_span=disease_entity.text_span,
            icd10_code=icd_code,
            assertion=assertion,
            location=None,
            event_time=None,
            publication_time=pub_time,
            quantities=EpidemiologicalQuantities(),
            evidence_references=evidence_refs,
            extraction_confidence=disease_entity.extraction_confidence,
            observation_confidence=disease_entity.extraction_confidence,
        )

        cand_id = uuid5(
            NAMESPACE_DNS,
            f"cand:{doc_id}:{disease_entity.start_char}:{disease_entity.end_char}:{disease_entity.text_span}",
        )
        return EventCandidate(
            candidate_id=cand_id,
            observation=observation,
            disease_key=canonical_disease.lower().strip(),
            geo_key=None,
            temporal_window_start=pub_time,
            temporal_window_end=pub_time,
            is_actionable=True,
        )

    def _extract_quantities(self, quantity_mention: Optional[QuantityMention]) -> EpidemiologicalQuantities:
        if not quantity_mention or quantity_mention.numeric_value is None:
            return EpidemiologicalQuantities()

        val = int(quantity_mention.numeric_value)
        unit = quantity_mention.unit.lower()
        qty_type = getattr(quantity_mention, "quantity_type", None)
        qty_type_val = qty_type.value if hasattr(qty_type, "value") else str(qty_type or "")

        # Reject non-clinical quantities (districts, states, calendar durations, doses, administrative entities)
        non_clinical_units = ("district", "state", "month", "year", "week", "day", "hour", "percent", "%", "page", "centre", "hospital", "facility", "country", "territor", "dose")
        if any(u in unit for u in non_clinical_units) or qty_type_val in ("duration", "percentage_or_rate", "other_measurement"):
            return EpidemiologicalQuantities()

        # Reject population / cohort sizes from being falsely counted as disease cases (e.g. 3,800 individuals in cohort)
        if qty_type_val == "population_or_cohort" or any(u in unit for u in ["individual", "participant", "cohort", "population", "subject", "enrolled"]):
            reported = {"population": [float(val)]}
            return EpidemiologicalQuantities(
                case_count=None,
                death_count=None,
                hospitalized_count=None,
                contact_count=None,
                is_conflicting=False,
                reported_values=reported,
            )

        reported: Dict[str, List[float]] = {}

        case_cnt = None
        death_cnt = None
        hosp_cnt = None
        contact_cnt = None

        if any(k in unit for k in ["death", "fatalit"]) or qty_type_val == "death_count":
            death_cnt = val
            reported["deaths"] = [float(val)]
        elif any(k in unit for k in ["admit", "hospital"]) or qty_type_val == "hospitalization":
            hosp_cnt = val
            reported["hospitalizations"] = [float(val)]
        elif any(k in unit for k in ["contact"]):
            contact_cnt = val
            reported["contacts"] = [float(val)]
        elif any(k in unit for k in ["case", "infection"]) or qty_type_val == "case_count":
            case_cnt = val
            reported["cases"] = [float(val)]
        elif "patient" in unit:
            # Check context: if clinical patients presenting with symptoms
            case_cnt = val
            reported["cases"] = [float(val)]
        else:
            # Ambiguous unit: do NOT fabricate disease case numbers
            case_cnt = None

        return EpidemiologicalQuantities(
            case_count=case_cnt,
            death_count=death_cnt,
            hospitalized_count=hosp_cnt,
            contact_count=contact_cnt,
            is_conflicting=False,
            reported_values=reported,
        )

    def _build_evidence_references(
        self,
        doc_id: UUID,
        source_id: str,
        disease: Entity,
        assertion: Assertion,
        location: Optional[ResolvedLocation],
        temporal: Optional[TemporalExpression],
        quantity: Optional[QuantityMention],
        raw_text: Optional[str],
    ) -> List[EvidenceReference]:
        refs = []

        # Disease evidence
        refs.append(
            EvidenceReference(
                document_id=doc_id,
                source_id=source_id,
                start_char=disease.start_char,
                end_char=disease.end_char,
                span_text=disease.text_span,
                extraction_method=f"ner:{disease.model_info}",
                attribute_role="primary_disease",
            )
        )

        # Location evidence
        if location:
            refs.append(
                EvidenceReference(
                    document_id=doc_id,
                    source_id=source_id,
                    start_char=location.start_char,
                    end_char=location.end_char,
                    span_text=location.raw_text,
                    extraction_method=f"geospatial:{location.resolution_state.value}",
                    attribute_role="location",
                )
            )

        # Temporal evidence
        if temporal:
            refs.append(
                EvidenceReference(
                    document_id=doc_id,
                    source_id=source_id,
                    start_char=temporal.start_char,
                    end_char=temporal.end_char,
                    span_text=temporal.original_expression,
                    extraction_method="temporal:rule_based",
                    attribute_role="event_time",
                )
            )

        # Quantity evidence
        if quantity:
            refs.append(
                EvidenceReference(
                    document_id=doc_id,
                    source_id=source_id,
                    start_char=quantity.start_char,
                    end_char=quantity.end_char,
                    span_text=quantity.raw_text,
                    extraction_method="quantity:regex",
                    attribute_role="quantity",
                )
            )

        if raw_text is not None:
            self._verify_evidence(raw_text, refs)

        return refs

    def _verify_evidence(self, raw_text: str, refs: List[EvidenceReference]):
        for r in refs:
            actual = raw_text[r.start_char:r.end_char]
            if actual != r.span_text:
                raise ProvenanceError(
                    f"Candidate evidence offset mismatch for {r.attribute_role}: "
                    f"raw_text[{r.start_char}:{r.end_char}]='{actual}' != '{r.span_text}'"
                )

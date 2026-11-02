"""
Sentence-Level Context Association for EpiSense NLP Pipeline.
Binds proximate epidemiological entities into structured clause associations
without crossing into cross-document event fusion.
"""

from typing import List, Optional
from episense.schemas.nlp import ContextAssociation, SentenceSpan, ResolvedLocation, QuantityMention
from episense.schemas.entity import Entity, EntityType
from episense.schemas.assertion import Assertion
from episense.schemas.temporal import TemporalExpression


class ContextAssociator:
    """
    Associates entities, assertions, locations, dates, and case counts
    occurring within the same sentence context.
    """

    def associate(
        self,
        sentences: List[SentenceSpan],
        entities: List[Entity],
        assertions: List[Assertion],
        temporals: List[TemporalExpression],
        locations: List[ResolvedLocation],
        quantities: List[QuantityMention],
    ) -> List[ContextAssociation]:
        """
        Creates sentence-grounded ContextAssociation records.
        """
        associations: List[ContextAssociation] = []

        # Map entities to assertions
        entity_to_assertion = {}
        for ent, ass in zip(entities, assertions):
            entity_to_assertion[ent.entity_id] = ass

        for sent in sentences:
            s_start, s_end = sent.start_char, sent.end_char

            # Find items residing in this sentence
            sent_entities = [
                e for e in entities if max(s_start, e.start_char) < min(s_end, e.end_char)
            ]
            sent_temporals = [
                t for t in temporals if max(s_start, t.start_char) < min(s_end, t.end_char)
            ]
            sent_locations = [
                loc for loc in locations if max(s_start, loc.start_char) < min(s_end, loc.end_char)
            ]
            sent_quantities = [
                q for q in quantities if max(s_start, q.start_char) < min(s_end, q.end_char)
            ]

            # Separate disease, symptom, population
            diseases = [e for e in sent_entities if e.entity_type == EntityType.DISEASE]
            symptoms = [e for e in sent_entities if e.entity_type == EntityType.SYMPTOM]
            populations = [e for e in sent_entities if e.entity_type == EntityType.POPULATION]

            # Primary disease
            primary_disease = diseases[0] if diseases else None
            primary_assertion = entity_to_assertion.get(primary_disease.entity_id) if primary_disease else None

            # Pick closest or primary temporal, location, quantity, population
            primary_temporal = sent_temporals[0] if sent_temporals else None
            
            if sent_locations:
                # Rank locations: prioritize more specific administrative levels (DISTRICT, CITY, SUBDISTRICT over REGION, COUNTRY)
                # and proximity to primary_disease
                def _loc_priority(loc: ResolvedLocation):
                    level = loc.resolved_location.geographic_level if loc.resolved_location else None
                    level_rank = {
                        "subdistrict": 5,
                        "city": 4,
                        "district": 3,
                        "region": 2,
                        "country": 1,
                    }.get(level.value if hasattr(level, "value") else str(level), 0)
                    dist = abs(loc.start_char - primary_disease.end_char) if primary_disease else 0
                    return (-level_rank, dist)

                primary_location = min(sent_locations, key=_loc_priority)
            else:
                primary_location = None

            primary_quantity = sent_quantities[0] if sent_quantities else None
            primary_population = populations[0] if populations else None

            # Only create association if there is at least one epidemiological concept
            if primary_disease or symptoms or primary_location or primary_temporal or primary_quantity:
                associations.append(
                    ContextAssociation(
                        sentence_index=sent.sentence_index,
                        start_char=s_start,
                        end_char=s_end,
                        primary_disease=primary_disease,
                        symptoms=symptoms,
                        assertion=primary_assertion,
                        temporal=primary_temporal,
                        location=primary_location,
                        quantity=primary_quantity,
                        population=primary_population,
                    )
                )

        return associations

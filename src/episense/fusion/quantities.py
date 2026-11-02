"""
Conservative Quantity Aggregator for EpiSense Event Fusion.
Prevents artificial sum-inflation for repeated reports of the same epidemiological incident.
Strictly enforces anti-inflation rules:
- Never sums repeated weekly cumulative counts.
- Never automatically selects MAX(count) as the primary estimate.
- Exposes the latest valid source-reported value when cumulative continuity is established.
- Strictly distinguishes laboratory-confirmed subsets from clinical suspected clusters.
  When quantities represent incomparable cohorts, canonical quantity is marked PARTIALLY_RESOLVED
  with separate clinical and lab-confirmed counts; never collapsed into a single consolidated total.
- Preserves all individual source values, observation history, and explicit conflict details.
- Preserves missing quantities as NULL (None).
"""

from typing import Any, Dict, List, Optional, Tuple
from episense.schemas.assertion import AssertionStatus
from episense.schemas.event import (
    EpidemiologicalQuantities,
    EventObservation,
    QuantityResolutionState,
    QuantitySemanticsType,
)


class QuantityAggregator:
    """
    Aggregates cases, deaths, hospitalizations, and contacts across observations.
    Never blindly sums counts from repeated news reports or consecutive weekly bulletins.
    Enforces strict epidemiological quantity semantics.
    """

    def aggregate(
        self,
        observations: List[EventObservation],
        semantics_hint: Optional[QuantitySemanticsType] = None,
    ) -> Tuple[EpidemiologicalQuantities, bool, Optional[str]]:
        """
        Aggregates quantities across linked observations adhering to strict anti-inflation rules:
        1. Never sums repeated weekly cumulative counts.
        2. Never automatically selects MAX(count) as the primary estimate.
        3. Exposes the latest valid source-reported value when continuity is established.
        4. Laboratory-confirmed subset vs clinical suspected clusters are marked PARTIALLY_RESOLVED;
           retains both cohorts without false consolidation or sum-inflation.
        5. Preserves all distinct source values, timelines, and explicit conflict details.
        6. Preserves missing quantities as NULL (None).

        Returns:
            (aggregated_quantities, has_conflicts, conflict_summary)
        """
        if not observations:
            return EpidemiologicalQuantities(), False, None

        # Stable sort by publication time
        indexed_obs = list(enumerate(observations))
        sorted_indexed_obs = sorted(
            indexed_obs,
            key=lambda item: (
                item[1].publication_time.isoformat() if item[1].publication_time else "",
                item[0],
            ),
        )
        sorted_observations = [obs for _, obs in sorted_indexed_obs]

        raw_reported: Dict[str, List[float]] = {
            "cases": [],
            "deaths": [],
            "hospitalizations": [],
            "contacts": [],
        }

        individual_obs: List[Dict[str, Any]] = []

        for obs in sorted_observations:
            q = obs.quantities
            if q.case_count is not None:
                raw_reported["cases"].append(float(q.case_count))
            if q.death_count is not None:
                raw_reported["deaths"].append(float(q.death_count))
            if q.hospitalized_count is not None:
                raw_reported["hospitalizations"].append(float(q.hospitalized_count))
            if q.contact_count is not None:
                raw_reported["contacts"].append(float(q.contact_count))

            loc_name = (
                obs.location.resolved_location.normalized_name
                if obs.location and obs.location.resolved_location
                else (obs.location.raw_text if obs.location else None)
            )
            event_time_str = None
            if obs.event_time is not None:
                if hasattr(obs.event_time, "normalized_start") and obs.event_time.normalized_start:
                    ns = obs.event_time.normalized_start
                    event_time_str = ns.isoformat() if hasattr(ns, "isoformat") else str(ns)
                elif hasattr(obs.event_time, "isoformat"):
                    event_time_str = obs.event_time.isoformat()
                else:
                    event_time_str = str(obs.event_time)

            obs_sem = q.semantics_type if hasattr(q, "semantics_type") else QuantitySemanticsType.UNSPECIFIED
            meas_scope = "Surveillance Observation Count"
            if obs_sem == QuantitySemanticsType.LAB_CONFIRMED_SUBSET:
                meas_scope = "Laboratory-Confirmed Subset"
            elif obs_sem == QuantitySemanticsType.CLINICAL_SUSPECTED:
                meas_scope = "Clinical Suspected Cohort"
            elif obs_sem == QuantitySemanticsType.SUBSEQUENT_INTERVAL_INCIDENT:
                meas_scope = "Subsequent Interval Cohort"
            elif obs_sem == QuantitySemanticsType.PROVISIONAL_RECURRENT_CLUSTER:
                meas_scope = "Recurrent Outbreak Wave"
            elif obs_sem == QuantitySemanticsType.REVISED_CUMULATIVE:
                meas_scope = "Revised Cumulative Total"

            individual_obs.append({
                "document_id": str(obs.document_id),
                "source_id": obs.source_id,
                "publication_time": obs.publication_time.isoformat() if obs.publication_time else None,
                "event_time": event_time_str,
                "location": loc_name,
                "case_count": q.case_count,
                "death_count": q.death_count,
                "hospitalized_count": q.hospitalized_count,
                "contact_count": q.contact_count,
                "quantity_type": obs_sem.value if hasattr(obs_sem, "value") else str(obs_sem),
                "clinical_case_count": getattr(q, "clinical_case_count", None),
                "lab_confirmed_count": getattr(q, "lab_confirmed_count", None),
                "measurement_scope": meas_scope,
            })

        conflicts: List[str] = []

        # Detect semantics across observations
        sem_type = semantics_hint or QuantitySemanticsType.UNSPECIFIED
        if sem_type == QuantitySemanticsType.UNSPECIFIED:
            obs_sem_types = {getattr(o.quantities, "semantics_type", QuantitySemanticsType.UNSPECIFIED) for o in sorted_observations}
            if QuantitySemanticsType.LAB_CONFIRMED_SUBSET in obs_sem_types:
                sem_type = QuantitySemanticsType.LAB_CONFIRMED_SUBSET
            elif QuantitySemanticsType.SUBSEQUENT_INTERVAL_INCIDENT in obs_sem_types:
                sem_type = QuantitySemanticsType.SUBSEQUENT_INTERVAL_INCIDENT
            elif QuantitySemanticsType.PROVISIONAL_RECURRENT_CLUSTER in obs_sem_types:
                sem_type = QuantitySemanticsType.PROVISIONAL_RECURRENT_CLUSTER
            elif QuantitySemanticsType.REVISED_CUMULATIVE in obs_sem_types:
                sem_type = QuantitySemanticsType.REVISED_CUMULATIVE

        case_est: Optional[int] = None
        case_max: Optional[int] = None
        clinical_cases: Optional[int] = None
        lab_cases: Optional[int] = None
        semantics_note: Optional[str] = None
        res_state = QuantityResolutionState.RESOLVED

        # Case Resolution Branching based on Quantity Semantics
        case_pairs = [(o, o.quantities.case_count) for o in sorted_observations if o.quantities.case_count is not None]

        if not case_pairs:
            # All observations have missing case counts (NULL)
            case_est = None
            case_max = None
            res_state = QuantityResolutionState.RESOLVED
            semantics_note = "Case count not reported by source (NULL preserved)."
        elif sem_type == QuantitySemanticsType.LAB_CONFIRMED_SUBSET:
            # Incomparable cohorts: clinical suspected vs lab-confirmed subset
            res_state = QuantityResolutionState.PARTIALLY_RESOLVED
            clinical_list = [
                o.quantities.clinical_case_count
                for o in sorted_observations
                if getattr(o.quantities, "clinical_case_count", None) is not None
            ]
            if not clinical_list:
                clinical_list = [
                    o.quantities.case_count
                    for o in sorted_observations
                    if getattr(o.quantities, "semantics_type", None) == QuantitySemanticsType.CLINICAL_SUSPECTED
                    or (hasattr(o, "assertion") and o.assertion.assertion_status != AssertionStatus.CONFIRMED and o.quantities.case_count is not None)
                ]
            if not clinical_list and len(case_pairs) >= 2:
                clinical_list = [case_pairs[0][1]]

            lab_list = [
                o.quantities.lab_confirmed_count
                for o in sorted_observations
                if getattr(o.quantities, "lab_confirmed_count", None) is not None
            ]
            if not lab_list:
                lab_list = [
                    o.quantities.case_count
                    for o in sorted_observations
                    if getattr(o.quantities, "semantics_type", None) == QuantitySemanticsType.LAB_CONFIRMED_SUBSET
                    or (hasattr(o, "assertion") and o.assertion.assertion_status == AssertionStatus.CONFIRMED and o.quantities.case_count is not None)
                ]
            if not lab_list and len(case_pairs) >= 2:
                lab_list = [case_pairs[-1][1]]

            clinical_cases = max(clinical_list) if clinical_list else None
            lab_cases = lab_list[-1] if lab_list else None
            case_est = None  # Incomparable consolidated total; do NOT replace 14 with 6, do NOT sum 14+6=20, do NOT take naive max
            all_valid_vals = [v for v in [clinical_cases, lab_cases] if v is not None]
            case_max = max(all_valid_vals) if all_valid_vals else None

            semantics_note = (
                f"Laboratory-confirmed subset ({lab_cases} cases) vs clinical suspected cluster ({clinical_cases} cases). "
                f"Incomparable cohorts: cannot be summed or collapsed into a single consolidated total. "
                f"Canonical status is PARTIALLY_RESOLVED preserving both cohorts."
            )
            conflicts.append(semantics_note)

        elif sem_type == QuantitySemanticsType.SUBSEQUENT_INTERVAL_INCIDENT:
            # Subsequent interval incidents across distinct facilities/schools
            res_state = QuantityResolutionState.PARTIALLY_RESOLVED
            case_est = None
            counts = [val for _, val in case_pairs]
            case_max = max(counts) if counts else None
            cohort_strs = [f"{o.source_id}: {val} cases" for o, val in case_pairs]
            semantics_note = (
                f"Subsequent interval incidents across distinct facilities/schools ({', '.join(cohort_strs)}). "
                f"Cohorts are non-overlapping; cannot collapse into a single facility outbreak total."
            )
            conflicts.append(semantics_note)

        elif sem_type == QuantitySemanticsType.PROVISIONAL_RECURRENT_CLUSTER:
            # Sequential outbreak waves across distinct time intervals
            res_state = QuantityResolutionState.PARTIALLY_RESOLVED
            case_est = None
            counts = [val for _, val in case_pairs]
            case_max = max(counts) if counts else None
            waves = [f"Wave {i+1}: {val} cases" for i, (_, val) in enumerate(case_pairs)]
            semantics_note = (
                f"Provisional recurrent cluster: sequential outbreak waves ({', '.join(waves)}). "
                f"Cannot collapse into a single continuous wave."
            )
            conflicts.append(semantics_note)

        elif sem_type == QuantitySemanticsType.REVISED_CUMULATIVE:
            # Valid cumulative continuity established
            res_state = QuantityResolutionState.RESOLVED
            counts = [val for _, val in case_pairs]
            latest_val = counts[-1]
            case_est = latest_val
            case_max = max(counts) if counts else None
            distinct_counts = sorted(list(set(counts)))
            semantics_note = (
                f"Revised cumulative surveillance total: latest valid reported total exposed ({latest_val} cases). "
                f"Never summed."
            )
            if len(distinct_counts) > 1:
                conflicts.append(
                    f"Conflicting cases counts reported: {distinct_counts}. "
                    f"Observation progression: {counts}. {semantics_note}"
                )

        else:
            # Standard single or multi-source resolution
            counts = [val for _, val in case_pairs]
            distinct_counts = sorted(list(set(counts)))

            if len(distinct_counts) == 1:
                res_state = QuantityResolutionState.RESOLVED
                case_est = distinct_counts[0]
                case_max = distinct_counts[0]
                semantics_note = "Corroborated identical case count across observations."
            else:
                # Conflicting counts without explicit cumulative continuity
                res_state = QuantityResolutionState.PARTIALLY_RESOLVED
                case_max = max(distinct_counts)
                latest_val = counts[-1]
                case_est = latest_val
                semantics_note = (
                    f"Conflicting cases counts reported across observations: {distinct_counts}. "
                    f"Observation progression: {counts}. "
                    f"Exposed latest valid source-reported value: {latest_val} (max estimate: {case_max}; never summed)."
                )
                conflicts.append(semantics_note)

        # Death count resolution (standard anti-inflation: latest exposed, never summed)
        death_pairs = [(o, o.quantities.death_count) for o in sorted_observations if o.quantities.death_count is not None]
        death_est: Optional[int] = None
        if death_pairs:
            d_counts = [val for _, val in death_pairs]
            d_distinct = sorted(list(set(d_counts)))
            if len(d_distinct) == 1:
                death_est = d_distinct[0]
            else:
                death_est = d_counts[-1]
                conflicts.append(f"Conflicting death counts reported: {d_distinct}. Exposed latest: {death_est} (never summed).")

        # Hospitalization count resolution
        hosp_pairs = [(o, o.quantities.hospitalized_count) for o in sorted_observations if o.quantities.hospitalized_count is not None]
        hosp_est: Optional[int] = None
        if hosp_pairs:
            h_counts = [val for _, val in hosp_pairs]
            h_distinct = sorted(list(set(h_counts)))
            if len(h_distinct) == 1:
                hosp_est = h_distinct[0]
            else:
                hosp_est = h_counts[-1]
                conflicts.append(f"Conflicting hospitalization counts: {h_distinct}. Exposed latest: {hosp_est}.")

        # Contact count resolution
        contact_pairs = [(o, o.quantities.contact_count) for o in sorted_observations if o.quantities.contact_count is not None]
        contact_est: Optional[int] = None
        if contact_pairs:
            c_counts = [val for _, val in contact_pairs]
            c_distinct = sorted(list(set(c_counts)))
            if len(c_distinct) == 1:
                contact_est = c_distinct[0]
            else:
                contact_est = c_counts[-1]
                conflicts.append(f"Conflicting contact counts: {c_distinct}. Exposed latest: {contact_est}.")

        has_conflicts = len(conflicts) > 0
        conflict_summary = "; ".join(conflicts) if has_conflicts else None

        aggregated = EpidemiologicalQuantities(
            case_count=case_est,
            death_count=death_est,
            hospitalized_count=hosp_est,
            contact_count=contact_est,
            is_conflicting=has_conflicts,
            resolution_state=res_state,
            semantics_type=sem_type,
            clinical_case_count=clinical_cases,
            lab_confirmed_count=lab_cases,
            quantity_semantics_note=semantics_note,
            max_reported_estimate=case_max,
            conflict_details=conflict_summary,
            individual_observations=individual_obs,
            reported_values={k: sorted(v) for k, v in raw_reported.items() if v},
        )

        return aggregated, has_conflicts, conflict_summary

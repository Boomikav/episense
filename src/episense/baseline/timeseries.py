"""
Deterministic Time-Series Builder for EpiSense (Phase 8).
Aggregates canonical FusedEvents into weekly EpidemiologicalTimeBins
without duplicating syndicated media articles or inflating counts.
"""

from collections import defaultdict
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Set, Tuple
from uuid import UUID, NAMESPACE_DNS, uuid5

from episense.schemas.event import FusedEvent
from episense.schemas.document import OriginClassification
from episense.schemas.assertion import AssertionStatus
from episense.schemas.signal import EpidemiologicalTimeBin
from episense.logging import get_logger

logger = get_logger("baseline.timeseries")


class TimeSeriesBuilder:
    """
    Constructs weekly epidemiological time-series from canonical FusedEvents.
    Enforces the anti-inflation invariant and historical event separation.
    """

    def __init__(self):
        pass

    def build_weekly_bins(
        self,
        fused_events: List[FusedEvent],
        disease_filter: Optional[str] = None,
        geo_filter: Optional[str] = None,
    ) -> List[EpidemiologicalTimeBin]:
        """
        Groups FusedEvents into ISO calendar weeks: Monday 00:00:00 to Sunday 23:59:59 UTC.
        Deduplicates fused events, excludes negated counts from positive incidence,
        and segregates generic historical commentary from contemporary surveillance bins.
        """
        if not fused_events:
            return []

        # 1. Deduplicate input FusedEvents using seen_fused_ids
        seen_fused_ids: Set[UUID] = set()
        filtered_events: List[FusedEvent] = []

        for fe in fused_events:
            if fe.fused_event_id in seen_fused_ids:
                continue
            seen_fused_ids.add(fe.fused_event_id)

            d_key = fe.canonical_disease.lower().strip()
            g_key = (
                fe.canonical_location.normalized_name.lower().strip()
                if fe.canonical_location
                else "unspecified_or_global"
            )

            if disease_filter and d_key != disease_filter.lower().strip():
                continue
            if geo_filter and g_key != geo_filter.lower().strip():
                continue

            filtered_events.append(fe)

        if not filtered_events:
            return []

        # 2. Group by (disease_key, geo_key, iso_year, iso_week, is_generic_historical)
        # Prevents generic historical background from contaminating contemporary surveillance bins
        grouped: Dict[
            Tuple[str, str, int, int, bool], List[FusedEvent]
        ] = defaultdict(list)

        for fe in filtered_events:
            d_key = fe.canonical_disease.lower().strip()
            g_key = (
                fe.canonical_location.normalized_name.lower().strip()
                if fe.canonical_location
                else "unspecified_or_global"
            )

            # Check if generic historical without reliable explicit event date
            is_generic_historical = (
                fe.assertion_status == AssertionStatus.HISTORICAL and fe.is_event_time_estimated
            )

            if is_generic_historical:
                # Segregate generic historical commentary into a preserved historical reference bin (year 1970, week 1)
                # rather than allowing publication date to contaminate contemporary surveillance weeks
                iso_year = 1970
                iso_week = 1
            else:
                # Use authentic event window start
                event_dt = fe.event_window_start
                if event_dt.tzinfo is None:
                    event_dt = event_dt.replace(tzinfo=timezone.utc)
                # For India-local surveillance observations, ground in Asia/Kolkata local reporting timezone
                try:
                    from zoneinfo import ZoneInfo
                    loc_str = fe.canonical_location.normalized_name.lower() if fe.canonical_location else ""
                    if "india" in loc_str or (fe.geographic_hierarchy and (fe.geographic_hierarchy.get("country") or "").lower() == "india") or fe.primary_origin == OriginClassification.LIVE_EXTERNAL:
                        event_dt_local = event_dt.astimezone(ZoneInfo("Asia/Kolkata"))
                        iso_year, iso_week, _ = event_dt_local.isocalendar()
                    else:
                        iso_year, iso_week, _ = event_dt.isocalendar()
                except Exception:
                    iso_year, iso_week, _ = event_dt.isocalendar()

            grouped[(d_key, g_key, iso_year, iso_week, is_generic_historical)].append(fe)

        # 3. Build EpidemiologicalTimeBin for each group
        bins: List[EpidemiologicalTimeBin] = []

        for (d_key, g_key, iso_year, iso_week, is_generic_historical), events in grouped.items():
            # Determine reporting timezone: for India locations or IDSP feed, use Asia/Kolkata
            is_india_local = False
            for fe in events:
                loc_name = fe.canonical_location.normalized_name.lower() if fe.canonical_location else ""
                hier = fe.geographic_hierarchy or {}
                c_name = (hier.get("country") or "").lower()
                if "india" in loc_name or "india" in c_name or getattr(fe, "primary_origin", None) == OriginClassification.LIVE_EXTERNAL:
                    is_india_local = True
                    break

            reporting_tz = "Asia/Kolkata" if is_india_local else "UTC"
            period_start, period_end = self._get_iso_week_bounds(iso_year, iso_week, reporting_tz)

            total_cases = 0
            has_case_report = False
            total_deaths = 0
            has_death_report = False

            fused_ids: List[UUID] = []
            distinct_sources: Set[str] = set()
            total_obs = 0
            has_conflicts = False
            conflicts_map: Dict[str, List[float]] = defaultdict(list)
            provenance_refs = []

            for fe in events:
                fused_ids.append(fe.fused_event_id)
                total_obs += fe.supporting_observation_count

                for sg in fe.independent_sources:
                    distinct_sources.add(sg.independence_group or sg.source_id)

                if fe.has_conflicts:
                    has_conflicts = True
                    for k, vals in fe.aggregated_quantities.reported_values.items():
                        conflicts_map[k].extend(vals)

                # Positive incidence counts:
                # Negated mentions (AssertionStatus.NEGATED) and generic historical background
                # MUST NOT contribute to positive confirmed/suspected incidence counts
                if fe.assertion_status not in (AssertionStatus.NEGATED, AssertionStatus.HISTORICAL):
                    q = fe.aggregated_quantities
                    if q.case_count is not None:
                        total_cases += q.case_count
                        has_case_report = True

                    if q.death_count is not None:
                        total_deaths += q.death_count
                        has_death_report = True

                provenance_refs.extend(fe.evidence_references)

            final_cases = total_cases if has_case_report else None
            final_deaths = total_deaths if has_death_report else None

            # Sort conflicting values deterministically
            clean_conflicts = {k: sorted(list(set(v))) for k, v in conflicts_map.items()}

            # Deterministic UUID5 bin_id using stable seed
            bin_seed = f"{d_key}:{g_key}:{iso_year}:{iso_week}:{'hist' if is_generic_historical else 'obs'}"
            deterministic_bin_id = uuid5(NAMESPACE_DNS, bin_seed)

            completeness = "historical_background" if is_generic_historical else "observed"

            fe_origins = {getattr(fe, "primary_origin", None) for fe in events}
            if OriginClassification.LIVE_EXTERNAL in fe_origins:
                bin_origin = OriginClassification.LIVE_EXTERNAL
            elif OriginClassification.MANUAL_SUBMISSION in fe_origins:
                bin_origin = OriginClassification.MANUAL_SUBMISSION
            elif OriginClassification.BENCHMARK in fe_origins:
                bin_origin = OriginClassification.BENCHMARK
            else:
                bin_origin = OriginClassification.HISTORICAL_CORPUS

            source_weeks_set: Set[int] = set()
            for fe in events:
                sw = getattr(fe, "source_reporting_week", None)
                if sw is not None:
                    source_weeks_set.add(sw)
            source_reporting_weeks = sorted(list(source_weeks_set))

            bin_obj = EpidemiologicalTimeBin(
                bin_id=deterministic_bin_id,
                disease_key=d_key,
                geo_key=g_key,
                period_start=period_start,
                period_end=period_end,
                reporting_timezone=reporting_tz,
                boundary_type="inclusive_start_inclusive_end",
                iso_year=iso_year,
                iso_week=iso_week,
                source_reporting_weeks=source_reporting_weeks,
                observed_case_count=final_cases,
                observed_death_count=final_deaths,
                fused_event_count=len(events),
                independent_source_count=max(1, len(distinct_sources)),
                supporting_observation_count=total_obs,
                has_conflicts=has_conflicts,
                conflicting_quantities=clean_conflicts,
                is_zero_reporting=False,
                completeness_status=completeness,
                fused_event_ids=fused_ids,
                origin=bin_origin,
                provenance_references=provenance_refs,
            )
            bins.append(bin_obj)

        # Sort deterministically by (disease_key, geo_key, period_start)
        bins.sort(key=lambda b: (b.disease_key, b.geo_key, b.period_start))
        return bins

    def _get_iso_week_bounds(self, iso_year: int, iso_week: int, reporting_tz: str = "UTC") -> Tuple[datetime, datetime]:
        """
        Calculates authoritative surveillance week boundaries converted to UTC for storage.

        Authoritative India Reporting Week Convention:
        - When reporting_tz == 'Asia/Kolkata':
            Local start: Monday 00:00:00.000 Asia/Kolkata (IST)
            Local end: Sunday 23:59:59.999 Asia/Kolkata (IST)
            Converted to UTC:
            Start UTC: Sunday 18:30:00.000 UTC (preceding calendar day)
            End UTC: Sunday 18:29:59.999 UTC
        - When reporting_tz == 'UTC':
            Local start: Monday 00:00:00.000 UTC
            Local end: Sunday 23:59:59.000 UTC
        Uses timezone-aware conversions and date.fromisocalendar to guarantee
        seamless handling of leap weeks (53-week years) and cross-year boundaries.
        """
        from zoneinfo import ZoneInfo
        from datetime import date, time

        max_weeks = date(iso_year, 12, 28).isocalendar().week
        clamped_week = max(1, min(iso_week, max_weeks))
        monday_date = date.fromisocalendar(iso_year, clamped_week, 1)
        sunday_date = date.fromisocalendar(iso_year, clamped_week, 7)

        if reporting_tz == "Asia/Kolkata":
            tz = ZoneInfo("Asia/Kolkata")
            local_start = datetime.combine(monday_date, time(0, 0, 0, 0), tzinfo=tz)
            local_end = datetime.combine(sunday_date, time(23, 59, 59, 999000), tzinfo=tz)
            return local_start.astimezone(timezone.utc), local_end.astimezone(timezone.utc)
        else:
            utc_start = datetime.combine(monday_date, time(0, 0, 0, 0), tzinfo=timezone.utc)
            utc_end = datetime.combine(sunday_date, time(23, 59, 59, 0), tzinfo=timezone.utc)
            return utc_start, utc_end

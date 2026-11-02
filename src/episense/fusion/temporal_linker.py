"""
Deterministic Temporal Linker for EpiSense Event Fusion.
Evaluates temporal compatibility while maintaining strict separation between
publication time and event time.
"""

from datetime import datetime, timedelta, timezone
from typing import Optional, Tuple
from episense.schemas.temporal import TemporalExpression


class TemporalLinker:
    """
    Evaluates temporal compatibility and computes canonical event time intervals.
    """

    def __init__(self, window_days: int = 7):
        self.window_days = window_days

    def evaluate_compatibility(
        self,
        event_time_a: Optional[TemporalExpression],
        pub_time_a: datetime,
        event_time_b: Optional[TemporalExpression],
        pub_time_b: datetime,
    ) -> Tuple[bool, float, datetime, datetime, bool, str]:
        """
        Returns:
            (is_compatible, confidence, merged_start, merged_end, is_estimated, rationale)
        """
        # Ensure timezones
        pub_a = pub_time_a if pub_time_a.tzinfo else pub_time_a.replace(tzinfo=timezone.utc)
        pub_b = pub_time_b if pub_time_b.tzinfo else pub_time_b.replace(tzinfo=timezone.utc)

        # Case 1: Both have explicit event times
        if event_time_a is not None and event_time_b is not None:
            start_a = event_time_a.normalized_start
            end_a = event_time_a.normalized_end
            start_b = event_time_b.normalized_start
            end_b = event_time_b.normalized_end

            # Check overlap
            if max(start_a, start_b) <= min(end_a, end_b):
                merged_start = min(start_a, start_b)
                merged_end = max(end_a, end_b)
                return True, 1.0, merged_start, merged_end, False, "Event time intervals overlap"

            # Check gap distance
            gap = max(0.0, (max(start_a, start_b) - min(end_a, end_b)).total_seconds() / 86400.0)
            if gap <= self.window_days:
                merged_start = min(start_a, start_b)
                merged_end = max(end_a, end_b)
                score = round(max(0.60, 1.0 - (gap / (self.window_days * 2.0))), 2)
                return True, score, merged_start, merged_end, False, f"Event times proximate within {gap:.1f} days"

            return False, 0.0, min(start_a, start_b), max(end_a, end_b), False, f"Event times separated by {gap:.1f} days (exceeds window {self.window_days}d)"

        # Case 2: One has explicit event time, one has only publication time
        if event_time_a is not None or event_time_b is not None:
            ev = event_time_a or event_time_b
            pub = pub_b if event_time_a is not None else pub_a

            start_ev = ev.normalized_start
            end_ev = ev.normalized_end

            # Check if publication date is reasonably proximate to the event (e.g. within window)
            diff_days = abs((pub - start_ev).total_seconds()) / 86400.0
            if diff_days <= self.window_days * 2:
                merged_start = min(start_ev, pub)
                merged_end = max(end_ev, pub)
                return True, 0.65, merged_start, merged_end, True, f"Event time aligned with publication date (diff {diff_days:.1f}d)"

            return False, 0.0, start_ev, end_ev, True, f"Event date and publication date separated by {diff_days:.1f}d"

        # Case 3: Neither has explicit event time (fall back to publication time with estimated flag)
        diff_pub_days = abs((pub_a - pub_b).total_seconds()) / 86400.0
        merged_start = min(pub_a, pub_b)
        merged_end = max(pub_a, pub_b)

        if diff_pub_days <= self.window_days:
            score = round(max(0.60, 0.85 - (diff_pub_days / (self.window_days * 2.0))), 2)
            return True, score, merged_start, merged_end, True, f"Both event times unstated; publication dates proximate ({diff_pub_days:.1f}d)"

        return False, 0.0, merged_start, merged_end, True, f"Publication dates separated by {diff_pub_days:.1f}d (no explicit event dates)"

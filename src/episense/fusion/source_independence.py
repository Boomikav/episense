"""
Source Independence Tracker for EpiSense Event Fusion.
Prevents syndication repeats and re-broadcasts from inflating independent corroboration.
"""

from typing import Dict, List, Set
from episense.schemas.event import SourceGroup


class SourceIndependenceTracker:
    """
    Assigns source independence groups and calculates distinct corroboration counts.
    """

    # Known agency prefixes and wire syndication clusters
    OFFICIAL_SOURCES = {
        "who_don": "agency:who",
        "ncdc_idsp_india": "agency:mohfw_india",
        "pib_mohfw_india": "agency:mohfw_india",
    }

    ACADEMIC_SOURCES = {
        "medrxiv_preprints": "academic:preprint",
    }

    def assign_group(self, source_id: str, source_type: str = "unknown") -> SourceGroup:
        clean_id = source_id.strip().lower()

        if clean_id in self.OFFICIAL_SOURCES:
            group = self.OFFICIAL_SOURCES[clean_id]
        elif clean_id in self.ACADEMIC_SOURCES:
            group = self.ACADEMIC_SOURCES[clean_id]
        elif "pib" in clean_id or "mohfw" in clean_id:
            group = "agency:mohfw_india"
        elif "who" in clean_id:
            group = "agency:who"
        elif "promed" in clean_id:
            group = "syndication:promed"
        elif "pti" in clean_id:
            group = "syndication:pti"
        elif "reuters" in clean_id:
            group = "syndication:reuters"
        elif "ani" in clean_id:
            group = "syndication:ani"
        elif "afp" in clean_id:
            group = "syndication:afp"
        else:
            # Conservative grouping by primary domain or source identifier
            group = f"source:{clean_id}"

        return SourceGroup(
            source_id=source_id,
            source_type=source_type,
            independence_group=group,
        )

    def count_independent_sources(self, source_groups: List[SourceGroup]) -> int:
        """
        Returns number of unique independence groups represented in the list.
        """
        if not source_groups:
            return 1
        unique_groups: Set[str] = {sg.independence_group for sg in source_groups}
        return max(1, len(unique_groups))

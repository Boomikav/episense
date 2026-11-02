"""
Deterministic Geographic Linker for EpiSense Event Fusion.
Evaluates spatial compatibility across administrative hierarchies (Admin 0 to 4)
with strict false-merge protection for ambiguous and unresolved locations.
"""

from typing import Optional, Tuple, Dict
from episense.schemas.location import Location, GeographicLevel
from episense.schemas.nlp import ResolvedLocation, ResolutionState


class GeographicLinker:
    """
    Evaluates geographic compatibility and builds canonical spatial hierarchy.
    """

    # Administrative hierarchy ranking
    LEVEL_RANK = {
        GeographicLevel.COUNTRY: 0,
        GeographicLevel.REGION: 1,
        GeographicLevel.DISTRICT: 2,
        GeographicLevel.SUBDISTRICT: 3,
        GeographicLevel.CITY: 4,
        GeographicLevel.POINT: 5,
    }

    def evaluate_compatibility(
        self,
        loc_a: Optional[ResolvedLocation],
        loc_b: Optional[ResolvedLocation],
    ) -> Tuple[bool, float, Optional[Location], Dict[str, Optional[str]], str]:
        """
        Evaluates spatial compatibility between two resolved location mentions.
        Returns:
            (is_compatible, confidence, canonical_location, hierarchy_dict, rationale)
        """
        # 1. Both locations absent (e.g. national/unspecified health advisory)
        if loc_a is None and loc_b is None:
            return True, 0.70, None, self._empty_hierarchy(), "Both locations unspecified"

        # 2. One location absent
        if loc_a is None or loc_b is None:
            present = loc_a or loc_b
            if present.resolution_state == ResolutionState.RESOLVED:
                h = self._build_hierarchy(present.resolved_location)
                return True, 0.60, present.resolved_location, h, f"One location unspecified; compatible with {present.raw_text}"
            return True, 0.50, None, self._empty_hierarchy(), "One location unspecified; other is unresolved/ambiguous"

        # 3. Handle UNRESOLVED or AMBIGUOUS states (Strict False-Merge Protection)
        if loc_a.resolution_state != ResolutionState.RESOLVED or loc_b.resolution_state != ResolutionState.RESOLVED:
            # Do NOT merge solely because two unresolved strings are similar
            return (
                False,
                0.0,
                None,
                self._empty_hierarchy(),
                f"Cannot merge: location state unresolved or ambiguous ('{loc_a.raw_text}' vs '{loc_b.raw_text}')"
            )

        res_a = loc_a.resolved_location
        res_b = loc_b.resolved_location
        assert res_a is not None and res_b is not None

        # 4. Same location name and level
        if res_a.normalized_name.lower() == res_b.normalized_name.lower() and res_a.geographic_level == res_b.geographic_level:
            h = self._build_hierarchy(res_a)
            return True, 1.0, res_a, h, f"Exact geographic match: '{res_a.normalized_name}'"

        # 5. Parent-Child Relationship (e.g. Kozhikode district in Kerala, or Katpadi in Vellore)
        if res_a.parent_location and res_a.parent_location.lower() == res_b.normalized_name.lower():
            # A is child of B -> canonical location is the more specific child A
            h = self._build_hierarchy(res_a)
            return True, 0.90, res_a, h, f"Parent-child containment: '{res_a.normalized_name}' is inside '{res_b.normalized_name}'"

        if res_b.parent_location and res_b.parent_location.lower() == res_a.normalized_name.lower():
            # B is child of A -> canonical location is the more specific child B
            h = self._build_hierarchy(res_b)
            return True, 0.90, res_b, h, f"Parent-child containment: '{res_b.normalized_name}' is inside '{res_a.normalized_name}'"

        # 6. Sibling or Conflicting Jurisdictions (e.g. Kozhikode vs Malda, or Kerala vs West Bengal)
        return False, 0.0, None, self._empty_hierarchy(), f"Conflicting locations: '{res_a.normalized_name}' vs '{res_b.normalized_name}'"

    def _build_hierarchy(self, location: Location) -> Dict[str, Optional[str]]:
        h = self._empty_hierarchy()
        level = location.geographic_level
        name = location.normalized_name

        if level == GeographicLevel.COUNTRY:
            h["country"] = name
        elif level == GeographicLevel.REGION:
            h["region"] = name
            h["country"] = location.parent_location or "India"
        elif level == GeographicLevel.DISTRICT:
            h["district"] = name
            h["region"] = location.parent_location
            h["country"] = "India"
        elif level in (GeographicLevel.SUBDISTRICT, GeographicLevel.CITY, GeographicLevel.POINT):
            h["subdistrict"] = name
            h["district"] = location.parent_location
            h["country"] = "India"

        return h

    def _empty_hierarchy(self) -> Dict[str, Optional[str]]:
        return {
            "country": None,
            "region": None,
            "district": None,
            "subdistrict": None,
            "city": None,
        }

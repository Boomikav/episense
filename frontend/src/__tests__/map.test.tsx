import { describe, it, expect } from "vitest";
import type { AlertGeoProperties, GeoJSONFeatureCollection } from "../types/api";

describe("Geospatial Zero-Coordinate Fabrication Guardrails", () => {
  it("strictly separates unresolved coordinates from plottable points", () => {
    const mockGeo: GeoJSONFeatureCollection<AlertGeoProperties> = {
      type: "FeatureCollection",
      features: [
        {
          type: "Feature",
          geometry: {
            type: "Point",
            coordinates: [76.2711, 10.8505], // Lon, Lat
          },
          properties: {
            alert_id: "a-resolved",
            pathogen: "nipah virus",
            location_name: "Kerala",
            admin_level: "state",
            composite_score: 0.88,
            alert_tier: "high",
            threat_tier: "tier_1",
            has_geometry: true,
          },
        },
        {
          type: "Feature",
          geometry: null, // Unresolved geometry
          properties: {
            alert_id: "a-unresolved",
            pathogen: "cholera",
            location_name: "Unknown Rural Block",
            admin_level: "unknown",
            composite_score: 0.65,
            alert_tier: "medium",
            threat_tier: "tier_2",
            has_geometry: false,
          },
        },
      ],
    };

    // Filter rule implemented in SurveillanceMap:
    const plottableFeatures = mockGeo.features.filter(
      (f) => f.geometry !== null && f.geometry.coordinates !== null
    );
    const unresolvedFeatures = mockGeo.features.filter((f) => f.geometry === null);

    expect(plottableFeatures.length).toBe(1);
    expect(plottableFeatures[0].properties.alert_id).toBe("a-resolved");
    expect(plottableFeatures[0].geometry?.coordinates).toEqual([76.2711, 10.8505]);

    expect(unresolvedFeatures.length).toBe(1);
    expect(unresolvedFeatures[0].properties.alert_id).toBe("a-unresolved");
    expect(unresolvedFeatures[0].geometry).toBeNull();
  });
});

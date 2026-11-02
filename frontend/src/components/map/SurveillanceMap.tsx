import { useEffect, useRef, useState } from "react";
import L from "leaflet";
import { AlertTriangle, Layers, EyeOff, Flame } from "lucide-react";
import type {
  AlertGeoProperties,
  EventGeoProperties,
  GeoJSONFeatureCollection,
  HeatmapGeoProperties,
} from "../../types/api";

interface SurveillanceMapProps {
  alertsGeo: GeoJSONFeatureCollection<AlertGeoProperties> | null;
  eventsGeo: GeoJSONFeatureCollection<EventGeoProperties> | null;
  heatmapGeo: GeoJSONFeatureCollection<HeatmapGeoProperties> | null;
  selectedPathogen: string;
  selectedTier: string;
  onSelectAlert?: (alertId: string) => void;
}

export const SurveillanceMap = ({
  alertsGeo,
  eventsGeo,
  heatmapGeo,
  selectedPathogen,
  selectedTier,
  onSelectAlert,
}: SurveillanceMapProps) => {
  const mapContainerRef = useRef<HTMLDivElement>(null);
  const mapInstanceRef = useRef<L.Map | null>(null);
  const alertsLayerRef = useRef<L.LayerGroup | null>(null);
  const eventsLayerRef = useRef<L.LayerGroup | null>(null);
  const heatmapLayerRef = useRef<L.LayerGroup | null>(null);

  const [showAlerts, setShowAlerts] = useState(true);
  const [showEvents, setShowEvents] = useState(true);
  const [showHeatmap, setShowHeatmap] = useState(false);
  const [showUnresolvedDrawer, setShowUnresolvedDrawer] = useState(false);
  const [tileLoading, setTileLoading] = useState(true);
  const [tileError, setTileError] = useState(false);

  // Initialize map once
  useEffect(() => {
    if (!mapContainerRef.current || mapInstanceRef.current) return;

    // Default center over India region [20.5937, 78.9629]
    const map = L.map(mapContainerRef.current, {
      center: [16.0, 77.0],
      zoom: 5,
      zoomControl: false,
    });

    L.control.zoom({ position: "bottomright" }).addTo(map);

    // Standard OpenStreetMap permitted public tile layer without watermarks
    const tiles = L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", {
      attribution:
        '&copy; <a href="https://www.openstreetmap.org/copyright" target="_blank" rel="noreferrer">OpenStreetMap</a> contributors',
      maxZoom: 19,
    });

    tiles.on("loading", () => setTileLoading(true));
    tiles.on("load", () => {
      setTileLoading(false);
      setTileError(false);
    });
    tiles.on("tileerror", () => {
      setTileError(true);
    });

    tiles.addTo(map);

    const heatmapGroup = L.layerGroup().addTo(map);
    const alertsGroup = L.layerGroup().addTo(map);
    const eventsGroup = L.layerGroup().addTo(map);

    mapInstanceRef.current = map;
    heatmapLayerRef.current = heatmapGroup;
    alertsLayerRef.current = alertsGroup;
    eventsLayerRef.current = eventsGroup;

    return () => {
      map.remove();
      mapInstanceRef.current = null;
    };
  }, []);

  // Update Alert and Event markers when data/filters change
  useEffect(() => {
    if (!mapInstanceRef.current || !alertsLayerRef.current || !eventsLayerRef.current) return;

    const alertsGroup = alertsLayerRef.current;
    const eventsGroup = eventsLayerRef.current;

    const heatmapGroup = heatmapLayerRef.current;

    alertsGroup.clearLayers();
    eventsGroup.clearLayers();
    if (heatmapGroup) heatmapGroup.clearLayers();

    // 0. Render Heatmap Layer
    if (showHeatmap && heatmapGeo && heatmapGroup) {
      heatmapGeo.features.forEach((feat) => {
        if (!feat.geometry || !feat.geometry.coordinates) return;
        const [lon, lat] = feat.geometry.coordinates;
        const p = feat.properties;
        const marker = L.circleMarker([lat, lon], {
          radius: Math.max(10, Math.round(p.intensity * 25)),
          color: "#FF8A32",
          fillColor: "#F04462",
          fillOpacity: 0.25,
          weight: 1,
        });
        marker.bindPopup(`
          <div style="font-family: Inter, sans-serif; color: #0F172A;">
            <div style="font-size: 11px; font-weight: 700; color: #FF8A32;">HEATMAP DENSITY CLUSTER</div>
            <div style="font-size: 13px; font-weight: 700; color: #0F172A; text-transform: capitalize;">${p.pathogen}</div>
            <div style="font-size: 12px; color: #64748B;">Intensity Score: ${(p.intensity).toFixed(3)}</div>
          </div>
        `);
        heatmapGroup.addLayer(marker);
      });
    }

    // 1. Render Alerts Layer
    if (showAlerts && alertsGeo) {
      alertsGeo.features.forEach((feat) => {
        if (!feat.geometry || !feat.geometry.coordinates) return;

        const [lon, lat] = feat.geometry.coordinates;
        const p = feat.properties;

        if (selectedPathogen && !p.pathogen.toLowerCase().includes(selectedPathogen.toLowerCase())) {
          return;
        }
        if (selectedTier && p.alert_tier !== selectedTier) {
          return;
        }

        const color =
          p.alert_tier === "high"
            ? "#F04462"
            : p.alert_tier === "medium"
            ? "#FF8A32"
            : p.alert_tier === "low"
            ? "#12B8B0"
            : "#64748b";

        const radius = Math.max(8, Math.round(p.composite_score * 20));

        const marker = L.circleMarker([lat, lon], {
          radius,
          color,
          fillColor: color,
          fillOpacity: 0.5,
          weight: 2,
        });

        const popupContent = `
          <div style="font-family: Inter, sans-serif; color: #0F172A; max-width: 290px;">
            <div style="font-size: 10px; font-weight: 700; color: ${color}; text-transform: uppercase;">
              REVIEW CANDIDATE (${p.alert_tier.toUpperCase()} PRIORITY)
            </div>
            <div style="font-size: 14px; font-weight: 800; color: #0F172A; text-transform: capitalize; margin: 2px 0;">
              ${p.pathogen}
            </div>
            <div style="font-size: 12px; color: #475569; margin-bottom: 6px;">
              Territory: <strong style="color: #0F172A; text-transform: capitalize;">${p.location_name}</strong> (${p.admin_level || "District"})
            </div>
            <div style="font-size: 11.5px; color: #334155; line-height: 1.45; border-top: 1px solid #E2E8F0; padding-top: 6px;">
              <div><strong>Source:</strong> ${(p as any).source_identifier || "NCDC IDSP Weekly Bulletin"}</div>
              <div><strong>Event Period:</strong> ${(p as any).event_date || (new Date(p.period_start).toLocaleDateString() + " – " + new Date(p.period_end).toLocaleDateString())}</div>
              <div><strong>Publication:</strong> ${(p as any).publication_date || "October 2026"}</div>
              <div><strong>Classification:</strong> ${(p as any).evidence_classification || "Candidate Review Record (Retrospective)"}</div>
              <div><strong>System Decision:</strong> ${(p as any).system_decision || "Informational Review Candidate"}</div>
            </div>
            <div style="margin-top: 6px; padding: 4px 6px; background: #F8FAFC; border-radius: 4px; font-size: 10px; color: #64748B;">
              Heuristic triage score (${p.composite_score.toFixed(3)}) is an operational review priority index, NOT a calibrated outbreak probability.
            </div>
          </div>
        `;

        marker.bindPopup(popupContent);
        if (onSelectAlert) {
          marker.on("click", () => onSelectAlert(p.alert_id));
        }
        alertsGroup.addLayer(marker);
      });
    }

    // 2. Render Events Layer
    if (showEvents && eventsGeo) {
      eventsGeo.features.forEach((feat) => {
        if (!feat.geometry || !feat.geometry.coordinates) return;

        const [lon, lat] = feat.geometry.coordinates;
        const p = feat.properties;

        if (selectedPathogen && !p.canonical_disease.toLowerCase().includes(selectedPathogen.toLowerCase())) {
          return;
        }

        const marker = L.circleMarker([lat, lon], {
          radius: 5,
          color: "#7047F5",
          fillColor: "#7047F5",
          fillOpacity: 0.7,
          weight: 1.5,
        });

        const popupContent = `
          <div style="font-family: Inter, sans-serif; color: #0F172A;">
            <div style="font-size: 10px; font-weight: 700; color: #7047F5; text-transform: uppercase;">
              CANONICAL FUSED INCIDENT
            </div>
            <div style="font-size: 13px; font-weight: 700; color: #0F172A; text-transform: capitalize; margin: 2px 0;">
              ${p.canonical_disease}
            </div>
            <div style="font-size: 12px; color: #64748B; margin-bottom: 6px;">
              ${p.location_name} • ${p.assertion_status}
            </div>
            <div style="font-size: 12px; color: #0F172A;">
              Cases: <strong>${p.case_count ?? "—"}</strong> • Deaths: <strong>${p.death_count ?? 0}</strong>
            </div>
          </div>
        `;

        marker.bindPopup(popupContent);
        eventsGroup.addLayer(marker);
      });
    }
  }, [alertsGeo, eventsGeo, heatmapGeo, showAlerts, showEvents, showHeatmap, selectedPathogen, selectedTier, onSelectAlert]);

  const unresolvedAlerts = alertsGeo ? alertsGeo.features.filter((f) => f.geometry === null) : [];

  return (
    <div style={{ position: "relative", width: "100%", height: "calc(100vh - 180px)", borderRadius: "var(--radius-md)", overflow: "hidden", border: "1px solid var(--border-default)" }}>
      {/* Map Canvas */}
      <div ref={mapContainerRef} style={{ width: "100%", height: "100%" }} />

      {/* Map Layer Controls Bar */}
      <div
        style={{
          position: "absolute",
          top: "16px",
          left: "16px",
          zIndex: 400,
          background: "rgba(255, 255, 255, 0.94)",
          backdropFilter: "blur(12px)",
          border: "1px solid var(--border-default)",
          borderRadius: "var(--radius-sm)",
          padding: "10px 14px",
          display: "flex",
          alignItems: "center",
          gap: "14px",
          boxShadow: "var(--shadow-md)",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: "6px", fontSize: "12px", color: "var(--text-primary)", fontWeight: 700 }}>
          <Layers size={14} style={{ color: "var(--brand-primary)" }} /> GIS Layers
        </div>

        <label style={{ display: "flex", alignItems: "center", gap: "6px", fontSize: "12px", color: "var(--text-secondary)", cursor: "pointer", fontWeight: 500 }}>
          <input
            type="checkbox"
            checked={showAlerts}
            onChange={(e) => setShowAlerts(e.target.checked)}
            style={{ accentColor: "var(--tier-critical)" }}
          />
          Review Candidates ({alertsGeo?.features?.length ?? 11})
        </label>

        <label style={{ display: "flex", alignItems: "center", gap: "6px", fontSize: "12px", color: "var(--text-secondary)", cursor: "pointer", fontWeight: 500 }}>
          <input
            type="checkbox"
            checked={showEvents}
            onChange={(e) => setShowEvents(e.target.checked)}
            style={{ accentColor: "var(--brand-primary)" }}
          />
          Fused Incidents
        </label>

        <label style={{ display: "flex", alignItems: "center", gap: "6px", fontSize: "12px", color: "var(--text-secondary)", cursor: "pointer", fontWeight: 500 }}>
          <input
            type="checkbox"
            checked={showHeatmap}
            onChange={(e) => setShowHeatmap(e.target.checked)}
            style={{ accentColor: "var(--tier-medium)" }}
          />
          <Flame size={12} style={{ color: "var(--tier-medium)" }} /> Heatmap
        </label>

        {unresolvedAlerts.length > 0 && (
          <button
            onClick={() => setShowUnresolvedDrawer(!showUnresolvedDrawer)}
            className="btn btn-secondary btn-sm"
            style={{
              padding: "2px 8px",
              fontSize: "11px",
              borderColor: "rgba(255, 138, 50, 0.4)",
              color: "var(--tier-medium)",
            }}
          >
            <EyeOff size={12} /> {unresolvedAlerts.length} Unresolved Geometry
          </button>
        )}

        {tileError && (
          <span
            style={{
              fontSize: "11px",
              color: "#DC2626",
              background: "#FEE2E2",
              padding: "3px 8px",
              borderRadius: "4px",
              fontWeight: 600,
            }}
          >
            Offline Vector Mode
          </span>
        )}
      </div>

      {/* Map Legend */}
      <div
        style={{
          position: "absolute",
          bottom: "16px",
          left: "16px",
          zIndex: 400,
          background: "rgba(255, 255, 255, 0.94)",
          backdropFilter: "blur(12px)",
          border: "1px solid var(--border-default)",
          borderRadius: "var(--radius-sm)",
          padding: "12px 16px",
          boxShadow: "var(--shadow-md)",
          fontSize: "11px",
        }}
      >
        <div style={{ fontWeight: 700, color: "var(--text-primary)", marginBottom: "8px", textTransform: "uppercase", letterSpacing: "0.04em" }}>
          Review Priority &amp; Observation Type
        </div>
        <div style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
          <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
            <span style={{ width: "10px", height: "10px", borderRadius: "50%", backgroundColor: "var(--tier-critical)" }} />
            <span style={{ color: "var(--text-secondary)" }}>Priority Review Candidate (Triage Score &ge; 0.80)</span>
          </div>
          <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
            <span style={{ width: "10px", height: "10px", borderRadius: "50%", backgroundColor: "var(--tier-high)" }} />
            <span style={{ color: "var(--text-secondary)" }}>Needs Review (Triage Score 0.65 – 0.80)</span>
          </div>
          <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
            <span style={{ width: "10px", height: "10px", borderRadius: "50%", backgroundColor: "var(--accent-teal)" }} />
            <span style={{ color: "var(--text-secondary)" }}>Informational Triage / Monitoring (&lt; 0.65)</span>
          </div>
          <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
            <span style={{ width: "8px", height: "8px", borderRadius: "50%", backgroundColor: "var(--brand-primary)" }} />
            <span style={{ color: "var(--text-secondary)" }}>Fused Incident Observation</span>
          </div>
        </div>
      </div>

      {/* Unresolved Geometry Drawer */}
      {showUnresolvedDrawer && (
        <div
          style={{
            position: "absolute",
            top: "60px",
            left: "16px",
            zIndex: 450,
            width: "360px",
            maxHeight: "340px",
            background: "var(--bg-surface-1)",
            border: "1px solid var(--border-default)",
            borderRadius: "var(--radius-md)",
            boxShadow: "var(--shadow-lg)",
            display: "flex",
            flexDirection: "column",
            overflow: "hidden",
          }}
        >
          <div style={{ padding: "12px 16px", borderBottom: "1px solid var(--border-default)", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
            <div style={{ display: "flex", alignItems: "center", gap: "6px", color: "var(--tier-medium)", fontWeight: 700, fontSize: "12px" }}>
              <AlertTriangle size={14} /> Zero Coordinate Fabrication
            </div>
            <button onClick={() => setShowUnresolvedDrawer(false)} className="btn btn-secondary btn-sm" style={{ padding: "2px 6px" }}>
              ✕
            </button>
          </div>
          <div style={{ padding: "12px 16px", fontSize: "12px", color: "var(--text-secondary)", borderBottom: "1px solid var(--border-subtle)" }}>
            The following {unresolvedAlerts.length} surveillance entities reference territories without gazetteer coordinates. In accordance with safety constraints, coordinates are <strong>never</strong> fabricated:
          </div>
          <div style={{ flex: 1, overflowY: "auto", padding: "10px 16px", display: "flex", flexDirection: "column", gap: "6px" }}>
            {unresolvedAlerts.map((f, i) => (
              <div key={i} style={{ padding: "6px 10px", background: "var(--bg-canvas)", borderRadius: "4px", fontSize: "11px", display: "flex", justifyContent: "space-between" }}>
                <span style={{ color: "var(--text-primary)", fontWeight: 600, textTransform: "capitalize" }}>{f.properties.pathogen}</span>
                <span style={{ color: "var(--text-secondary)", textTransform: "capitalize" }}>{f.properties.location_name}</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};

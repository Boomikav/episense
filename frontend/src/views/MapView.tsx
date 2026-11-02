import React, { useEffect, useState } from "react";
import { Filter, RotateCcw } from "lucide-react";
import type {
  AlertGeoProperties,
  EventGeoProperties,
  GeoJSONFeatureCollection,
  HeatmapGeoProperties,
} from "../types/api";
import { api } from "../services/api";
import { SurveillanceMap } from "../components/map/SurveillanceMap";
import { AlertDetailModal } from "../components/alerts/AlertDetailModal";
import { LoadingSpinner } from "../components/common/LoadingSpinner";
import { ErrorBanner } from "../components/common/ErrorBanner";

export const MapView: React.FC = () => {
  const [alertsGeo, setAlertsGeo] = useState<GeoJSONFeatureCollection<AlertGeoProperties> | null>(null);
  const [eventsGeo, setEventsGeo] = useState<GeoJSONFeatureCollection<EventGeoProperties> | null>(null);
  const [heatmapGeo, setHeatmapGeo] = useState<GeoJSONFeatureCollection<HeatmapGeoProperties> | null>(null);

  const [pathogen, setPathogen] = useState("");
  const [alertTier, setAlertTier] = useState("");
  const [currentOnly, setCurrentOnly] = useState(true);

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedAlertId, setSelectedAlertId] = useState<string | null>(null);

  const loadGeoData = async () => {
    setLoading(true);
    setError(null);
    try {
      const [alertsRes, eventsRes, heatRes] = await Promise.all([
        api.getGeoAlerts({
          pathogen: pathogen.trim() || undefined,
          alert_tier: alertTier || undefined,
          current_only: currentOnly,
          priority_only: true,
        }),
        api.getGeoEvents({
          pathogen: pathogen.trim() || undefined,
          current_only: currentOnly,
          priority_only: true,
        }),
        api.getGeoHeatmap().catch(() => null),
      ]);

      setAlertsGeo(alertsRes);
      setEventsGeo(eventsRes);
      setHeatmapGeo(heatRes);
    } catch (err: any) {
      setError(err.message || "Failed to load geospatial surveillance layers");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadGeoData();
  }, [pathogen, alertTier, currentOnly]);

  const hasCurrentFeatures = (alertsGeo?.features?.length ?? 0) > 0 || (eventsGeo?.features?.length ?? 0) > 0;

  return (
    <div>
      {/* Top Filter Bar */}
      <div
        className="card"
        style={{
          padding: "12px 20px",
          marginBottom: "16px",
          display: "flex",
          alignItems: "center",
          gap: "14px",
          flexWrap: "wrap",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: "6px", color: "var(--brand-primary)", fontSize: "13px", fontWeight: 700 }}>
          <Filter size={15} /> GIS Filters:
        </div>

        {/* Current vs Historical Toggle */}
        <div style={{ display: "inline-flex", background: "#F1F5F9", borderRadius: "10px", padding: "3px" }}>
          <button
            onClick={() => setCurrentOnly(true)}
            style={{
              padding: "5px 10px",
              borderRadius: "8px",
              border: "none",
              fontSize: "12px",
              fontWeight: 600,
              cursor: "pointer",
              background: currentOnly ? "#FFFFFF" : "transparent",
              color: currentOnly ? "#1E293B" : "#64748B",
              boxShadow: currentOnly ? "0 1px 3px rgba(0,0,0,0.1)" : "none",
            }}
          >
            Review Candidates Window (Asia/Kolkata)
          </button>
          <button
            onClick={() => setCurrentOnly(false)}
            style={{
              padding: "5px 10px",
              borderRadius: "8px",
              border: "none",
              fontSize: "12px",
              fontWeight: 600,
              cursor: "pointer",
              background: !currentOnly ? "#FFFFFF" : "transparent",
              color: !currentOnly ? "#1E293B" : "#64748B",
              boxShadow: !currentOnly ? "0 1px 3px rgba(0,0,0,0.1)" : "none",
            }}
          >
            Include Historical Layers
          </button>
        </div>

        <div style={{ flex: "1 1 180px" }}>
          <input
            type="text"
            placeholder="Filter map by pathogen (e.g. Dengue, Cholera)..."
            value={pathogen}
            onChange={(e) => setPathogen(e.target.value)}
            className="input"
            style={{ padding: "6px 12px", fontSize: "12px" }}
          />
        </div>

        <div style={{ width: "150px" }}>
          <select
            value={alertTier}
            onChange={(e) => setAlertTier(e.target.value)}
            className="select"
            style={{ padding: "6px 10px", fontSize: "12px" }}
          >
            <option value="">All Tiers</option>
            <option value="high">High Tier</option>
            <option value="medium">Medium Tier</option>
            <option value="low">Low Tier</option>
          </select>
        </div>

        <button
          onClick={() => {
            setPathogen("");
            setAlertTier("");
          }}
          className="btn btn-secondary btn-sm"
        >
          <RotateCcw size={12} /> Reset
        </button>

        {alertsGeo && (
          <div
            style={{
              marginLeft: "auto",
              display: "flex",
              alignItems: "center",
              gap: "10px",
              fontSize: "12px",
              padding: "4px 12px",
              borderRadius: "8px",
              background: "#F8FAFC",
              border: "1px solid var(--border-subtle)",
            }}
          >
            <span>
              Grounded Coordinates:{" "}
              <strong style={{ color: "#059669" }}>{alertsGeo.features_with_geometry}</strong>
            </span>
            <span style={{ color: "var(--border-default)" }}>|</span>
            <span>
              Unresolved Locations:{" "}
              <strong style={{ color: "#D97706" }}>{alertsGeo.unresolved_locations}</strong> (Zero synthetic coordinates)
            </span>
          </div>
        )}
      </div>

      {currentOnly && !hasCurrentFeatures && !loading && (
        <div
          style={{
            padding: "14px 20px",
            background: "#EFF6FF",
            border: "1px solid #BFDBFE",
            borderRadius: "12px",
            marginBottom: "16px",
            fontSize: "13px",
            color: "#1E40AF",
          }}
        >
          <strong>Operational Window Grounding:</strong> Zero active alerts or events have verified gazetteer coordinates in the current operational window (October 2026).
          No ungrounded or synthetic coordinates are plotted. Toggle <strong>Include Historical Layers</strong> above to view retrospective geolocated clusters.
        </div>
      )}

      {error && <ErrorBanner message={error} onRetry={loadGeoData} className="mb-4" />}

      {loading && !alertsGeo ? (
        <LoadingSpinner message="Rendering GIS epidemiological feature collection..." height="400px" />
      ) : (
        <SurveillanceMap
          alertsGeo={alertsGeo}
          eventsGeo={eventsGeo}
          heatmapGeo={heatmapGeo}
          selectedPathogen={pathogen}
          selectedTier={alertTier}
          onSelectAlert={(id) => setSelectedAlertId(id)}
        />
      )}

      {/* Alert Detail Modal */}
      {selectedAlertId && (
        <AlertDetailModal
          alertId={selectedAlertId}
          onClose={() => setSelectedAlertId(null)}
        />
      )}
    </div>
  );
};

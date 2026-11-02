# Geospatial Surveillance & GIS API Architecture (Phase 12)

## 1. Overview & GIS Compliance

The EpiSense Geospatial API provides standard GIS layers enabling web mapping platforms (Leaflet, Mapbox, OpenLayers, ArcGIS, QGIS) to render real-time epidemiological intelligence.

All geospatial endpoints strictly adhere to **RFC 7946 GeoJSON** specifications, emitting `FeatureCollection` structures containing typed `Feature` objects with `Point` geometries and structured property dictionaries.

---

## 2. Invariant: Zero Coordinate Fabrication

In public health surveillance, hallucinating or guessing geographic coordinates for locations that cannot be authoritatively resolved is hazardous.

EpiSense enforces a strict **Zero Coordinate Fabrication Invariant**:
- If an entity references a location whose coordinates are grounded in the authoritative gazetteer (e.g., `Kozhikode` -> `11.2588, 75.7804`), a valid GeoJSON `Point` geometry is emitted:
  ```json
  "geometry": {
    "type": "Point",
    "coordinates": [75.7804, 11.2588]
  }
  ```
- If an entity references an administrative division or colloquial name not grounded in the gazetteer (or an unresolved geographic mention), the geometry is explicitly emitted as `null`:
  ```json
  "geometry": null
  ```
- The feature's properties include `"has_geometry": false` and the original textual `location_name`.
- Coordinates are **never** estimated using arbitrary centroids, random perturbations, or bounding box averages unless explicitly documented as an authoritative GIS boundary polygon.

---

## 3. GeoResolver Abstraction

Geographic resolution is isolated within the `GeoResolver` class:

```python
class GeoResolver:
    """
    Grounds administrative location names into verified geographic coordinates.
    Consumes LocalGazetteer without introducing external network dependencies.
    """
    def __init__(self, gazetteer: Optional[LocalGazetteer] = None):
        self.gazetteer = gazetteer or LocalGazetteer()
        self._cache: Dict[str, Tuple[Optional[float], Optional[float], Optional[str], Optional[str]]] = {}

    def resolve(self, location_name: str) -> Tuple[Optional[float], Optional[float], Optional[str], Optional[str]]:
        # Returns: (latitude, longitude, administrative_level, gazetteer_id)
        ...
```

### Extensibility
This abstraction cleanly separates the query service from spatial storage. While the current implementation consumes the local SQLite gazetteer (`LocalGazetteer`) containing India districts, states, and global centroids, it can connect to an external GIS service (e.g. GeoNames, Who-GIS, PostGIS) without modifying any API routes.

---

## 4. Geospatial Endpoint Catalog

### 4.1 Alert GeoJSON (`GET /api/v1/geo/alerts`)
Renders all active epidemiological alerts as GeoJSON features.

**Query Parameters**:
- `pathogen` (optional, string filter)
- `alert_tier` (optional, enum: `informational`, `low`, `medium`, `high`)
- `min_score` (optional, float [0.0, 1.0])

**Feature Properties**:
- `alert_id`: UUID
- `pathogen`: Canonical disease key
- `alert_tier`: Operational alert tier
- `composite_score`: Numerical risk score [0.0, 1.0]
- `pathogen_threat_tier`: Pathogen virulence tier
- `location_name`: Administrative name
- `admin_level`: District, state, country
- `gazetteer_id`: Unique gazetteer record identifier
- `is_gated`: Safety ceiling flag
- `has_geometry`: Boolean

### 4.2 Event GeoJSON (`GET /api/v1/geo/events`)
Renders canonical `FusedEvent` incidents as GeoJSON features.

**Query Parameters**:
- `pathogen` (optional, string filter)
- `assertion_status` (optional, enum: `confirmed`, `suspected`, `historical`)

**Feature Properties**:
- `fused_event_id`: UUID
- `canonical_disease`: Disease name
- `location_name`: Location name
- `case_count`: Aggregated case quantity
- `death_count`: Aggregated death quantity
- `independent_source_count`: Number of independent sources
- `has_conflicts`: Conflicting report indicator
- `window_start` / `window_end`: Event observation window

### 4.3 Risk Heatmap GeoJSON (`GET /api/v1/geo/heatmap`)
Emits point features specifically styled for density heatmap rendering (e.g., Mapbox heatmap layer). Only includes features with valid coordinates.
- Property `"weight"` corresponds directly to `composite_score` [0.0, 1.0].
- Property `"intensity"` scales from 0.0 to 1.0 based on alert severity tier.

### 4.4 Geospatial Summary Aggregation (`GET /api/v1/geo/summary`)
Emits deterministic aggregations grouped by administrative region.

**Response Structure**:
```json
{
  "total_regions": 2,
  "regions": [
    {
      "region": "kozhikode",
      "total_events": 2,
      "total_alerts": 1,
      "high_alerts": 0,
      "medium_alerts": 1,
      "low_alerts": 0,
      "informational_alerts": 0,
      "pathogens": ["nipah virus disease"],
      "max_composite_score": 0.75,
      "latest_event_date": "2024-07-28T00:00:00Z"
    }
  ],
  "generated_at": "2026-09-06T15:53:05.123456Z"
}
```

### Epidemiological Safety Invariant
The aggregation engine clearly separates:
- **Observed Event Count**: Frequency of reported observations.
- **Alert Count**: Signals exceeding statistical thresholds.
- **Max Composite Score**: Multi-criteria epidemiological risk.

The API **never** equates higher report volume with inherent epidemic severity, preserving the core multi-criteria scoring principles from Phase 9.

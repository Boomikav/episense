import { useEffect, useState } from "react";
import { Sidebar, type NavView } from "./components/layout/Sidebar";
import { Header } from "./components/layout/Header";
import { DashboardView } from "./views/DashboardView";
import { EightDiseaseIntelligenceView } from "./views/EightDiseaseIntelligenceView";
import { NLPWorkbenchView } from "./views/NLPWorkbenchView";
import { EventsSignalsView } from "./views/EventsSignalsView";
import { MapView } from "./views/MapView";
import { DataEvaluationView } from "./views/DataEvaluationView";
import { SourcesSystemHealthView } from "./views/SourcesSystemHealthView";
import { wsService, type ConnectionStatus } from "./services/websocket";
import { api } from "./services/api";

const VIEW_METADATA: Record<NavView, { title: string; subtitle: string }> = {
  overview: {
    title: "Surveillance Intelligence Overview",
    subtitle: "Real-time epidemiological situational awareness & multi-source risk assessment",
  },
  "eight-diseases": {
    title: "Eight Priority Pathogens Surveillance & Modelling Matrix",
    subtitle: "Canonical registry, continuous spatiotemporal panel, and decoupled modeling statuses",
  },
  "events-signals": {
    title: "Event Intelligence & Validated Clusters",
    subtitle: "Canonical event fusion, narrative reviews, and statistical baseline gating",
  },
  map: {
    title: "Geospatial Surveillance Map",
    subtitle: "RFC 7946 GeoJSON layers with grounded coordinates & zero coordinate fabrication",
  },
  "data-evaluation": {
    title: "Historical Data & Empirical Evaluation",
    subtitle: "Baseline sufficiency profiler, count regression models, and gold benchmark validation",
  },
  sources: {
    title: "Sources & System Health Telemetry",
    subtitle: "Public health feed connectors, ingestion polling telemetry, and SQLite WAL persistence",
  },
  workbench: {
    title: "NLP Forensic Workbench & 17-Stage Traces",
    subtitle: "Deep character span offset groundings, entity classifications, and stage-by-stage pipeline telemetry",
  },
  // Legacy aliases
  live: {
    title: "Live Surveillance Intelligence",
    subtitle: "Real-time epidemiological situational awareness & multi-source risk assessment",
  },
  fusion: {
    title: "Event Fusion & Anti-Inflation Inspector",
    subtitle: "Explainable multi-criteria resolution and anti-inflation deduplication",
  },
  alerts: {
    title: "Epidemiological Alert Inventory",
    subtitle: "Prioritized public health risk alerts with multi-criteria scores & safety ceilings",
  },
  events: {
    title: "Canonical Fused Events",
    subtitle: "Cross-document fused incidents with anti-inflation case aggregation",
  },
  signals: {
    title: "Early Warning Signals",
    subtitle: "Statistical aberrations detected via EARS C1/C2/C3 and Farrington methods",
  },
  research: {
    title: "Research & Empirical Validation",
    subtitle: "Exact span F1 evaluation against gold annotations (v1) and documented failure modes",
  },
  submit: {
    title: "Ingest Public Health Report",
    subtitle: "Analyst document submission directly into ContinuousSurveillancePipeline",
  },
  status: {
    title: "System Health & Architecture",
    subtitle: "Operational health probes, state availability, and pipeline diagnostics",
  },
  forecasting: {
    title: "Epidemiological Forecasting & Baseline Sufficiency",
    subtitle: "Gated count regression, prediction intervals, and empirical data-sufficiency matrix",
  },
};

export function App() {
  const [currentView, setCurrentView] = useState<NavView>("overview");
  const [connectionStatus, setConnectionStatus] = useState<ConnectionStatus>("disconnected");
  const [alertCount, setAlertCount] = useState<number>(0);
  const [refreshKey, setRefreshKey] = useState<number>(0);
  const [isRefreshing, setIsRefreshing] = useState(false);

  useEffect(() => {
    // 1. Connect WebSocket for global live feed
    wsService.connect();

    const unsubStatus = wsService.onStatusChange((status) => {
      setConnectionStatus(status);
    });

    const unsubEvent = wsService.onEvent(() => {
      // Increment or refresh alert count when update arrives
      fetchAlertCount();
    });

    // 2. Fetch initial alert count for badge
    fetchAlertCount();

    return () => {
      unsubStatus();
      unsubEvent();
    };
  }, []);

  const fetchAlertCount = async () => {
    try {
      const resp = await api.getAlerts({ page: 1, page_size: 1, priority_only: true, current_only: true });
      setAlertCount(resp.total);
    } catch {
      // Ignored if API is temporarily initializing
    }
  };

  const handleRefresh = async () => {
    setIsRefreshing(true);
    setRefreshKey((k) => k + 1);
    await fetchAlertCount();
    setTimeout(() => setIsRefreshing(false), 500);
  };

  const { title, subtitle } = VIEW_METADATA[currentView];

  return (
    <div className="app-container">
      {/* 1. Sidebar Navigation */}
      <Sidebar
        currentView={currentView}
        onNavigate={(view) => setCurrentView(view)}
        connectionStatus={connectionStatus}
        alertCount={alertCount}
      />

      {/* 2. Main Content Area */}
      <div className="main-content">
        <Header
          viewTitle={title}
          viewSubtitle={subtitle}
          connectionStatus={connectionStatus}
          onRefresh={handleRefresh}
          isRefreshing={isRefreshing}
        />

        <main className="page-wrapper" key={refreshKey}>
          {currentView === "overview" && <DashboardView onNavigate={setCurrentView} />}
          {currentView === "eight-diseases" && <EightDiseaseIntelligenceView onNavigate={setCurrentView} />}
          {currentView === "events-signals" && <EventsSignalsView initialTab="fusion" />}
          {currentView === "map" && <MapView />}
          {currentView === "data-evaluation" && <DataEvaluationView initialTab="forecasting" />}
          {currentView === "sources" && <SourcesSystemHealthView initialTab="connectors" />}
          {currentView === "workbench" && <NLPWorkbenchView />}

          {/* Legacy navigation aliases */}
          {currentView === "live" && <DashboardView onNavigate={setCurrentView} />}
          {currentView === "fusion" && <EventsSignalsView initialTab="fusion" />}
          {currentView === "events" && <EventsSignalsView initialTab="fusion" />}
          {currentView === "signals" && <EventsSignalsView initialTab="signals" />}
          {currentView === "alerts" && <EventsSignalsView initialTab="alerts" />}
          {currentView === "research" && <DataEvaluationView initialTab="benchmark" />}
          {currentView === "status" && <SourcesSystemHealthView initialTab="health" />}
          {currentView === "forecasting" && <DataEvaluationView initialTab="forecasting" />}
          {currentView === "submit" && <NLPWorkbenchView initialOpenSubmitModal={true} />}
        </main>
      </div>
    </div>
  );
}

export default App;

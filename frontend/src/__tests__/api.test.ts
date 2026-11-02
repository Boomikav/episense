import { describe, it, expect, vi, beforeEach } from "vitest";
import { api } from "../services/api";

describe("EpiSense API Client", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it("fetches service health", async () => {
    const mockHealth = {
      status: "healthy",
      service: "EpiSense Production REST API",
      version: "1.0.0",
      active_alerts: 170,
      timestamp: "2026-09-07T12:00:00Z",
    };

    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => mockHealth,
    } as Response);

    const result = await api.getHealth();
    expect(result.status).toBe("healthy");
    expect(result.active_alerts).toBe(170);
    expect(global.fetch).toHaveBeenCalledWith(expect.stringContaining("/health"), expect.anything());
  });

  it("fetches paginated alerts with query parameters", async () => {
    const mockAlerts = {
      items: [
        {
          alert_id: "alert-123",
          pathogen: "nipah virus",
          location_name: "Kerala",
          alert_tier: "high",
          composite_score: 0.85,
        },
      ],
      total: 1,
      page: 1,
      page_size: 20,
      total_pages: 1,
    };

    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => mockAlerts,
    } as Response);

    const result = await api.getAlerts({ pathogen: "nipah", alert_tier: "high", min_score: 0.7 });
    expect(result.items.length).toBe(1);
    expect(result.items[0].alert_id).toBe("alert-123");
    expect(global.fetch).toHaveBeenCalledWith(
      expect.stringContaining("pathogen=nipah&alert_tier=high&min_score=0.7"),
      expect.anything()
    );
  });

  it("fetches explainability dossier", async () => {
    const mockDossier = {
      alert_id: "alert-123",
      generated_at: "2026-09-07T12:00:00Z",
      briefing_5w1h: {
        who: "Clinical population",
        what: "Nipah encephalitis outbreak",
        where: "Kerala",
        when: "2026-W36",
        why: "Surge above historical baseline",
        how: "Contact and zoonotic transmission",
      },
      why_generated: "Observed cases deviated 4.2 sigma from historical baseline",
      primary_drivers: ["Rapid case acceleration", "High case fatality pathogen"],
      evidence_spans: [],
      contributing_documents: [],
    };

    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => mockDossier,
    } as Response);

    const dossier = await api.getAlertDossier("alert-123");
    expect(dossier.briefing_5w1h.what).toContain("Nipah");
    expect(dossier.primary_drivers.length).toBe(2);
  });

  it("submits document for ingestion", async () => {
    const mockResponse = {
      status: "accepted",
      message: "Document ingested and pipeline processed",
      document_id: "doc-abc",
      fused_events_affected: ["fe-1"],
      signals_generated: ["sig-1"],
      alerts_generated: ["alt-1"],
    };

    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => mockResponse,
    } as Response);

    const payload = {
      title: "Nipah Outbreak in Kozhikode",
      source_id: "who_bulletin",
      source_type: "official_bulletin" as const,
      publication_date: "2026-09-07T00:00:00Z",
      text: "Two confirmed cases of Nipah virus reported.",
    };

    const res = await api.submitDocument(payload);
    expect(res.status).toBe("accepted");
    expect(res.alerts_generated).toContain("alt-1");
  });

  it("throws formatted error on HTTP failure", async () => {
    global.fetch = vi.fn().mockResolvedValue({
      ok: false,
      status: 404,
      statusText: "Not Found",
      json: async () => ({ detail: "Alert not found" }),
      text: async () => JSON.stringify({ detail: "Alert not found" }),
    } as Response);

    await expect(api.getAlertById("non-existent")).rejects.toThrow("Alert not found");
  });
});

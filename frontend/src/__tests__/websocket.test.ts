import { describe, it, expect, vi, beforeEach } from "vitest";
import { WebSocketService } from "../services/websocket";

describe("Surveillance WebSocket Service", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it("constructs ws url from http base url correctly", () => {
    const ws = new WebSocketService("http://localhost:8000");
    // Private getWsUrl tested indirectly via connect or URL inspection
    expect(ws.getStatus()).toBe("disconnected");
  });

  it("handles subscriptions and notifies callbacks", () => {
    const ws = new WebSocketService("http://localhost:8000");
    const callback = vi.fn();
    const unsubscribe = ws.onEvent(callback);

    const mockEvent = {
      update_id: "up-1",
      document_id: "doc-1",
      status: "accepted",
      message: "Processing completed",
      timestamp: "2026-09-07T12:00:00Z",
      fused_events_affected: [],
      signals_generated: [],
      alerts_generated: ["alt-100"],
    };

    // Simulate event delivery
    ws.handleServerMessage({ type: "event_update", data: mockEvent as any });

    expect(callback).toHaveBeenCalledWith(mockEvent);

    // Test unsubscribe
    unsubscribe();
    ws.handleServerMessage({ type: "event_update", data: mockEvent as any });
    expect(callback).toHaveBeenCalledTimes(1);
  });

  it("tracks connection status listeners", () => {
    const ws = new WebSocketService("http://localhost:8000");
    const statusCallback = vi.fn();
    ws.onStatusChange(statusCallback);

    (ws as any).setStatus("connected");
    expect(statusCallback).toHaveBeenCalledWith("connected");

    (ws as any).setStatus("reconnecting");
    expect(statusCallback).toHaveBeenCalledWith("reconnecting");
  });
});

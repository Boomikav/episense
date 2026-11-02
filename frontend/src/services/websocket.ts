/**
 * EpiSense Native WebSocket Streaming Feed Service (Phase 12).
 * Handles real-time push updates, connection lifecycle, auto-reconnect,
 * heartbeat pings, and topic subscription filtering.
 */

import type {
  SurveillanceEventUpdate,
  WSClientMessage,
  WSServerMessage,
  WSSubscriptionFilter,
} from "../types/api";

export type ConnectionStatus =
  | "connected"
  | "connecting"
  | "reconnecting"
  | "disconnected";

export type EventUpdateCallback = (update: SurveillanceEventUpdate) => void;
export type StatusCallback = (status: ConnectionStatus) => void;

export class SurveillanceWebSocketService {
  private ws: WebSocket | null = null;
  private status: ConnectionStatus = "disconnected";
  private currentFilter: WSSubscriptionFilter = {};
  private eventListeners: Set<EventUpdateCallback> = new Set();
  private statusListeners: Set<StatusCallback> = new Set();
  private reconnectAttempts = 0;
  private maxReconnectDelay = 10000;
  private reconnectTimeoutId: any = null;
  private pingIntervalId: any = null;
  private explicitDisconnect = false;
  private customApiUrl?: string;

  constructor(customApiUrl?: string) {
    this.customApiUrl = customApiUrl;
  }

  public getStatus(): ConnectionStatus {
    return this.status;
  }

  private getWebSocketUrl(): string {
    const apiBase =
      this.customApiUrl ||
      import.meta.env.VITE_API_BASE_URL ||
      "http://localhost:8008";
    const wsBase = apiBase
      .replace(/^https:\/\//i, "wss://")
      .replace(/^http:\/\//i, "ws://");
    return `${wsBase}/api/v1/ws/surveillance`;
  }

  public connect(): void {
    if (this.ws && (this.ws.readyState === WebSocket.OPEN || this.ws.readyState === WebSocket.CONNECTING)) {
      return;
    }

    this.explicitDisconnect = false;
    this.setStatus(this.reconnectAttempts > 0 ? "reconnecting" : "connecting");

    try {
      const url = this.getWebSocketUrl();
      this.ws = new WebSocket(url);

      this.ws.onopen = () => {
        this.reconnectAttempts = 0;
        this.setStatus("connected");
        this.startHeartbeat();

        // Re-apply existing filter if any
        if (Object.keys(this.currentFilter).length > 0) {
          this.sendSubscribe(this.currentFilter);
        }
      };

      this.ws.onmessage = (event) => {
        try {
          const msg: WSServerMessage = JSON.parse(event.data);
          this.handleServerMessage(msg);
        } catch (err) {
          console.error("[WebSocket] Failed to parse message:", err, event.data);
        }
      };

      this.ws.onclose = () => {
        this.stopHeartbeat();
        this.setStatus("disconnected");
        if (!this.explicitDisconnect) {
          this.scheduleReconnect();
        }
      };

      this.ws.onerror = (err) => {
        console.warn("[WebSocket] Connection error:", err);
      };
    } catch (err) {
      console.error("[WebSocket] Failed to establish connection:", err);
      this.setStatus("disconnected");
      this.scheduleReconnect();
    }
  }

  public disconnect(): void {
    this.explicitDisconnect = true;
    this.stopHeartbeat();
    if (this.reconnectTimeoutId) {
      clearTimeout(this.reconnectTimeoutId);
      this.reconnectTimeoutId = null;
    }
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
    this.setStatus("disconnected");
  }

  public setSubscriptionFilter(filter: WSSubscriptionFilter): void {
    this.currentFilter = { ...filter };
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.sendSubscribe(this.currentFilter);
    }
  }

  public clearSubscriptionFilter(): void {
    this.currentFilter = {};
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.sendSubscribe({});
    }
  }

  public onEvent(callback: EventUpdateCallback): () => void {
    this.eventListeners.add(callback);
    return () => this.eventListeners.delete(callback);
  }

  public onStatusChange(callback: StatusCallback): () => void {
    this.statusListeners.add(callback);
    callback(this.status);
    return () => this.statusListeners.delete(callback);
  }

  private sendSubscribe(filter: WSSubscriptionFilter): void {
    const payload: WSClientMessage = {
      action: "subscribe",
      filter,
    };
    this.send(payload);
  }

  private send(msg: WSClientMessage): void {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(msg));
    }
  }

  public handleServerMessage(msg: WSServerMessage): void {
    switch (msg.type) {
      case "connection_ack":
        // Connection confirmed
        break;
      case "subscription_ack":
        // Subscription acknowledged
        break;
      case "event_update":
        if (msg.data) {
          this.eventListeners.forEach((cb) => cb(msg.data!));
        }
        break;
      case "pong":
        // Heartbeat confirmed
        break;
      case "error":
        console.warn("[WebSocket Server Error]", msg.message);
        break;
    }
  }

  private startHeartbeat(): void {
    this.stopHeartbeat();
    this.pingIntervalId = setInterval(() => {
      if (this.ws && this.ws.readyState === WebSocket.OPEN) {
        this.send({ action: "ping" });
      }
    }, 25000);
  }

  private stopHeartbeat(): void {
    if (this.pingIntervalId) {
      clearInterval(this.pingIntervalId);
      this.pingIntervalId = null;
    }
  }

  public setStatus(newStatus: ConnectionStatus): void {
    this.status = newStatus;
    this.statusListeners.forEach((cb) => cb(newStatus));
  }

  private scheduleReconnect(): void {
    if (this.explicitDisconnect) return;
    this.reconnectAttempts++;
    const delay = Math.min(1000 * Math.pow(1.5, this.reconnectAttempts), this.maxReconnectDelay);
    this.setStatus("reconnecting");
    this.reconnectTimeoutId = setTimeout(() => {
      this.connect();
    }, delay);
  }
}

export const wsService = new SurveillanceWebSocketService();
export { SurveillanceWebSocketService as WebSocketService };

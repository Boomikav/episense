"""
Unit Tests for EpiSense Real-Time WebSocket Surveillance Feed (Phase 12).
Verifies connection management, acknowledgments, subscription filtering, ping/pong, and broadcast on ingestion.
"""

import json
from uuid import uuid4
import pytest
from fastapi.testclient import TestClient

from episense.schemas.alert import AlertTier
from episense.schemas.streaming import IngestionStatus, SurveillanceEventUpdate
from episense.streaming.state import SurveillanceStateStore
from episense.api.app import create_app
from episense.api.websocket import SurveillanceEventPublisher
from tests.unit.test_geo_api import make_alert


class TestWebSocket:

    def test_websocket_connection_ack(self):
        publisher = SurveillanceEventPublisher()
        app = create_app(publisher=publisher)
        client = TestClient(app)

        with client.websocket_connect("/api/v1/ws/surveillance") as ws:
            ack = ws.receive_json()
            assert ack["type"] == "connection_ack"
            assert ack["status"] == "connected"
            assert "client_id" in ack
            assert len(publisher.active_sessions) == 1

        # After exiting with block, client should be disconnected
        assert len(publisher.active_sessions) == 0

    def test_websocket_ping_pong(self):
        app = create_app()
        client = TestClient(app)

        with client.websocket_connect("/api/v1/ws/surveillance") as ws:
            _ = ws.receive_json()  # connection ack
            ws.send_json({"action": "ping"})
            resp = ws.receive_json()
            assert resp["type"] == "pong"

    def test_websocket_subscription_ack(self):
        app = create_app()
        client = TestClient(app)

        with client.websocket_connect("/api/v1/ws/surveillance") as ws:
            _ = ws.receive_json()  # ack
            ws.send_json({
                "action": "subscribe",
                "filter": {
                    "pathogen": "nipah",
                    "min_score": 0.5,
                    "alert_tier": "medium",
                }
            })
            resp = ws.receive_json()
            assert resp["type"] == "subscription_ack"
            assert resp["status"] == "subscribed"

    def test_websocket_malformed_message_handling(self):
        app = create_app()
        client = TestClient(app)

        with client.websocket_connect("/api/v1/ws/surveillance") as ws:
            _ = ws.receive_json()  # ack
            ws.send_text("THIS IS NOT VALID JSON")
            err_resp = ws.receive_json()
            assert err_resp["type"] == "error"

            ws.send_json({"action": "unsupported_unknown_action"})
            err_resp2 = ws.receive_json()
            assert err_resp2["type"] == "error"

    def test_websocket_filtered_broadcast(self):
        state = SurveillanceStateStore()
        alert_nipah = make_alert("nipah", "kozhikode", 0.85, AlertTier.HIGH)
        alert_cholera = make_alert("cholera", "puri", 0.50, AlertTier.LOW)
        state.alerts[alert_nipah.alert_id] = alert_nipah
        state.alerts[alert_cholera.alert_id] = alert_cholera

        publisher = SurveillanceEventPublisher()
        app = create_app(state=state, publisher=publisher)
        client = TestClient(app)

        with client.websocket_connect("/api/v1/ws/surveillance") as ws_nipah:
            _ = ws_nipah.receive_json()  # ack
            # Subscribe specifically to nipah
            ws_nipah.send_json({
                "action": "subscribe",
                "filter": {"pathogen": "nipah"}
            })
            _ = ws_nipah.receive_json()  # sub ack

            # Broadcast update for Cholera
            update_cholera = SurveillanceEventUpdate(
                status=IngestionStatus.ACCEPTED,
                alerts_generated=[alert_cholera.alert_id],
            )
            import asyncio
            asyncio.run(publisher.broadcast(update_cholera, alerts_lookup=state.alerts))

            # Broadcast update for Nipah
            update_nipah = SurveillanceEventUpdate(
                status=IngestionStatus.ACCEPTED,
                alerts_generated=[alert_nipah.alert_id],
                message="Nipah outbreak detected",
            )
            asyncio.run(publisher.broadcast(update_nipah, alerts_lookup=state.alerts))

            # ws_nipah should receive only the Nipah update!
            msg = ws_nipah.receive_json()
            assert msg["type"] == "event_update"
            assert msg["data"]["message"] == "Nipah outbreak detected"

    def test_websocket_document_ingestion_end_to_end(self):
        import uuid
        state = SurveillanceStateStore()
        publisher = SurveillanceEventPublisher()
        app = create_app(state=state, publisher=publisher)
        client = TestClient(app)

        with client.websocket_connect("/api/v1/ws/surveillance") as ws:
            _ = ws.receive_json()  # connection ack

            # Submit document via REST POST with unique token to avoid cross-test deduplication collision
            doc_payload = {
                "title": f"Health Alert: Confirmed Dengue in Kozhikode {uuid.uuid4().hex[:8]}",
                "text": f"Two confirmed Dengue cases were reported in Kozhikode on 25 July 2024. RunID: {uuid.uuid4()}",
                "source_id": "test_src",
            }
            res = client.post("/api/v1/documents", json=doc_payload)
            assert res.status_code == 200

            # WebSocket client should receive the broadcast event update!
            broadcast_frame = ws.receive_json()
            assert broadcast_frame["type"] == "event_update"
            assert broadcast_frame["data"]["status"] == "accepted"
            assert len(broadcast_frame["data"]["fused_events_affected"]) >= 1

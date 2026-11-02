"""
Surveillance Event Publisher and WebSocket Real-Time Feed for EpiSense (Phase 12).
Provides an in-process, non-blocking broadcast manager with client subscription filtering.
"""

import asyncio
import json
from typing import Any, Dict, Optional, Set
from uuid import UUID, uuid4

from fastapi import WebSocket, WebSocketDisconnect

from episense.schemas.alert import AlertTier, EpidemiologicalAlert
from episense.schemas.streaming import SurveillanceEventUpdate
from episense.api.models import (
    WSClientMessage,
    WSServerMessage,
    WSSubscriptionFilter,
)
from episense.logging import get_logger

logger = get_logger("api.websocket")


class WebSocketClientSession:
    """Represents an active WebSocket client session and its subscription criteria."""

    def __init__(self, client_id: str, websocket: WebSocket):
        self.client_id = client_id
        self.websocket = websocket
        self.filter: Optional[WSSubscriptionFilter] = None
        self.connected_at = asyncio.get_event_loop().time()

    async def send_message(self, message: WSServerMessage):
        """Sends a JSON-serialized server message to the client."""
        payload = message.model_dump(mode="json")
        await self.websocket.send_json(payload)

    def matches(self, update: SurveillanceEventUpdate, alerts_lookup: Optional[Dict[UUID, EpidemiologicalAlert]] = None) -> bool:
        """Evaluates whether an outgoing SurveillanceEventUpdate matches client filter criteria."""
        if not self.filter:
            return True

        # If filtering by pathogen, tier, or min_score, evaluate against affected alerts
        f = self.filter
        if alerts_lookup and update.alerts_generated:
            matching_alert = False
            for aid in update.alerts_generated:
                alert = alerts_lookup.get(aid)
                if not alert:
                    continue

                if f.pathogen and f.pathogen.lower() not in alert.disease_key.lower():
                    continue
                if f.alert_tier and alert.alert_tier != f.alert_tier:
                    continue
                if f.min_score is not None and alert.composite_score < f.min_score:
                    continue
                if f.region and f.region.lower() not in alert.geo_key.lower():
                    continue

                matching_alert = True
                break

            if matching_alert:
                return True

            # If the filter specifies alert properties and no alert matched, suppress update
            if f.pathogen or f.alert_tier or f.min_score is not None or f.region:
                return False

        return True


class SurveillanceEventPublisher:
    """
    In-process surveillance event broker broadcasting real-time pipeline events
    to connected WebSocket clients with subscriber-side filtering.
    """

    def __init__(self):
        self.active_sessions: Dict[str, WebSocketClientSession] = {}
        self._lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket) -> str:
        """Accepts a new WebSocket connection and returns a unique client identifier."""
        await websocket.accept()
        client_id = f"ws_client_{uuid4().hex[:12]}"
        session = WebSocketClientSession(client_id, websocket)

        async with self._lock:
            self.active_sessions[client_id] = session

        logger.info("WebSocket client connected: %s (Total: %d)", client_id, len(self.active_sessions))

        # Send connection acknowledgment frame
        ack = WSServerMessage(
            type="connection_ack",
            client_id=client_id,
            status="connected",
        )
        await session.send_message(ack)
        return client_id

    async def disconnect(self, client_id: str):
        """Removes a client session on disconnect."""
        async with self._lock:
            if client_id in self.active_sessions:
                del self.active_sessions[client_id]
                logger.info("WebSocket client disconnected: %s (Total: %d)", client_id, len(self.active_sessions))

    def update_subscription(self, client_id: str, sub_filter: Optional[WSSubscriptionFilter]):
        """Updates subscription filter for a specific client session."""
        session = self.active_sessions.get(client_id)
        if session:
            session.filter = sub_filter
            logger.debug("Updated subscription filter for client %s: %s", client_id, sub_filter)

    async def broadcast(
        self,
        update: SurveillanceEventUpdate,
        alerts_lookup: Optional[Dict[UUID, EpidemiologicalAlert]] = None,
    ):
        """
        Broadcasts an emitted SurveillanceEventUpdate to all matching subscribers.
        Dead or failed connections are safely pruned.
        """
        if not self.active_sessions:
            return

        message = WSServerMessage(
            type="event_update",
            data=update.model_dump(mode="json"),
        )

        dead_clients: Set[str] = set()

        async with self._lock:
            sessions = list(self.active_sessions.values())

        for session in sessions:
            try:
                if session.matches(update, alerts_lookup=alerts_lookup):
                    await session.send_message(message)
            except Exception as e:
                logger.warning("Error dispatching event to client %s: %s", session.client_id, e)
                dead_clients.add(session.client_id)

        if dead_clients:
            async with self._lock:
                for cid in dead_clients:
                    self.active_sessions.pop(cid, None)

    def broadcast_sync(self, payload: Dict[str, Any]):
        """
        Synchronously schedules a broadcast message to all connected WebSocket clients.
        Safe to call from background worker threads or synchronous request handlers.
        """
        if not self.active_sessions:
            return

        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                asyncio.run_coroutine_threadsafe(self._dispatch_raw_json(payload), loop)
            else:
                loop.run_until_complete(self._dispatch_raw_json(payload))
        except RuntimeError:
            pass
        except Exception as e:
            logger.debug("Failed to dispatch sync broadcast: %s", e)

    async def _dispatch_raw_json(self, payload: Dict[str, Any]):
        """Dispatches raw JSON payload to connected clients."""
        if not self.active_sessions:
            return
        dead_clients: Set[str] = set()
        async with self._lock:
            sessions = list(self.active_sessions.values())
        for session in sessions:
            try:
                await session.websocket.send_json(payload)
            except Exception as e:
                dead_clients.add(session.client_id)
        if dead_clients:
            async with self._lock:
                for cid in dead_clients:
                    self.active_sessions.pop(cid, None)

    async def handle_client_loop(self, client_id: str):
        """Handles inbound frames from client (subscription requests, pings)."""
        session = self.active_sessions.get(client_id)
        if not session:
            return

        ws = session.websocket
        try:
            while True:
                data = await ws.receive_text()
                try:
                    raw_dict = json.loads(data)
                    msg = WSClientMessage.model_validate(raw_dict)
                    if msg.action == "subscribe":
                        self.update_subscription(client_id, msg.filter)
                        await session.send_message(
                            WSServerMessage(
                                type="subscription_ack",
                                client_id=client_id,
                                status="subscribed",
                                data=msg.filter.model_dump() if msg.filter else {},
                            )
                        )
                    elif msg.action == "unsubscribe":
                        self.update_subscription(client_id, None)
                        await session.send_message(
                            WSServerMessage(
                                type="subscription_ack",
                                client_id=client_id,
                                status="unsubscribed",
                            )
                        )
                    elif msg.action == "ping":
                        await session.send_message(
                            WSServerMessage(type="pong", client_id=client_id)
                        )
                    else:
                        await session.send_message(
                            WSServerMessage(
                                type="error",
                                client_id=client_id,
                                error=f"Unknown action: '{msg.action}'",
                            )
                        )
                except Exception as e:
                    await session.send_message(
                        WSServerMessage(
                            type="error",
                            client_id=client_id,
                            error=f"Malformed message payload: {e}",
                        )
                    )
        except WebSocketDisconnect:
            pass
        finally:
            await self.disconnect(client_id)

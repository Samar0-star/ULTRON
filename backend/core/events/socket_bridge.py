"""
Beast Socket Bridge - Bridging Internal Events to the Real-Time UI.
"""
import asyncio
import logging
from typing import Dict, Any, Optional
from backend.core.events.event_bus import events, BeastEvent

try:
    from backend.collaboration.websocket_manager import get_websocket_manager
except ImportError:
    class DummyWebSocketManager:
        async def broadcast_to_session(self, session_id: str, message: dict):
            pass
    def get_websocket_manager():
        return DummyWebSocketManager()

logger = logging.getLogger("backend.core.events.bridge")

class BeastSocketBridge:
    """
    Listens to internal BeastEventBus events and forwards them 
    to relevant WebSocket sessions.
    """
    _instance: Optional['BeastSocketBridge'] = None

    def __init__(self):
        self._running = False
        self._task: Optional[asyncio.Task] = None
        self.ws_manager = get_websocket_manager()

    @classmethod
    def get_instance(cls) -> 'BeastSocketBridge':
        if cls._instance is None:
            cls._instance = BeastSocketBridge()
        return cls._instance

    async def start(self):
        """Start listening to events"""
        if self._running:
            return
        
        self._running = True
        # Subscribe to all events
        await events.subscribe("*", self._handle_event)
        logger.info("BeastSocketBridge started and subscribed to all events (*)")

    async def stop(self):
        """Stop listening to events"""
        self._running = False
        await events.unsubscribe("*", self._handle_event)
        logger.info("BeastSocketBridge stopping...")

    async def _handle_event(self, event: BeastEvent):
        """
        Handle an internal event and decide if it should be broadcast to UI.
        """
        if not self._running:
            return

        # Extract session_id from payload if available
        session_id = event.payload.get("session_id")
        
        # Prepare the message for the frontend
        socket_message = {
            "type": "beast_event",
            "event_type": event.type,
            "source": event.source,
            "timestamp": event.timestamp.isoformat(),
            "payload": event.payload
        }

        # If a research session ID is present, we target that specific collaboration session
        # In Avon-1, research session IDs usually match or are linked to collaboration sessions
        if session_id:
            # We broadcast to the session if it exists in the WS manager
            # Note: The WS manager might use different session IDs for visualization collaboration,
            # but for research, we'll try to use the research session id as the primary channel.
            try:
                await self.ws_manager.broadcast_to_session(session_id, socket_message)
            except Exception as e:
                logger.debug(f"Could not broadcast to research session {session_id}: {e}")
                
        # Also broadcast to a global "system_monitor" if configured, or just rely on session-based
        # For now, we only push to active sessions that match the research session id.

# Global bridge instance
bridge = BeastSocketBridge.get_instance()

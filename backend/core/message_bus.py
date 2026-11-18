"""
Multi-Agent Message Bus
========================

Central communication backbone for Beast-level agent orchestration.
Allows agents, adapters, and tools to:
- Broadcast results and partial outputs
- Subscribe to events from other components
- Request assistance from peers
- Share knowledge and avoid duplicate work
"""

import asyncio
import logging
import os
import time
import uuid
from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set

logger = logging.getLogger(__name__)


class MessageType(Enum):
    """Types of messages that can flow through the bus"""
    # Agent lifecycle
    AGENT_STARTED = "agent_started"
    AGENT_COMPLETED = "agent_completed"
    AGENT_FAILED = "agent_failed"

    # Task coordination
    TASK_CREATED = "task_created"
    TASK_CLAIMED = "task_claimed"
    TASK_DELEGATED = "task_delegated"
    TASK_COMPLETED = "task_completed"

    # Results sharing
    PARTIAL_RESULT = "partial_result"
    FINAL_RESULT = "final_result"
    KNOWLEDGE_UPDATE = "knowledge_update"

    # Tool/LLM usage
    TOOL_CALLED = "tool_called"
    TOOL_RESULT = "tool_result"
    LLM_CALLED = "llm_called"
    LLM_RESULT = "llm_result"

    # Inter-agent communication
    REQUEST_HELP = "request_help"
    OFFER_HELP = "offer_help"
    NEGOTIATE = "negotiate"

    # System events
    FALLBACK_TRIGGERED = "fallback_triggered"
    ERROR = "error"
    TRACE = "trace"


@dataclass
class Message:
    """A message on the bus"""
    msg_type: MessageType
    sender: str
    payload: Dict[str, Any]
    msg_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    timestamp: float = field(default_factory=time.time)
    target: Optional[str] = None  # Specific recipient, or None for broadcast
    correlation_id: Optional[str] = None  # Link related messages
    priority: int = 5  # 1=highest, 10=lowest

    def to_dict(self) -> Dict[str, Any]:
        """Serialize message"""
        return {
            "msg_id": self.msg_id,
            "msg_type": self.msg_type.value,
            "sender": self.sender,
            "target": self.target,
            "payload": self.payload,
            "timestamp": self.timestamp,
            "correlation_id": self.correlation_id,
            "priority": self.priority
        }


class MessageBus:
    """
    Central event bus for multi-agent orchestration.

    Features:
    - Pub/sub pattern for loose coupling
    - Direct messaging for targeted communication
    - Priority queuing for critical messages
    - Message history for debugging
    - Async handlers for non-blocking operation
    """

    def __init__(self, max_history: int = 1000):
        self.max_history = max_history

        # Subscriptions: message_type -> set of (subscriber_id, handler)
        self._subscriptions: Dict[MessageType, Set[tuple]] = defaultdict(set)

        # Direct subscribers: subscriber_id -> handler
        self._direct_subscribers: Dict[str, Callable] = {}

        # Message history for debugging/replay
        self._history: List[Message] = []

        # Active agents/components on the bus
        self._active_components: Set[str] = set()

        # Statistics
        self._stats = {
            "messages_sent": 0,
            "messages_delivered": 0,
            "errors": 0
        }
        
        # =====================================================================
        # PERSISTENCE: LOCAL MEMORY ONLY (Godzilla Stability Lock)
        # =====================================================================
        logger.info(" MessageBus: Local Memory Backend INITIALIZED (Single Compute Node).")
        logger.info(" MessageBus initialized")

    async def _start_redis_listener(self):
        """DEPRECATED - Redis listener disabled in headless mode."""
        return

    def register_component(self, component_id: str):
        """Register a component as active on the bus"""
        self._active_components.add(component_id)
        logger.debug(f" Component registered: {component_id}")

    def unregister_component(self, component_id: str):
        """Remove a component from the bus"""
        self._active_components.discard(component_id)

        # Remove all subscriptions for this component
        for msg_type in list(self._subscriptions.keys()):
            self._subscriptions[msg_type] = {
                (sub_id, handler) for sub_id, handler in self._subscriptions[msg_type]
                if sub_id != component_id
            }

        # Remove direct subscription
        self._direct_subscribers.pop(component_id, None)

        logger.debug(f" Component unregistered: {component_id}")

    def subscribe(
        self,
        subscriber_id: str,
        msg_type: MessageType,
        handler: Callable[[Message], Any]
    ):
        """Subscribe to a message type"""
        self._subscriptions[msg_type].add((subscriber_id, handler))
        logger.debug(f" {subscriber_id} subscribed to {msg_type.value}")

    def subscribe_direct(
        self,
        subscriber_id: str,
        handler: Callable[[Message], Any]
    ):
        """Subscribe to direct messages addressed to this component"""
        self._direct_subscribers[subscriber_id] = handler
        logger.debug(f" {subscriber_id} subscribed to direct messages")

    def unsubscribe(self, subscriber_id: str, msg_type: MessageType):
        """Unsubscribe from a message type"""
        self._subscriptions[msg_type] = {
            (sub_id, handler) for sub_id, handler in self._subscriptions[msg_type]
            if sub_id != subscriber_id
        }
        logger.debug(f" {subscriber_id} unsubscribed from {msg_type.value}")

    async def publish(
        self,
        msg_type: MessageType,
        sender: str,
        payload: Dict[str, Any],
        target: Optional[str] = None,
        correlation_id: Optional[str] = None,
        priority: int = 5
    ) -> Message:
        """
        Publish a message to the bus.
        """
        msg = Message(
            msg_type=msg_type,
            sender=sender,
            payload=payload,
            target=target,
            correlation_id=correlation_id,
            priority=priority
        )
        
        try:
            from backend.logging.atomic_logger import AtomicLogger
            if AtomicLogger.is_active():
                AtomicLogger.log("bus", msg_type.value.upper(), {
                    "Sender": sender,
                    "Target": target or "BROADCAST",
                    "CorrID": correlation_id,
                    "Payload": payload
                })
        except ImportError:
            pass

        # Add to history (FIXed MEMORY LEAK)
        self._history.append(msg)
        if len(self._history) > self.max_history:
            # Efficiently trim list
            self._history = self._history[-self.max_history:]

        self._stats["messages_sent"] += 1
        
        # Deliver message locally
        await self._deliver(msg)

        return msg

    async def _deliver(self, msg: Message):
        """Deliver message to subscribers"""
        delivered_count = 0

        # Direct message
        if msg.target:
            handler = self._direct_subscribers.get(msg.target)
            if handler:
                try:
                    if asyncio.iscoroutinefunction(handler):
                        await handler(msg)
                    else:
                        handler(msg)
                    delivered_count += 1
                except Exception as e:
                    logger.error(f" Error delivering to {msg.target}: {e}")
                    self._stats["errors"] += 1
            else:
                logger.warning(f" No direct subscriber for target: {msg.target}")

        # Broadcast to all subscribers of this message type
        else:
            subscribers = self._subscriptions.get(msg.msg_type, set())

            # Execute handlers in parallel
            tasks = []
            for sub_id, handler in subscribers:
                tasks.append(self._safe_call(handler, msg, sub_id))

            if tasks:
                results = await asyncio.gather(*tasks, return_exceptions=True)
                delivered_count = sum(1 for r in results if r is not False)

        self._stats["messages_delivered"] += delivered_count

        if delivered_count > 0:
            logger.debug(
                f" Message {msg.msg_id} ({msg.msg_type.value}) "
                f"from {msg.sender} delivered to {delivered_count} subscriber(s)"
            )

    async def _safe_call(
        self,
        handler: Callable,
        msg: Message,
        subscriber_id: str
    ) -> bool:
        """Safely call a handler, catching exceptions"""
        try:
            if asyncio.iscoroutinefunction(handler):
                await handler(msg)
            else:
                handler(msg)
            return True
        except Exception as e:
            logger.error(
                f" Error in handler for {subscriber_id} "
                f"on message {msg.msg_id}: {e}"
            )
            self._stats["errors"] += 1
            return False

    def get_history(
        self,
        msg_type: Optional[MessageType] = None,
        sender: Optional[str] = None,
        correlation_id: Optional[str] = None,
        limit: int = 100
    ) -> List[Message]:
        """
        Query message history.

        Args:
            msg_type: Filter by message type
            sender: Filter by sender
            correlation_id: Filter by correlation ID
            limit: Maximum messages to return

        Returns:
            List of matching messages (most recent first)
        """
        filtered = self._history

        if msg_type:
            filtered = [m for m in filtered if m.msg_type == msg_type]

        if sender:
            filtered = [m for m in filtered if m.sender == sender]

        if correlation_id:
            filtered = [m for m in filtered if m.correlation_id == correlation_id]

        return list(reversed(filtered[-limit:]))

    def get_stats(self) -> Dict[str, Any]:
        """Get bus statistics"""
        return {
            **self._stats,
            "active_components": len(self._active_components),
            "subscriptions": sum(len(subs) for subs in self._subscriptions.values()),
            "direct_subscribers": len(self._direct_subscribers),
            "history_size": len(self._history)
        }

    def clear_history(self):
        """Clear message history"""
        self._history.clear()
        logger.info(" Message history cleared")

    def get_active_components(self) -> Set[str]:
        """Get list of active components"""
        return self._active_components.copy()

    async def request_and_wait(
        self,
        msg_type: MessageType,
        sender: str,
        payload: Dict[str, Any],
        timeout: float = 30.0,
        expected_responses: int = 1
    ) -> List[Message]:
        """
        Publish a message and wait for responses.

        Args:
            msg_type: Type of request
            sender: Sender ID
            payload: Request payload
            timeout: How long to wait for responses
            expected_responses: How many responses to expect

        Returns:
            List of response messages
        """
        correlation_id = str(uuid.uuid4())[:8]

        # Track responses
        responses = []
        response_event = asyncio.Event()

        # Subscribe to responses
        def response_handler(msg: Message):
            if msg.correlation_id == correlation_id:
                responses.append(msg)
                if len(responses) >= expected_responses:
                    response_event.set()

        # Subscribe to relevant response types
        response_types = [
            MessageType.OFFER_HELP,
            MessageType.FINAL_RESULT,
            MessageType.TASK_COMPLETED
        ]

        temp_id = f"temp_{correlation_id}"
        for resp_type in response_types:
            self.subscribe(temp_id, resp_type, response_handler)

        try:
            # Publish request
            await self.publish(
                msg_type=msg_type,
                sender=sender,
                payload=payload,
                correlation_id=correlation_id
            )

            # Wait for responses
            try:
                await asyncio.wait_for(response_event.wait(), timeout=timeout)
            except asyncio.TimeoutError:
                logger.warning(
                    f" Request {correlation_id} timed out "
                    f"(got {len(responses)}/{expected_responses} responses)"
                )

            return responses

        finally:
            # Clean up subscriptions
            for resp_type in response_types:
                self.unsubscribe(temp_id, resp_type)


# Container for single compute node bus
_bus_instance: Optional[MessageBus] = None

def get_message_bus() -> MessageBus:
    """Get the message bus singleton for the compute container"""
    global _bus_instance
    if _bus_instance is None:
        _bus_instance = MessageBus()
    return _bus_instance

def reset_message_bus():
    """Reset the message bus instance"""
    global _bus_instance
    _bus_instance = None

"""
Beast Event Bus - The Nervous System of Avon-1.
Provides asynchronous Pub/Sub for decoupling agents, tools, and UI.
"""
import asyncio
import logging
from typing import Dict, List, Any, Callable, Optional, Type, Set
from pydantic import BaseModel, Field
from datetime import datetime
import uuid

logger = logging.getLogger("backend.core.events")

class BeastEvent(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = Field(default_factory=datetime.now)
    type: str
    payload: Dict[str, Any]
    source: str

class BeastEventBus:
    """
    Centralized, asynchronous event bus.
    Allows for decoupled communication between system components.
    """
    _instance: Optional['BeastEventBus'] = None

    def __init__(self):
        self._subscribers: Dict[str, List[Callable]] = {}
        self._history: List[BeastEvent] = []
        self._max_history: int = 1000
        self._async_lock = None
        # [GODZILLA V211.0] GHOST TASK PROTECTION
        # Physically track all background callback tasks to prevent memory leaks
        self._pending_tasks: Set[asyncio.Task] = set()

    @property
    def _lock(self) -> asyncio.Lock:
        if self._async_lock is None:
            try:
                self._async_lock = asyncio.Lock()
            except RuntimeError:
                try:
                    loop = asyncio.get_event_loop_policy().get_event_loop()
                except Exception:
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                self._async_lock = asyncio.Lock()
        return self._async_lock

    @_lock.setter
    def _lock(self, val: Any):
        self._async_lock = val

    @classmethod
    def get_instance(cls) -> 'BeastEventBus':
        if cls._instance is None:
            cls._instance = BeastEventBus()
        return cls._instance

    def subscribe(self, event_type: str, callback: Callable):
        """
        Subscribe to a specific event type (supports both sync call and await).
        """
        if not hasattr(self, "_subscribers") or self._subscribers is None:
            self._subscribers = {}
        if not hasattr(self, "_history") or self._history is None:
            self._history = []
        if not hasattr(self, "_max_history"):
            self._max_history = 1000
        if event_type not in self._subscribers:
            self._subscribers[event_type] = []
        if callback not in self._subscribers[event_type]:
            self._subscribers[event_type].append(callback)
        logger.info(f"Subscribed callback to event type: {event_type}")
        class _AwaitableNoOp:
            def __await__(self):
                async def _noop(): return None
                return _noop().__await__()
        return _AwaitableNoOp()

    async def unsubscribe(self, event_type: str, callback: Callable):
        """
        Unsubscribe a callback from an event type.
        """
        async with self._lock:
            if event_type in self._subscribers:
                try:
                    self._subscribers[event_type].remove(callback)
                    logger.info(f"Unsubscribed callback from event type: {event_type}")
                except ValueError:
                    logger.warning(f"Callback not found for event type: {event_type}")

    async def emit(self, event_type: str, payload: Dict[str, Any], source: str):
        """
        Emit an event to all subscribers and persist to the vault.
        """
        event = BeastEvent(type=event_type, payload=payload, source=source)
        
        # Project Godzilla: Thermodynamic Persistence (ASYNC OFF-LOAD)
        try:
            from backend.core.state.persistence_vault import vault
            session_id = payload.get("session_id", "system")
            # [ULTRON BEAST FIX] Prevent Event Loop Strangulation
            loop = asyncio.get_running_loop()
            loop.run_in_executor(None, vault.log_action, session_id, source, event_type, payload)
        except Exception as e:
            logger.error(f"Persistence failure in EventBus: {e}")

        async with self._lock:
            # Store in history
            self._history.append(event)
            max_hist = getattr(self, "_max_history", 1000)
            if len(self._history) > max_hist:
                self._history.pop(0)
            
            # Identify subscribers (copy list to avoid mutating _subscribers[event_type] in-place!)
            callbacks = list(self._subscribers.get(event_type, []))
            for g_cb in self._subscribers.get("*", []):
                if g_cb not in callbacks:
                    callbacks.append(g_cb)

        if not callbacks:
            return

        # Callback execution
        for cb in callbacks:
            try:
                if asyncio.iscoroutinefunction(cb):
                    task = asyncio.create_task(cb(event))
                    self._pending_tasks.add(task)
                    # Self-cleaning callback
                    task.add_done_callback(self._pending_tasks.discard)
                else:
                    # Run sync callbacks in thread pool
                    loop = asyncio.get_running_loop()
                    loop.run_in_executor(None, cb, event)
            except Exception as e:
                logger.error(f"Error scheduling event callback: {e}")

    async def wait_for_all(self, timeout: float = 10.0):
        """Wait for all pending event tasks to complete."""
        if not self._pending_tasks:
            return
        
        logger.info(f" EventBus: Waiting for {len(self._pending_tasks)} pending event tasks...")
        await asyncio.wait(list(self._pending_tasks), timeout=timeout)

    def get_history(self, event_type: Optional[str] = None) -> List[BeastEvent]:
        """
        Get event history, optionally filtered by type.
        """
        if not event_type:
            return self._history
        return [e for e in self._history if e.type == event_type]

# Global access point
events = BeastEventBus.get_instance()

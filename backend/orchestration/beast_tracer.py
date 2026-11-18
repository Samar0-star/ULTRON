"""
Beast Tracer - Comprehensive Execution Logging
================================================

Records every action during Beast execution for debugging and analysis.

Features:
- Trace every agent/tool/LLM call
- Timestamp all actions
- Track provider usage and fallbacks
- Generate post-execution analysis
- Export to JSON for replay/debugging
"""

import json
import logging
import os
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class TraceStep:
    """A single step in the execution trace"""
    step_id: str
    step_type: str  # "decomposition", "subtask", "llm_call", "tool_call", "merge"
    start_time: float
    end_time: Optional[float] = None
    status: str = "running"  # "running", "success", "error"
    agent: Optional[str] = None
    tool: Optional[str] = None
    adapter: Optional[str] = None
    llm_model: Optional[str] = None
    provider: Optional[str] = None
    input_data: Optional[Dict[str, Any]] = None
    output_data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dict"""
        return {
            "step_id": self.step_id,
            "step_type": self.step_type,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "duration_s": self.end_time - self.start_time if self.end_time else None,
            "status": self.status,
            "agent": self.agent,
            "tool": self.tool,
            "adapter": self.adapter,
            "llm_model": self.llm_model,
            "provider": self.provider,
            "input_preview": str(self.input_data)[:200] if self.input_data else None,
            "output_preview": str(self.output_data)[:200] if self.output_data else None,
            "error": self.error,
            "metadata": self.metadata
        }


@dataclass
class ExecutionTrace:
    """Complete execution trace for a Beast workflow"""
    trace_id: str
    mission_id: str  # NEW: Tenant ID
    query: str
    start_time: float
    end_time: Optional[float] = None
    status: str = "running"
    steps: List[TraceStep] = field(default_factory=list)
    context: Dict[str, Any] = field(default_factory=dict)
    statistics: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dict"""
        return {
            "trace_id": self.trace_id,
            "mission_id": self.mission_id,
            "query": self.query,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "duration_s": self.end_time - self.start_time if self.end_time else None,
            "status": self.status,
            "context": self.context,
            "steps": [step.to_dict() for step in self.steps],
            "statistics": self.statistics
        }


class BeastTracer:
    """
    Comprehensive execution tracer for Beast workflows.

    Tracks:
    - Task decomposition
    - Subtask execution
    - Agent/tool/adapter calls
    - LLM calls (model, tokens, duration)
    - Provider fallbacks
    - Result merging
    """

    def __init__(
        self,
        trace_dir: str = "logs/Ultron_traces",
        auto_save: bool = True
    ):
        """
        Args:
            trace_dir: Directory for trace files
            auto_save: Auto-save trace to file on finalize
        """
        self.trace_dir = trace_dir
        self.auto_save = auto_save

        # Create trace directory
        Path(self.trace_dir).mkdir(parents=True, exist_ok=True)

        # Current trace
        self._current_trace: Optional[ExecutionTrace] = None

        # Active steps (for nested tracking)
        self._active_steps: Dict[str, TraceStep] = {}

        logger.info(f" BeastTracer initialized (trace_dir={trace_dir})")

    def start_trace(
        self,
        query: str,
        mission_id: str = "default_user",
        context: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Start a new execution trace.

        Args:
            query: User query
            mission_id: Tenant ID
            context: Optional context

        Returns:
            Trace ID
        """
        trace_id = str(uuid.uuid4())[:8]

        self._current_trace = ExecutionTrace(
            trace_id=trace_id,
            mission_id=mission_id,
            query=query,
            start_time=time.time(),
            context=self._sanitize(context or {})
        )

        logger.info(f" Started trace: {trace_id} for user: {mission_id}")

        return trace_id

    def _sanitize(self, data: Any) -> Any:
        """Sanitize data for JSON serialization"""
        if isinstance(data, dict):
            return {str(k): self._sanitize(v) for k, v in data.items()}
        elif isinstance(data, list):
            return [self._sanitize(v) for v in data]
        elif isinstance(data, (str, int, float, bool, type(None))):
            return data
        elif callable(data):
            return f"<callable: {getattr(data, '__name__', 'unknown')}>"
        elif hasattr(data, 'to_dict') and callable(getattr(data, 'to_dict')):
            try:
                return self._sanitize(data.to_dict())
            except Exception:
                return str(data)
        elif hasattr(data, '__dict__'):
            # Convert simple objects to string representation to avoid circular refs
            return str(data)
        else:
            return str(data)


    def log_decomposition(
        self,
        subtasks: List[Any],
        reasoning: Optional[str] = None,
        duration: Optional[float] = None
    ):
        """Log task decomposition"""

        if not self._current_trace:
            logger.warning("No active trace for decomposition log")
            return

        step = TraceStep(
            step_id=f"decompose_{len(self._current_trace.steps)}",
            step_type="decomposition",
            start_time=time.time() - (duration or 0),
            end_time=time.time(),
            status="success",
            output_data={
                "subtask_count": len(subtasks),
                "subtasks": [
                    {
                        "id": getattr(st, "id", f"subtask_{i}"),
                        "type": getattr(st, "type", "unknown"),
                        "description": str(getattr(st, "description", ""))[:100]
                    }
                    for i, st in enumerate(subtasks)
                ],
                "reasoning": reasoning
            }
        )

        self._current_trace.steps.append(step)

        logger.debug(f" Logged decomposition: {len(subtasks)} subtasks")

    def log_step_start(
        self,
        step_id: str,
        step_type: str,
        agent: Optional[str] = None,
        tool: Optional[str] = None,
        adapter: Optional[str] = None,
        input_data: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Log start of a step.

        Args:
            step_id: Step identifier
            step_type: Type of step
            agent: Agent name (if applicable)
            tool: Tool name (if applicable)
            adapter: Adapter name (if applicable)
            input_data: Input data

        Returns:
            Internal step tracking ID
        """
        if not self._current_trace:
            logger.warning("No active trace for step start")
            return ""

        import uuid
        internal_id = f"{step_id}_{uuid.uuid4().hex[:8]}"

        step = TraceStep(
            step_id=internal_id,
            step_type=step_type,
            start_time=time.time(),
            agent=agent,
            tool=tool,
            adapter=adapter,
            input_data=self._sanitize(input_data)
        )

        self._active_steps[internal_id] = step

        logger.debug(f" Step start: {step_id} ({step_type})")

        return internal_id

    def log_step_complete(
        self,
        internal_id: str,
        status: str = "success",
        output_data: Optional[Dict[str, Any]] = None,
        error: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """Log completion of a step"""

        step = self._active_steps.get(internal_id)

        if not step:
            logger.warning(f"No active step found for ID: {internal_id}")
            return

        step.end_time = time.time()
        step.status = status
        step.output_data = self._sanitize(output_data)
        step.error = error

        if metadata:
            step.metadata.update(self._sanitize(metadata))

        # Move to trace
        if self._current_trace:
            self._current_trace.steps.append(step)

        # Remove from active
        del self._active_steps[internal_id]

        duration = step.end_time - step.start_time

        if status == "success":
            logger.debug(f" Step complete: {step.step_id} ({duration:.2f}s)")
        else:
            logger.debug(f" Step failed: {step.step_id} ({duration:.2f}s) - {error}")

    def log_llm_call(
        self,
        model: str,
        provider: str,
        tokens: Optional[int] = None,
        duration: Optional[float] = None,
        prompt_preview: Optional[str] = None,
        response_preview: Optional[str] = None
    ):
        """Log an LLM call"""

        if not self._current_trace:
            return

        step = TraceStep(
            step_id=f"llm_{len(self._current_trace.steps)}",
            step_type="llm_call",
            start_time=time.time() - (duration or 0),
            end_time=time.time(),
            status="success",
            llm_model=model,
            provider=provider,
            input_data={"prompt_preview": prompt_preview[:200] if prompt_preview else None},
            output_data={"response_preview": response_preview[:200] if response_preview else None},
            metadata=self._sanitize({
                "tokens": tokens,
                "duration_s": duration
            })
        )

        self._current_trace.steps.append(step)

        logger.debug(f" LLM call: {model} via {provider} ({tokens} tokens, {duration:.2f}s)")

    def log_tool_call(
        self,
        tool: str,
        duration: Optional[float] = None,
        status: str = "success",
        error: Optional[str] = None
    ):
        """Log a tool call"""

        if not self._current_trace:
            return

        step = TraceStep(
            step_id=f"tool_{len(self._current_trace.steps)}",
            step_type="tool_call",
            start_time=time.time() - (duration or 0),
            end_time=time.time(),
            status=status,
            tool=tool,
            error=error,
            metadata={"duration_s": duration}
        )

        self._current_trace.steps.append(step)

        if status == "success":
            logger.debug(f" Tool call: {tool} ({duration:.2f}s)")
        else:
            logger.debug(f" Tool call failed: {tool} - {error}")

    def log_fallback(
        self,
        primary_provider: str,
        fallback_provider: str,
        reason: str
    ):
        """Log a fallback event"""

        if not self._current_trace:
            return

        step = TraceStep(
            step_id=f"fallback_{len(self._current_trace.steps)}",
            step_type="fallback",
            start_time=time.time(),
            end_time=time.time(),
            status="success",
            provider=fallback_provider,
            metadata={
                "primary": primary_provider,
                "fallback": fallback_provider,
                "reason": reason
            }
        )

        self._current_trace.steps.append(step)

        logger.debug(f" Fallback: {primary_provider}  {fallback_provider}")

    def log_merge(
        self,
        strategy: str,
        input_count: int,
        conflicts: int,
        duration: Optional[float] = None
    ):
        """Log result merging"""

        if not self._current_trace:
            return

        step = TraceStep(
            step_id=f"merge_{len(self._current_trace.steps)}",
            step_type="merge",
            start_time=time.time() - (duration or 0),
            end_time=time.time(),
            status="success",
            metadata={
                "strategy": strategy,
                "input_count": input_count,
                "conflicts": conflicts,
                "duration_s": duration
            }
        )

        self._current_trace.steps.append(step)

        logger.debug(f" Merge: {input_count} inputs, {conflicts} conflicts ({strategy})")

    def finalize_trace(
        self,
        status: str = "success",
        error: Optional[str] = None,
        result_preview: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Finalize the trace and compute statistics.

        Args:
            status: Final status
            error: Error message (if failed)
            result_preview: Preview of final result

        Returns:
            Complete trace dict
        """
        if not self._current_trace:
            logger.warning("No active trace to finalize")
            return {}

        self._current_trace.end_time = time.time()
        self._current_trace.status = status

        # Compute statistics
        stats = self._compute_statistics()
        self._current_trace.statistics = stats

        # Add result preview
        if result_preview:
            self._current_trace.context["result_preview"] = result_preview[:500]

        if error:
            self._current_trace.context["error"] = error

        trace_dict = self._current_trace.to_dict()

        # Auto-save if enabled
        if self.auto_save:
            self._save_trace(trace_dict)

        logger.info(
            f" Finalized trace {self._current_trace.trace_id}: "
            f"{stats.get('total_steps', 0)} steps, "
            f"{stats.get('total_duration_s', 0):.2f}s"
        )

        # Clear current trace
        self._current_trace = None

        return trace_dict

    def _compute_statistics(self) -> Dict[str, Any]:
        """Compute execution statistics"""

        if not self._current_trace:
            return {}

        steps = self._current_trace.steps

        # Count by type
        step_types = {}
        for step in steps:
            step_types[step.step_type] = step_types.get(step.step_type, 0) + 1

        # Count by agent/tool/adapter
        agents_used = list(set(s.agent for s in steps if s.agent))
        tools_used = list(set(s.tool for s in steps if s.tool))
        adapters_used = list(set(s.adapter for s in steps if s.adapter))

        # LLM stats
        llm_calls = [s for s in steps if s.step_type == "llm_call"]
        providers_used = list(set(s.provider for s in llm_calls if s.provider))

        # Duration stats
        durations = [
            s.end_time - s.start_time
            for s in steps
            if s.end_time
        ]

        # Success/failure counts
        success_count = sum(1 for s in steps if s.status == "success")
        error_count = sum(1 for s in steps if s.status == "error")

        return {
            "total_steps": len(steps),
            "step_types": step_types,
            "agents_used": agents_used,
            "tools_used": tools_used,
            "adapters_used": adapters_used,
            "providers_used": providers_used,
            "llm_calls": len(llm_calls),
            "success_count": success_count,
            "error_count": error_count,
            "total_duration_s": sum(durations) if durations else 0.0,
            "avg_step_duration_s": (sum(durations) / len(durations)) if durations else 0.0,
            "min_step_duration_s": min(durations) if durations else 0.0,
            "max_step_duration_s": max(durations) if durations else 0.0
        }

    def _save_trace(self, trace_dict: Dict[str, Any]):
        """Save trace to file"""

        trace_id = trace_dict.get("trace_id", "unknown")
        filename = f"{trace_id}.json"
        filepath = os.path.join(self.trace_dir, filename)

        try:
            with open(filepath, "w") as f:
                json.dump(trace_dict, f, indent=2)

            logger.info(f" Saved trace to: {filepath}")

        except Exception as e:
            logger.error(f"Failed to save trace: {e}")

    def export_trace(self, trace_id: str, mission_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        Load a previously saved trace with security check.

        Args:
            trace_id: Trace ID to load
            mission_id: Tenant ID for verification

        Returns:
            Trace dict or None if not found or unauthorized
        """
        filename = f"{trace_id}.json"
        filepath = os.path.join(self.trace_dir, filename)

        if not os.path.exists(filepath):
            logger.warning(f"Trace not found: {trace_id}")
            return None

        try:
            with open(filepath, "r") as f:
                trace = json.load(f)
            
            # SECURITY FIX: IDOR Prevention
            if mission_id and trace.get("mission_id") != mission_id:
                logger.warning(f"IDOR DETECTED: User {mission_id} tried to access trace {trace_id} belonging to {trace.get('mission_id')}")
                return None
                
            return trace
        except Exception as e:
            logger.error(f"Failed to load trace {trace_id}: {e}")
            return None

    def list_traces(self, mission_id: Optional[str] = None, limit: int = 50) -> List[Dict[str, Any]]:
        """
        List recent traces for a specific user.

        Args:
            mission_id: Filter by mission ID
            limit: Maximum traces to return

        Returns:
            List of trace summaries
        """
        traces = []

        try:
            files = sorted(
                Path(self.trace_dir).glob("*.json"),
                key=lambda p: p.stat().st_mtime,
                reverse=True
            )

            for filepath in files:
                if len(traces) >= limit:
                    break
                    
                try:
                    with open(filepath, "r") as f:
                        trace = json.load(f)

                    # Filter by mission_id
                    if mission_id and trace.get("mission_id") != mission_id:
                        continue

                    traces.append({
                        "trace_id": trace.get("trace_id"),
                        "mission_id": trace.get("mission_id"),
                        "query": trace.get("query", "")[:100],
                        "start_time": trace.get("start_time"),
                        "duration_s": trace.get("duration_s"),
                        "status": trace.get("status"),
                        "total_steps": trace.get("statistics", {}).get("total_steps", 0)
                    })

                except Exception as e:
                    logger.warning(f"Failed to read trace {filepath.name}: {e}")

        except Exception as e:
            logger.error(f"Failed to list traces: {e}")

        return traces


# Alias for backward compatibility with orchestration/__init__.py
UltronTracer = BeastTracer


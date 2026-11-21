# Exhaustive Audit: SVEL Central Router & Autonomous Scheduling Engine

**Audit Targets:**
- `/Users/samaraldico/SVEL AI Scientist/backend/central_router_beast.py`
- `/Users/samaraldico/SVEL AI Scientist/backend/core/task_decomposer.py`
- `/Users/samaraldico/SVEL AI Scientist/backend/core/scheduler.py`
- `/Users/samaraldico/SVEL AI Scientist/backend/core/planning/` (`plan_creator.py`, `plan_reviewer.py`)
- Related orchestration runtime files: `backend/orchestration/singularity.py`, `backend/orchestration/deep_research_orchestrator.py`, `backend/orchestration/swarm_manager.py`

---

## 1. Central Router Beast (`central_router_beast.py`)
- **Native Fleet Discovery**: Dynamically discovers and registers 11 specialized agents via `importlib.import_module`.
- **3-Tier Routing Cascade**:
  1. Explicit Bypass (`kwargs["agent_name"]`)
  2. SVEL Core Redirect (`research_agent` with deep mode)
  3. Dynamic LLM Component Selection (`TASK_ROUTING_MODEL` JSON prompt)
- **Execution Dispatch**: `ThreadPoolExecutor` with automatic awaitable bridging (`inspect.isawaitable`), supporting both async and sync worker agents.
- **Anti-Amputation JSON Truncation**: Truncates individual internal string nodes rather than amputating the serialized text, preventing JSON syntax corruption.

---

## 2. Task Decomposition & Topological DAG Sort
- **Topological Sort with Parallel Batching**: Resolves task dependencies and clusters ready tasks into parallel execution waves:
  $$\text{ready} = \{t \in \text{remaining} \mid \text{dependencies}(t) \subseteq \text{completed}\}$$
  Detects circular dependencies and halts gracefully without process hanging.
- **Semantic Loop Guard**: Jaccard similarity between query and recently decomposed tasks with a 0.65 threshold to prevent reasoning loops.
- **Sawtooth Exploration Schedule**: Cycles 1-3 high exploration (0.9 -> 0.45); Cycles 4+ damped sine wave oscillating between 0.2 (exploitation) and 0.5 (bursts).
- **Plan Reviewer Gate**: Evaluates plans across Feasibility (30%), Coherence (25%), Coverage (25%), Resources (20%). Circular dependencies trigger critical issue penalties.

---

## 3. The Hydra Protocol: Error Catching & Fractal Recovery
- Triggered in `DeepResearchOrchestrator._execute_cycle()` upon child task failure.
- `singularity.re_decompose()` fractures the failed task into 2-3 simpler recovery sub-tasks targeting the failure mode (e.g. searching alternative data sources or simplifying code).
- Injected dynamically into running session plans (`p.tasks.extend(recovery_tasks)`).
- **Hydra Death Spiral Killer**: Strict recursion depth clamp (`if depth > 3: return []`) prevents runaway exponential sub-task explosion.

---

## 4. Long-Horizon 12-72 Hour Queue & Capacity Scheduling
- **Capacity Scheduling with AIMD**:
  - Configured with explicit RPM/TPM/concurrency quotas across OpenAI, Anthropic, Gemini, Moonshot.
  - Multiplicative Backoff: -30% concurrency upon HTTP 429/errors (`conc = max(1, int(old_conc * 0.7))`).
  - Additive Ramp-Up: +1 concurrency upon successful completion.
- **Swarm Queue RAM Streaming**:
  - Worker pool managing 50-200 concurrent agents (`Agent-001` .. `Agent-N`).
  - Results yielded directly as tasks finish via `asyncio.Queue`, eliminating intermediate memory buffering.
  - 15-minute watchdog timeout with serial rescue for zombie workers.
- **Endurance Controls**:
  - 72-hour hard ceiling with paced progress monitoring.
  - Overmind semantic drift auditing every $N$ cycles.
  - Context compaction every 3 cycles.
  - 96-hour Redis persistence TTL for full session recovery.

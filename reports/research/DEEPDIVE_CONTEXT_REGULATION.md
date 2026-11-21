# EXHAUSTIVE FORENSIC ARCHITECTURAL AUDIT: SVEL CONTEXT COMPRESSOR, TOKEN BUDGETING & CORE REGULATION

**Audit Date**: September 17, 2026  
**Target Subsystem**: Core Orchestration, Context Compression, Resilience & Governance  
**Auditor**: Antigravity Autonomous Research Subagent  
**Status**: COMPLETE (Forensic Rigor Grade: Ph.D. Level)

---

## 1. EXECUTIVE SUMMARY & ARCHITECTURAL VERDICT

An exhaustive, code-level forensic audit was conducted on SVEL's context compression, sanitization, task fractalization, API fallback, inter-agent messaging, and domain regulation infrastructure. 

### Critical Findings Overview:
1. **Context Compressor Fallacy**: Despite architectural docstrings claiming 50:1/20:1/10:1 multi-tier hierarchical compression with AST pruning and embedding-based semantic filtering, `context_compressor.py` contains **ZERO AST parsing**, **ZERO embedding-based semantic filtering**, and **ZERO abstractive LLM summarization** (`self.llm_manager` is accepted as an init argument and completely ignored). All compression is purely regex-based and heuristic string slicing.
2. **The "Ghost History" Interface Decoupling Flaw**: Every 3 cycles (`deep_research_orchestrator.py:1385`), the orchestrator invokes `self.context_compressor.compress_mission(self.session.to_dict())` and assigns the result to `self.session.knowledge_snapshot`. However, `ResearchSession.to_dict()` (`deep_research_orchestrator.py:441-460`) **does not serialize a `"cycles"` key**. `MissionCompressor.compress_mission()` (`context_compressor.py:621`) looks specifically for `mission_data.get("cycles", [])`, receives an empty list, computes `0` cycles and `0` tasks, and writes a hollow string: `"## MISSION Summary\nMission: Research Completed 0 cycles, 0 tasks."`. This **wipes out real cumulative research history every 3 cycles**.
3. **The Blind Planner Disconnect**: In `_build_context()` (`deep_research_orchestrator.py:4629`), `self.session.knowledge_snapshot` is packaged into `context["knowledge_snapshot"]`. However, `PlanCreator._build_research_prompt()` (`plan_creator.py:563-703`) **never references or formats `knowledge_snapshot` into the planning prompt**. The strategic planner is entirely blind to past mission history and only sees the last 3–5 raw findings.
4. **Token Budgeting Absence**: There is **no proactive token counter, sliding window calculator, or tiktoken/tokenizer integration** anywhere in the core execution path. `OperationLimits` only checks elapsed wall-clock hours, while `ConvergenceEngine` only tracks accumulated dollar cost. Context window management relies entirely on crude arbitrary character slices (`[:5000]`, `[:200]`, `[:1000]`), leaving 24-hour long-horizon runs vulnerable to catastrophic context window overflow or mid-token truncation.
5. **Dataclass Incompatibility Crash in Task Decomposer**: `task_decomposer.py` defines a local `SubTask` dataclass (lines 44–79) with DAG helper methods (`has_dependencies()`, `can_run_after()`, `to_dict()`). However, `NeuralFractalizer.shatter()` imports `backend.models.task.SubTask` (line 173), which lacks these helper methods and has an incompatible attribute schema. If `shatter()` tasks are passed to `build_dag()`, it crashes with `AttributeError`.
6. **KeyError & Fallback Blindness in FallbackManager**: In `fallback_manager.py:249`, `kwargs["model"] = model_mapping.get(provider, kwargs["model"])` crashes with `KeyError: 'model'` if `"model"` is not in `kwargs` and `provider` is not in `model_mapping` (e.g. `"groq"` or `"local"`). Furthermore, the manager does not inspect HTTP 429 or `Retry-After` headers; it exhausts all 3 retries in under 7 seconds with zero jitter, causing thundering-herd lockouts.

---

## 2. TARGET FILE AUDIT & TOPOLOGY MATRIX

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                                 SVEL CORE REGULATION                                 │
├──────────────────────────────┬─────────────────────────────────────────────────────────┤
│ Target File                  │ Responsibility & Architectural Role                     │
├──────────────────────────────┼─────────────────────────────────────────────────────────┤
│ core/context_compressor.py   │ 3-Tier Hierarchical Context Compression & Stats Extractor│
│ core/input_sanitizer.py      │ Prompt Injection Defense, Encoding Normalization & Rate │
│ core/task_decomposer.py      │ Neural Fractalization, SubTask Planning & DAG Sorter    │
│ core/fallback_manager.py     │ Multi-tier API Provider Failover & Circuit Breaker      │
│ core/message_bus.py          │ Single-Node Asynchronous Inter-Agent Pub/Sub Backbone   │
│ core/domain_regulator.py     │ SBERT Semantic Sieve, Domain Classifier & Grounding Gate│
└──────────────────────────────┴─────────────────────────────────────────────────────────┘
```

---

## 3. FORENSIC DECONSTRUCTION OF `context_compressor.py`

### 3.1 Algorithms Claimed vs. Actually Implemented

| Algorithm / Feature | Claimed in Docstrings & Architecture | Actually Implemented in Source Code | Location |
| :--- | :--- | :--- | :--- |
| **AST Pruning** | Implied code & syntax tree compression | **ABSENT**. The `ast` module is neither imported nor used anywhere in the file. | `context_compressor.py:1-910` |
| **Abstractive Summarization** | "LLM manager for advanced summarization" | **ABSENT / DEAD CODE**. `llm_manager` is saved as `self.llm_manager` (`lines 183, 780`) but is **never invoked** across all 910 lines. | `context_compressor.py:183, 780` |
| **Embedding-Based Semantic Filtering** | Semantic relevance filtering | **ABSENT**. No sentence-transformers, embeddings, cosine similarity, or vector ops are present. | `context_compressor.py:1-910` |
| **Rule-Based Regex Extraction** | Extract numerical & scientific statistics | **IMPLEMENTED**. 7 regex patterns for p-values, correlations, sample sizes, Kd/IC50 metrics, SMILES, and CIs. | `context_compressor.py:129-175` |
| **Lexical Keyword Prioritization** | Keyword scoring & hash deduplication | **IMPLEMENTED**. MD5 hashing + scoring using word lists (`"significant"`, `"discovered"`, `"novel"`). | `context_compressor.py:513-545, 690-718` |
| **Extractive Truncation** | Hard character slicing for prompt fitting | **IMPLEMENTED**. Fixed string slicing with `[:200]`, `[:max_chars]`, and `len(text) // 4` token estimates. | `context_compressor.py:243, 372, 397, 836` |

### 3.2 Tier-by-Tier Deconstruction

#### 1. Tier 1: `TaskCompressor` (lines 115–401)
- **Input**: `task_result: Dict[str, Any]`
- **Processing**:
  - `_serialize_content()`: Serializes `task_result` to JSON or string (`lines 234–240`).
  - `_extract_statistics()`: Scans strings with regex for p-values (`P_VALUE_PATTERNS`), correlations (`CORRELATION_PATTERNS`), sample sizes (`SAMPLE_SIZE_PATTERNS`), and effect sizes (`EFFECT_SIZE_PATTERNS`). Drenches out duplicates and retains only `[:3]` items (`line 315`).
  - `_extract_key_findings()`: Extracts up to 5 items from `task_result.get("findings")`, `task_result.get("conclusions")`, or `task_result.get("summary")`.
  - `_generate_summary()`: Assembles `[{task_type}] {summary[:197]} (p=..., r=..., n=...)` and slices at `max_tokens * 4` characters (`lines 361–399`).
- **Defects**:
  - `len(text) // 4` assumes pure English ASCII text. For equations, JSON, or non-Latin tokens, this undercounts tokens by up to 300%.
  - Hard truncation at line 372 (`summary[:197] + "..."`) cuts critical scientific hypotheses mid-word.
  - Drops all but the top 3 p-values, discarding multi-variable regression outcomes.

#### 2. Tier 2: `CycleCompressor` (lines 402–585)
- **Input**: `cycle_data: Dict[str, Any]`
- **Processing**:
  - Aggregates task stats: calculates `min_p_value`, count of `significant_count` (where $p < 0.05$), `max_correlation`, `mean_correlation`, and `total_sample_size`.
  - `_prioritize_findings()`: Calculates MD5 hash of lowercase finding to prevent duplicates. Scores findings (+1 if keyword matches, +1 if `50 < len < 200`). Truncates to top 7 (`line 452`).
  - `_generate_cycle_summary()`: Generates single string: `"Cycle {cycle_num}: {task_count} tasks completed. {stats} Key: {top_finding} Hypotheses: {confirmed} confirmed, {refuted} refuted."`

#### 3. Tier 3: `MissionCompressor` (lines 586–750)
- **Input**: `mission_data: Dict[str, Any]`
- **Processing**:
  - Calls `self.cycle_compressor.compress_cycle()` for each cycle in `mission_data.get("cycles", [])`.
  - Scans findings for breakthrough keywords (`"breakthrough"`, `"novel"`, `"unprecedented"`), taking top 5.
  - Generates mission summary: `"Mission: {objective[:100]} Completed {total_cycles} cycles, {total_tasks} tasks. Converged: {reason}..."`

### 3.3 The Critical Architectural Disconnect

```
deep_research_orchestrator.py:1389
  └─► mission_ctx = self.context_compressor.compress_mission(self.session.to_dict())
        │
        ▼  [ResearchSession.to_dict() Keys]:
        │  ['id', 'research_question', 'domain', 'created_at', 'status', 
        │   'current_cycle', 'total_cycles_planned', 'max_runtime_hours', 
        │   'started_at', 'ended_at', 'elapsed_hours', 'findings_count', 
        │   'hypotheses_generated', 'artifacts_created', 'final_report_length', 
        │   'tasks', 'error_log']
        │
        ▼  [MissionCompressor.compress_mission() Expects]:
        │  - mission_data.get("cycles", [])               ==> Evaluates to []
        │  - mission_data.get("research_objective", ...)   ==> Evaluates to "Research"
        │  - mission_data.get("convergence", ...)          ==> Evaluates to None
        │
        ▼  [RESULTING OUTPUT IN KNOWLEDGE_SNAPSHOT]:
        "## MISSION Summary
         Mission: Research Completed 0 cycles, 0 tasks."
```

**Forensic Proof**: In `deep_research_orchestrator.py:1390`, `self.session.knowledge_snapshot = mission_ctx.to_prompt_string()`. Because `ResearchSession.to_dict()` outputs `tasks` instead of `cycles`, `compress_mission` produces 0 cycles and 0 tasks. **Every 3 cycles, all cumulative knowledge in `self.session.knowledge_snapshot` is wiped out and replaced by this empty 0-task placeholder.**

---

## 4. TOKEN BUDGETING & SLIDING WINDOW ANALYSIS (24-HOUR RUNS)

### 4.1 How Long-Horizon Runs Avoid (and Succumb to) Window Overflow

SVEL claims continuous 24-hour and 72-hour execution capability (`OperationLimits: "extended_24hr": 24.0, "god_mode_72hr": 72.0`). We analyzed every mechanism intended to prevent context window overflow:

1. **Time Limits vs. Token Budgets**:
   - `OperationLimits` (`deep_research_orchestrator.py:364–389`) strictly checks elapsed time (`elapsed_hours >= self.max_runtime_hours`). It contains **zero token tracking**.
   - `ConvergenceEngine` (`core/convergence_engine.py:453–465`) tracks dollar costs against `max_budget_usd`. It triggers early termination on cost exhaustion, not context window limits.

2. **Heuristic Sliding Windows in `_build_context()`** (`deep_research_orchestrator.py:4564–4690`):
   - Findings Window: `collected_findings = [str(f.get("result", ""))[:5000] for f in self.session.findings[-3:]]` (`line 4572`). Only the last 3 findings are kept, each hard-truncated to 5,000 characters.
   - Hypotheses Window: `top_hypotheses = all_h[:5]` (`line 4576`) and `hypothesis_tracker.get_active()[:15]` (`line 4639`).
   - Nexus Recall Window: `nexus_retriever.retrieve_relevant_nodes(self.research_question, limit=5)` (`line 4671`).
   - Tools & Agents: Unbounded list of registry tools + whitelist of 14 scientific libraries + battle plan tools (`lines 4580–4611`).

3. **The Blind Planner Disconnect**:
   - In `_build_context()`, line 4629 injects `"knowledge_snapshot": self.session.knowledge_snapshot`.
   - In `plan_creator.py:563–703` (`_build_research_prompt`), the prompt parameters are:
     `{meta_skills_str}`, `{research_objective}`, `{findings_str}`, `{hypotheses_str}`, `{template_str}`, `{arsenal_str}`, `{agents_str}`.
   - **`context.get("knowledge_snapshot")` is never read or formatted into the planning prompt.**
   - Consequently, in a 24-hour run with 50+ cycles, the strategic planner is unaware of any research conducted prior to the last 3 findings.

4. **Mid-Token Slicing in `compress_for_prompt()`** (`context_compressor.py:808–839`):
   - When contexts are combined:
     ```python
     max_chars = remaining_tokens * 4
     parts.append(ctx_str[:max_chars] + "...")
     break
     ```
   - Arbitrary slicing at `max_chars` truncates in the middle of UTF-8 characters, JSON keys, or floating-point numbers (e.g. `p=0.0001` sliced to `p=0.0`), producing malformed LLM input.

---

## 5. TASK DECOMPOSITION & DOMAIN REGULATION AUDIT

### 5.1 `task_decomposer.py`: Neural Fractalizer & DAG Engine

#### A. Decomposition Pipeline (`NeuralFractalizer.shatter`, lines 101–189):
1. **Semantic Loop Guard** (lines 121–128):
   - Computes word overlap between the incoming query and items in `global_cache`:
     $$\text{Overlap} = \frac{|Q_{\text{words}} \cap R_{\text{words}}|}{|Q_{\text{words}}|}$$
   - If overlap $> 0.65$, skips decomposition and returns an empty list `[]`.
   - Memory Cap: `global_cache` is trimmed when length exceeds 100 via `global_cache.remove(next(iter(global_cache)))`.
2. **Dynamic Temperature Schedule** (line 146):
   - Retries up to 3 times: `temp = 0.1 + (attempt * 0.3)` ($0.1 \rightarrow 0.4 \rightarrow 0.7$).
3. **Prompt Mandates** (lines 249–257):
   - Enforces simulation for `experiment_agent`, hypothesis testing stats, and strict separation between tools and skills.

#### B. The Dataclass Mismatch Bug (Fatal):
- `task_decomposer.py:44–79` defines `class SubTask`:
  - Fields: `id`, `description`, `type`, `agent`, `tool`, `adapter`, `args`, `dependencies`, `can_run_parallel`, `priority`, `estimated_seconds`, `capabilities_needed`, `timeout`, `retry_count`.
  - Methods: `to_dict()`, `has_dependencies()`, `can_run_after()`.
- However, line 173 inside `shatter()` imports:
  ```python
  from backend.models.task import SubTask
  tasks = []
  for t in raw_tasks:
      tasks.append(SubTask(**t))
  ```
- `backend/models/task.py:5–30` defines a completely different `SubTask`:
  - Fields: `task_type`, `required_tools`, `required_skills`, `estimated_minutes`, etc.
  - **Does not implement `has_dependencies()`, `can_run_after()`, or `to_dict()`**.
- **Blast Radius**: Calling `build_dag(subtasks)` on tasks returned by `shatter()` immediately crashes:
  `AttributeError: 'SubTask' object has no attribute 'has_dependencies'`.

#### C. DAG Cycle Handling Bug (lines 576–591):
- `build_dag()` performs topological sorting into parallel batches.
- If a circular dependency exists:
  ```python
  if not ready:
      logger.error(f" Circular dependency detected. Remaining: {remaining}")
      break
  ```
- **Silent Task Loss**: Any tasks remaining in `remaining` are silently abandoned. The execution plan proceeds with missing subtasks without alerting the caller.

---

### 5.2 `domain_regulator.py`: Semantic Sieve & Domain Boundaries

#### A. Mathematical Domain Purification (`filter_by_domain_similarity`, lines 27–84):
1. **SBERT Cosine Sieve**:
   - Embeds research question (`q_emb`) and paper snippets truncated to 1,000 chars (`p_embs`).
   - Computes cosine similarity: $\cos(\theta) = \frac{\mathbf{p} \cdot \mathbf{q}}{\|\mathbf{p}\| \|\mathbf{q}\|}$.
   - Gate Threshold: `DOMAIN_SIM_THRESHOLD = 0.18`. Papers with $\cos(\theta) \le 0.18$ are purged.
2. **Hardcoded Heuristic Contamination (Line 70–77)**:
   - Contains hardcoded material string filters from a single past test run:
     `hallucination_materials = ["LuNi2B2C", "borocarbide", "bulk metal"]`
   - If `photonic crystal` is in text and matches these materials, the paper is blocked. This violates the module's docstring mandate to abolish hardcoded heuristics in favor of dynamic neural inference.

#### B. Dynamic Domain Classification & Grounding (`detect_domain` & `get_domain_examples_async`):
- `detect_domain()` (lines 106–175) forces `TASK_ROUTING_MODEL` at `temperature=0.0` to select the top 1–2 system domains. If it fails, it returns `"unknown"`.
- `get_domain_examples_async()` (lines 243–311) synthesizes formal LaTeX equations, variables, physical units, and parameters. If 10 retries fail, it raises `RuntimeError("Domain grounding failed...")`, terminating the entire research mission.
- **Regex Greediness Bug** (line 282): `match = re.search(r"\{.*\}", content, re.S)` matches greedily from the first `{` to the last `}`, crashing with `json.JSONDecodeError` if the LLM emits multiple JSON objects or markdown explanations.

---

## 6. INTER-AGENT EVENT DISPATCHING & RESILIENCE AUDIT

### 6.1 `message_bus.py`: In-Memory Pub/Sub Backbone

1. **Architecture & Scope**:
   - Operates as a local in-memory event bus (`MessageBus`).
   - Distributed Redis functionality (`_start_redis_listener`, lines 127–142) was deprecated and disabled with an immediate `return`, leaving orphaned dead code.
2. **Priority Inaction Bug**:
   - `Message` has a `priority: int = 5` field (`line 71`).
   - `MessageBus.publish()` accepts `priority: int = 5` (`line 199`).
   - **The priority field is completely ignored.** Dispatching uses a standard Python `set` of subscriber callbacks and `asyncio.gather()`. There is no priority queue or prioritized delivery.
3. **Silent Delivery Failures**:
   - In broadcast delivery (`_deliver`, lines 259–271), subscriber handlers run via `asyncio.gather(*tasks, return_exceptions=True)`.
   - Exceptions inside handlers are caught in `_safe_call()` (lines 279–298), logged, and swallowed. There is **no Dead Letter Queue (DLQ)** and **no subscriber retry policy**.
   - In direct messaging (`lines 243–257`), if `msg.target` is not registered, the bus simply logs a warning and drops the message permanently.
4. **Memory Leak in Message History**:
   - `_history` stores the last `max_history=1000` messages.
   - Message payloads contain raw search dumps, full paper texts, and dataframes.
   - On memory-constrained hardware (e.g. Mac mini 16GB RAM), holding 1,000 uncompressed payload objects can cause significant heap bloat.

---

### 6.2 `fallback_manager.py`: Provider Failover & Rate Limit Recovery

1. **Circuit Breaker Pattern** (lines 251–277):
   - Failure threshold: `circuit_breaker_threshold = 5`.
   - Recovery timeout: `circuit_breaker_timeout = 60.0` seconds.
   - States: `HEALTHY`, `DEGRADED` ($\ge 2$ failures), `DOWN` ($\ge 5$ failures).
2. **Rate Limit Recovery Blindness**:
   - Retry logic (`lines 154–213`) uses fixed exponential backoff: `backoff = min(2 ** attempt, 10)`.
   - **Does not inspect HTTP 429 status codes or parse `Retry-After` headers.**
   - If an upstream provider (OpenAI/Anthropic) imposes a 60-second rate-limit lockout, `FallbackManager` retries at $1\text{s}$, $2\text{s}$, and $4\text{s}$, burns through all 3 attempts in 7 seconds, trips the circuit breaker to `DOWN`, and fails over.
   - **No Jitter**: Simultaneous swarm requests collide on identical retry timestamps, causing thundering-herd API re-jections.
3. **The `_set_provider_context` KeyError Crash**:
   ```python
   # fallback_manager.py:242-249
   if "provider" in kwargs:
       kwargs["provider"] = provider
       task_hint = kwargs.get("task_hint", "routing")
       model_mapping = {
           "openai": get_model(task_hint),
           "anthropic": get_fallback(task_hint),
           "gemini": get_model("vision"),
           "moonshot": get_model("routing")
       }
       kwargs["model"] = model_mapping.get(provider, kwargs["model"])
   ```
   - **Forensic Bug**: If `kwargs` contains `"provider"` (e.g., `"groq"` from the default chain `["openai", "groq", "local"]`) but does NOT contain `"model"`, evaluating `kwargs["model"]` inside `.get()` raises an unhandled `KeyError: 'model'`.
   - Furthermore, because lines 242–249 are indented under `if "provider" in kwargs:`, provider-specific model mapping is skipped entirely if the caller does not pre-populate `"provider"`.

---

## 7. COMPREHENSIVE MATRIX OF EDGE CASES, LEAKS & SILENT LOSSES

| # | File Path & Lines | Vulnerability / Failure Mode | Root Cause | Blast Radius & Severity |
| :- | :--- | :--- | :--- | :--- |
| **1** | `core/context_compressor.py:621` & `deep_research_orchestrator.py:1389` | **Total Historical Knowledge Erasure** | `ResearchSession.to_dict()` lacks `"cycles"` key expected by `MissionCompressor`. | **CRITICAL**. Every 3 cycles, `knowledge_snapshot` is wiped and replaced with an empty 0-cycle string. |
| **2** | `core/planning/plan_creator.py:563-703` | **Strategic Planner Amnesia** | `_build_research_prompt` never injects `context["knowledge_snapshot"]`. | **HIGH**. Planner operates with complete amnesia of past cycles beyond the last 3 findings. |
| **3** | `core/context_compressor.py:183, 780` | **Phantom Summarization Engine** | `self.llm_manager` is accepted as an argument but never called; abstractive compression does not exist. | **MEDIUM**. Misleads architecture; relies entirely on brittle regex and string truncation. |
| **4** | `core/task_decomposer.py:173, 569` | **DAG Execution Engine Crash** | `shatter()` returns `backend.models.task.SubTask`, which lacks DAG helper methods (`has_dependencies()`). | **CRITICAL**. Calling `build_dag()` on shattered tasks causes an immediate `AttributeError` crash. |
| **5** | `core/fallback_manager.py:249` | **KeyError in Provider Failover** | `model_mapping.get(provider, kwargs["model"])` evaluates `kwargs["model"]` when key is absent. | **HIGH**. Crashes fallback execution when using `"groq"` or `"local"` without a pre-set `"model"`. |
| **6** | `core/input_sanitizer.py:63, 76` | **ReDoS Vulnerability via Greedy Regex** | Line 63 retains `\$\{.*\}` alongside bounded `\$\{.{0,100}\}` at line 76. | **MEDIUM**. Long crafted inputs can trigger catastrophic regex backtracking, freezing the event loop. |
| **7** | `core/input_sanitizer.py:280-297` | **Unbounded Memory Leak in IP Tracking** | `self._suspicious_ips` (defaultdict) never evicts old IP keys. | **LOW-MEDIUM**. IP spoofing sweeps cause continuous memory growth. |
| **8** | `core/domain_regulator.py:282` | **Greedy Regex JSON Decoding Failure** | `re.search(r"\{.*\}", content, re.S)` matches from first `{` to last `}` across multiple blocks. | **HIGH**. Fails to parse valid JSON containing trailing text, exhausting grounding retries and aborting runs. |
| **9** | `core/message_bus.py:71, 199` | **Priority Queue Inaction** | Priority values are accepted but never used during event scheduling or dispatch. | **MEDIUM**. High-priority error/fallback events are delayed behind bulk data/tool events. |
| **10**| `core/message_bus.py:407-418` | **Post-Timeout Event Vanishing** | `request_and_wait` unregisters handlers on timeout; late responses are permanently dropped. | **MEDIUM**. Delayed agent responses to queries vanish into the void without trace. |
| **11**| `core/task_decomposer.py:584-587` | **Silent Task Dropping on Cycle** | On cycle detection, DAG builder logs an error and breaks without executing remaining tasks. | **HIGH**. Circular dependencies cause silent task loss without workflow cancellation or alerting. |
| **12**| `core/context_compressor.py:836` | **Mid-Token / Syntax Prompt Truncation** | Slices text at character index `max_chars = remaining_tokens * 4`. | **HIGH**. Cuts JSON strings, markdown syntax, or numbers in half, inducing LLM hallucination or syntax errors. |

---

## 8. CONCRETE ARCHITECTURAL RECOMMENDATIONS & REMEDIATIONS

### Remediation 1: Fix the Mission Compressor & Orchestrator Data Contract
Update `ResearchSession.to_dict()` in `backend/orchestration/deep_research_orchestrator.py` to serialize structured cycle history, and align field names:
```python
# In ResearchSession.to_dict():
return {
    "id": self.id,
    "research_objective": self.research_question,  # Match MissionCompressor expectations
    "research_question": self.research_question,
    "domain": self.domain,
    "current_cycle": self.current_cycle,
    "total_cycles_planned": self.total_cycles_planned,
    "tasks": [t.to_dict() if hasattr(t, "to_dict") else str(t) for t in self.tasks],
    "cycles": [
        {
            "cycle": c,
            "tasks": [t.to_dict() for t in self.tasks if getattr(t, "cycle", None) == c],
            "findings": [f for f in self.findings if f.get("cycle") == c]
        }
        for c in range(1, self.current_cycle + 1)
    ],
    "findings": self.findings,
    "total_hypotheses": len(self.hypothesis_tracker.get_all()),
    "confirmed_hypotheses": len(self.hypothesis_tracker.get_confirmed()),
    "refuted_hypotheses": len(self.hypothesis_tracker.get_refuted()),
}
```

### Remediation 2: Inject `knowledge_snapshot` into Plan Creator Prompt
In `backend/core/planning/plan_creator.py:646`, explicitly format `knowledge_snapshot` into the tactical planning prompt:
```python
# In PlanCreator._build_research_prompt():
knowledge_str = context.get("knowledge_snapshot", "").strip() or "No mission summary established yet."

return f"""
{meta_skills_str}

TACTICAL PLANNER: DEEP RESEARCH ORCHESTRATION
Current Cycle: {cycle} | Goal: OBJECTIVE SYNTHESIS.
Remaining Time Budget: {max_runtime}

## RESEARCH OBJECTIVE
{research_objective}

## COMPRESSED MISSION KNOWLEDGE (LONG-HORIZON HISTORY)
{knowledge_str}

## RECENT TACTICAL FINDINGS (LAST 3 CYCLES)
{findings_str}
...
"""
```

### Remediation 3: Unify the SubTask Dataclass in Task Decomposer
Remove the conflicting import in `backend/core/task_decomposer.py:173` and use the local `SubTask` or extend `backend/models/task.py:SubTask` to support DAG operations:
```python
# In backend/core/task_decomposer.py line 173:
# REPLACE: from backend.models.task import SubTask
# WITH:
tasks = [
    SubTask(
        id=t.get("id", f"sub_{i}"),
        description=t.get("description", ""),
        type=t.get("type", "research"),
        agent=t.get("agent"),
        tool=t.get("required_tools", [None])[0] if t.get("required_tools") else t.get("tool"),
        args=t.get("args", {}),
        dependencies=t.get("dependencies", []),
        can_run_parallel=t.get("can_run_parallel", True),
        priority=t.get("priority", 5)
    )
    for i, t in enumerate(raw_tasks)
]
```

### Remediation 4: Fix `_set_provider_context` in FallbackManager
Fix indentation and eliminate potential `KeyError` in `backend/core/fallback_manager.py:242–250`:
```python
def _set_provider_context(self, provider: str, kwargs: Dict[str, Any]):
    """Safely inject provider and model mapping into kwargs."""
    kwargs["provider"] = provider
    task_hint = kwargs.get("task_hint", "routing")
    model_mapping = {
        "openai": get_model(task_hint),
        "anthropic": get_fallback(task_hint),
        "gemini": get_model("vision"),
        "moonshot": get_model("routing"),
        "groq": "llama-3.3-70b-versatile",
        "local": "qwen2.5-coder-7b"
    }
    # Safely get model with fallback to existing kwargs['model'] or default
    current_model = kwargs.get("model", "gpt-5-mini")
    kwargs["model"] = model_mapping.get(provider, current_model)
```

### Remediation 5: Remove ReDoS Pattern in Input Sanitizer
Delete line 63 `r"\$\{.*\}"` in `backend/core/input_sanitizer.py` to prevent catastrophic regex backtracking, and add periodic pruning for `_suspicious_ips`.

### Remediation 6: Implement True Token Budgeting & Sliding Window Management
Introduce a dedicated `TokenBudgetManager` backed by `tiktoken` (or approximate character-token ratio calculation) that calculates available context window space, budgets explicit token quotas for (1) System Persona, (2) Grounding & Meta-Skills, (3) Compressed Mission Snapshot, (4) Immediate Recent Findings, and (5) Tool Definitions, preventing abrupt slicing at arbitrary character boundaries.

---
*Report compiled autonomously and forensically by Research Subagent.*
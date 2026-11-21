# SVEL AI Scientist Orchestration Layer: 2024/2025 LLM Workarounds Audit

**Document Version:** 1.0.0  
**Date:** September 2026  
**Auditor:** Senior AI Agent Orchestration Architect  
**Scope:** Complete audit of SVEL AI Scientist backend orchestration, planning, hypothesis, interface, and agent layers.  
**Target Output Path:** `/Users/samaraldico/SVEL AI Scientist/research/10_orchestration_workarounds_audit.md`

---

## Executive Summary

The SVEL AI Scientist codebase contains a sophisticated, multi-tiered autonomous research system designed across 2024 and early 2025. During that era, frontier Large Language Models (GPT-4o, Claude 3/3.5 Sonnet, Gemini 1.0/1.5) suffered from significant operational constraints:
- Inability to output strict, guaranteed JSON without markdown prose or fence artifacts.
- Output token ceilings capped at 4,096 tokens.
- Strict and volatile API rate limits (Tier 1-3 TPM/RPM throttles).
- Instruction drift and hallucination under complex multi-constraint prompts.
- Weak multi-step reasoning requiring tasks to be manually decomposed into multi-turn sequential chains.

To achieve stability in 2024, the SVEL architecture implemented hundreds of defensive workarounds: brute-force regex JSON extractors, brace-counting parsers, hardcoded emergency fallback roadmaps, aggressive string slicing (`[:4000]`, `[:8000]`), artificial sleep timers (up to 120 seconds), keyword validation checks (`"bootstrap" in code`), and combative system prompts shouting in capital letters (`YOU MUST`, `MANDATORY`).

With **late-2026 frontier models** (GPT-5/o3, Claude 3.7 Sonnet Thinking, Gemini 2.5 Pro):
1. **Guaranteed Constrained Decoding**: Native JSON Schema / Pydantic structured outputs guarantee 100% syntactically valid JSON matching strict typing at the token-generation level.
2. **Massive Output & Context Windows**: Context windows of 1M–2M+ tokens and output generation limits of 64k–128k tokens eliminate the need for slicing or section-by-section prompting.
3. **Single-Shot Multi-Dimensional Synthesis**: Integrated reasoning models can brainstorm, formalize, mathematically structure, and validate hypotheses in a single request.
4. **Natural Instruction Following**: Coercive shouting is counter-productive; modern models follow calibrated, neutral developer directives.
5. **High API Throughput**: Modern Tier 4/5 enterprise endpoints support millions of TPM, rendering artificial sleep timers and local token-bucket poll loops obsolete.

This audit examines **26 core files** across four architectural layers, pinpointing exact line numbers, obsolete workaround patterns, the 2026 capabilities that replace them, and clean production code patterns.

---

## Workaround Taxonomy

| Category | Description | 2024/Early-2025 Cause | Late-2026 Frontier Solution |
| :--- | :--- | :--- | :--- |
| **1. Regex JSON Parsing** | `find('{')`, `rfind('}')`, `re.search`, `repair_json`, markdown fence stripping | LLMs returned conversational chatter, markdown backticks, or trailing commas | Native Structured Outputs (`response_format={"type": "json_schema"}` or Pydantic model passing) |
| **2. Canned Rescue Plans** | Hardcoded dummy plans, fallback hypotheses, mock responses on error | LLMs frequently produced empty strings or unparseable gibberish | Guaranteed schema adherence + deterministic model fallback |
| **3. Context Truncation** | Slicing strings to `[:4000]`, `[:8000]`, `[:10000]`, `max_tokens=4000` | 8k/32k/128k input limits and 4,096 output token limits | 1M–2M token context windows, 64k–128k output tokens |
| **4. Artificial Sleep Timers** | `asyncio.sleep(20)`, `sleep(30)`, `sleep(65)`, `sleep(120)` | Preventing HTTP 429 rate limit errors on low-tier 2024 accounts | Asynchronous provider SDK client rate-limiting, retry-after headers, Tier 5 TPM |
| **5. Threatening Prompts** | Shouting in capital letters: `MANDATORY`, `YOU MUST`, `REJECTED` | Early LLMs suffered from attention drift and ignored soft constraints | Calibrated developer system prompts, system instructions, and schema validation |
| **6. Keyword Validation Hacks** | String checks like `if "bootstrap" in code:` or `if "p_value" in code:` | Early LLMs hallucinated simplistic linear regressions without rigor | AST semantic inspection, unit test execution in sandbox, LLM-as-a-judge |
| **7. Excessive Retry Loops** | 5 to 10 retries with cascading fallbacks for single prompts | Frequent transient failures, rate limit exhaustion, or format degradation | 2 retries max with exponential backoff; schema guarantees format correctness |
| **8. Multi-Step Prompt Chains** | Splitting one task into 3–5 sequential calls (brainstorm -> extract -> harden) | Context dilution and inability of old models to reason and structure simultaneously | Single-shot chain-of-thought / native thinking reasoning models |

---

## Priority 1: Orchestration Core

### 1. `backend/orchestration/deep_research_orchestrator.py` (4,953 lines)

The central orchestrator driving autonomous research cycles, swarm deployment, convergence checks, and report compilation.

#### Finding 1.1: Regex Extraction and Manual Array Repair of Hypothesis Updates
- **Location:** [deep_research_orchestrator.py#L3478-L3504](file:///Users/samaraldico/SVEL%20AI%20Scientist/backend/orchestration/deep_research_orchestrator.py#L3478-L3504)
- **Code Pattern:**
  ```python
  # Robust JSON cleaning
  cleaned_text = text.strip()
  import re
  # Try to find the JSON object block
  json_match = re.search(r'\{.*\}', cleaned_text, re.DOTALL)
  if json_match:
      cleaned_text = json_match.group(0)
  try:
      data = json.loads(cleaned_text)
  except json.JSONDecodeError as je:
      logger.warning(f"Analysis JSON parse failed: {je}")
      try:
          match = re.search(r'"hypothesis_updates"\s*:\s*(\[.*?\])', text, re.DOTALL)
          if match:
              json_str = "{" + match.group(0) + "}"
              json_str = re.sub(r',\s*\]', ']', json_str)
              data = json.loads(json_str)
          else:
              raise je
      except Exception:
          logger.error(f"Failed to parse analysis JSON: {text[:200]}...")
          data = {"hypothesis_updates": []}
  ```
- **Obsolescence Rationale:** In 2024, LLMs often wrapped JSON in commentary or generated trailing commas inside arrays (`[..., ]`), failing standard `json.loads`. Late-2026 models support grammar-constrained decoding (e.g. OpenAI structured outputs, Anthropic tool use/JSON mode, Gemini structured output schema), which guarantees that the model's output stream adheres strictly to the target JSON schema without trailing commas or preamble text.
- **Clean Replacement:**
  ```python
  class HypothesisUpdate(BaseModel):
      hypothesis_id: str
      action: Literal["confirm", "refute", "refine", "keep"]
      reason: str

  class AnalysisResult(BaseModel):
      hypothesis_updates: List[HypothesisUpdate]

  result = await self.llm_manager.run_structured_async(
      prompt=analysis_prompt,
      response_model=AnalysisResult
  )
  data = result.model_dump()
  ```

#### Finding 1.2: Hardcoded Emergency Task Injection on Planning Collapse
- **Location:** [deep_research_orchestrator.py#L2611-L2632](file:///Users/samaraldico/SVEL%20AI%20Scientist/backend/orchestration/deep_research_orchestrator.py#L2611-L2632)
- **Code Pattern:**
  ```python
  if rigor_candidates and len(global_ready_tasks) < 10:
      logger.info(f" [RIGOR] Rigor Guard: Injecting Emergency Experiment for {rigor_candidates[0].id}")
      if self.session.plans:
          target_plan = self.session.plans[0]
          emergency_task = ResearchTask(
              id=f"rigor_{cycle}_{uuid.uuid4().hex[:4]}",
              description=f"EXPERIMENTAL VALIDATION: {rigor_candidates[0].statement}",
              task_type="experiment",
              required_agents=[agent_key],
              estimated_minutes=30,
              is_exploration=False,
              payload={
                  "statement": rigor_candidates[0].statement,
                  "rationale": rigor_candidates[0].rationale
              }
          )
          target_plan.tasks.append(emergency_task)
          global_ready_tasks.append(emergency_task)
  ```
- **Obsolescence Rationale:** When 2024 planners hallucinated empty task sets or failed to generate empirical validation tasks, orchestrators had to fabricate synthetic fallback tasks to prevent the swarm from terminating. Frontier 2026 models with reasoning tokens and calibrated planning instructions reliably generate complete, dependency-resolved task graphs matching required task quotas.
- **Clean Replacement:** Remove synthetic task fabrication. If task generation yields zero tasks, trigger an explicit re-plan with the failure reason in context or raise an actionable orchestrator exception.

#### Finding 1.3: Aggressive Context Slicing across Findings, Entities, and Summaries
- **Location:** [deep_research_orchestrator.py#L1806-L1811](file:///Users/samaraldico/SVEL%20AI%20Scientist/backend/orchestration/deep_research_orchestrator.py#L1806-L1811), [L3266](file:///Users/samaraldico/SVEL%20AI%20Scientist/backend/orchestration/deep_research_orchestrator.py#L3266), [L4411](file:///Users/samaraldico/SVEL%20AI%20Scientist/backend/orchestration/deep_research_orchestrator.py#L4411), [L4579](file:///Users/samaraldico/SVEL%20AI%20Scientist/backend/orchestration/deep_research_orchestrator.py#L4579)
- **Code Pattern:**
  ```python
  # Line 1806 & 1811:
  value=text[:10000],
  self.world_model._ground_scientific_entities(f_id, text[:10000], {"domain": self.domain})

  # Line 3266:
  result_str = str(result.get("result", ""))[:2000]

  # Line 4411:
  summary = summary[:2000]

  # Line 4579:
  collected_findings = [str(f.get("result", ""))[:5000] for f in self.session.findings[-3:]]
  ```
- **Obsolescence Rationale:** Hardcoded limits of 2,000 to 10,000 characters (~500 to 2,500 tokens) were designed to prevent context window overflow on 8k/32k token models and limit prompt token expense. With 1M+ context windows standard on late-2026 models, slicing text arbitrarily chops off critical data tables, methodology sections, and statistical confidence intervals mid-sentence.
- **Clean Replacement:** Feed complete finding texts and entity contexts directly. Utilize hierarchical summarization only when aggregating over hundreds of documents (>500k tokens), rather than arbitrary string character slices.

#### Finding 1.4: Artificial Sleep Timers for Rate Limiting and Backoff
- **Location:** [deep_research_orchestrator.py#L1636](file:///Users/samaraldico/SVEL%20AI%20Scientist/backend/orchestration/deep_research_orchestrator.py#L1636), [L4736-L4741](file:///Users/samaraldico/SVEL%20AI%20Scientist/backend/orchestration/deep_research_orchestrator.py#L4736-L4741)
- **Code Pattern:**
  ```python
  # Line 1636:
  if i > 0:
      logger.info(f" [JITTER] Respecting academic rate limits. Sleeping 20s before next pulse...")
      await asyncio.sleep(20)

  # Line 4736-4741:
  ERROR_BACKOFF_SECONDS = [2, 4, 8, 16, 32]
  backoff_idx = min(self.session.consecutive_errors - 1, len(ERROR_BACKOFF_SECONDS) - 1)
  backoff = ERROR_BACKOFF_SECONDS[backoff_idx]
  await asyncio.sleep(backoff)
  ```
- **Obsolescence Rationale:** Fixed 20-second sleeps between seed queries introduce dead time into the asynchronous loop. Academic APIs (PubMed, ArXiv) and modern LLM gateway routers support token-bucket rate limiters with HTTP 429 `Retry-After` header parsing rather than hardcoded sleep pauses.
- **Clean Replacement:** Implement an asynchronous token-bucket rate limiter with adaptive jitter that sleeps only when a rate limit header is returned by the upstream endpoint.

#### Finding 1.5: Fragile Keyword Matching for Grounding and Verdicts
- **Location:** [deep_research_orchestrator.py#L2445-L2447](file:///Users/samaraldico/SVEL%20AI%20Scientist/backend/orchestration/deep_research_orchestrator.py#L2445-L2447), [L2852](file:///Users/samaraldico/SVEL%20AI%20Scientist/backend/orchestration/deep_research_orchestrator.py#L2852), [L4681](file:///Users/samaraldico/SVEL%20AI%20Scientist/backend/orchestration/deep_research_orchestrator.py#L4681)
- **Code Pattern:**
  ```python
  # Line 2445-2447:
  if "VERDICT: CONFIRMED" in content_upper or "CONFIRMED" in content_upper:
      ...
  elif "VERDICT: REFUTED" in content_upper or "REFUTED" in content_upper:
      ...

  # Line 2852 & 4681:
  if "electrolyte" in self.research_question.lower() and "qubit" in t_text:
      # Cross-domain contamination hack
  ```
- **Obsolescence Rationale:** Relying on literal substring matching for semantic verdicts is notoriously brittle (e.g., matching `"NOT CONFIRMED"` as `"CONFIRMED"`). Hardcoding domain keywords (`"electrolyte"`, `"qubit"`) into orchestrator routing logic represents domain-specific overfitting.
- **Clean Replacement:** Structured outputs with enum fields (`verdict: Literal["confirmed", "refuted", "inconclusive"]`) and semantic vector embedding similarity for cross-domain contamination detection.

---

### 2. `backend/orchestration/singularity.py` (545 lines)

The dynamic task re-decomposition and subtask branching engine.

#### Finding 2.1: Markdown Fence Stripping and json_repair Type-Sniffing
- **Location:** [singularity.py#L118-L132](file:///Users/samaraldico/SVEL%20AI%20Scientist/backend/orchestration/singularity.py#L118-L132), [L308-L336](file:///Users/samaraldico/SVEL%20AI%20Scientist/backend/orchestration/singularity.py#L308-L336)
- **Code Pattern:**
  ```python
  # Line 118-129:
  if "```json" in text:
      text = text.split("```json")[1].split("```")[0]
  elif "```" in text:
      text = text.split("```")[1].split("```")[0]
  try:
      from backend.utils.json_repair import repair_json
      sub_dicts = repair_json(text.strip())
      if not isinstance(sub_dicts, list):
          if isinstance(sub_dicts, dict) and "subtasks" in sub_dicts:
              sub_dicts = sub_dicts["subtasks"]
          else:
              sub_dicts = [sub_dicts]
  except Exception as pe:
      logger.error(f" [SINGULARITY] JSON repair failed in re_decompose: {pe}")
      sub_dicts = []

  # Line 323-334:
  if isinstance(parsed_data, dict):
      if "tasks" in parsed_data:
          sub_task_dicts = parsed_data["tasks"]
      elif "sub_tasks" in parsed_data:
          sub_task_dicts = parsed_data["sub_tasks"]
      else:
          sub_task_dicts = [parsed_data]
  ```
- **Obsolescence Rationale:** Because 2024 models inconsistently returned either top-level JSON lists `[{...}]`, wrapped dicts `{"tasks": [...]}`, or alternative keys `{"sub_tasks": [...]}`, complex fallback code was required to inspect types at runtime. In 2026, passing a Pydantic schema enforces the exact key names and types at token emission time.
- **Clean Replacement:**
  ```python
  class SubtaskPlan(BaseModel):
      tasks: List[ResearchTaskModel]

  result = await self.llm_manager.run_structured_async(prompt, response_model=SubtaskPlan)
  sub_tasks = result.tasks
  ```

---

### 3. `backend/orchestration/overmind.py` (338 lines)

The meta-governor and strategic trajectory auditor.

#### Finding 3.1: Anthropic SDK Object Type-Unwrapping & Fallback Directive
- **Location:** [overmind.py#L265-L284](file:///Users/samaraldico/SVEL%20AI%20Scientist/backend/orchestration/overmind.py#L265-L284)
- **Code Pattern:**
  ```python
  if isinstance(result, dict):
      text = result.get("text", "")
  elif hasattr(result, 'content'):
      if isinstance(result.content, list) and len(result.content) > 0:
          text = getattr(result.content[0], 'text', str(result.content[0]))
      else:
          text = str(result.content)
  else:
      text = str(result)

  from backend.utils.json_repair import repair_json
  directive = repair_json(text)
  if not directive:
       logger.warning(f"Overmind audit failed to parse JSON. Raw: {text[:100]}...")
       directive = {"action": "continue", "rationale": "JSON Parsing Failure"}
  ```
- **Obsolescence Rationale:** Heterogeneous payload unpacking was required due to varying response shapes across early SDK iterations. In modern orchestration, a standardized LLM client wrapper normalizes outputs into typed Pydantic models. Hardcoded fallback directives (`{"action": "continue", "rationale": "JSON Parsing Failure"}`) mask catastrophic audit failures.
- **Clean Replacement:** Enforce a typed response schema `OvermindDirective(BaseModel)` directly in the client call.

---

### 4. `backend/orchestration/swarm_manager.py` (476 lines)

The parallel execution coordinator and consensus engine.

#### Finding 4.1: Brace Matching with Regex Fallback to Word Boundary Heuristics
- **Location:** [swarm_manager.py#L76-L96](file:///Users/samaraldico/SVEL%20AI%20Scientist/backend/orchestration/swarm_manager.py#L76-L96)
- **Code Pattern:**
  ```python
  start = text.find('{')
  end = text.rfind('}')
  if start != -1 and end != -1:
      json_str = text[start:end+1]
      parsed = repair_json(json_str)
      if not parsed:
          parsed = json.loads(json_str)

  if not parsed or not isinstance(parsed, dict):
      import re
      text_upper = text.upper()
      has_yes = bool(re.search(r'\bYES\b', text_upper))
      has_no = bool(re.search(r'\b(NO|NOT|NEITHER|FALSE)\b', text_upper))
      verdict = "YES" if has_yes and not has_no else "NO"
  ```
- **Obsolescence Rationale:** This combines Category 1 (Regex JSON parsing) with Category 6 (Keyword validation hack). If JSON parsing failed, the code fell back to searching for `\bYES\b` or `\bNO\b` in raw text. A sentence like *"There is NO doubt the result is valid"* would be incorrectly parsed as `NO` due to `\bNO\b`.
- **Clean Replacement:**
  ```python
  class ConsensusVerdict(BaseModel):
      verdict: Literal["YES", "NO"]
      confidence: float = Field(ge=0.0, le=1.0)
      metrics_found: Dict[str, float]

  result = await self.llm_manager.run_structured_async(prompt, response_model=ConsensusVerdict)
  verdict = result.verdict
  ```

#### Finding 4.2: Artificial Jitter Sleep for Worker Startup
- **Location:** [swarm_manager.py#L286-L288](file:///Users/samaraldico/SVEL%20AI%20Scientist/backend/orchestration/swarm_manager.py#L286-L288)
- **Code Pattern:**
  ```python
  # [GODZILLA TUNING] Neural Jitter: Startup staggered delay
  import random
  await asyncio.sleep(random.uniform(0.1, 5.0))
  ```
- **Obsolescence Rationale:** Staggering worker startup with artificial 0.1s–5.0s sleeps was introduced to prevent simultaneous API calls from triggering 2024 Tier 1 rate limit spikes. With modern client connection pooling and Tier 4/5 API rate tiers, this jitter is unnecessary delay.
- **Clean Replacement:** Remove the artificial sleep; let the connection pool and client semaphore handle dispatch.

#### Finding 4.3: Summary Context Truncation
- **Location:** [swarm_manager.py#L46](file:///Users/samaraldico/SVEL%20AI%20Scientist/backend/orchestration/swarm_manager.py#L46)
- **Code Pattern:**
  ```python
  {summary[:10000]}
  ```
- **Obsolescence Rationale:** Arbitrary character slicing to 10k characters truncates detailed scientific summaries mid-table or mid-equation.
- **Clean Replacement:** Pass full summary text or utilize structured entity models.

---

### 5. `backend/central_router_beast.py` (339 lines)

The central router responsible for delegating queries to specialized agents.

#### Finding 5.1: Regex JSON Search with Canned Fallback Agent Selection
- **Location:** [central_router_beast.py#L303-L313](file:///Users/samaraldico/SVEL%20AI%20Scientist/backend/central_router_beast.py#L303-L313)
- **Code Pattern:**
  ```python
  cands = list(self.agent_map.keys())
  prompt = f"Select the best agent from {cands} for: {query}. Return JSON: {{\"selected\": \"name\"}}"
  try:
      from backend.llm_manager import TASK_ROUTING_MODEL
      raw = await self.llm_manager.run_async(prompt, model=TASK_ROUTING_MODEL)
      text = raw.get("text", "{}")
      parsed = json.loads(re.search(r"\{.*\}", text, re.S).group(0))
      return {"selected": parsed.get("selected"), "confidence": 1.0}
  except Exception as e:
      logger.warning(f"Component selection parsing failed: {e}")
      return {"selected": "research_agent", "confidence": 0.5}
  ```
- **Obsolescence Rationale:** Using `re.search(r"\{.*\}", text, re.S)` on raw text and falling back to a hardcoded `"research_agent"` on regex failure is an archetype of 2024 brittle routing. Modern models support native function/tool calling or Enum constrained output.
- **Clean Replacement:**
  ```python
  AgentEnum = Literal[tuple(self.agent_map.keys())]

  class RouteDecision(BaseModel):
      selected: AgentEnum
      confidence: float = Field(ge=0.0, le=1.0)
      rationale: str

  decision = await self.llm_manager.run_structured_async(prompt, response_model=RouteDecision)
  ```

---

## Priority 2: Planning & Hypothesis Layer

### 6. `backend/core/planning/plan_creator.py` (915 lines)

The primary planning engine that creates, structures, and revises multi-stage research plans.

#### Finding 6.1: Hardcoded Masterpiece Roadmap Canned Injection
- **Location:** [plan_creator.py#L319-L330](file:///Users/samaraldico/SVEL%20AI%20Scientist/backend/core/planning/plan_creator.py#L319-L330)
- **Code Pattern:**
  ```python
  # [GODZILLA RESCUE] Hard-coded Plan Injection
  if not plan.tasks:
      logger.critical(" [RESCUE] LLM returned 0 tasks. Injecting Masterpiece Roadmap.")
      plan.tasks = [
          ResearchTask(id=f"rescue_{cycle}_1", task_type="research", description=f"Extract empirical data regarding {research_objective}.", required_tools=["pubmed_search", "arxiv_search"], priority=1, estimated_minutes=30),
          ResearchTask(id=f"rescue_{cycle}_2", task_type="analysis", description=f"Analyze datasets for {research_objective}.", required_tools=["data_cleaner"], priority=2, estimated_minutes=30),
          ResearchTask(id=f"rescue_{cycle}_3", task_type="experiment", description="Execute modeling or simulation for the objective.", required_tools=["experiment_agent"], required_agents=["experiment_agent"], priority=3, estimated_minutes=60, dependencies=[f"rescue_{cycle}_1", f"rescue_{cycle}_2"]),
          ResearchTask(id=f"rescue_{cycle}_4", task_type="synthesis", description="Generate high-rigor discovery report with falsification metrics.", required_tools=["report_generator"], priority=4, estimated_minutes=30, dependencies=[f"rescue_{cycle}_3"])
      ]
      plan.rationale = "Rescue roadmap injected to bypass LLM planning failure and ensure discovery execution."
  ```
- **Obsolescence Rationale:** A canned, hardcoded 4-task pipeline (`rescue_{cycle}_1` through `rescue_{cycle}_4`) that injects generic search, analysis, experiment, and synthesis tasks. In 2024, if a model failed to generate valid JSON or hallucinated 0 tasks, this avoided hard aborts. In 2026, structured output schemas enforce `min_items=4` on the generated task list, making zero-task responses impossible.
- **Clean Replacement:**
  ```python
  class ResearchPlanModel(BaseModel):
      tasks: List[ResearchTaskModel] = Field(min_items=4)
      rationale: str
      exploration_ratio: float
  ```

#### Finding 6.2: 120-Second Artificial Sleep on Plan Revision
- **Location:** [plan_creator.py#L870-L875](file:///Users/samaraldico/SVEL%20AI%20Scientist/backend/core/planning/plan_creator.py#L870-L875)
- **Code Pattern:**
  ```python
  MAX_RETRIES = 3
  for attempt in range(MAX_RETRIES):
      if attempt > 0:
          logger.info(f" [JITTER] Respecting rate limits. Sleeping 120s before plan revision attempt {attempt+1}...")
          await asyncio.sleep(120.0)
  ```
- **Obsolescence Rationale:** A 2-minute (`120.0s`) hard sleep on every retry attempt. In 2024, tier 1/2 accounts hit TPM limits during long planning prompts and required multi-minute reset windows. In 2026, enterprise rate limits and reasoning model endpoints handle continuous streams without requiring 2-minute pauses.
- **Clean Replacement:** Replace with standard client-level backoff (`min=2s, max=10s`) governed by HTTP response headers.

#### Finding 6.3: Nuclear Clean JSON Parsing with Brace Slicing
- **Location:** [plan_creator.py#L812-L829](file:///Users/samaraldico/SVEL%20AI%20Scientist/backend/core/planning/plan_creator.py#L812-L829)
- **Code Pattern:**
  ```python
  cleaned_text = response_text.strip()
  # Nuclear Clean: Isolate JSON block
  start = cleaned_text.find('{')
  end = cleaned_text.rfind('}')
  if start != -1 and end != -1:
      cleaned_text = cleaned_text[start:end+1]

  try:
      from backend.utils.json_repair import repair_json
      data = repair_json(cleaned_text)
  except ImportError:
      try:
          data = json.loads(cleaned_text)
      except:
          data = None
  ```
- **Obsolescence Rationale:** Slicing from `find('{')` to `rfind('}')` fails when the prompt includes introductory JSON snippets or nested examples in the preamble.
- **Clean Replacement:** Native structured output decoding directly to `ResearchPlanModel`.

#### Finding 6.4: Verbose Shouting Prompts with Capitalized Threats
- **Location:** [plan_creator.py#L476](file:///Users/samaraldico/SVEL%20AI%20Scientist/backend/core/planning/plan_creator.py#L476), [L681-L684](file:///Users/samaraldico/SVEL%20AI%20Scientist/backend/core/planning/plan_creator.py#L681-L684)
- **Code Pattern:**
  ```python
  - **{t.name}**: {t.description} (MANDATORY AGENT: `experiment_agent`)
  2. **MANDATORY PARALLELISM**: At least 3 tasks MUST have `dependencies: []`. Minimize sequential chains to enable parallel execution.
  3. **MANDATORY EXPERIMENTATION**: You MUST assign at least one task to the `experiment_agent`. Plans without code execution are REJECTED.
  4. **MANDATORY DEEP KNOWLEDGE**: You MUST assign at least 3 tasks to the `doc_reader_agent` to process full PDFs...
  ```
- **Obsolescence Rationale:** Shouting (`MANDATORY`, `MUST`, `REJECTED`) was 2024 prompt engineering designed to force weak instruction-following models to allocate agents appropriately. Modern models follow neutral system specifications and structured dependency schemas without capitalization emphasis.
- **Clean Replacement:** Clean system role definition with declarative constraint fields:
  ```markdown
  Planning Constraints:
  - Parallelism: Define at least 3 tasks with empty dependency lists.
  - Experimentation: Include empirical execution tasks delegated to experiment_agent.
  - Literature Grounding: Include document reading tasks for retrieved papers.
  ```

---

### 7. `backend/core/planning/plan_reviewer.py` (472 lines)

The automated plan review and feasibility verification module.

#### Finding 7.1: Wet-Lab Equipment Whitelist & String-Stripping Fuzzy Matcher
- **Location:** [plan_reviewer.py#L226-L250](file:///Users/samaraldico/SVEL%20AI%20Scientist/backend/core/planning/plan_reviewer.py#L226-L250)
- **Code Pattern:**
  ```python
  # HARDWARE BYPASS: List of PHYSICAL LAB EQUIPMENT only (not computational tools!)
  PHYSICAL_HARDWARE = {"pipette", "beaker", "centrifuge", "sequencer", "spectrometer", "microscope", "reagent", "lab", "physical", "equipment", "synthesizer", "cluster"}

  for task in plan.tasks:
      for tool in task.required_tools:
          tool_str = str(tool.get("name") if isinstance(tool, dict) else tool)
          # Strip versioning for matching (e.g. summarizer_v1.2 -> summarizer)
          # This handles LLMs that hallucinate versions despite mandates.
          tool_base = tool_str.split("_v")[0].split("-v")[0].strip()
          tool_clean = tool_base.lower().replace("_", "").replace("-", "").replace("tool", "").replace("database", "").strip()
  ```
- **Obsolescence Rationale:** In 2024, models frequently hallucinated physical wet-lab tools (`pipette`, `centrifuge`) or hallucinated version suffixes (`summarizer_v1.2`). Complex regex/string cleaning was built to strip version strings and filter physical lab equipment. With schema-constrained tool selection, the model is bound to an exact enum of registered tools.
- **Clean Replacement:** Constrain `required_tools` to `List[AvailableToolsEnum]`.

---

### 8. `backend/core/task_decomposer.py` (561 lines)

Decomposes complex research objectives into structured subtasks.

#### Finding 8.1: Dual Split/Rsplit Slicing & Rate Limit Staggering
- **Location:** [task_decomposer.py#L118-L141](file:///Users/samaraldico/SVEL%20AI%20Scientist/backend/core/task_decomposer.py#L118-L141)
- **Code Pattern:**
  ```python
  # [RIGOR] Precise JSON extraction
  json_str = raw_text
  if "```json" in raw_text:
      json_str = raw_text.split("```json")[1].split("```")[0]
  elif "{" in raw_text:
      json_str = "{" + raw_text.split("{", 1)[1].rsplit("}", 1)[0] + "}"

  plan_data = json.loads(json_str)
  ...
  await asyncio.sleep(2) # Stagger to avoid rate limits
  ```
- **Obsolescence Rationale:** Slicing strings using `.split("{", 1)[1].rsplit("}", 1)[0]` is unsafe if the text contains multiple curly braces in explanation prose before the JSON object. The `await asyncio.sleep(2)` artificial pause between attempts is unnecessary.
- **Clean Replacement:** Direct structured output using `SubTaskPlan` schema.

---

### 9. `backend/core/hypothesis/generator.py` (803 lines)

The hypothesis generation engine producing formal scientific hypotheses.

#### Finding 9.1: 65-Second Nuclear Cognitive Jitter Sleep & 10 Retries
- **Location:** [generator.py#L104-L111](file:///Users/samaraldico/SVEL%20AI%20Scientist/backend/core/hypothesis/generator.py#L104-L111)
- **Code Pattern:**
  ```python
  MAX_RETRIES = 10
  for attempt in range(MAX_RETRIES):
      # [TITAN V154.9] NUCLEAR COGNITIVE JITTER
      # Physically sleep 65s to ensure API gates reset.
      if attempt > 0:
          logger.info(f" [JITTER] Respecting hardware rate limits. Sleeping 65s before attempt {attempt+1}...")
          await asyncio.sleep(65.0)
  ```
- **Obsolescence Rationale:** A `65.0s` sleep across a loop of `MAX_RETRIES = 10` can stall the pipeline for up to 585 seconds (nearly 10 minutes) on transient failures. This was instituted for Tier 1 2024 TPM limits. Modern endpoints easily handle hypothesis generation queries without multi-minute cooldowns.
- **Clean Replacement:** Maximum 2 retries with an exponential backoff capped at 8 seconds.

#### Finding 9.2: Three-Pass Sequential Chain for Hypothesis Formulation
- **Location:** [generator.py#L134-L520](file:///Users/samaraldico/SVEL%20AI%20Scientist/backend/core/hypothesis/generator.py#L134-L520)
- **Code Pattern:**
  - **Turn 1 (Lines 134–279):** Semantic Brainstorming (`_call_llm_async` for unstructured prose reasoning) + `sleep(5.0)` retry loop.
  - **Turn 2 (Lines 315–395):** Skeleton Extraction (`extract_json_brute` -> `repair_json`) + `sleep(5.0)` retry loop.
  - **Turn 3 (Lines 420–515):** Prediction Hardening & Formalization + `sleep(5.0)` retry loop.
- **Obsolescence Rationale:** 2024 models lacked the reasoning capacity to simultaneously brainstorm creative scientific associations and output formal mathematical variables/equations in valid JSON in one shot. Splitting this into three separate LLM calls tripled token cost, latency, and failure probability. Late-2026 reasoning models (with native thinking tokens) natively perform the brainstorm phase in their thinking tokens before emitting the structured hypothesis schema in a single pass.
- **Clean Replacement:**
  ```python
  class FormalHypothesis(BaseModel):
      statement: str
      rationale: str
      variables: List[VariableModel]
      parameters: List[ParameterModel]
      functional_form: str
      predictions: List[PredictionModel]
      falsification_criteria: str

  class HypothesisBatch(BaseModel):
      hypotheses: List[FormalHypothesis]

  # Single-shot with reasoning/thinking enabled:
  hypotheses = await self.llm_manager.run_structured_async(
      prompt=integrated_discovery_prompt,
      response_model=HypothesisBatch,
      reasoning_effort="high"
  )
  ```

#### Finding 9.3: Brute Force JSON Extractor (`extract_json_brute`)
- **Location:** [generator.py#L33-L47](file:///Users/samaraldico/SVEL%20AI%20Scientist/backend/core/hypothesis/generator.py#L33-L47), [L284-L287](file:///Users/samaraldico/SVEL%20AI%20Scientist/backend/core/hypothesis/generator.py#L284-L287), [L771-L784](file:///Users/samaraldico/SVEL%20AI%20Scientist/backend/core/hypothesis/generator.py#L771-L784)
- **Code Pattern:**
  ```python
  def extract_json_brute(s):
      first_brace = s.find('{')
      first_bracket = s.find('[')
      start = -1
      end = -1
      if first_brace != -1 and (first_bracket == -1 or first_brace < first_bracket):
          start = first_brace
          end = s.rfind('}')
      elif first_bracket != -1:
          start = first_bracket
          end = s.rfind(']')
      if start != -1 and end != -1 and end > start:
          return s[start:end+1]
      return s
  ```
- **Obsolescence Rationale:** Brute force search for the outermost `{...}` or `[...]` delimiters. Replaced completely by structured decoding.
- **Clean Replacement:** Direct Pydantic parsing.

#### Finding 9.4: Context Truncation and Input Curly Brace Sanitization
- **Location:** [generator.py#L137-L144](file:///Users/samaraldico/SVEL%20AI%20Scientist/backend/core/hypothesis/generator.py#L137-L144)
- **Code Pattern:**
  ```python
  sliced_context = context_str[:8000]
  if len(context_str) > 8000 and '\n' in sliced_context:
      sliced_context = sliced_context.rsplit('\n', 1)[0]

  # [RIGOR FIX] TOPOLOGICAL PROMPT INJECTION DEFENSE
  safe_rq = research_question.replace('{', '(').replace('}', ')')
  safe_context = sliced_context.replace('{', '(').replace('}', ')')
  ```
- **Obsolescence Rationale:** Slicing context to 8,000 characters (~2,000 tokens) chokes the hypothesis generator, blinding it to the vast majority of retrieved literature. Replacing `{` with `(` and `}` with `)` was a workaround for python f-string formatting collisions and early LLM attention corruption on raw braces.
- **Clean Replacement:** Pass the full context string (without slicing) using template parameters rather than f-string replacements.

---

### 10. `backend/core/hypothesis/prioritizer.py` (437 lines)

Ranks and prioritizes scientific hypotheses by novelty, feasibility, impact, and testability.

#### Finding 10.1: Prompt Demanding Strict JSON Choked to max_tokens=50 with Regex Float Parser
- **Location:** [prioritizer.py#L237-L275](file:///Users/samaraldico/SVEL%20AI%20Scientist/backend/core/hypothesis/prioritizer.py#L237-L275)
- **Code Pattern:**
  ```python
  # Prompt asks for full JSON schema with justification:
  """
  OUTPUT FORMAT (strict JSON only, no prose):
  {
    "impact_score": 0.0 to 1.0,
    "breakdown": { ... },
    "justification": "One paragraph of specific, citable reasoning..."
  }
  """
  # Execution chokes generation to 50 tokens:
  result = self.llm_manager.run(
      prompt=impact_prompt,
      model=PRIORITY_SCORING_MODEL,
      temperature=0.2,
      max_tokens_override=50,
      timeout=60
  )
  text = result.get("text", "0.5").strip()
  # Extract first number found
  import re
  match = re.search(r"0?\.\d+|1\.0|0|1", text)
  if match:
      return float(match.group())
  return 0.5
  ```
- **Obsolescence Rationale:** A stark self-contradiction: the prompt explicitly instructs the LLM to output a complete JSON dictionary containing `impact_score`, `breakdown`, and a paragraph of `justification`, but the call passes `max_tokens_override=50`. Because 50 tokens cuts off the response mid-JSON, the author gave up on parsing JSON altogether and used `re.search(r"0?\.\d+|1\.0|0|1", text)` to grab the first floating-point number.
- **Clean Replacement:** Use a structured output schema with adequate token allowance:
  ```python
  class ImpactAssessment(BaseModel):
      impact_score: float = Field(ge=0.0, le=1.0)
      novelty_depth: float
      domain_implications: float
      justification: str

  assessment = self.llm_manager.run_structured(prompt, response_model=ImpactAssessment)
  return assessment.impact_score
  ```

#### Finding 10.2: Keyword-Based Scientific Estimation Heuristics
- **Location:** [prioritizer.py#L281-L297](file:///Users/samaraldico/SVEL%20AI%20Scientist/backend/core/hypothesis/prioritizer.py#L281-L297), [L361-L383](file:///Users/samaraldico/SVEL%20AI%20Scientist/backend/core/hypothesis/prioritizer.py#L361-L383)
- **Code Pattern:**
  ```python
  # Line 287-295:
  if any(term in statement for term in ["novel", "first", "breakthrough", "paradigm"]):
      score += 0.2
  if any(term in statement for term in ["incremental", "minor", "specific case"]):
      score -= 0.1

  # Line 361-366:
  if "simple" in statement or "quick" in statement:
      hours *= 0.5
  if "complex" in statement or "extensive" in statement:
      hours *= 2
  if "ml" in hypothesis.domain or "training" in statement:
      hours *= 3

  # Line 374-383:
  if "model" in statement or "accuracy" in statement:
      return "ml_experiment"
  if "data" in statement or "analysis" in statement:
      return "data_analysis"
  ```
- **Obsolescence Rationale:** Estimating experiment duration and classifying experiment types by checking for the words `"quick"`, `"complex"`, `"simple"`, or `"model"` in the hypothesis text is a primitive 2024 heuristic that rewards superficial buzzword usage.
- **Clean Replacement:** Perform semantic categorization using structured LLM evaluation with reasoning or pass the hypothesis to the experiment agent for an execution plan estimate.

---

## Priority 3: LLM Interface & Messaging Layer

### 11. `backend/llm_manager.py` (496 lines)

The central LLM interface wrapper across Anthropic, OpenAI, and Gemini.

#### Finding 11.1: Universal Hardcoded max_tokens=4000 Ceiling
- **Location:** [llm_manager.py#L303](file:///Users/samaraldico/SVEL%20AI%20Scientist/backend/llm_manager.py#L303), [L321](file:///Users/samaraldico/SVEL%20AI%20Scientist/backend/llm_manager.py#L321), [L340](file:///Users/samaraldico/SVEL%20AI%20Scientist/backend/llm_manager.py#L340)
- **Code Pattern:**
  ```python
  def _call_anthropic(prompt: str, max_tokens: int = 4000, ...)
  def _call_openai(prompt: str, model: str = None, max_tokens: int = 4000, ...)
  def _call_gemini(prompt: str, max_tokens: int = 4000, ...)
  ```
- **Obsolescence Rationale:** 4,000 tokens was the output limit for GPT-4 and Claude 3. Setting this as the default parameter across all callers artificially truncates modern models (which support 64k to 128k output tokens) during code generation, literature reviews, and discovery reports.
- **Clean Replacement:** Set defaults according to task needs (e.g. `max_tokens: int = 16384` or `32768` for code and reports, or omit to allow provider defaults).

#### Finding 11.2: Excessive Tenacity Retry Loop (5 Attempts with 60s Backoff)
- **Location:** [llm_manager.py#L302](file:///Users/samaraldico/SVEL%20AI%20Scientist/backend/llm_manager.py#L302), [L320](file:///Users/samaraldico/SVEL%20AI%20Scientist/backend/llm_manager.py#L320), [L339](file:///Users/samaraldico/SVEL%20AI%20Scientist/backend/llm_manager.py#L339)
- **Code Pattern:**
  ```python
  @retry(wait=wait_exponential(multiplier=1, min=2, max=60), stop=stop_after_attempt(5), retry=retry_if_not_exception_type(AttributeError))
  def _call_anthropic(...)
  ```
- **Obsolescence Rationale:** Retrying 5 times with exponential backoff up to 60 seconds each means a single failed or malformed call can block a worker thread for 3–5 minutes. Modern SDKs possess built-in connection management; 2 retries with maximum 10s backoff is standard.
- **Clean Replacement:** Limit retries to 2 attempts with `stop=stop_after_attempt(2), wait=wait_exponential(min=1, max=10)`.

#### Finding 11.3: Token Bucket Capacity Polling with time.sleep(0.1)
- **Location:** [llm_manager.py#L54-L70](file:///Users/samaraldico/SVEL%20AI%20Scientist/backend/llm_manager.py#L54-L70)
- **Code Pattern:**
  ```python
  def _acquire_capacity(provider: str, token_estimate: int, priority: int = 10, timeout: int = 600):
      ...
      while True:
          status, reason = scheduler.acquire_non_blocking(provider, token_estimate, context)
          if status.value == "granted":
              return True
          if time.time() - start_time > timeout:
              return False
          time.sleep(0.1)
  ```
- **Obsolescence Rationale:** Blocking synchronization via `time.sleep(0.1)` in a busy loop inside an asynchronous application causes thread contention and latency spikes. Modern tier-5 accounts with tens of millions of TPM do not need artificial client token-bucketing.
- **Clean Replacement:** Use an asynchronous semaphore or async condition variable (`asyncio.Semaphore`), or eliminate local capacity gating entirely.

---

### 12. `backend/utils/json_repair.py` (128 lines)

The universal JSON extraction and repair utility imported across the entire codebase.

#### Finding 12.1: The Archetypal 2024 Regex JSON Surgery Kernel
- **Location:** [json_repair.py#L1-L128](file:///Users/samaraldico/SVEL%20AI%20Scientist/backend/utils/json_repair.py#L1-L128)
- **Code Pattern:**
  ```python
  def repair_json(json_str: str) -> any:
      # 1. Replace Unicode Pi
      json_str = json_str.replace("Π", "3.14159").replace("M-^@", "3.14159")
      # 2. Backslash escape scanner for LaTeX (\lambda, \nabla)
      ...
      # 3. Markdown regex hunter
      block_match = re.search(r'```(?:json)?\s*(.*?)\s*```', json_str, re.DOTALL | re.IGNORECASE)
      ...
      # 4. O(N^2) brace counting loop finding every JSON object
      def find_objects(s, start_char='{', end_char='}'): ...
      objs = find_objects(json_str, '{', '}') + find_objects(json_str, '[', ']')
      # 5. Aggressive truncated JSON recovery (appending '}' and ']')
      for _ in range(10):
          if open_brackets > close_brackets:
              repaired += ']' * (open_brackets - close_brackets)
          if open_braces > close_braces:
              repaired += '}' * (open_braces - close_braces)
  ```
- **Obsolescence Rationale:** This entire 128-line utility is a monument to 2024-era LLM unreliability. It manually balances braces, escapes LaTeX backslashes, cuts at arbitrary comma boundaries, and appends trailing brackets in a loop. With native constrained decoding, models emit 100% valid JSON conforming to strict schemas.
- **Clean Replacement:** Deprecate and remove `repair_json.py`. Use native SDK structured output validation (`response_format=PydanticModel`).

---

### 13. `backend/core/events/event_bus.py` & `backend/core/message_bus.py`
- **Location:** [message_bus.py#L56](file:///Users/samaraldico/SVEL%20AI%20Scientist/backend/core/message_bus.py#L56), [L128-L143](file:///Users/samaraldico/SVEL%20AI%20Scientist/backend/core/message_bus.py#L128-L143)
- **Findings:**
  - `MessageType.FALLBACK_TRIGGERED`: Telemetry designed to track how often models failed and needed rescue.
  - Dead Redis listener stubs with manual `json.loads` catching.
  - Core event infrastructure is clean, decoupled pub/sub; workarounds in other modules should emit typed events rather than fallback notifications.

---

## Priority 4: Agent Layer (All 13 Agents)

### 14. `backend/agents/data_analyzer_agent.py` (464 lines)

#### Finding 14.1: Keyword Matching for Schema Switching & Canned Fallback Interpretation
- **Location:** [data_analyzer_agent.py#L351-L359](file:///Users/samaraldico/SVEL%20AI%20Scientist/backend/agents/data_analyzer_agent.py#L351-L359), [L404-L405](file:///Users/samaraldico/SVEL%20AI%20Scientist/backend/agents/data_analyzer_agent.py#L404-L405), [L441-L455](file:///Users/samaraldico/SVEL%20AI%20Scientist/backend/agents/data_analyzer_agent.py#L441-L455)
- **Code Pattern:**
  ```python
  # Keyword-based domain branching:
  is_ml = any(x in session_id or x in hypothesis.lower() for x in [
      "nas", "cifar", "mnist", "imagenet", "vit", "attention", "prun", "entropy",
      "ml", "neural", "deep learning", "classifier", "flops", "params", ...
  ])
  relevance_field = '"model_implications": "..."' if is_ml else '"biological_relevance": "..."'

  # Regex JSON stripping:
  if "```json" in raw: raw = raw.split("```json")[1].split("```")[0].strip()
  data = json.loads(raw)

  # Canned Fallback Plan:
  def _create_fallback(self, audit: Dict, tests: List[StatisticalTestResult]) -> ResultInterpretation:
      return ResultInterpretation(
          experiment_id=f"fallback_{uuid.uuid4().hex[:8]}",
          summary="Automated audit completed. Basic statistical correlations detected. Neural synthesis unavailable.",
          statistical_significance="Unverified.",
          ...
      )
  ```
- **Obsolescence Rationale:** Hardcoded substring matching on `"cifar"`, `"mnist"`, `"nas"` to switch JSON schema fields is crude; modern structured models can provide both biological and computational implications in a polymorphic schema. Slicing with `raw.split("```json")` and falling back to canned dummy text degrades the analysis audit trail.
- **Clean Replacement:** Use a unified `ResultInterpretation` Pydantic model with structured outputs.

---

### 15. `backend/agents/doc_reader_agent.py` (180 lines)

#### Finding 15.1: Context Choke to 25k Chars, Regex Fence Search, and Exponential Sleep
- **Location:** [doc_reader_agent.py#L45](file:///Users/samaraldico/SVEL%20AI%20Scientist/backend/agents/doc_reader_agent.py#L45), [L87-L101](file:///Users/samaraldico/SVEL%20AI%20Scientist/backend/agents/doc_reader_agent.py#L87-L101), [L121](file:///Users/samaraldico/SVEL%20AI%20Scientist/backend/agents/doc_reader_agent.py#L121), [L167](file:///Users/samaraldico/SVEL%20AI%20Scientist/backend/agents/doc_reader_agent.py#L167)
- **Code Pattern:**
  ```python
  MAX_DOC_CHARS = int(os.getenv("DOC_READER_MAX_CHARS", "25000"))
  ...
  prompt_text = f"{_PROMPT_TXT}\n{goal_block}\nRESEARCH QUERY: {query}\n\nDOCUMENT CONTEXT:\n{doc_text[:MAX_DOC_CHARS]}"
  ...
  code_block_pattern = r"```(?:json)?\s*(\{.*?\})\s*```"
  match = re.search(code_block_pattern, text, re.DOTALL)
  ...
  start = text.find("{")
  end = text.rfind("}")
  ...
  await asyncio.sleep(attempt * 2)
  ```
- **Obsolescence Rationale:** A document reader capping input at 25,000 characters (~6,000 tokens) cuts off scientific papers after Section 2, discarding experimental tables, supplementary methods, and discussion.
- **Clean Replacement:** Remove `MAX_DOC_CHARS` truncation; pass full multi-page PDF extracted text (up to 200k+ tokens) directly into modern large-context models with structured extraction schemas.

---

### 16. `backend/agents/experiment_agent.py` (2,201 lines)

The flagship experimentation agent generating, debugging, and running Python empirical code.

#### Finding 16.1: The Igor Audit — Literal Keyword Checks on Generated Code
- **Location:** [experiment_agent.py#L224-L252](file:///Users/samaraldico/SVEL%20AI%20Scientist/backend/agents/experiment_agent.py#L224-L252)
- **Code Pattern:**
  ```python
  def _audit_code_igor(self, code: str, data_paths: Dict[str, str]) -> Tuple[bool, str]:
      code_lower = code.lower()
      
      # 1. Visualization Purity
      if "plt.plot" in code_lower and "plt.subplots" not in code_lower and "make_subplots" not in code_lower:
          return False, "Generic single-panel plot detected. Use multi-panel subplots..."
          
      # 2. Advanced Statistical Check
      advanced_stat_libs = ["statsmodels", "scipy.optimize", "imblearn", "sklearn", "torch", "torch.nn", "torch.optim"]
      if not any(lib in code_lower for lib in advanced_stat_libs):
          return False, "No advanced libraries detected (statsmodels, sklearn, torch)..."

      # 3. Robustness Gate: Literal string presence check!
      robustness_terms = ["bootstrap", "resample", "durbin", "firth", "penalized", "cross_val", "kfold", "mcc"]
      if not any(term in code_lower for term in robustness_terms):
          return False, "No robustness or temporal checks detected. Your code MUST include Bootstrapping, Cross-Validation..."

      # 4. Statistical Rigor Check
      stat_terms = ["p_value", "p-value", "significance", "confidence_interval", "likelihood", "mcc", "wald", "auc"]
      if not any(term in code_lower for term in stat_terms):
          return False, "Lack of formal statistical significance testing. No p-values or confidence intervals found..."
  ```
- **Obsolescence Rationale:** This is the most glaring example of Category 6 (Keyword validation hacks). Checking whether the literal string `"bootstrap"` or `"p_value"` appears in Python source code incentivizes the model to add dummy comments like `# bootstrap p_value` to bypass the gate without actually performing rigorous statistics. It rejects valid, innovative code that calculates exact permutations, Bayes factors, or custom Monte Carlo methods.
- **Clean Replacement:** Execute the code in an isolated sandbox and validate empirical outputs semantically via structured JSON execution artifacts (evaluating computed confidence intervals and standard errors), rather than checking string tokens in the source code.

#### Finding 16.2: Artificial 30-Second Pauses & Nested 5-Retry Loop on Mock Responses
- **Location:** [experiment_agent.py#L842-L860](file:///Users/samaraldico/SVEL%20AI%20Scientist/backend/agents/experiment_agent.py#L842-L860), [L886-L890](file:///Users/samaraldico/SVEL%20AI%20Scientist/backend/agents/experiment_agent.py#L886-L890)
- **Code Pattern:**
  ```python
  if current_code and "MOCK_RESPONSE" in current_code:
      logger.warning(" [LLM_SAFETY] Detected MOCK_RESPONSE (API Exhausted). Pausing simulation for 30s...")
      await asyncio.sleep(30.0)
      design_retries = 0
      while "MOCK_RESPONSE" in current_code and design_retries < 5:
          design_retries += 1
          logger.info(f" [LLM_SAFETY] LLM unavailable. Retry {design_retries}/5 in 30s...")
          await asyncio.sleep(30.0)
          current_code = await self.design_experiment(hypothesis, experiment_id, task_description=task_desc)
  ```
- **Obsolescence Rationale:** A 5-retry `while` loop with 30-second sleeps between retries (`5 * 30s = 150 seconds` = 2.5 minutes of complete thread stall) when an API mock response is detected.
- **Clean Replacement:** Remove mock response fallback loops. Fail fast with an explicit API error or rely on standard client-level backoff.

#### Finding 16.3: Balanced Brace Parser and Subprocess JSON Extraction
- **Location:** [experiment_agent.py#L55-L80](file:///Users/samaraldico/SVEL%20AI%20Scientist/backend/agents/experiment_agent.py#L55-L80), [L1716-L1730](file:///Users/samaraldico/SVEL%20AI%20Scientist/backend/agents/experiment_agent.py#L1716-L1730), [L2178](file:///Users/samaraldico/SVEL%20AI%20Scientist/backend/agents/experiment_agent.py#L2178)
- **Code Pattern:**
  ```python
  def extract_json_balanced(text: str) -> str:
      start_idx = text.find('{')
      ...
      for i in range(start_idx, len(text)):
          ... # manual state machine tracking in_string, escape, brace_count
  ```
- **Obsolescence Rationale:** Custom 30-line brace tracking state machine. For LLM responses, structured outputs make this obsolete; for sandbox execution results, python code should write output directly to a designated JSON artifact file (`results.json`) rather than printing to stdout where it must be extracted with regex.
- **Clean Replacement:** Have the generated experiment script write results directly to an execution output JSON file read via `json.load()`.

#### Finding 16.4: Verbose Shouting Directives in System Prompts
- **Location:** [experiment_agent.py#L823](file:///Users/samaraldico/SVEL%20AI%20Scientist/backend/agents/experiment_agent.py#L823), [L1201](file:///Users/samaraldico/SVEL%20AI%20Scientist/backend/agents/experiment_agent.py#L1201), [L1224](file:///Users/samaraldico/SVEL%20AI%20Scientist/backend/agents/experiment_agent.py#L1224), [L1235](file:///Users/samaraldico/SVEL%20AI%20Scientist/backend/agents/experiment_agent.py#L1235)
- **Code Pattern:**
  ```python
  MANDATORY FIX: You MUST use the REAL data variables injected at the top of the script:
  DO NOT use np.random.rand() or create sample data. Load the REAL data.
  [TITAN BLUEPRINT - MANDATORY STRUCTURE]
  3. **MANDATORY RENDERING**: You MUST physically render a PNG figure to os.path.join(RESULTS_DIR, 'viz.png')
  ### CORRECT data loading (MANDATORY):
  ```
- **Obsolescence Rationale:** Excessive use of shouting words (`MANDATORY`, `MUST`, `CORRECT`, `DO NOT`) in 2024 to prevent models from generating synthetic dummy data. Modern coding models follow execution protocols and script contracts when provided clear execution environments.
- **Clean Replacement:** Specify explicit interface requirements in calm, declarative developer prompts.

---

### 17. `backend/agents/fact_checker_agent.py` (147 lines)

#### Finding 17.1: Slicing Evidence to 12k Chars and Preamble-Banning Directives
- **Location:** [fact_checker_agent.py#L27](file:///Users/samaraldico/SVEL%20AI%20Scientist/backend/agents/fact_checker_agent.py#L27), [L36](file:///Users/samaraldico/SVEL%20AI%20Scientist/backend/agents/fact_checker_agent.py#L36), [L89](file:///Users/samaraldico/SVEL%20AI%20Scientist/backend/agents/fact_checker_agent.py#L89), [L107-L110](file:///Users/samaraldico/SVEL%20AI%20Scientist/backend/agents/fact_checker_agent.py#L107-L110)
- **Code Pattern:**
  ```python
  MAX_CONTEXT_CHARS = 12000
  ...
  3. MACHINE OUTPUT ONLY: Return strictly a valid JSON object. Do not wrap the JSON in markdown formatting (no ```json). Do not output any preamble or conversational text.
  ...
  prompt_text = _PROMPT_TXT + f"\n\nClaim:\n{claim}\n\nEvidence/Context:\n{str(evidence)[:MAX_CONTEXT_CHARS]}"
  ...
  start = resp_text.find("{")
  end = resp_text.rfind("}")
  data = json.loads(resp_text[start:end+1])
  ```
- **Obsolescence Rationale:** The prompt desperately begs the model: *"MACHINE OUTPUT ONLY: Return strictly a valid JSON object. Do not wrap the JSON in markdown formatting (no ```json). Do not output any preamble"*. Despite this shouting, lines 107-110 still have to call `find("{")` and `rfind("}")`. Evidence is truncated to 12,000 chars.
- **Clean Replacement:**
  ```python
  class FactCheckVerdict(BaseModel):
      verdict: Literal["VERIFIED", "CONTRADICTED", "UNSUPPORTED", "PARTIAL"]
      confidence: float
      logical_analysis: str
      evidence_extracted: List[str]
      corrected_claim: Optional[str]

  verdict = await self.llm_manager.run_structured_async(prompt, response_model=FactCheckVerdict)
  ```

---

### 18. `backend/agents/ml_model_builder_agent.py` (715 lines)

#### Finding 18.1: JSON Brace Slicing with Fallback to Raw Code
- **Location:** [ml_model_builder_agent.py#L57-L92](file:///Users/samaraldico/SVEL%20AI%20Scientist/backend/agents/ml_model_builder_agent.py#L57-L92), [L607-L635](file:///Users/samaraldico/SVEL%20AI%20Scientist/backend/agents/ml_model_builder_agent.py#L607-L635)
- **Code Pattern:**
  ```python
  # Shouting prompt:
  MANDATORY CODE REQUIREMENTS
  2. CATEGORICAL DATA: YOU MUST ENCODE STRING/OBJECT COLUMNS!
  NEVER pass raw strings to a Neural Network or Model directly (TypeError risk).

  # Parsing:
  start = text.find("{")
  end = text.rfind("}") + 1
  if start != -1 and end > start:
      data = json.loads(text[start:end])
  ...
  # Fallback: treat entire response as code
  logger.warning("Could not parse JSON, treating response as raw code")
  return {"code": text, ...}
  ```
- **Obsolescence Rationale:** Prompt contains all-caps panic directives to avoid string passing into neural nets. If JSON parsing fails, the agent treats arbitrary conversational output as Python code.
- **Clean Replacement:** Structured Pydantic output separating code, description, and hyperparameters into guaranteed schema fields.

---

### 19. `backend/agents/protocol_validator.py` (127 lines)

#### Finding 19.1: DotAll Regex Parsing and Hardcoded Sleep Retries
- **Location:** [protocol_validator.py#L93-L116](file:///Users/samaraldico/SVEL%20AI%20Scientist/backend/agents/protocol_validator.py#L93-L116)
- **Code Pattern:**
  ```python
  match = re.search(r"\{.*\}", text, re.S)
  if match:
      data = json.loads(match.group(0))
  else:
      if attempt == 0:
          logger.warning("No JSON found in validator response, retrying...")
          await asyncio.sleep(5)
          continue
      return PlanReview(plan.id, False, 0.0, "Validator failed to produce structured JSON.")
  ```
- **Obsolescence Rationale:** Uses regex `re.search(r"\{.*\}", text, re.S)` and sleeps for 5 seconds if the model returns non-JSON text, rejecting valid plans on format failure.
- **Clean Replacement:** Structured outputs with `PlanReview` model.

---

### 20. `backend/agents/qa_agent.py` (492 lines)

#### Finding 20.1: Context Slicing to 1000 Chars and Output Choke to 1500 Tokens
- **Location:** [qa_agent.py#L411](file:///Users/samaraldico/SVEL%20AI%20Scientist/backend/agents/qa_agent.py#L411), [L429](file:///Users/samaraldico/SVEL%20AI%20Scientist/backend/agents/qa_agent.py#L429)
- **Code Pattern:**
  ```python
  raw_answer = await asyncio.wait_for(self.llm.generate(prompt, max_tokens=1500), timeout=LLM_TIMEOUT + 5)
  ...
  self._memory[session_id].append({"q": question, "answer": raw_answer[:1000], "ts": time.time()})
  ```
- **Obsolescence Rationale:** Limiting output to 1,500 tokens and slicing session memory answers to 1,000 characters (~250 words) destroys continuity in multi-turn scientific QA sessions.
- **Clean Replacement:** Store full answers in memory and let modern 1M context windows maintain conversational context.

---

### 21. `backend/agents/red_team_agent.py` (760 lines)

The adversarial critique node inspecting claims, methodologies, and findings.

#### Finding 21.1: Ubiquitous Balanced Brace Extractor Calls & Evidence Slicing
- **Location:** [red_team_agent.py#L12-L45](file:///Users/samaraldico/SVEL%20AI%20Scientist/backend/agents/red_team_agent.py#L12-L45), [L118](file:///Users/samaraldico/SVEL%20AI%20Scientist/backend/agents/red_team_agent.py#L118), [L177](file:///Users/samaraldico/SVEL%20AI%20Scientist/backend/agents/red_team_agent.py#L177), [L245](file:///Users/samaraldico/SVEL%20AI%20Scientist/backend/agents/red_team_agent.py#L245), [L296](file:///Users/samaraldico/SVEL%20AI%20Scientist/backend/agents/red_team_agent.py#L296), [L362](file:///Users/samaraldico/SVEL%20AI%20Scientist/backend/agents/red_team_agent.py#L362), [L383](file:///Users/samaraldico/SVEL%20AI%20Scientist/backend/agents/red_team_agent.py#L383), [L607](file:///Users/samaraldico/SVEL%20AI%20Scientist/backend/agents/red_team_agent.py#L607), [L686](file:///Users/samaraldico/SVEL%20AI%20Scientist/backend/agents/red_team_agent.py#L686), [L706](file:///Users/samaraldico/SVEL%20AI%20Scientist/backend/agents/red_team_agent.py#L706)
- **Code Pattern:**
  ```python
  # Red team calls extract_json_balanced across 7 distinct critique methods:
  json_str = extract_json_balanced(response)
  response = json_repair.repair_json(response, return_objects=True)

  # Aggressive context slicing across all critique methods:
  {evidence[:15000]}
  {cited_abstract[:3000]}
  EVIDENCE: {evidence[:5000] if evidence else "No evidence provided"}
  ```
- **Obsolescence Rationale:** The red team agent relies on `extract_json_balanced` in 7 separate places and slices critique evidence to 3,000–5,000 characters. Slicing evidence prevents the adversarial agent from detecting subtle errors or fraud hidden deep in the experimental logs.
- **Clean Replacement:** Use native structured outputs for `CritiqueVerdict` across all red-team methods and feed complete evidence datasets into the prompt.

---

### 22. `backend/agents/report_composer.py` (2,209 lines)

The comprehensive report and scientific manuscript generator.

#### Finding 22.1: Regex Citation Parsing, Mermaid Fence Stripping, and Exponential Sleep
- **Location:** [report_composer.py#L773](file:///Users/samaraldico/SVEL%20AI%20Scientist/backend/agents/report_composer.py#L773), [L1034](file:///Users/samaraldico/SVEL%20AI%20Scientist/backend/agents/report_composer.py#L1034), [L1289](file:///Users/samaraldico/SVEL%20AI%20Scientist/backend/agents/report_composer.py#L1289), [L1309](file:///Users/samaraldico/SVEL%20AI%20Scientist/backend/agents/report_composer.py#L1309), [L1399-L1402](file:///Users/samaraldico/SVEL%20AI%20Scientist/backend/agents/report_composer.py#L1399-L1402), [L2112](file:///Users/samaraldico/SVEL%20AI%20Scientist/backend/agents/report_composer.py#L2112)
- **Code Pattern:**
  ```python
  # Kroki exponential sleep:
  await asyncio.sleep(2 ** attempt)  # 1s, 2s, 4s

  # Context truncation:
  context_text += f"Content: {str(item.get('content', ''))[:2500]}\n"

  # Regex stripping:
  found_cites = re.findall(r'\[([A-Za-z\s]+,?\s*\d{4})\]', content)
  content = content.replace("```html", "").replace("```", "")
  content = re.sub(rf'^\s*(<h[1-6]>)?\s*{title_clean}\s*(</h[1-6]>)?\s*', '', content, flags=re.IGNORECASE)
  return re.findall(r'```mermaid\s+(.*?)\s+```', text, re.DOTALL)
  ```
- **Obsolescence Rationale:** The report composer uses regex post-processing to strip markdown backticks, clean HTML header duplicates injected by LLMs, and parse citation brackets. Item content is truncated to 2,500 characters.
- **Clean Replacement:** Native Markdown/HTML section generation using structured multi-field manuscript schemas where title, body, and citations are isolated fields.

---

### 23. `backend/agents/research_agent.py` (393 lines)

#### Finding 23.1: Video Transcript & Description Hardcoded Slicing
- **Location:** [research_agent.py#L352-L354](file:///Users/samaraldico/SVEL%20AI%20Scientist/backend/agents/research_agent.py#L352-L354)
- **Code Pattern:**
  ```python
  context_str += f"Description: {video_info.get('description', '')[:500]}...\n"
  if video_info.get("transcript"):
      context_str += f"Transcript Summary:\n{video_info.get('transcript')[:10000]}...\n"
  ```
- **Obsolescence Rationale:** Video transcripts are capped at 10,000 characters (~2,500 tokens). A 45-minute technical seminar transcript contains 10,000+ words (40,000+ characters). Slicing drops 75% of the scientific content.
- **Clean Replacement:** Ingest the full transcript; modern multimodal models process hours of audio/video and transcripts without truncation.

---

### 24. `backend/agents/summarizer_agent.py` (376 lines)

#### Finding 24.1: Regex Code Block Matching, Artificial Backoff Sleep, and Canned Fallback Markdown
- **Location:** [summarizer_agent.py#L108-L126](file:///Users/samaraldico/SVEL%20AI%20Scientist/backend/agents/summarizer_agent.py#L108-L126), [L252](file:///Users/samaraldico/SVEL%20AI%20Scientist/backend/agents/summarizer_agent.py#L252), [L270-L289](file:///Users/samaraldico/SVEL%20AI%20Scientist/backend/agents/summarizer_agent.py#L270-L289), [L357-L375](file:///Users/samaraldico/SVEL%20AI%20Scientist/backend/agents/summarizer_agent.py#L357-L375)
- **Code Pattern:**
  ```python
  code_block_pattern = r"```(?:json)?\s*(\{.*?\})\s*```"
  match = re.search(code_block_pattern, text, re.DOTALL)
  ...
  start = text.find("{")
  end = text.rfind("}")
  ...
  await asyncio.sleep(1 + attempt)
  ...
  # Canned Markdown Fallback:
  fallback_md = _fallback_markdown(query, components, raw_text=content)
  def _fallback_markdown(query: str, components: List[Dict[str, Any]], raw_text: Optional[str] = None) -> str:
      # Generates synthetic markdown stitching component titles together
  ```
- **Obsolescence Rationale:** Triple combination of regex codeblock extraction, artificial sleep on retry, and canned fallback markdown generation if the model output fails JSON parsing.
- **Clean Replacement:** Structured output with `SummaryModel` schema; remove `_fallback_markdown` dummy generator.

---

### 25. `backend/agents/web_search_agent.py` (426 lines)

#### Finding 25.1: 100-Token Query Reformulation Choke
- **Location:** [web_search_agent.py#L269](file:///Users/samaraldico/SVEL%20AI%20Scientist/backend/agents/web_search_agent.py#L269), [L279](file:///Users/samaraldico/SVEL%20AI%20Scientist/backend/agents/web_search_agent.py#L279)
- **Code Pattern:**
  ```python
  refined = await run_llm_async(
      prompt,
      model=WEB_QUERY_FORMULATION_MODEL,
      max_tokens=100,
      temperature=0.3
  )
  ```
- **Obsolescence Rationale:** Hard-capping search query reformulation to 100 tokens prevents the model from generating nuanced Boolean search strings or multiple alternative keywords for complex chemical or biological queries.
- **Clean Replacement:** Allow adequate tokens (`max_tokens=1024`) and output a structured list of query variations: `List[SearchQuery]`.

---

### 26. `backend/agents/writer_agent.py` (1,182 lines)

The section authoring agent synthesizing research findings into publication-grade prose.

#### Finding 26.1: Component Truncation to 4k Chars and Threatening Shouting Directives
- **Location:** [writer_agent.py#L216-L237](file:///Users/samaraldico/SVEL%20AI%20Scientist/backend/agents/writer_agent.py#L216-L237), [L407](file:///Users/samaraldico/SVEL%20AI%20Scientist/backend/agents/writer_agent.py#L407), [L772](file:///Users/samaraldico/SVEL%20AI%20Scientist/backend/agents/writer_agent.py#L772)
- **Code Pattern:**
  ```python
  # Component Slicing:
  result_text = result_text[:4000]  # Allow more context per component

  # Threatening Directives:
  6. CLAIM REGISTRY (MANDATORY):
     - You MUST output a JSON block BEFORE your text.
     - Constraint: Uncited assertions are hallucinations.
  7. MISSING DATA PROTOCOL:
     - NEVER apologize for missing data or temporal limitations
     - INVALID: "I'm sorry, I cannot provide 2025 data."
     - Be ASSERTIVE with hedged claims, not APOLOGETIC
  8. STRUCTURAL RIGOR (MANDATORY):
  2. MANDATORY CITATION PROTOCOL:
  ```
- **Obsolescence Rationale:**
  - Input component texts are capped at 4,000 characters, discarding 80% of experimental results, table dumps, and metric distributions passed from earlier stages.
  - The system prompt threatens the model with capital letters (`MANDATORY`, `NEVER`, `INVALID`, `ASSERTIVE`, `NOT APOLOGETIC`). In 2024, models like GPT-4 would apologize ("As of my knowledge cutoff in 2023..."). 2026 frontier models maintain appropriate academic register when given neutral style instructions.
- **Clean Replacement:** Remove the 4,000 character component slice. Replace shouting rules with calibrated academic style guidelines and structured claim registries.

---

## Comprehensive Workaround Matrix

| File Path | Regex JSON Parsing | Canned Rescue Plans | Context Truncation | Artificial Sleeps | Threatening Prompts | Keyword Validation | Excessive Retries | Multi-Step Chains |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| `orchestration/deep_research_orchestrator.py` | **Yes** (L3482) | **Yes** (L2617) | **Yes** (L1806, L3266) | **Yes** (L1636, L4740) | No | **Yes** (L2445, L2852) | No | No |
| `orchestration/singularity.py` | **Yes** (L118, L309) | **Yes** (L336) | No | No | No | No | No | No |
| `orchestration/overmind.py` | **Yes** (L278) | **Yes** (L283) | No | No | No | No | No | No |
| `orchestration/swarm_manager.py` | **Yes** (L76) | **Yes** (L268) | **Yes** (L46) | **Yes** (L288) | No | **Yes** (L89) | No | No |
| `central_router_beast.py` | **Yes** (L308) | **Yes** (L312) | No | No | No | No | No | No |
| `core/planning/plan_creator.py` | **Yes** (L815) | **Yes** (L321) | **Yes** (L343) | **Yes** (L335, L874) | **Yes** (L681) | No | **Yes** (L871) | No |
| `core/planning/plan_reviewer.py` | No | **Yes** (L116) | No | No | No | **Yes** (L231, L248) | No | No |
| `core/task_decomposer.py` | **Yes** (L119, L254) | No | No | **Yes** (L141) | No | No | No | No |
| `core/hypothesis/generator.py` | **Yes** (L33, L284) | No | **Yes** (L137) | **Yes** (L110, L271) | **Yes** (L330) | No | **Yes** (L104) | **Yes** (L134-520) |
| `core/hypothesis/prioritizer.py` | **Yes** (L272) | **Yes** (L281) | **Yes** (L265) | No | No | **Yes** (L287, L361) | No | No |
| `llm_manager.py` | No | **Yes** (L87-108) | **Yes** (L303, L321) | **Yes** (L68) | No | No | **Yes** (L302) | No |
| `core/events/event_bus.py` | No | No | No | No | No | No | No | No |
| `core/message_bus.py` | **Yes** (L135) | No | No | No | No | No | No | No |
| `utils/json_repair.py` | **Yes** (L1-128) | **Yes** (L127) | No | No | No | No | No | No |
| `agents/data_analyzer_agent.py` | **Yes** (L404) | **Yes** (L441) | **Yes** (L348) | No | No | **Yes** (L352) | No | No |
| `agents/doc_reader_agent.py` | **Yes** (L87) | **Yes** (L171) | **Yes** (L121) | **Yes** (L167) | No | No | No | No |
| `agents/experiment_agent.py` | **Yes** (L55, L1716) | **Yes** (L2158) | No | **Yes** (L845, L888) | **Yes** (L823, L1201) | **Yes** (L225-245) | **Yes** (L851) | No |
| `agents/fact_checker_agent.py` | **Yes** (L107) | **Yes** (L138) | **Yes** (L89) | No | **Yes** (L36) | No | No | No |
| `agents/ml_model_builder_agent.py` | **Yes** (L607) | **Yes** (L630) | No | No | **Yes** (L57, L92) | No | No | No |
| `agents/protocol_validator.py` | **Yes** (L93) | **Yes** (L111) | No | **Yes** (L106, L116) | No | No | No | No |
| `agents/qa_agent.py` | No | **Yes** (L413) | **Yes** (L411, L429) | No | No | No | No | No |
| `agents/red_team_agent.py` | **Yes** (L12, L177) | **Yes** (L299) | **Yes** (L118, L362) | No | No | No | No | No |
| `agents/report_composer.py` | **Yes** (L1309, L2112) | **Yes** (L2189) | **Yes** (L1034, L1355) | **Yes** (L773) | **Yes** (L993, L1184) | No | No | No |
| `agents/research_agent.py` | No | No | **Yes** (L352-354) | No | No | No | No | No |
| `agents/summarizer_agent.py` | **Yes** (L108) | **Yes** (L270) | **Yes** (L364) | **Yes** (L252, L273) | No | No | No | No |
| `agents/web_search_agent.py` | No | No | **Yes** (L269, L279) | No | No | No | No | No |
| `agents/writer_agent.py` | **Yes** (L601) | No | **Yes** (L407, L577) | No | **Yes** (L216, L772) | **Yes** (L532) | No | No |

---

## Target Refactoring Roadmap

To transition the SVEL AI Scientist orchestration layer to late-2026 frontier standards, execute the following three-phase refactoring plan:

### Phase 1: LLM Interface & Schema Foundation (Immediate)
1. **Pydantic Structured Output Layer**:
   - Add `run_structured(prompt, response_model: Type[BaseModel])` and `run_structured_async` to `llm_manager.py` leveraging native provider structured outputs (`response_format` with strict schema validation).
   - Deprecate `backend/utils/json_repair.py`. Replace all imports of `repair_json` and `extract_json_balanced` across the 26 files with native Pydantic models.
2. **Token Limit Modernization**:
   - Increase default `max_tokens` across provider wrappers from `4000` to `16384` (or omit for provider defaults).
   - Remove token choke limits in `prioritizer.py` (`max_tokens=50`), `qa_agent.py` (`max_tokens=1500`), and `web_search_agent.py` (`max_tokens=100`).
3. **Retry Loop Calibration**:
   - Reduce `@retry` on provider calls from 5 attempts to 2 attempts.
   - Replace fixed exponential backoff with adaptive retry-after header parsing.

### Phase 2: Elimination of Artificial Sleeps & Context Slicing (Core)
1. **Sleep Removal**:
   - Delete `await asyncio.sleep(120.0)` in `plan_creator.py`.
   - Delete `await asyncio.sleep(65.0)` in `generator.py`.
   - Delete `await asyncio.sleep(30.0)` loops in `experiment_agent.py`.
   - Delete `await asyncio.sleep(20)` in `deep_research_orchestrator.py`.
   - Remove worker startup random jitter in `swarm_manager.py`.
2. **Context Window Expansion**:
   - Remove `[:MAX_DOC_CHARS]` (25k) in `doc_reader_agent.py`.
   - Remove `[:12000]` in `fact_checker_agent.py`.
   - Remove `[:4000]` component slicing in `writer_agent.py`.
   - Remove `[:8000]` context slicing in `generator.py`.
   - Remove `[:10000]` video transcript slicing in `research_agent.py`.
   - Remove `[:10000]` entity text slicing in `deep_research_orchestrator.py`.

### Phase 3: Reasoning Consolidation & Rigor Modernization (Advanced)
1. **Consolidate Multi-Step Prompt Chains**:
   - Collapse the 3-turn hypothesis generation loop (semantic brainstorm -> skeletonize -> harden) in `generator.py` into a single-pass call using reasoning models with thinking tokens.
2. **Replace Keyword Validation with Sandbox Execution & AST**:
   - Replace `_audit_code_igor` in `experiment_agent.py` (which checks for literal strings `"bootstrap"` and `"p_value"`) with a sandbox execution step that checks empirical output data (standard errors, p-value bounds, and confidence interval widths).
   - Replace string-matching heuristics in `prioritizer.py` (`"simple"`, `"complex"`, `"breakthrough"`) with structured semantic scoring.
3. **Purge Canned Rescue Roadmaps**:
   - Remove the hardcoded 4-task rescue roadmap (`rescue_{cycle}_1-4`) in `plan_creator.py`.
   - Remove emergency task injection in `deep_research_orchestrator.py`.
   - Enforce schema contracts so planning failures raise actionable exceptions rather than injecting synthetic artifacts into the scientific knowledge base.
4. **Prompt Normalization**:
   - Rewrite capitalized, threatening prompts across `experiment_agent.py`, `ml_model_builder_agent.py`, `writer_agent.py`, and `plan_creator.py` into neutral, objective system specifications.

---
*End of Audit Document.*

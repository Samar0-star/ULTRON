# Exhaustive Audit Report: SVEL Observability, Database & Migration Infrastructure

**Auditor:** Research Subagent  
**Target Repository:** `/Users/samaraldico/SVEL AI Scientist`  
**Date:** 2026-09-17  

---

## Executive Summary & Operational Health Assessment

| Subsystem | Declared / Nominal Status | Actual Runtime Implementation | Operational Health | Severity |
| :--- | :--- | :--- | :--- | :--- |
| **SQLAlchemy ORM** | PostgreSQL/SQLite ORM (`database.py`, `models/execution.py`) | **Completely Disconnected & Latent Crash**: Zero runtime components query or insert into SQLAlchemy models. `ForeignKey` is missing from imports in `execution.py` causing a syntax `NameError` if loaded. | 🔴 **Broken / Unused** | **Critical** |
| **Alembic Migrations** | Version-controlled DB migrations (`alembic.ini`, `alembic/`) | **Zero Migrations**: `alembic/versions/` does not exist; `env.py` has `target_metadata = None`; DB URL is dummy string `driver://user:pass@localhost/dbname`. | 🔴 **Non-Functional** | **High** |
| **Storage Directory** | `/Users/samaraldico/SVEL AI Scientist/storage/` | Contains empty `reproducibility/` directory. Target for `ReproducibilityManager.create_bundle()`. | 🟡 **Nominal / Sparse** | **Low** |
| **Observability & Metrics** | Prometheus metrics wrapper (`observability/metrics.py`) | **Completely Dead Code**: `prometheus_client` is not in `requirements.txt`. `observe_step()` and `metrics_handler()` are never imported or invoked anywhere in backend. | 🔴 **Dead / Disconnected** | **High** |
| **OpenTelemetry** | Mentioned in architectural documentation | **Zero Code**: Completely absent across backend (0 imports, 0 dependencies). | 🔴 **Non-Existent** | **Medium** |
| **True Runtime Persistence** | Ad-hoc SQLite + Flat JSON + JSONL Architecture | Dispersed across `WorldModel` SQLite (`data/world_model_*.db`), `ProvenanceDB` (`data/provenance/`), `PersistenceVault` JSONL/JSON, and `HypothesisTracker` JSON files. | 🟡 **Functional but Fragmented** | **Medium** |

---

## 1. Target Files & Infrastructure Review

### 1.1 `/backend/observability/`
- **Files present:** Only one file exists: `metrics.py` (41 lines).
- **Location:** [`backend/observability/metrics.py`](file:///Users/samaraldico/SVEL%20AI%20Scientist/backend/observability/metrics.py#L1-L41)
- **Detailed Inspection:**
  - Lines 13-18: Attempts to import `Counter, Histogram, generate_latest, REGISTRY` from `prometheus_client`.
  - Lines 19-25: If `ImportError`, sets `HAVE_PROM = False` and defines dummy `_Noop` class with empty `inc()` and `observe()` methods.
  - Lines 15-17: Defines:
    - `METRIC_STEP_COUNT = Counter("beast_steps_total", "Total steps executed")`
    - `METRIC_STEP_ERRORS = Counter("beast_step_errors_total", "Step errors")`
    - `METRIC_STEP_LATENCY = Histogram("beast_step_latency_seconds", "Step latency")`
  - Lines 27-31: `metrics_handler()` returns Prometheus byte payload or `b"# prometheus_client not available\n"`.
  - Lines 33-40: `observe_step(duration: float, error: bool = False)`.
- **Forensic Findings:**
  1. `prometheus_client` is **omitted** from [`backend/requirements.txt`](file:///Users/samaraldico/SVEL%20AI%20Scientist/backend/requirements.txt#L1-L40).
  2. A repository-wide ripgrep confirms that **neither `observe_step` nor `metrics_handler` is imported or called by any file** in `backend/`.
  3. No Prometheus scraping endpoint (e.g. `/metrics`) is mounted in any active server.

### 1.2 `/backend/database.py`
- **Location:** [`backend/database.py`](file:///Users/samaraldico/SVEL%20AI%20Scientist/backend/database.py#L1-L171) (171 lines)
- **Engine & Pool Configuration:**
  - Lines 23-40: `get_database_url()` falls back to `sqlite:///data/svel.db` if `DATABASE_URL` is unset, and translates `postgres://` to `postgresql://`.
  - Lines 51-91: `get_engine()` with double-checked thread locking (`_engine_lock`):
    - SQLite: Uses `sqlalchemy.pool.NullPool` with `connect_args={"check_same_thread": False}`. Note comments citing `[TITAN V162.0]` and `[GODZILLA V211.0]`.
    - PostgreSQL: Uses `sqlalchemy.pool.QueuePool` (`pool_size=20`, `max_overflow=40`, `pool_timeout=60`, `pool_recycle=1800`, `pool_pre_ping=True`).
  - Lines 94-105: `get_session_factory()` initializes `sessionmaker(autocommit=False, autoflush=False, bind=get_engine())`.
  - Lines 112-122: `get_db()` generator context for FastAPI/dependency injection.
  - Lines 125-143: `get_db_context()` context manager with auto-commit and rollback.
  - Lines 149-159: `init_db()` calls `from backend.models import Base; Base.metadata.create_all(bind=engine)`.
  - Lines 161-170: `check_db_connection()` executes `SELECT 1`.
- **Forensic Findings:**
  1. `get_db()`, `get_db_context()`, `init_db()`, and `check_db_connection()` are **never called anywhere in the active execution stack**.
  2. The SQLite target `data/svel.db` **does not exist** on disk anywhere in the project.

### 1.3 `/backend/alembic/` & `alembic.ini`
- **Location:** [`backend/alembic.ini`](file:///Users/samaraldico/SVEL%20AI%20Scientist/backend/alembic.ini#L1-L111) & [`backend/alembic/`](file:///Users/samaraldico/SVEL%20AI%20Scientist/backend/alembic/)
- **Detailed Inspection:**
  - `alembic.ini` Line 5: `script_location = alembic`
  - `alembic.ini` Line 63: `sqlalchemy.url = driver://user:pass@localhost/dbname` (unconfigured default placeholder).
  - `alembic/env.py` Lines 17-21:
    ```python
    # add your model's MetaData object here
    # for 'autogenerate' support
    # from myapp import mymodel
    # target_metadata = mymodel.Base.metadata
    target_metadata = None
    ```
  - `alembic/versions/`: **DOES NOT EXIST**. There are 0 revision scripts in the directory.
  - `backend/migrate_db.py` ([`backend/migrate_db.py:L1-L30`](file:///Users/samaraldico/SVEL%20AI%20Scientist/backend/migrate_db.py#L1-L30)): An ad-hoc script bypassing Alembic:
    ```python
    from backend.database import engine
    from backend.models.execution import Base, ResearchLog
    def migrate():
        Base.metadata.create_all(bind=engine)
    ```
- **Forensic Findings:**
  Alembic was initialized via standard CLI scaffolding and abandoned. The migration pipeline has 0 version history. Schema changes were never tracked or migrated through Alembic.

### 1.4 `/storage/`
- **Location:** [`/Users/samaraldico/SVEL AI Scientist/storage/`](file:///Users/samaraldico/SVEL%20AI%20Scientist/storage/)
- **Detailed Inspection:**
  - Contains `.DS_Store` and subfolder `storage/reproducibility/` (currently empty).
  - Reference in codebase: [`backend/core/validation/reproducibility.py:L50`](file:///Users/samaraldico/SVEL%20AI%20Scientist/backend/core/validation/reproducibility.py#L50):
    ```python
    class ReproducibilityManager:
        def __init__(self, storage_dir: str = "storage/reproducibility"):
            self.storage_dir = storage_dir
            os.makedirs(storage_dir, exist_ok=True)
    ```
  - When `ReproducibilityManager.create_bundle(finding_id, snapshot, seed)` runs, it writes `storage/reproducibility/repro_bundle_{finding_id}.json`.

---

## 2. Database Schema Analysis: Nominal vs. Actual

### 2.1 The Declared SQLAlchemy Schema (`backend/models/execution.py`)
Found in [`backend/models/execution.py`](file:///Users/samaraldico/SVEL%20AI%20Scientist/backend/models/execution.py#L18-L116):

#### 1. `research_logs`
- **Class:** `ResearchLog(Base)` ([execution.py:L18](file:///Users/samaraldico/SVEL%20AI%20Scientist/backend/models/execution.py#L18))
- **Primary Key:** `id` (`UUID(as_uuid=True)`, default `uuid.uuid4`)
- **Columns:**
  - `session_id`: `String(255)`, index=True, nullable=True
  - `query`: `Text`, nullable=False
  - `query_type`: `String(50)`, default="research"
  - `response`: `Text`, nullable=True
  - `response_tokens`: `Integer`, nullable=True
  - `context`: `Text`, nullable=True
  - `tools_used`: `Text`, nullable=True
  - `agent_flow`: `Text`, nullable=True
  - `search_results`: `Text`, nullable=True
  - `latency_ms`: `Integer`, nullable=True
  - `success`: `Boolean`, default=True
  - `error_message`: `Text`, nullable=True
  - `created_at`: `DateTime`, default=`datetime.utcnow`

#### 2. `research_executions`
- **Class:** `ResearchExecution(Base)` ([execution.py:L49](file:///Users/samaraldico/SVEL%20AI%20Scientist/backend/models/execution.py#L49))
- **Primary Key:** `id` (`String(255)`, trace_id)
- **Columns:**
  - `query`: `Text`, nullable=False
  - `status`: `String(50)`, default="pending"
  - `mode`: `String(50)`, default="standard"
  - `start_time`: `DateTime(timezone=True)`
  - `end_time`: `DateTime(timezone=True)`
  - `duration_s`: `Float`
  - `final_report`: `Text`
  - `confidence`: `Float`
  - `error`: `Text`
  - `context`: `Text`
  - `stats`: `Text`
  - **Relationships:** `steps` (`TraceStep`), `artifacts` (`Artifact`)

#### 3. `trace_steps`
- **Class:** `TraceStep(Base)` ([execution.py:L77](file:///Users/samaraldico/SVEL%20AI%20Scientist/backend/models/execution.py#L77))
- **Primary Key:** `id` (`Integer`, autoincrement=True)
- **Foreign Key:** `execution_id` (`String(255)`, `ForeignKey("research_executions.id", ondelete="CASCADE")`)
- **Columns:** `step_type`, `agent_id`, `tool_name`, `status`, `input_data`, `output_data`, `error`, `start_time`, `end_time`, `duration_s`, `metadata_json`.

#### 4. `artifacts`
- **Class:** `Artifact(Base)` ([execution.py:L102](file:///Users/samaraldico/SVEL%20AI%20Scientist/backend/models/execution.py#L102))
- **Primary Key:** `id` (`Integer`, autoincrement=True)
- **Foreign Key:** `execution_id` (`String(255)`, `ForeignKey("research_executions.id", ondelete="CASCADE")`)
- **Columns:** `artifact_type`, `filename`, `file_path`, `created_at`.

> [!CAUTION]
> **Critical Code Defect in `backend/models/execution.py`:**
> On line 10: `from sqlalchemy import Column, String, Boolean, DateTime, Text, Integer, Float`
> `ForeignKey` **is NOT imported from sqlalchemy**!
> As a result, line 82 (`execution_id = Column(String(255), ForeignKey(...))`) and line 107 trigger an immediate `NameError: name 'ForeignKey' is not defined` whenever `TraceStep`, `Artifact`, or `backend.models` is imported.

---

### 2.2 How Sessions, Hypotheses, Experiments, Metrics & Logs are ACTUALLY Stored

SVEL operates as an isolated compute node where operational state bypasses SQLAlchemy completely. The true data plane is:

| Domain Entity | Actual Physical Storage | Responsible File / Module | Schema / Data Structure |
| :--- | :--- | :--- | :--- |
| **Sessions** | Flat JSON / Mission Directories | [`backend/data/sessions.json`](file:///Users/samaraldico/SVEL%20AI%20Scientist/backend/data/sessions.json#L1-L8), [`backend/core/state/persistence_vault.py:L39`](file:///Users/samaraldico/SVEL%20AI%20Scientist/backend/core/state/persistence_vault.py#L39) | `sessions.json` stores `{ session_id: [{ token_hash, created_at }] }`. `PersistenceVault` writes metadata to `data/research_vault/missions/{session_id}/metadata.json`. |
| **Hypotheses** | JSON files (per session) | [`backend/core/hypothesis/tracker.py:L23-L86`](file:///Users/samaraldico/SVEL%20AI%20Scientist/backend/core/hypothesis/tracker.py#L23-L86), [`backend/core/hypothesis/models.py:L81-L120`](file:///Users/samaraldico/SVEL%20AI%20Scientist/backend/core/hypothesis/models.py#L81-L120) | Dataclass `Hypothesis` serialized to `data/hypotheses/session_{session_id}.json`. Fields: `id, statement, rationale, domain, state, confidence, uncertainty, novelty_score, testability_score, impact_score, priority_score, survival_score`. |
| **Experiments** | In-Memory Dataclasses & Log output | [`backend/experiments/models.py:L149-L222`](file:///Users/samaraldico/SVEL%20AI%20Scientist/backend/experiments/models.py#L149-L222) | Dataclasses `ExperimentProtocol`, `ProtocolStep`, `ValidationCheck`, `ExperimentResult`. Stored in orchestrator state and serialized into session checkpoints. |
| **Metrics** | Flat JSON predictions | [`backend/core/validation/accuracy_tracker.py:L123-L166`](file:///Users/samaraldico/SVEL%20AI%20Scientist/backend/core/validation/accuracy_tracker.py#L123-L166) | Dataclass `PredictionRecord` saved to `data/accuracy/predictions.json`. Includes `prediction_type, predicted_value, actual_value, confidence, is_correct, session_id, hypothesis_id`. |
| **Logs & Checkpoints** | JSONL + Atomic JSON Checkpoints | [`backend/core/state/persistence_vault.py:L20-L86`](file:///Users/samaraldico/SVEL%20AI%20Scientist/backend/core/state/persistence_vault.py#L20-L86) | 1. `data/research_vault/missions/{session_id}/logs/action_log.jsonl` (streaming event logs)<br>2. `data/research_vault/missions/{session_id}/checkpoints/cycle_{cycle}.json` (atomic fsync checkpoints). |
| **Traces** | Standalone JSON Files | [`backend/orchestration/beast_tracer.py:L28-L93`](file:///Users/samaraldico/SVEL%20AI%20Scientist/backend/orchestration/beast_tracer.py#L28-L93) | Dataclasses `TraceStep` and `ExecutionTrace` saved to `logs/Svel_traces/{trace_id}.json`. (Currently unhooked from `DeepResearchOrchestrator`). |
| **World Model (Knowledge DB)** | Native SQLite DB | [`backend/core/world_model.py:L760-L870`](file:///Users/samaraldico/SVEL%20AI%20Scientist/backend/core/world_model.py#L760-L870) | SQLite databases `data/world_model_*.db` with tables: `facts`, `entities`, `relationships`, `hyperedges`, `temporal_facts`, `causal_links`. |
| **Task Provenance** | Native SQLite DB | [`backend/memory/provenance_db.py:L41-L73`](file:///Users/samaraldico/SVEL%20AI%20Scientist/backend/memory/provenance_db.py#L41-L73) | SQLite `data/provenance/provenance_{session_id}.db` with tables `task_graph` and `agent_executions`. |
| **Key-Value Store** | Native SQLite DB | [`backend/memory/result_store.py:L189-L215`](file:///Users/samaraldico/SVEL%20AI%20Scientist/backend/memory/result_store.py#L189-L215) | SQLite `data/result_store.db` with table `kv (key TEXT PRIMARY KEY, value TEXT)`. |

---

## 3. Observability Layer Inspection

### 3.1 Prometheus / OpenTelemetry
- **Prometheus:**
  - Implemented in [`backend/observability/metrics.py`](file:///Users/samaraldico/SVEL%20AI%20Scientist/backend/observability/metrics.py#L1-L41).
  - Only declares 3 basic metrics (`beast_steps_total`, `beast_step_errors_total`, `beast_step_latency_seconds`).
  - **Verdict:** Dead code. It is never invoked by any agent, orchestrator, or router. `prometheus_client` is not in requirements.
- **OpenTelemetry:**
  - **Verdict:** Completely absent. There are no OpenTelemetry packages, SDKs, tracers, spans, or exporters.

### 3.2 Latency Tracking
- In [`backend/logging/json_logger.py:L78-L101`](file:///Users/samaraldico/SVEL%20AI%20Scientist/backend/logging/json_logger.py#L78-L101), `log_performance(logger, operation, duration, metadata)` is available to log duration via standard logger.
- In [`backend/orchestration/beast_tracer.py:L502-L526`](file:///Users/samaraldico/SVEL%20AI%20Scientist/backend/orchestration/beast_tracer.py#L502-L526), steps track `start_time` and `end_time` (using `time.time()`) and aggregate total duration, average step duration, min/max step duration.
- In [`backend/memory/provenance_db.py:L90-L104`](file:///Users/samaraldico/SVEL%20AI%20Scientist/backend/memory/provenance_db.py#L90-L104), `complete_task()` records `duration_s` in SQLite.

### 3.3 Token Spend & Credit Accounting
- Handled in [`backend/llm_manager.py`](file:///Users/samaraldico/SVEL%20AI%20Scientist/backend/llm_manager.py):
  - Line 670: `_estimate_provider_tokens(text: str) -> int`: Heuristic based on text character count.
  - Lines 397-416: `calculate_credit_cost(input_tokens, output_tokens, model, tool_use) -> float`: Calculates USD/credit cost against `MODEL_COSTS` and `TOOL_COSTS` with a multiplier `MARKUP`.
  - Line 102: `_release_capacity(provider, tokens_used)` notifies `ProviderScheduler` for concurrency rate limiting.
  - [`backend/data/credits.json`](file:///Users/samaraldico/SVEL%20AI%20Scientist/backend/data/credits.json#L1-L16): Contains static user balance fixture (`monthly_credits: 100000`), but is not actively written to by headless runs.

### 3.4 Error Rates & Logging
- [`backend/logging/atomic_logger.py`](file:///Users/samaraldico/SVEL%20AI%20Scientist/backend/logging/atomic_logger.py#L23-L72): Interceptor for high-visibility terminal debugging when `SVEL_ATOMIC_DEBUG=1`.
- [`backend/logging/json_logger.py`](file:///Users/samaraldico/SVEL%20AI%20Scientist/backend/logging/json_logger.py#L28-L65): Despite being named `json_logger.py`, `configure_json_logging()` configures standard text output: `[%(asctime)s] %(levelname)s [%(name)s] %(message)s`. It does **not** output structured JSON.
- `Sentry`: Defined as `sentry_dsn: str = Field(default="", env="SENTRY_DSN")` in [`backend/config.py:L58`](file:///Users/samaraldico/SVEL%20AI%20Scientist/backend/config.py#L58), but Sentry SDK is never initialized anywhere in backend.

---

## 4. Alembic Migrations Evolution

- **Alembic Version Files:** `backend/alembic/versions/` **does not exist**.
- **Migration History:** **0 revisions**. The schema has never evolved through Alembic.
- **Root Cause:**
  - `alembic/env.py:L21` leaves `target_metadata = None`. Running `alembic revision --autogenerate` fails to detect any SQLAlchemy models.
  - `alembic.ini:L63` leaves database URL as `driver://user:pass@localhost/dbname`.
- **Ad-Hoc Manual Alternative:**
  - `backend/migrate_db.py` was created as an emergency workaround to run `Base.metadata.create_all(bind=engine)`.
  - However, because `backend/models/execution.py` contains a missing import bug (`ForeignKey`), running `migrate_db.py` will crash if `TraceStep` or `Artifact` is imported or registered on `Base`.

---

## 5. Architectural Synthesis & Recommendations

### Architecture Divergence Summary
There is a 100% split between the **Nominal Web/SaaS Architecture** and the **Actual Headless Compute Engine**:
1. The **Nominal Web/SaaS layer** (`database.py`, `models/execution.py`, `alembic/`, `observability/metrics.py`) was scaffolded for a centralized web backend with PostgreSQL and Prometheus, but was abandoned and left with fatal import bugs and dummy configurations.
2. The **Actual Headless Autonomous Engine** (`cli.py`, `deep_research_orchestrator.py`, `world_model.py`, `persistence_vault.py`, `provenance_db.py`) relies exclusively on local SQLite databases (`world_model_*.db`, `provenance_*.db`, `result_store.db`) and atomic JSON checkpoints (`data/research_vault/missions/{session_id}/`).

### Recommended Remediation Steps
1. **Fix `backend/models/execution.py`:** Add `ForeignKey` to `from sqlalchemy import ..., ForeignKey` (line 10).
2. **Decide on Primary Data Plane:**
   - If maintaining headless SQLite architecture: Clean up or deprecate the unused SQLAlchemy and Alembic scaffolding, and wire `BeastTracer` / `observe_step` directly into `DeepResearchOrchestrator`.
   - If migrating to PostgreSQL/SQLAlchemy: Connect `DeepResearchOrchestrator` to `get_db_context()`, point `alembic/env.py` to `backend.models.execution.Base.metadata`, configure `alembic.ini`, and generate the initial baseline migration script.
3. **Connect Observability:** Integrate `observe_step()` inside `DeepResearchOrchestrator`'s cycle and subtask dispatch loops, and add `prometheus_client` to `requirements.txt`.
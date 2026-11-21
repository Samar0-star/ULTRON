# EXHAUSTIVE SECURITY & SYSTEMS AUDIT: SVEL EXECUTION & SANDBOXING ARCHITECTURE

**Audit Target Files:**
1. `/Users/samaraldico/SVEL AI Scientist/backend/execution/sandbox.py`
2. `/Users/samaraldico/SVEL AI Scientist/backend/core/safety/code_scanner.py`
3. `/Users/samaraldico/SVEL AI Scientist/backend/core/safety/operation_guard.py`
4. `/Users/samaraldico/SVEL AI Scientist/code_exec/`
*(Also audited execution callers: `backend/agents/experiment_agent.py` and `backend/tools/code_executor_tool.py`)*

---

## 1. Executive Summary & Critical Findings

- **GodModeSandbox is a Subprocess Runner, NOT Docker:** Despite the presence of a `DockerProvider` class in `sandbox.py` (lines 257–309), `GodModeSandbox.__init__` hardcodes `self._provider = RestrictedSubprocessProvider()` (line 313). No runtime toggle exists. All code executes as a bare host subprocess under the host user account.
- **Critical Architectural Disconnection:** Neither `code_scanner.py` nor `operation_guard.py` is ever called in the live execution pipeline (`GodModeSandbox.run` in `sandbox.py` line 315; `ExperimentAgent.run_experiment` in `experiment_agent.py` line 1575; `code_executor_tool.py` line 37). Both security modules are completely dead code in production.
- **Resource Enforcement Deficits:** Memory limits and CPU limits are **0% enforced** in `RestrictedSubprocessProvider`. An LLM script can allocate all host RAM (exhausting 16GB RAM) or max out all CPU cores indefinitely until timeout.
- **Trivial Sandbox Escape & Credential Access:** Untrusted LLM code can read `.env` and host filesystem secrets via standard `open("../.env")` because file reads are unblocked, or achieve arbitrary code execution via AST subscripting on `__builtins__` (`__builtins__["eval"](...)`), which bypasses `ASTValidator`.
- **Clean-Room & Scavenger Contamination:** The sandbox working directory (`results/`) is shared across all runs and **never wiped between executions**. The Scavenger protocol in `experiment_agent.py` copies all leftover `.csv`, `.pdb`, `.png`, `.json` files from `results/` into `experiments/`, creating cross-run contamination and false proof-of-work validations.
- **`code_exec/` Status:** `code_exec/` is an abandoned legacy directory created at import time by `code_executor_tool.py` (lines 18–19); it is completely empty and unused.

---

## 2. Deconstruction of `GodModeSandbox` (`sandbox.py`)

### A. Execution Mechanism: Subprocess vs. Docker vs. AST
- **Runtime Provider:** In `backend/execution/sandbox.py`:
  ```python
  311: class GodModeSandbox:
  312:     def __init__(self):
  313:         self._provider = RestrictedSubprocessProvider() # Default to subprocess for stability in this session
  314: 
  315:     def run(self, code: str, timeout: int = 300, profile: str = "general", extra_env: Optional[Dict[str, str]] = None) -> SandboxResult:
  316:         return self._provider.run(code, timeout, profile, extra_env=extra_env)
  ```
  `GodModeSandbox` hardcodes `RestrictedSubprocessProvider`. There is no option to pass a Docker flag.
- **Dead Docker Implementation:** `DockerProvider` (lines 257–309) is completely unreferenced by callers. Furthermore, `DockerProvider` contains a configuration bug: `cpu_percent: float = 0.5` is accepted in `__init__` (line 258) but is never passed into `client.containers.run()` (lines 283–295), where `nano_cpus` or `cpu_period`/`cpu_quota` is required by the Docker SDK.
- **Actual Pipeline of `RestrictedSubprocessProvider.run` (lines 187–255):**
  1. Static syntax and AST validation via local `ASTValidator` (lines 189–196).
  2. String prepend of `NUCLEAR_PREAMBLE` to the code (line 199).
  3. Writes to a temporary file via `tempfile.NamedTemporaryFile(suffix=".py")` (lines 201–203).
  4. Launches host subprocess:
     ```python
     222: process = subprocess.Popen(
     223:     [sys.executable, "-u", tmp_path],
     224:     stdout=subprocess.PIPE,
     225:     stderr=subprocess.PIPE,
     226:     text=True,
     227:     env=env,
     228:     cwd=results_cwd,
     229:     preexec_fn=os.setsid # [RIGOR FIX] Process group isolation for clean kills
     230: )
     ```

### B. Timeout Enforcement Mechanics
- **Implementation (lines 231–237):**
  ```python
  231: stdout, stderr = process.communicate(timeout=timeout)
  232: exit_code = process.returncode
  233: except subprocess.TimeoutExpired:
  234:     # [RIGOR FIX] Explicit SIGKILL to the entire process group
  235:     os.killpg(os.getpgid(process.pid), signal.SIGKILL)
  236:     stdout, stderr = "", f"Timeout after {timeout}s"
  237:     exit_code = 1
  ```
- **Strengths:** Using `preexec_fn=os.setsid` (line 229) assigns the child process to its own process group (`pgid`). When `subprocess.TimeoutExpired` triggers, `os.killpg(..., signal.SIGKILL)` kills all children in that group, avoiding orphaned worker processes.
- **Vulnerabilities / Architectural Risks:**
  1. `preexec_fn` is unsafe in multi-threaded Python processes (can deadlock if another thread holds an allocator or GIL lock during fork).
  2. If the untrusted code itself calls `os.setsid()` (or forks into a new detached session), `os.killpg` will not kill the grandchild.
  3. Default timeout is 300 seconds (5 minutes), and callers like `ExperimentAgent` pass up to 2400 seconds (40 minutes), leaving a massive window for resource monopolization.

### C. Memory Limit Enforcement
- **Status:** **NOT ENFORCED (0% enforcement).**
- **Analysis:** In `RestrictedSubprocessProvider`, there are **no memory caps**. There is no call to `resource.setrlimit(resource.RLIMIT_AS, ...)`, no cgroups, and no memory monitor.
- **Impact:** An untrusted script can allocate 100GB of virtual memory (`[0] * (10**10)`) or massive PyTorch tensors, crashing the host OS or invoking the macOS kernel memory pressure killer.

### D. CPU Limit Enforcement
- **Status:** **NOT ENFORCED (0% enforcement).**
- **Analysis:** No `RLIMIT_CPU`, `nice` priority adjustment, or CPU affinity is applied to the child process.
- **Impact:** Multi-threaded numpy/torch routines or `while True: pass` will saturate 100% of all CPU cores until timeout.

### E. Network Lockdown Mechanics
- **Implementation (lines 166–185):**
  ```python
  166:     NUCLEAR_PREAMBLE = """
  167: import sys
  168: import os
  169: 
  170: # [TITAN V72.6] Transparent Network Block
  171: def block_network(*args, **kwargs): raise RuntimeError("GodMode Sandbox: Network access forbidden.")
  172: 
  173: try:
  174:     import socket
  175:     socket.socket.connect = block_network
  176:     socket.socket.bind = block_network
  177:     socket.getaddrinfo = block_network
  178: except Exception as e: print(f"[SANDBOX ESCAPE ATTEMPTED] Network block failed: {e}")
  179: 
  180: os.system = block_network
  181: os.popen = block_network
  182: """
  ```
- **Flaws & Inconsistencies:**
  1. **Trivial Python-Level Monkey Patch:** It only patches `socket.socket.connect`, `socket.socket.bind`, and `socket.getaddrinfo`. It does NOT block `_socket` (the underlying C module), `urllib`, `http.client`, or any library compiled in C/Rust.
  2. **Profile Parameter Ignored:** Line 187 accepts `profile: str = "general"`, and `ExperimentAgent` calls it with `profile="scientific"` (line 1575) expecting network to be allowed for PDB/ChEMBL fetching. However, `RestrictedSubprocessProvider.run` completely ignores `profile` and **always** prepends `NUCLEAR_PREAMBLE` (line 199).

---

## 3. Analysis of `code_scanner.py`, `ASTValidator`, and `operation_guard.py`

### A. The Disconnection Vulnerability
Neither `code_scanner.py` (`CodeScanner`, `scan_code`) nor `operation_guard.py` (`OperationGuard`, `request_approval`) is connected to the execution pipeline:
- `GodModeSandbox.run()` (sandbox.py:315) only calls `self._provider.run()`.
- `RestrictedSubprocessProvider.run()` (sandbox.py:187) only invokes its own local `ASTValidator` (sandbox.py:191).
- `deep_research_orchestrator.py` imports `OperationGuard` at line 32 but **never calls it**.
- `code_executor_tool.py` imports `GodModeSandbox` at line 35 and bypasses `code_scanner.py`.

### B. What is Blocked by `ASTValidator` (`sandbox.py:46–158`)
- **Blocked Imports (`DANGEROUS_IMPORTS`, lines 51–55):**
  `subprocess`, `shutil`, `importlib`, `builtins`, `pty`, `ctypes`, `_ctypes`, `cffi`, `_cffi_backend`.
- **Blocked Functions (`DANGEROUS_FUNCTIONS`, lines 58–65):**
  `eval`, `exec`, `compile`, `input`, `breakpoint`, `setattr`, `delattr`, `getattr`, `globals`, `system`, `popen`, `spawn`, `fork`, `kill`, `setuid`, `setgid`, `chroot`, `chmod`, `chown`, `remove`, `rmdir`, `rename`, `execve`, `execv`, `execvp`, `execl`.
- **Blocked Attributes (`DANGEROUS_ATTRIBUTES`, lines 70–73):**
  `modules`, `meta_path`, `path_hooks`, `argv`, `__subclasses__`, `execve`, `execv`, `execvp`, `execl`.
- **Magic Attributes Check (lines 130–131):**
  Blocks attributes starting and ending with `__` (except `__name__`, `__init__`, `__main__`).
- **Sys Attribute Filter (lines 121–128):**
  Restricts `sys.<attr>` to only: `stdout`, `stderr`, `version`, `version_info`, `executable`, `platform`.

### C. What is Blocked by `code_scanner.py` (when called standalone)
- **Regex Patterns (lines 114–125):**
  `os.system\(`, `subprocess.Popen\(`, `eval\(`, `exec\(`, `__import__\(`, `open\s*\(['"]/(?:etc|sys|proc)`, `shutil.rmtree\(`, `os.remove\(`, `marshal.load`.
  *(Note line 123: Network blocking patterns were explicitly commented out in `code_scanner.py`)*.
- **Blocked Imports (lines 128–132):**
  - `os`: only blocks `["system", "popen", "spawn", "exec"]`. `import os` is allowed!
  - `subprocess`: only blocks `["Popen", "call", "check_call"]`.
  - `ctypes`: blocked entirely.
- **AST Checks (lines 341–383):**
  Only checks for `while True:` loops without `break` and recursive functions.

### D. Can Untrusted LLM Code Break Out or Access `.env` Credentials?
**YES. Multiple concrete bypasses exist:**

1. **Direct Filesystem Access to `.env` (No AST Violation):**
   - In `sandbox.py:228`, the working directory is set to `<project_root>/results`.
   - `open()` is **not** in `DANGEROUS_FUNCTIONS` (sandbox.py:59).
   - `ASTValidator` has no rule blocking `open`.
   - An LLM script can simply execute:
     ```python
     with open("../.env", "r") as f:
         leaked_creds = f.read()
     print(leaked_creds)  # Exfiltrated directly into stdout!
     ```
   - It can also read `~/.ssh/id_rsa`, `~/.aws/credentials`, or any file on the developer's computer.

2. **AST Subscript Bypass on `__builtins__`:**
   - Look at `ASTValidator.visit_Call` (lines 136–157):
     ```python
     136: def visit_Call(self, node):
     137:     if isinstance(node.func, ast.Name):
     ...
     144:     elif isinstance(node.func, ast.Attribute):
     ...
     ```
   - `visit_Call` **only** checks `ast.Name` and `ast.Attribute`. It completely ignores `ast.Subscript`!
   - `visit_Name` (lines 113–117) checks for `globals`, `getattr`, `setattr`, but does **not** check `__builtins__`.
   - Magic attribute filtering (line 130) only applies to `node.attr` in `visit_Attribute`, not to bare names in scope.
   - Therefore, calling a function via dictionary subscript on `__builtins__`:
     ```python
     __builtins__["eval"]("__import__('os').system('touch /tmp/pwned')")
     ```
     is parsed as `Call(func=Subscript(value=Name(id='__builtins__'), slice=Constant(value='eval')))`.
     - `visit_Name`: `__builtins__` is allowed (not in `{"globals", "getattr", "setattr"}`).
     - `visit_Subscript`: not implemented.
     - `visit_Call`: `node.func` is neither `ast.Name` nor `ast.Attribute`, so it skips checks!
     - Result: Complete arbitrary code execution and sandbox escape.

3. **Bypass via Unblocked Standard Modules:**
   - Neither `ASTValidator` nor `code_scanner.py` blocks:
     - `_socket`: Bypasses `NUCLEAR_PREAMBLE` network lock (`import _socket; s = _socket.socket(); s.connect(...)`).
     - `pickle`: In `SCIENTIFIC_WHITELIST` (code_scanner.py:136). Unpickling untrusted strings achieves arbitrary code execution via `__reduce__`.
     - `posix` / `pathlib`: Filesystem manipulation and traversal without using `os.remove` or `os.rename`.

4. **Environment Variable Scrubbing Analysis:**
   - In `sandbox.py:206–212`:
     ```python
     206: whitelist = {"PATH", "PYTHONPATH", "LANG", "LC_ALL", "LC_CTYPE", "HOME"}
     207: env = {k: v for k, v in os.environ.items() if k in whitelist}
     208: 
     209: if extra_env:
     210:     clean_extra = {k: v for k, v in extra_env.items() if not any(x in k.upper() for x in ["KEY", "TOKEN", "PASSWORD", "SECRET"])}
     211:     env.update(clean_extra)
     ```
   - **Strength:** Whitelisting is applied to the environment passed to the subprocess.
   - **Weakness:** Because the script has filesystem access, it doesn't need inherited environment variables; it can read `.env` directly from disk. Furthermore, `HOME` is passed, allowing the script to find user home files.

---

## 4. Inspection of Clean-Room Environment & Scavenger Protocol

### A. The Clean-Room Architecture
- **Location:** The sandbox sets `cwd` to `os.path.join(os.getcwd(), "results")` (sandbox.py:218, 228).
- **Flaw: Not a Clean Room:**
  - `results/` is a fixed, non-isolated host folder.
  - In `sandbox.py`, `results/` is **never wiped or cleared** before or after a run!
  - `sandbox.py:246–250` actually writes debugging files (`last_executed_script.py`, `failed_script.py`) directly into `results/`.

### B. The Scavenger Protocol (`backend/agents/experiment_agent.py`)
- **Lifecycle in `experiment_agent.py`:**
  1. **Pre-Execution Evidence Wipe (lines 1553–1568):**
     `experiment_agent.py` wipes all files inside `<project_root>/experiments/`:
     ```python
     1553: exp_dir = os.path.join(os.getcwd(), "experiments")
     ...
     1559: for f in os.listdir(exp_dir):
     1560:     f_path = os.path.join(exp_dir, f)
     1561:     if os.path.isfile(f_path):
     1562:         os.unlink(f_path)
     1567: os.makedirs(exp_dir, exist_ok=True)
     1568: initial_files = set(os.listdir(exp_dir))
     ```
     **Notice:** It wipes `experiments/`, but it does **NOT** wipe `results/`!

  2. **Execution (line 1575):**
     `exec_result = self.sandbox.run(code, timeout=self.default_timeout, profile="scientific")`
     The code executes inside `results/`.

  3. **Scavenger File Rescue (lines 1581–1596):**
     ```python
     1581: workdir = getattr(exec_result, 'workdir', None)
     1582: if workdir and os.path.exists(workdir):
     1583:     import shutil
     1584:     for f in os.listdir(workdir):
     1585:         if f.endswith(('.csv', '.pdb', '.png', '.json', '.pdf', '.txt', '.hash')) and f != 'script.py':
     1586:             src = os.path.join(workdir, f)
     1587:             dst = os.path.join(exp_dir, f)
     1588:             try:
     1589:                 shutil.copy2(src, dst)
     1590:                 logger.info(f" [SCAVENGER] Rescued Ph.D. artifact: {f}")
     ```

  4. **Artifact Integrity Verification (lines 1651–1681):**
     - Compares `final_files - initial_files` in `experiments/`.
     - Rejects if no new files and no `plt.show()`/`fig.show()`.
     - **PDB minimum size check (line 1673):** `if f.endswith(".pdb") and f_size < 1024:` -> Fraud detected (rejects coordinates < 1KB).
     - **CSV minimum size check (line 1678):** `if f.endswith(".csv") and f_size < 50:` -> Fraud detected (rejects placeholders < 50B).

### C. Vulnerabilities & Architectural Flaws in Scavenger Protocol
1. **Cross-Run State Leakage & Fraud By Contamination:**
   Because `results/` is never wiped, if Run 1 creates `discovery.csv`, and Run 2 fails to generate any file or crashes, the Scavenger protocol in Run 2 loops through `results/`, finds `discovery.csv` from Run 1, copies it to `experiments/`, and marks Run 2 as having produced valid physical artifacts!
2. **Concurrency / Race Conditions:**
   If multiple research agents run concurrently, both execute within the single shared `results/` folder and both wipe/read the single `experiments/` folder, causing file overwrites and race conditions.
3. **Unbounded Copying:**
   Any file matching the extensions (including `.txt`, `.json`, `.hash`) in `results/` is copied without file size upper limits, allowing untrusted code to fill the host disk.

---

## 5. Status of `code_exec/`

- **Inspection:** `/Users/samaraldico/SVEL AI Scientist/code_exec/` is an empty directory.
- **Origin in `backend/tools/code_executor_tool.py`:**
  ```python
  18: EXEC_DIR = os.getenv("CODE_EXEC_DIR", "code_exec")
  19: os.makedirs(EXEC_DIR, exist_ok=True)
  20: 
  21: def _write_code_to_file(code: str, dirpath: str, filename: str = "main.py"):
  ...
  35:         from backend.execution.sandbox import GodModeSandbox
  36:         sandbox = GodModeSandbox()
  37:         result = sandbox.run(code, timeout=timeout)
  ```
- **Finding:** `EXEC_DIR` is initialized and creates `code_exec/` on module import, but `run_python_code()` delegates directly to `GodModeSandbox` (which runs in `results/`). `EXEC_DIR` is never used. `code_exec/` is dead legacy scaffolding.

---

## 6. Comprehensive Vulnerability & Strength Matrix

| Component | Target File & Lines | Classification | Vulnerability / Architectural Gap | Severity | Recommended Fix |
|---|---|---|---|---|---|
| **Sandbox Architecture** | `sandbox.py:311–316` | False Security Barrier | `GodModeSandbox` defaults to host subprocess; `DockerProvider` is dead code. Runs on host OS. | **CRITICAL** | Instantiate `DockerProvider` by default, or run ephemeral container with `--read-only`, non-root user, and `--network=none`. |
| **Pipeline Integration** | `sandbox.py:187`, `code_scanner.py:90`, `operation_guard.py:25` | Dead Security Code | `CodeScanner` and `OperationGuard` are never invoked in `GodModeSandbox.run` or `ExperimentAgent`. | **HIGH** | Wire `CodeScanner.scan()` and `OperationGuard.check_operation()` into `RestrictedSubprocessProvider.run()` before AST parsing. |
| **AST Inspection** | `sandbox.py:136–157` | Sandbox Escape | `visit_Call` ignores `ast.Subscript`. `__builtins__["eval"](...)` bypasses all checks. | **CRITICAL** | Add `visit_Subscript` to block indexing into dangerous objects, and block `__builtins__` name in `visit_Name`. |
| **Credential Access** | `sandbox.py:218, 228` | Information Disclosure | `open()` is unblocked; subprocess runs in host directory and can read `../.env` or `~/.ssh`. | **CRITICAL** | Jail execution inside a temporary chroot / Docker mount with access only to the isolated dataset. |
| **Resource Limits** | `sandbox.py:187–255` | Denial of Service | Memory and CPU limits are completely unmanaged in `RestrictedSubprocessProvider`. | **HIGH** | Use Python `resource.setrlimit(resource.RLIMIT_AS, ...)` in `preexec_fn`, or use Docker/cgroups limits. |
| **Network Mocking** | `sandbox.py:166–185` | Network Leak | `NUCLEAR_PREAMBLE` only mocks high-level `socket.socket.connect`. Does not block `_socket` C module. | **MEDIUM** | Enforce network disconnection at OS level (`unshare -n` / Linux network namespace, macOS sandbox-exec, or Docker `--network none`). |
| **Clean-Room & Scavenger** | `sandbox.py:218`, `experiment_agent.py:1553, 1584` | Integrity / State Leak | Working directory `results/` is never cleared between runs. Residual files trigger false validation. | **HIGH** | Use `tempfile.TemporaryDirectory()` for each run as `workdir`, wiping it immediately after artifact extraction. |
| **Directory Hygiene** | `code_executor_tool.py:18–19`, `code_exec/` | Dead Code | `code_exec/` is created on import and never used. | **LOW** | Remove unused `EXEC_DIR` and delete `code_exec/`. |

---

### Architectural Strengths Observed
1. **Process Group Termination (`sandbox.py:229, 235`):** Setting `preexec_fn=os.setsid` and terminating via `os.killpg(..., signal.SIGKILL)` successfully prevents orphaned child processes on timeout.
2. **Environment Variable Whitelist (`sandbox.py:206–212`):** Passing only `PATH`, `PYTHONPATH`, `LANG`, `LC_ALL`, `LC_CTYPE`, and `HOME` prevents accidental injection of parent environment credentials via `os.environ`.
3. **Physicality Checks in Scavenger (`experiment_agent.py:1672–1681`):** Size-based gating for `.pdb` (>1KB) and `.csv` (>50B) effectively blocks empty mock files and LLM placeholder hallucinations.
4. **Forensic Trace Preservation (`sandbox.py:246–250`):** Always copying the temporary script to `last_executed_script.py` and `failed_script.py` ensures deterministic post-mortem debugging.
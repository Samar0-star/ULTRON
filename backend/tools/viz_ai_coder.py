import logging
import pandas as pd
import json
import os
import ast
import importlib.util
import re
from pathlib import Path
from typing import Any, Dict, Optional

from .common import VizResult, safe_df
from backend.llm_manager import get_llm_manager, get_model
from backend.tools.code_executor_tool import run_python_code

logger = logging.getLogger(__name__)


# ==========================================================
#  HARD SECURITY SANITIZER
# ==========================================================

FORBIDDEN_BUILTINS = {
    "eval", "exec", "open", "__import__", "compile",
    "globals", "locals", "input", "getattr", "setattr", "delattr"
}

FORBIDDEN_MODULES = {
    "os", "sys", "subprocess", "socket",
    "shutil", "pathlib", "multiprocessing"
}


class SecuritySanitizer(ast.NodeTransformer):
    def visit_Import(self, node):
        node.names = [
            n for n in node.names
            if n.name.split(".")[0] not in FORBIDDEN_MODULES
        ]
        return node if node.names else None

    def visit_ImportFrom(self, node):
        if node.module and node.module.split(".")[0] in FORBIDDEN_MODULES:
            return None
        return node

    def visit_Name(self, node):
        if node.id in FORBIDDEN_BUILTINS:
            raise ValueError(f"Forbidden builtin usage: {node.id}")
        return node


def sanitize_code(code: str) -> str:
    """Force-kill known Plotly API hallucinations and Data Painting fraud."""
    import re

    # 2. [RIGOR] FLAW 07 & 08 FIX: Block 'Data Painting' and 'Pseudo-Physics'
    # Detects patterns like: column * 0.54 or values * 1.2
    # Also blocks NumPy-generated fake residuals.
    painting_patterns = [
        r"\w+\[.*\]\s*\*\s*0\.\d+", # column * 0.XX
        r"\w+\[.*\]\s*\*\s*1\.\d+", # column * 1.XX
        r"discovery_delta\s*=",
        r"multiplier\s*=\s*\d+\.\d+",
        r"residuals\s*=\s*np\.random", # Fake residual dots
        r"errors\s*=\s*np\.random", # Fake error bars
        r"np\.random\.normal\(0,\s*0\.", # The hallmark of fake residuals
        r"np\.random\.seed" # Blocking seed setting to prevent deterministic forgery
    ]
    if any(re.search(pattern, code) for pattern in painting_patterns):
        logger.error(" [RIGOR] Forgery Detected: Hardcoded discovery multipliers or random residuals found in visualization code.")
        raise ValueError("Code blocked due to suspected scientific forgery (hardcoded deltas or random residuals).")

    # Standard AST verification
    tree = ast.parse(code)
    SecuritySanitizer().visit(tree)
    return ast.unparse(tree)


# ==========================================================
#  PUBLICATION VIZ ENGINE FROM SCIENTIFIC-VISUALIZATION SKILL
# ==========================================================


def _load_publication_viz_engine():
    engine_path = (
        Path(__file__).resolve().parents[1]
        / "skills"
        / "scientific-visualization"
        / "scripts"
        / "publication_viz_engine.py"
    )
    spec = importlib.util.spec_from_file_location("publication_viz_engine", engine_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Could not load publication visualization engine: {engine_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_publication_viz_engine = _load_publication_viz_engine()
build_publication_grade_figure = _publication_viz_engine.build_publication_grade_figure
audit_plotly_json = _publication_viz_engine.audit_plotly_json
extract_plotly_json = _publication_viz_engine.extract_plotly_json


def _viz_result_from_figure(fig, caption: str, df: pd.DataFrame, intent: str, audit: Dict[str, Any]) -> VizResult:
    import plotly.io as pio

    fig_json = json.loads(fig.to_json())
    figure_audit = audit_plotly_json(fig_json)
    audit = {**audit, **figure_audit}
    html_snippet = pio.to_html(fig, full_html=False, include_plotlyjs="cdn")
    return VizResult(
        status="success",
        message=f"Generated publication-grade visualization: {caption}",
        fig_json=fig_json,
        html=html_snippet,
        meta={
            "engine": "DeterministicPublicationViz_DeepMindGrade",
            "rows": int(len(df)),
            "intent": intent,
            "audit": audit,
            "quality_gates": {
                "barcharts_strictly_forbidden": True,
                "synthetic_data_allowed": False,
                "multicolour_high_fidelity": True,
                "raw_observations_visible": True,
            },
        },
    )


# ==========================================================
#  AI CODER BACKEND
# ==========================================================

class AiCoderBackend:
    """
    AI visualization engine.

    Backend responsibilities:
    - Secure code synthesis
    - Controlled execution
    - Output validation
    - Data context preparation

    Visualization doctrine is delegated to visualization skill.
    """

    def __init__(self):
        self._titan_cache = None

    # ------------------------------------------------------
    # Visualization Protocol Loader
    # ------------------------------------------------------
    def _get_visualization_protocols(self) -> str:
        if '_protocol_cache' in self.__dict__:
            return self._protocol_cache

        skill_path = os.path.join("backend", "skills", "scientific-visualization", "SKILL.md")

        try:
            with open(skill_path, "r", encoding="utf-8") as f:
                content = f.read()
                self._protocol_cache = content
                logger.info(f"[VIZ] Loaded visualization protocol from: {skill_path}")
                return content
        except Exception as e:
            logger.warning(f"Failed to load visualization protocol: {e}")
            return "Produce a publication-quality scientific visualization using Plotly. Use multi-panel layouts, statistical overlays, and Nature/Science journal aesthetics."

    # ------------------------------------------------------
    # Core Visualization Entry
    # ------------------------------------------------------
    def visualize(
        self,
        data: Any,
        intent: str,
        config: Optional[Dict] = None
    ) -> VizResult:

        if isinstance(data, list):
            # Attempt to extract from deep nested structures common in SVEL findings
            extracted = []
            for item in data:
                if isinstance(item, dict):
                    # Hoist 'result' items if they exist to flatten finding structure
                    if "result" in item and isinstance(item["result"], dict):
                        row = item.copy()
                        row.update(item["result"])
                        extracted.append(row)
                        continue

                    # Check for deep nesting: result -> result -> result -> results -> summary -> claim_leaderboard
                    res = item.get("result", {})
                    if isinstance(res, dict):
                        res = res.get("result", {})
                        if isinstance(res, dict):
                            res = res.get("result", {})
                            if isinstance(res, dict):
                                res = res.get("results", {})
                                if isinstance(res, dict):
                                    summary = res.get("summary", {})
                                    if isinstance(summary, dict) and "claim_leaderboard" in summary:
                                        for claim in summary["claim_leaderboard"]:
                                            extracted.append({
                                                "Hypothesis": claim.get("statement", "")[:50] + "...",
                                                "Confidence": claim.get("confidence", 0),
                                                "Novelty": claim.get("novelty_score", 0),
                                                "Priority": claim.get("priority_score", 0)
                                            })
                                        continue
            if extracted:
                df = pd.DataFrame(extracted)
            else:
                df = safe_df(data)
        else:
            df = safe_df(data)

        if df.empty:
            return VizResult(status="error", message="Empty dataset.")

        # RIGOR CHECK: Reject software metadata DataFrames (agent IDs, orchestrator state, logs)
        cols_set = set(str(c).lower() for c in df.columns)
        software_meta_keys = {
            "engine", "agent_id", "attempts", "hypothesis_id", "trace", "status", "meta",
            "error", "task_id", "cycle", "verdict", "attachments", "session_id", "summary",
            "rationale", "statement"
        }
        matched_meta = cols_set.intersection(software_meta_keys)
        if len(matched_meta) >= 3 or (len(cols_set) > 0 and len(matched_meta) / len(cols_set) > 0.4):
            num_cols = df.select_dtypes(include=["number"]).columns
            meta_num = set(str(c).lower() for c in num_cols).intersection({"confidence", "attempts", "step", "cycle", "priority"})
            if len(num_cols) <= len(meta_num):
                logger.warning(f"[VIZ] Rejected software orchestration metadata DataFrame (columns: {list(df.columns)[:5]}). Refusing to synthesize fake visualization from engine logs.")
                return VizResult(status="error", message="Refusing to synthesize scientific visualization from software orchestration metadata.")

        cfg = config or {}
        caption = cfg.get("caption", "AI Visualization")

        # Default path: deterministic, audited, raw-data-first visualization.
        # LLM synthesis remains available via {"prefer_llm": True}, but it is no
        # longer trusted as the primary publication-figure mechanism.
        if not cfg.get("prefer_llm", False):
            try:
                fig, audit = build_publication_grade_figure(df, intent=intent, caption=caption)
                logger.info(
                    "[VIZ] Deterministic publication figure selected: %s",
                    audit.get("plot_family"),
                )
                return _viz_result_from_figure(fig, caption, df, intent, audit)
            except Exception as det_err:
                logger.warning(
                    "[VIZ] Deterministic publication builder failed; falling back to guarded LLM path: %s",
                    det_err,
                )

        # Structured data summary for LLM reasoning
        cols = list(df.columns)
        if len(cols) > 1000:
            cols = cols[:1000] + ["...truncated..."]
            logger.info(f" [VIZ] Truncated columns from {len(df.columns)} to 1000")

        summary = {
            "rows": len(df),
            "columns": cols,
            "dtypes": df.dtypes.astype(str).to_dict(),
            "null_counts": df.isnull().sum().to_dict()
        }

        sample = df.head(10).to_json(orient="records")
        if len(sample) > 100000:
            logger.info(f" [VIZ] Truncating massive sample JSON ({len(sample)} chars)")
            sample = sample[:100000] + " ... [TRUNCATED]"

        protocol_rules = self._get_visualization_protocols()

        # --------------------------------------------------
        # PhD Prompt  Protocol Injected (BRUTAL DEEPMIND RIGOR)
        # --------------------------------------------------

        prompt = f"""
Write ONLY executable Python code. No markdown. No explanation.

{protocol_rules}

## TASK INTENT:
{intent}

## DATA CONTEXT:
- A pandas DataFrame named `df` is already loaded in your environment.
- **DO NOT** redefine or create a new `df`. USE THE EXISTING ONE.
- Columns: {", ".join(cols)}

Data summary:
{json.dumps(summary, indent=2)}

## BRUTAL PhD SCIENTIFIC VISUALIZATION DOCTRINE (DEEPMIND/NATURE/SCIENCE PEER-REVIEW GRADE):
- **ABSOLUTELY NO BAR CHARTS**: Under no circumstances will you generate a simplistic bar chart. They are for business presentations, not rigorous science.
- **Aesthetic**: Absolute highest-prestige academic research paper style. Pure white backgrounds (`#FFFFFF`), very subtle grey gridlines, standard academic text sizes. Use multi-color, complex, and beautiful continuous colormaps like `Viridis`, `Magma`, `Plasma`, or `Inferno` for rich data density.
- **Rigor**: Professional axis labels with standard SI units, scientific notation where appropriate. Include legends, grid lines, and robust layout styling.
- **Complexity over Simplicity**: Produce MULTICOLOUR, rich, multi-dimensional visualizations. You MUST employ advanced plotting techniques: Violin plots with jittered scatter points, 2D/3D Heatmaps, 3D Surface Plots, multi-panel Subplots, PCA projections, or Kinetic Trajectory paths. DO NOT generate simplistic or sparse plots.
- **Empirical Fidelity**: Use ONLY the raw data provided in `df`. DO NOT interpolate, extrapolate, or generate synthetic data points. Show the raw observations.
- **Surface Logic**: For 3D Surface plots (`go.Surface`), ensure `z` is a 2D matrix (`pivot_table` with index/columns). Fallback to high-density scatter if pivot fails.
- **Legend & Colorbars**:
    - Place legends cleanly. Colorbars MUST have a scientific title and units.
- **API Rigor**:
    - Use `title={{'text': '...'}}` or `fig.update_layout(xaxis_title='...')`.
- **Requirements**:
    - YOU MUST USE PLOTLY (`import plotly.graph_objects as go` or `import plotly.express as px`).
    - You MUST end the code with: `print(fig.to_json())`
    - Apply `template='plotly_white'` and scientific colormaps.
    - If the user intent implies distribution, use Violin/Box+Strip plots. If multi-variable, use Subplots, PCA, or Heatmaps.

Return only valid executable Python code. The output MUST look like a stunning, peer-review ready, publication-grade figure. Any failure to meet this standard is unacceptable.
"""

        model_override = cfg.get("model") or get_model("code_generation")

        try:
            logger.info(f"[AI CODER] Synthesizing visualization for intent: {intent}")

            llm_manager = get_llm_manager()
            llm_result = llm_manager.run(
                prompt=prompt,
                max_tokens_override=None,
                temperature=0.1,
                use_cache=False,
                model=model_override
            )

            # F-99: Harden against string responses
            if isinstance(llm_result, str):
                logger.warning(f" [AI CODER] LLM Manager returned STRING instead of dict. Wrapping...")
                llm_result = {"text": llm_result, "model": model_override}

            raw_text = llm_result.get("text", "") if isinstance(llm_result, dict) else str(llm_result)
            if not raw_text and isinstance(llm_result, dict) and llm_result.get("error"):
                logger.error(f" [AI CODER] LLM Manager returned INTERNAL ERROR: {llm_result.get('error')}")



            # ROBUST CODE EXTRACTION (F-42 Armored)
            import re
            if "```" in raw_text:
                # 1. Complete Block
                match = re.search(r'```(?:python)?\n?(.*?)\n?```', raw_text, re.DOTALL)
                if match:
                    gen_code = match.group(1).strip()
                else:
                    # 2. Truncated Block (Missing closing fence)
                    match = re.search(r'```(?:python)?\n?(.*)', raw_text, re.DOTALL)
                    if match:
                        gen_code = match.group(1).strip()
                    else:
                        gen_code = raw_text.strip()
            else:
                gen_code = raw_text.strip()

            # GUARD: Catch LLM Error strings or "thinking" passed as code without rejecting valid scripts that mention 'failed' in comments/labels
            stripped_low = gen_code.strip().lower()
            is_error_banner = (
                gen_code.strip().startswith("ERROR:")
                or stripped_low.startswith("llm error")
                or stripped_low.startswith("all providers failed")
                or ("import " not in stripped_low and "fig" not in stripped_low and len(gen_code) < 50)
            )
            if is_error_banner:
                logger.error(f" [AI CODER] LLM returned invalid content: {gen_code[:100]}")
                return VizResult(
                    status="error",
                    message=f"LLM Synthesis Failed or returned non-code: {gen_code[:50]}"
                )

            # Final check - if no fences, use the raw response but trimmed
            if not gen_code:
                logger.error(" [AI CODER] CRITICAL: Extracted code is EMPTY.")
                return VizResult(status="error", message="Empty synthesis")

            # Sanitize AST
            gen_code = sanitize_code(gen_code)

            # Safety: Force-inject print(fig.to_json()) if model just ends with 'fig'
            if "fig.to_json()" not in gen_code:
                if "fig =" in gen_code or "fig=" in gen_code:
                    logger.warning(" [AI CODER] Model omitted print(fig.to_json()). Injecting...")
                    gen_code += "\n\nif 'fig' in locals(): print(fig.to_json())"
                elif "fig.show()" in gen_code:
                    gen_code = gen_code.replace("fig.show()", "print(fig.to_json())")

            # Controlled execution with unique temp CSV to prevent concurrent race conditions
            import tempfile
            fd, csv_path = tempfile.mkstemp(prefix="svel_viz_", suffix=".csv")
            os.close(fd)
            try:
                df.to_csv(csv_path, index=False)

                execution_preamble = f"""
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import matplotlib.pyplot as plt

# DATA HYDRATION: Loading the 'df' DataFrame from robust absolute CSV source
df = pd.read_csv(r"{csv_path}")
"""

                final_code = execution_preamble + "\n" + gen_code

                # Allow controlled execution override
                allow_exec = cfg.get("allow_exec", False)

                res = run_python_code(
                    final_code,
                    timeout=120,
                    allow_exec=allow_exec
                )
            finally:
                if os.path.exists(csv_path):
                    try:
                        os.remove(csv_path)
                    except OSError:
                        pass

            stdout = res.get("stdout", "").strip()
            stderr = res.get("stderr", "").strip()

            if res.get("status") != "ok":
                err_msg = res.get("error") or stderr[:200]
                logger.error(f" [AI CODER] Execution failed. Error: {err_msg}")
                return VizResult(
                    status="error",
                    message=f"Execution failed: {err_msg}",
                    meta={
                        "stderr": stderr,
                        "error": res.get("error"),
                        "code": final_code
                    }
                )

            # If interactive JSON output
            try:
                fig_json = extract_plotly_json(stdout)
                figure_audit = audit_plotly_json(fig_json)
                if not figure_audit["passes"]:
                    logger.warning(
                        " [VIZ AUDIT] LLM figure rejected (trace_counts=%s). Rebuilding deterministically.",
                        figure_audit["trace_counts"],
                    )
                    fig, audit = build_publication_grade_figure(df, intent=intent, caption=caption)
                    audit["rejected_llm_audit"] = figure_audit
                    return _viz_result_from_figure(fig, caption, df, intent, audit)

                # [AUTO-RENDER] Convert fig_json to embeddable HTML snippet
                html_snippet = None
                try:
                    import plotly.io as pio
                    html_snippet = pio.to_html(fig_json, full_html=False, include_plotlyjs='cdn')
                except Exception as pio_err:
                    logger.warning(f" [AI CODER] Failed to render HTML from fig_json: {pio_err}")

                return VizResult(
                    status="success",
                    message=f"Generated: {caption}",
                    fig_json=fig_json,
                    html=html_snippet,
                    meta={
                        "engine": "AiCoder",
                        "rows": len(df),
                        "intent": intent,
                        "audit": figure_audit,
                        "code": final_code
                    }
                )
            except json.JSONDecodeError:
                # Non-JSON output (e.g., static Matplotlib)
                return VizResult(
                    status="success",
                    message=f"Generated static visualization: {caption}",
                    html=None,
                    meta={
                        "engine": "AiCoder",
                        "rows": len(df),
                        "intent": intent,
                        "stdout": stdout[:10000],
                        "code": final_code
                    }
                )

        except Exception as e:
            logger.exception("AI Coder failure")
            return VizResult(status="error", message=str(e))

    # ------------------------------------------------------
    # Router Compatibility
    # ------------------------------------------------------
    def ai_coder(self, data, intent, config=None):
        return self.visualize(data, intent, config)

    def __getattr__(self, name):
        def wrapper(data, **config):
            return self.visualize(data, intent=name, config=config)
        return wrapper


# Singleton
ai_coder = AiCoderBackend()


def run_ai_coder(df: pd.DataFrame, intent: str,
                 config: Optional[Dict] = None) -> VizResult:
    return ai_coder.visualize(df, intent, config)

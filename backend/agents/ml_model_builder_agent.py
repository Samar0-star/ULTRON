from __future__ import annotations

"""

   AUTOMATED ML ARCHITECT  HIGH-FIDELITY MODEL GENERATOR                   


The most ADVANCED Machine Learning code generation agent.

CAPABILITIES:
- Generates production-ready ML code (PyTorch, TensorFlow, scikit-learn)
- Automatic architecture design based on problem type
- Hyperparameter optimization built-in
- Data preprocessing pipelines included
- Model evaluation and metrics
- Deployment-ready code with Docker/Flask
- GPU acceleration when applicable

SUPPORTED TASKS:
- Classification (binary, multiclass)
- Regression
- Time Series Forecasting
- Anomaly Detection
- Clustering
- Deep Learning (CNN, RNN, Transformers)
- AutoML pipelines
"""

import os
import json
import logging
import asyncio
from typing import Any, Dict, List, Optional
from datetime import datetime

# Logging
logger = logging.getLogger("backend.ml_builder")
logger.setLevel(os.getenv("GODZILLA_LOG_LEVEL", "INFO"))
if not logger.handlers:
    ch = logging.StreamHandler()
    ch.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))
    logger.addHandler(ch)

# 
# GODZILLA ML PROMPT
# 

_ML_ARCHITECT_PROMPT = """

   ML ARCHITECT  HIGH-FIDELITY CODE GENERATOR                             


You are the ULTIMATE Machine Learning Engineer and Code Architect.
Your code is PRODUCTION-READY, BATTLE-TESTED, and DEPLOYMENT-GRADE.


MANDATORY CODE REQUIREMENTS


1.  COMPLETE IMPORTS  Include ALL necessary imports (torch, transformers, sklearn).
2.  ERROR HANDLING  Wrap critical sections in try/except with meaningful errors.
3.  METRICS  Include comprehensive evaluation metrics (accuracy, F1, MSE, R2).
4.  HYPERPARAMETERS  Make key hyperparameters (lr, batch_size, embed_dim) configurable.
5.  MODEL SAVING  Include code to save/load trained models.
6.  DOCUMENTATION  Include docstrings for classes and functions.
7.  GPU SUPPORT  Use GPU when available (device = 'cuda' if torch.cuda.is_available() else 'cpu').
8.  INTELLIGENT PROFILING  Use `DataAnalyzer` or similar logic to profile data before training.


FRAMEWORK & ARCHITECTURE SELECTION RULES


- TABULAR DATA: Use scikit-learn + XGBoost/LightGBM.
- COMPUTER VISION: Use PyTorch + torchvision (ResNet, EfficientNet). 
  - For advanced tasks, consider Vision Transformers (ViT).
- NLP: Use transformers (Hugging Face) + PyTorch (BERT, RoBERTa).
- DNA/PROTEIN: Use specialized encoders (DNABERT, Nucleotide Transformer) or 1D CNNs.
- TIME SERIES: Use statsmodels, Prophet, or LSTM/Transformer for complex dependencies.

- **MULTI-MODAL FUSION (CRITICAL)**:
  - If inputs include MULTIPLE types (e.g., Image + DNA + Text):
    - DO NOT just concatenate features.
    - USE CROSS-ATTENTION: One modality (e.g., DNA/Text) queries the other (e.g., Image).
    - Or use a Transformer Fusion layer after individual encoders.
    - Example: `DNA queries Image` is superior to `cat(DNA, Image)`.


DATA PREPROCESSING RULES (CRITICAL)

 
1.  NUMERIC DATA: Always impute missing values (mean/median) and Scale (StandardScaler)!
2.  CATEGORICAL DATA: YOU MUST ENCODE STRING/OBJECT COLUMNS!
   - Use `LabelEncoder` for target variables or ordinal features.
   - Use `OneHotEncoder` or `pd.get_dummies` for nominal features.
   - NEVER pass raw strings to a Neural Network or Model directly (TypeError risk).
3.  IMAGE DATA: Normalize pixel values (usually /255.0 or ImageNet Mean/Std).
4.  DNA DATA: Tokenize using k-mers or character-level encoding (A=1, C=2...).
5.  MISSING MODALITIES: If a modality can be missing, implement Masking or Zero-Padding.


OUTPUT FORMAT (STRICT JSON)


Return ONLY a valid JSON object with these exact keys:
{
    "code": "# Complete Python code here...",
    "description": "Brief description of what the code does",
    "model_type": "classification|regression|deep_learning|multi_modal|etc",
    "framework": "sklearn|pytorch|tensorflow|xgboost|etc",
    "libraries_needed": ["library1", "library2"],
    "estimated_training_time": "approximate time for typical dataset",
    "hyperparameters": {
        "param1": "value1",
        "param2": "value2"
    },
    "deployment_notes": "Notes for deploying this model in production"
}



HIGH-FIDELITY MODE ACTIVATED. GENERATE PRODUCTION-GRADE CODE.
"""


# 
# ML BUILDER AGENT
# 


# 
# GODZILLA ML BUILDER AGENT
# 

# Defensive imports for "Hybrid Execution" mode
try:
    from backend.tools.ml_model_builder_tool import AutomatedMLBuilder, AutomatedAlgorithmZoo
    from backend.visualization.data_analyzer import DataAnalyzer, AnalyzerConfig
    _HAVE_LOCAL_TOOLS = True
except ImportError as e:
    logger.warning(f"Local ML tools not found: {e}. Hybrid execution disabled.")
    _HAVE_LOCAL_TOOLS = False

class MLModelBuilderAgent:
    """
     ML BUILDER AGENT
    
    Generates production-ready Machine Learning code based on requirements.
    Uses LLM to architect and generate complete ML pipelines.
    
    [NEW] HYBRID MODE: Can now EXECUTE training locally using:
    - DataCleaner
    - DataTransformer
    - AutomatedAlgorithmZoo
    """
    
    name = "ml_model_builder"
    
    def __init__(self, llm_manager=None):
        """Initialize the ML Builder Agent."""
        self.llm_manager = llm_manager
        self._load_llm_manager()
        logger.info(" ML Builder Agent initialized")
    
    def _load_llm_manager(self):
        """Lazy load llm_manager if not provided."""
        if self.llm_manager is None:
            try:
                from backend.llm_manager import llm_manager
                self.llm_manager = llm_manager
            except ImportError:
                try:
                    from llm_manager import llm_manager
                    self.llm_manager = llm_manager
                except ImportError:
                    logger.warning("LLM Manager not available - code generation will fail")
                    self.llm_manager = None
    
    async def run(self, task: Dict[str, Any], context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
         MAIN ENTRY POINT: Generate ML code OR Execute Local Training.
        
        Args:
            task: Dict containing:
                - requirements: str - Description of ML task
                - query: str - Alternative to requirements
                - problem_type: str - Optional hint (classification, regression, etc.)
                - framework: str - Optional framework preference
                - payload: Dict - Optional data payload
                    - execution_mode: "code_gen" (default) or "local"
                    - data_path: str (required for local)
                    - target_col: str (required for local)
            context: Optional context dict
        
        Returns:
            Dict with generated code OR execution results
        """
        context = context or {}
        
        # Extract requirements from task
        payload = task.get("payload") or {}
        requirements = (
            payload.get("requirements") or 
            task.get("requirements") or
            task.get("query") or 
            task.get("instruction") or
            ""
        )
        
        # [TITAN MANDATE] Default to LOCAL EXECUTION to ensure real work is done
        execution_mode = payload.get("execution_mode", "local")
        
        if execution_mode == "local":
            return await self._execute_local_training(task, payload)
        
        if not requirements:
            return {
                "error": "No requirements provided",
                "status": "failed",
                "help": "Provide ML requirements in the 'requirements' or 'query' field"
            }
        
        # Optional hints
        problem_type = payload.get("problem_type") or task.get("problem_type") or ""
        framework = payload.get("framework") or task.get("framework") or ""
        
        logger.info(f" Building ML model for: {requirements[:80]}...")
        
        # Build the prompt
        full_prompt = self._build_prompt(requirements, problem_type, framework)
        
        # Generate code via LLM
        try:
            result = await self._generate_code(full_prompt)
            return result
        except Exception as e:
            logger.error(f"ML code generation failed: {e}")
            return {
                "error": str(e),
                "status": "failed",
                "requirements": requirements
            }

    async def _execute_local_training(self, task: Dict[str, Any], payload: Dict[str, Any]) -> Dict[str, Any]:
        """
         HYBRID EXECUTION: Run the actual ML pipeline locally.
        Uses DataCleaner -> DataTransformer -> MLModelBuilder.
        """
        if not _HAVE_LOCAL_TOOLS:
            return {"status": "error", "error": "Local ML tools are missing from backend/tools."}

        # [NEW] Multi-Modal / GSTM Routing
        multi_modal_config = payload.get("multi_modal_config")
        if multi_modal_config:
             return await self._execute_multimodal_training(multi_modal_config, payload)

        logger.info(" COMMENCING LOCAL TRAINING RUN...")
        
        data_path = payload.get("data_path")
        target_col = payload.get("target_col")
        
        if not data_path:
             # P0-31: If called for general ML/scientific discovery without a legacy tabular data_path,
             # delegate to ExperimentAgent so the frontier LLM designs and executes a custom experiment.
             if not payload.get("force_legacy_automl"):
                 try:
                     from backend.agents.experiment_agent import ExperimentAgent
                     exp_agent = ExperimentAgent(llm_manager=self.llm_manager)
                     return await exp_agent.run(task, context={"delegated_from": "ml_model_builder_agent"})
                 except Exception as exp_err:
                     logger.warning(f"Delegation to ExperimentAgent failed ({exp_err}); falling back.")
             return {"status": "error", "error": "Local execution requires 'data_path' in payload."}
             
        try:
            import pandas as pd
            import os # Added import for os
            
            # 1. Load Data with Robust Handling
            if not os.path.exists(data_path):
                 return {"status": "error", "error": f"File not found: {data_path}"}
            
            # Try loading with default settings, then fallbacks
            df = None
            for encoding in ['utf-8', 'latin1', 'cp1252']: # Added cp1252 for broader compatibility
                try:
                    # Use 'on_bad_lines' for pandas >= 1.3
                    df = pd.read_csv(data_path, encoding=encoding, on_bad_lines='skip')
                    break
                except UnicodeDecodeError:
                    continue
                except TypeError:
                     # Fallback for older pandas (error_bad_lines)
                    try:
                        df = pd.read_csv(data_path, encoding=encoding, error_bad_lines=False)
                        break
                    except Exception:
                        continue
                except Exception:
                    break
            
            # If 1 column or failed, try whitespace separator
            if df is None or len(df.columns) <= 1:
                try:
                    # Try whitespace with fallback encodings
                    for encoding in ['utf-8', 'latin1']:
                        try:
                            # Try with skipping bad lines
                            try:
                                df = pd.read_csv(data_path, delim_whitespace=True, header=None, encoding=encoding, on_bad_lines='skip')
                            except TypeError:
                                df = pd.read_csv(data_path, delim_whitespace=True, header=None, encoding=encoding, error_bad_lines=False)
                            # Auto-generate column names if header=None
                            df.columns = [f"col_{i}" for i in range(len(df.columns))]
                            # If target_col is an integer index (e.g. "13" or 13), map it
                            try:
                                tgt_idx = int(target_col)
                                if 0 <= tgt_idx < len(df.columns):
                                    target_col = df.columns[tgt_idx]
                            except ValueError:
                                pass
                            break
                        except UnicodeDecodeError:
                            continue
                except Exception as e:
                    return {"status": "error", "error": f"Failed to load messy data: {e}"}
            
            if df is None:
                 return {"status": "error", "error": f"Failed to load data with utf-8 or latin1"}
            
            logger.info(f"Loaded data: {df.shape}. Target column: '{target_col}'")
            
            # 2. Clean Data (graceful fallback if DataCleaner is not imported)
            df_clean = df.copy()
            try:
                from backend.tools.data_cleaner_tool import DataCleaner
                cleaner = DataCleaner()
                clean_res = cleaner.clean_dataframe(df)
                if isinstance(clean_res, tuple):
                    df_clean = clean_res[0]
                elif isinstance(clean_res, pd.DataFrame):
                    df_clean = clean_res
                else:
                    df_clean = clean_res.get("result") if hasattr(clean_res, "get") else clean_res
            except Exception as clean_err:
                logger.debug(f"DataCleaner unavailable or skipped ({clean_err}); applying standard pandas cleaning.")
                df_clean = df.dropna(how="all").copy()
                
            if not isinstance(df_clean, pd.DataFrame):
                return {"status": "error", "error": f"Data cleaning failed using {type(df_clean)}"}
            logger.info(f"Data cleaned: {df_clean.shape}")
            
            # 3. Transform Data (Feature Engineering with graceful fallback)
            df_transformed = df_clean
            try:
                from backend.tools.data_transformer_tool import DataTransformer
                transformer = DataTransformer()
                if hasattr(transformer, "fit_transform"):
                    df_transformed = transformer.fit_transform(df_clean)
            except Exception as trans_err:
                logger.debug(f"DataTransformer unavailable or skipped ({trans_err}); proceeding with cleaned DataFrame.")
            
            # 4. Intelligent Profiling & Target Inference (NATIVE)
            # Autonomous Target Inference
            if not target_col:
                # Heuristic: look for common scientific target names
                for c in ["yield", "target", "label", "outcome", "severity", "mortality"]:
                    if c in df_clean.columns:
                        target_col = c
                        break
                if not target_col:
                    target_col = df_clean.columns[-1]
                logger.info(f" [AUTO] Inferred target column: '{target_col}' via native heuristics.")

            # Autonomous Task Detection
            problem_type = payload.get("problem_type") or task.get("problem_type") or ""
            if not problem_type:
                unique_tgt = df_clean[target_col].nunique()
                if unique_tgt < 20 and df_clean[target_col].dtype == 'object':
                    problem_type = "classification"
                else:
                    problem_type = "regression"
                logger.info(f" [AUTO] Problem type fallback: '{problem_type}' (Unique targets: {unique_tgt})")

            # 5. Train Model
            builder = AutomatedMLBuilder()
            
            logger.info(f"Training model (type={problem_type}) on target '{target_col}'...")
            
            # Prepare Data for Builder (it expects a DataFrame with target)
            # We use df_transformed which includes the target
            
            # Disable builder's internal feature engineering if we already did it?
            # Actually, let's let the builder do its advanced engineering (interactions/polynomials) 
            # on top of our basic cleaning.
            
            model_res = builder.fit(
                data=df_transformed,
                target_col=target_col,
                problem_type=problem_type
            )
            
            if model_res.status == "error":
                return {
                    "status": "error", 
                    "error": f"AutoML failed: {model_res.error}"
                }
            
            # 6. Save Model for Persistence
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            model_filename = f"model_{model_res.experiment_id}_{timestamp}.pkl"
            
            # Save to saved_models/ for backend persistence
            try:
                os.makedirs("saved_models", exist_ok=True)
            except Exception as e:
                logger.warning(f"Failed to create saved_models directory: {e}")
            save_path = os.path.join("saved_models", model_filename)
            builder.save_model(save_path)
            
            # Copy to reports/ for frontend visibility
            report_path = None
            try:
                reports_dir = os.getenv("REPORTS_DIR", "reports")
                os.makedirs(reports_dir, exist_ok=True)
                report_model_path = os.path.join(reports_dir, model_filename)
                
                import shutil
                shutil.copy2(save_path, report_model_path)
                report_path = report_model_path
                logger.info(f" Model artifact exposed at: {report_path}")
            except Exception as e:
                logger.warning(f" Failed to copy model to reports dir: {e}")
            
            return {
                "status": "success",
                "mode": "local_execution",
                "model_metrics": {
                    "accuracy": model_res.best_score, # Approximation (or R2)
                    "best_metric": model_res.best_metric
                },
                "best_model": model_res.best_model_name,
                "pipeline_steps": ["DataCleaner", "DataTransformer", "AutomatedMLBuilder", "SmartDownsampler"],
                "experiment_id": model_res.experiment_id,
                "problem_type": model_res.problem_type,
                "model_path": report_path or save_path,
                "model_filename": model_filename
            }
            
        except Exception as e:
            logger.exception("Local training failed")
            return {"status": "error", "error": str(e)}

    async def _execute_multimodal_training(self, config: Dict[str, Any], payload: Dict[str, Any]) -> Dict[str, Any]:
        """
         Run Multi-Modal Training (GSTM).
        Expects config with: images_path/dir, dna_path, metadata_path, target_col.
        """
        logger.info(" COMMENCING MULTI-MODAL TRAINING RUN (GSTM)...")
        logger.info(f"DEBUG: Config received: {config}")
        
        try:
            # 1. Extract Paths from Config
            images_path = config.get("images_path") or config.get("images_dir")
            dna_path = config.get("dna_path")
            metadata_path = config.get("metadata_path")
            timeseries_path = config.get("timeseries_path")
            text_path = config.get("text_path")
            graphs_path = config.get("graphs_path")
            target_col = config.get("target_col") or "yield"
            
            # 2. Train using Tool (Paths Only)
            builder = AutomatedMLBuilder()
            
            logger.info(f"Training Fusion Model on target '{target_col}'...")
            
            model_res = builder.fit_multimodal(
                images_path=images_path,
                dna_path=dna_path,
                metadata_path=metadata_path,
                target_col=target_col,
                timeseries_path=timeseries_path,
                text_path=text_path,
                graphs_path=graphs_path,
                drop_columns=config.get("drop_columns"),
                epochs=config.get("epochs", 10),
                batch_size=config.get("batch_size", 32)
            )
            
            if model_res.status == "error":
                return {
                    "status": "error", 
                    "error": f"AutoML failed: {model_res.error}"
                }
            
            # Save Model
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            save_path = f"saved_models/gstm_model_{timestamp}.pkl"
            try:
                if not os.path.exists("saved_models"):
                    os.makedirs("saved_models")
            except Exception:
                pass
                
            builder.save_model(save_path)
            
            return {
                "status": "success",
                "mode": "local_multimodal",
                "model_metrics": {
                    "best_score": model_res.best_score,
                    "metric": model_res.best_metric
                },
                "best_model": model_res.best_model_name,
                "model_path": save_path,
                "pipeline_steps": ["MultiModalLoader", "AutomatedMLBuilder"],
                "experiment_id": model_res.experiment_id,
                "problem_type": "multi_modal_fusion"
            }
            
        except Exception as e:
            logger.exception("Multi-modal training failed")
            return {"status": "error", "error": str(e)}

    def _load_multimodal_data(self, config: Dict[str, Any], payload: Dict[str, Any]):
        """Helper to load heterogeneous data sources."""
        import pandas as pd
        import numpy as np
        
        # Paths
        images_path = config.get("images_path") or config.get("images_dir")
        dna_path = config.get("dna_path")
        metadata_path = config.get("metadata_path")
        timeseries_path = config.get("timeseries_path")  # New
        text_path = config.get("text_path")              # New
        graphs_path = config.get("graphs_path")          # New
        
        # 1. Images
        images = None
        if images_path and os.path.exists(images_path):
            images = images_path

        # 2. DNA sequences
        dna = None
        if dna_path and os.path.exists(dna_path):
            dna = dna_path

        # 3. Load Metadata
        metadata = None
        if metadata_path and os.path.exists(metadata_path):
            if str(metadata_path).endswith(".csv"):
                metadata = pd.read_csv(metadata_path)
            elif str(metadata_path).endswith(".parquet"):
                metadata = pd.read_parquet(metadata_path)
        
        target_col = config.get("target_col") or (metadata.columns[-1] if metadata is not None and len(metadata.columns) > 0 else None)
             
        return images, dna, metadata, target_col

    def _build_prompt(self, requirements: str, problem_type: str = "", 
                      framework: str = "") -> str:
        """Build the complete prompt for the LLM."""
        prompt = _ML_ARCHITECT_PROMPT
        
        prompt += f"\n\nUSER REQUIREMENTS:\n{requirements}\n"
        
        if problem_type:
            prompt += f"\nPROBLEM TYPE HINT: {problem_type}\n"
        
        if framework:
            prompt += f"\nPREFERRED FRAMEWORK: {framework}\n"
        
        prompt += "\n\nGENERATE THE CODE NOW:"
        
        return prompt
    
    async def _generate_code(self, prompt: str) -> Dict[str, Any]:
        """Generate ML code using the LLM."""
        if self.llm_manager is None:
            self._load_llm_manager()
            if self.llm_manager is None:
                raise RuntimeError("LLM Manager not available")
        
        # Call LLM via explicit model variable (No Cross-Work Policy)
        from backend.llm_manager import CODE_GENERATION_MODEL
        
        # Execute run (handle both sync and async)
        try:
            response = self.llm_manager.run(
                prompt=prompt,
                model=CODE_GENERATION_MODEL,
                temperature=0.2,
                task_hint="code_generation"
            )
            
            if asyncio.iscoroutine(response) or asyncio.isfuture(response):
                response = await response
        except Exception as e:
            # Fallback if run is not async but was treated as such? No, just standard error handling
            logger.error(f"LLM run failed: {e}")
            raise e
        
        raw_text = response.get("text", "")
        
        if not raw_text:
            logger.error(f"LLM Response Empty! Raw Response: {response}")
            raise RuntimeError(f"LLM returned empty response: {response}")
        
        # Parse JSON response
        result = self._parse_response(raw_text)
        result["meta"] = {
            "model": response.get("model"),
            "provider": response.get("provider"),
            "raw_length": len(raw_text),
            "timestamp": datetime.now().isoformat()
        }
        
        return result
    
    def _parse_response(self, text: str) -> Dict[str, Any]:
        """Parse the LLM response into structured format."""
        # Try to find JSON in the response
        try:
            # Look for JSON block
            start = text.find("{")
            end = text.rfind("}") + 1
            
            if start != -1 and end > start:
                json_str = text[start:end]
                data = json.loads(json_str)
                
                # Validate expected keys
                if "code" in data:
                    return {
                        "status": "success",
                        "code": data.get("code", ""),
                        "description": data.get("description", ""),
                        "model_type": data.get("model_type", "unknown"),
                        "framework": data.get("framework", "unknown"),
                        "libraries_needed": data.get("libraries_needed", []),
                        "hyperparameters": data.get("hyperparameters", {}),
                        "deployment_notes": data.get("deployment_notes", ""),
                        "estimated_training_time": data.get("estimated_training_time", "unknown")
                    }
        except json.JSONDecodeError:
            pass
        
        # Fallback: treat entire response as code
        logger.warning("Could not parse JSON, treating response as raw code")
        return {
            "status": "success",
            "code": text,
            "description": "Generated ML code (raw format)",
            "model_type": "unknown",
            "framework": "unknown",
            "libraries_needed": [],
            "hyperparameters": {},
            "deployment_notes": "",
            "estimated_training_time": "unknown"
        }
    
    # 
    # CONVENIENCE METHODS
    # 
    
    async def build_classifier(self, description: str, 
                               framework: str = "sklearn") -> Dict[str, Any]:
        """Build a classification model."""
        return await self.run({
            "requirements": description,
            "problem_type": "classification",
            "framework": framework
        })
    
    async def build_regressor(self, description: str,
                              framework: str = "sklearn") -> Dict[str, Any]:
        """Build a regression model."""
        return await self.run({
            "requirements": description,
            "problem_type": "regression",
            "framework": framework
        })
    
    async def build_deep_learning(self, description: str,
                                  framework: str = "pytorch") -> Dict[str, Any]:
        """Build a deep learning model."""
        return await self.run({
            "requirements": description,
            "problem_type": "deep_learning",
            "framework": framework
        })
    
    async def build_time_series(self, description: str) -> Dict[str, Any]:
        """Build a time series forecasting model."""
        return await self.run({
            "requirements": description,
            "problem_type": "time_series"
        })


# 
# COMPATIBILITY ALIASES
# 

# Backward compatibility
Agent = MLModelBuilderAgent


# 
# STANDALONE TEST
# 

if __name__ == "__main__":
    import asyncio
    
    async def test():
        agent = MLModelBuilderAgent()
        
        print("\n--- Testing Code Gen ---")
        result = await agent.run({
            "requirements": "Build a binary classifier for predicting customer churn using XGBoost"
        })
        
        print("\n" + "="*60)
        print(" ML BUILDER AGENT RESULT (Code Gen)")
        print("="*60)
        print(f"Status: {result.get('status')}")
        print(f"Framework: {result.get('framework')}")
        print(f"Code length: {len(result.get('code', ''))} chars")
        print("="*60)
    
    asyncio.run(test())


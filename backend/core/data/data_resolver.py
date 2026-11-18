"""
Data Resolver for Avon-2 Deep Mode
===================================
Finds and resolves physical data files in the local filesystem to bond 
with generated hypotheses and ground experiments.
"""

import os
import re
import logging
from typing import Dict, List, Optional, Tuple
from pathlib import Path
import json

logger = logging.getLogger("backend.core.data.data_resolver")

_EXCLUDED_FILENAMES = {".DS_Store", "Thumbs.db", ".git", "__pycache__"}


class DataResolver:
    """
    [TITAN V62] Scientific Data Resolver
    Acts as the 'Scientific Librarian' to find physical files for bonding.
    """

    def __init__(self, data_root: Optional[str] = None):
        self.data_root = data_root or os.path.join(os.getcwd(), "data")
        os.makedirs(self.data_root, exist_ok=True)

    def _introspect_schema_tokens(self, f: Path) -> List[str]:
        """Fast, zero-copy schema introspection for SQLite, Parquet, CSV/TSV, and HDF5 files."""
        ext = f.suffix.lower()
        tokens: List[str] = []
        try:
            if ext in (".db", ".sqlite", ".sqlite3"):
                import sqlite3
                conn = sqlite3.connect(f"file:{f.absolute()}?mode=ro", uri=True)
                cur = conn.cursor()
                cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%';")
                tables = [r[0] for r in cur.fetchall()]
                for t in tables[:25]:
                    tokens.append(t.lower())
                    cur.execute(f'PRAGMA table_info("{t}");')
                    for col_row in cur.fetchall():
                        tokens.append(str(col_row[1]).lower())
                conn.close()
            elif ext in (".parquet", ".pq"):
                try:
                    import pyarrow.parquet as pq
                    schema = pq.read_schema(f)
                    tokens.extend([name.lower() for name in schema.names])
                except Exception:
                    import pandas as pd
                    df_head = pd.read_parquet(f)
                    tokens.extend([str(c).lower() for c in df_head.columns])
            elif ext in (".csv", ".tsv", ".txt"):
                with open(f, "r", encoding="utf-8", errors="ignore") as fp:
                    header = fp.readline().strip()
                for col in re.split(r"[,;\t|]", header):
                    c_clean = col.strip().strip("\'\"").lower()
                    if c_clean:
                        tokens.append(c_clean)
            elif ext in (".h5", ".hdf5"):
                import h5py
                with h5py.File(f, "r") as hf:
                    tokens.extend([str(k).lower() for k in hf.keys()])
        except Exception:
            pass
        return tokens

    def resolve_data_for_hypothesis(self, hypothesis_statement: str) -> Dict[str, str]:
        """
        Scan the data_root for files and databases semantically or structurally related to the hypothesis.
        Introspects both filenames and internal database/table/column schemas.
        Returns: {variable_label: absolute_path}
        """
        _excluded_dirs = _EXCLUDED_FILENAMES | {
            "provenance", "research_vault", "checkpoints", "logs",
            "cache", "morgue", "telemetry", "sessions", "artifacts"
        }
        all_files = []
        for root, dirs, files in os.walk(self.data_root):
            dirs[:] = [d for d in dirs if d not in _excluded_dirs and not d.startswith(".")]
            for f in files:
                if f not in _EXCLUDED_FILENAMES:
                    all_files.append(Path(root) / f)

        cleaned = re.sub(r"[{\'}\":\[\]]", " ", str(hypothesis_statement or ""))
        cleaned = re.sub(r"doc_[a-f0-9]+", " ", cleaned)
        cleaned = re.sub(r"\s+", " ", cleaned).strip()
        statement_lower = cleaned.lower()

        domain_mappings = {
            "superconduct": ["superconduct", "superconductivity", "superconductor", "critical_temp", "tc", "ved", "kappa", "valence", "condensed", "bcs", "materials"],
            "exoplanet": ["planet", "exoplanet", "orbit", "stellar", "radius", "mass", "astrophysics", "kepler", "tess"],
            "skempi": ["affinity", "binding", "kd", "ddg", "mutation", "mutant", "thermodynamic", "coupling", "skempi", "protein", "rbd", "ace2", "n501y", "spike", "alanine"],
            "6m0j": ["6m0j", "rbd", "ace2", "spike", "pdb", "structure", "interface", "tyr41", "501", "n501y", "q498h", "k417n", "e484k", "coulomb", "sasa", "salt_bridge", "biophys"],
            "6lzg": ["6lzg", "rbd", "ace2", "spike", "pdb", "structure", "interface"],
            "starr": ["dms", "deep mutational", "starr", "escape", "epitope", "expression", "bind_avg", "expr_avg", "rbd", "mutation", "affinity", "ace2", "spike", "variant", "enhancer", "biophys", "biophysics"],
            "covid": ["sars", "cov", "covid", "coronavirus", "spike", "epidemiology", "omicron"],
            "fusion": ["fusion", "tokamak", "mhd", "plasma", "magnetic"],
            "alzheimer": ["alzheimer", "dementia", "brain", "counts", "gene"],
        }

        if "cifar" in statement_lower:
            llm_keywords = ["cifar", "transformer", "vision", "pruning", "accuracy", "flops"]
        else:
            llm_keywords = [w.lower() for w in statement_lower.split() if len(w) > 3]

        valid_exts = [
            ".csv", ".parquet", ".pq", ".feather", ".arrow", ".ipc",
            ".db", ".sqlite", ".sqlite3", ".duckdb",
            ".pkl", ".pickle", ".pt", ".pth", ".h5", ".hdf5",
            ".npz", ".npy", ".pdb", ".cif", ".ent", ".tsv", ".jsonl", ".nc", ".fits"
        ]

        _internal_db_prefixes = (
            "world_model", "knowledge_graph", "result_store", "sessions",
            "ultron", "persistence", "morgue", "checkpoint", "memory_store",
            "telemetry", "provenance", "action_log", "audit_log", "event_log"
        )
        _internal_db_tables = {
            "facts", "entities", "relationships", "hyperedges",
            "temporal_facts", "causal_links", "sessions", "checkpoints",
            "task_graph", "agent_executions", "hypotheses", "findings", "papers", "evidence"
        }

        candidates: List[Path] = []
        scored: List[tuple] = []
        for f in all_files:
            fname_lower_for_check = f.name.lower()
            if not any(fname_lower_for_check.endswith(ext) for ext in valid_exts):
                continue
            # 1. Block internal ULTRON state databases by filename prefix or exact match
            if any(fname_lower_for_check.startswith(pfx) for pfx in _internal_db_prefixes):
                continue
            if any(k in fname_lower_for_check for k in ("world_model", "knowledge_graph", "result_store", "provenance", "action_log")):
                continue
            # 2. Block empty / 0-byte stub files (< 50 bytes) or placeholder raw_data.csv
            try:
                f_size = f.stat().st_size
                if f_size < 50:
                    continue
                if fname_lower_for_check == "raw_data.csv" and f_size < 100:
                    continue
                if f.suffix.lower() in (".csv", ".tsv", ".txt"):
                    with open(f, "r", encoding="utf-8", errors="ignore") as _cf:
                        _hdr = _cf.readline().strip()
                        _row1 = _cf.readline().strip()
                    if not _hdr or not _row1:
                        continue
            except Exception:
                continue
            # 3. Block SQLite files whose schema consists exclusively of ULTRON internal state tables
            schema_tokens = self._introspect_schema_tokens(f)
            if f.suffix.lower() in (".db", ".sqlite", ".sqlite3"):
                try:
                    import sqlite3
                    _conn = sqlite3.connect(f"file:{f.absolute()}?mode=ro", uri=True)
                    _cur = _conn.cursor()
                    _cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%';")
                    _tbls = {r[0].lower() for r in _cur.fetchall()}
                    _conn.close()
                    if not _tbls or _tbls.issubset(_internal_db_tables):
                        continue
                except Exception:
                    pass
            candidates.append(f)
            fname_lower = str(f.absolute()).lower()
            stem_lower = f.stem.lower()
            score = 0

            # 1. Exact stem match or stem-part match
            if stem_lower in statement_lower or stem_lower.replace("_", "") in statement_lower:
                score += 50
            elif any(len(part) >= 4 and part in statement_lower for part in stem_lower.split("_")):
                score += 40

            # 2. Domain semantic mapping
            for key, kws in domain_mappings.items():
                if key in fname_lower:
                    for kw in kws:
                        if kw.lower() in statement_lower:
                            score += 5

            # 3. Direct filename word match
            for kw in llm_keywords:
                if kw in fname_lower:
                    score += 5

            # 4. Internal Database / Table / Column Schema Match
            schema_tokens = self._introspect_schema_tokens(f)
            for tok in schema_tokens:
                tok_clean = tok.strip()
                if len(tok_clean) >= 3 and (tok_clean in statement_lower or any(p in statement_lower for p in tok_clean.split("_") if len(p) >= 4)):
                    score += 15

            if score > 0:
                scored.append((score, f))

        result = {}
        scored.sort(key=lambda x: x[0], reverse=True)
        if scored:
            top_score = scored[0][0]
            filtered_scored = [s for s in scored if s[0] >= max(5, top_score * 0.30)]
            for _, f in filtered_scored[:6]:
                safe_label = "DATA_" + re.sub(r"[^A-Z0-9_]", "_", f.name.upper())
                result[safe_label] = str(f.absolute())

        # Fallback to biophysics datasets if hypothesis is protein/binding/biophysics related
        if not result and candidates:
            is_biophysics = any(kw in statement_lower for kw in [
                "affinity", "binding", "kd", "ddg", "protein", "mutation", "spike", "rbd",
                "ace2", "sars", "amino", "residue", "biophys", "biophysics", "dms",
                "enhancer", "structural", "interface", "omicron"
            ])
            if is_biophysics:
                bio_files = [
                    f for f in candidates
                    if any(str(f.absolute()).lower().endswith(ext) for ext in [".pdb", ".cif", ".ent", ".csv", ".parquet", ".db", ".sqlite"])
                    and any(b in str(f.absolute()).lower() for b in ["pdb", "struct", "complex", "bind", "affinit", "mutation", "protein", "dms", "skempi", "covid"])
                ]
                bio_files.sort(key=lambda f: (0 if f.suffix.lower() in [".pdb", ".cif", ".ent"] else 1, f.name))
                for f in bio_files[:5]:
                    safe_label = "DATA_" + re.sub(r"[^A-Z0-9_]", "_", f.name.upper())
                    result[safe_label] = str(f.absolute())

        # Universal Empirical Database/Dataset Fallback:
        # If the user placed custom databases (.db/.sqlite/.duckdb/.parquet/.csv/.h5) in data/ whose names don't
        # literally appear in the hypothesis statement, bind the primary empirical databases/datasets rather than failing!
        if not result and candidates:
            priority_order = {".db": 0, ".sqlite": 0, ".sqlite3": 0, ".duckdb": 0, ".parquet": 1, ".pq": 1, ".h5": 2, ".hdf5": 2, ".csv": 3, ".tsv": 3, ".pdb": 4}
            sorted_cands = sorted(
                candidates,
                key=lambda f: (priority_order.get(f.suffix.lower(), 5), -f.stat().st_size if f.exists() else 0)
            )
            for f in sorted_cands[:5]:
                safe_label = "DATA_" + re.sub(r"[^A-Z0-9_]", "_", f.name.upper())
                result[safe_label] = str(f.absolute())

        return result

    def build_data_preamble(self, data_paths: Dict[str, str]) -> str:
        """Build a safe, out-of-core-capable Python preamble for the sandbox."""
        if not data_paths:
            return (
                "# ============================================================\n"
                "# [SIMULATION MODE] No physical files bound\n"
                "DATA_PRIMARY = None\n"
                "DF_PRIMARY = None\n"
                "DB_CONN = None\n"
                "# ============================================================\n"
            )

        has_cifar = any("cifar" in str(p).lower() for p in data_paths.values())
        has_pdb = any(str(p).lower().endswith((".pdb", ".ent", ".cif")) for p in data_paths.values())

        lines = [
            "# ============================================================",
            "# [PHYSICAL DATA BONDING] Cleanroom Dataset & Database Harness",
            "# ============================================================",
            "import numpy as np",
            "import pandas as pd",
            "import sqlite3",
            "import os, sys",
            "",
            "MAX_PRELOAD_ROWS = int(os.environ.get('ULTRON_MAX_PRELOAD_ROWS', '500000'))",
            "",
            "def connect_verified_db(path):",
            "    if not path or not os.path.exists(str(path)): return None",
            "    ext = os.path.splitext(str(path))[1].lower()",
            "    if ext in ('.db', '.sqlite', '.sqlite3'):",
            "        try: return sqlite3.connect(f'file:{path}?mode=ro', uri=True)",
            "        except Exception: return sqlite3.connect(str(path))",
            "    return None",
            "",
            "# Smart Data Loader: detects format from file extension, supports SQLite/DuckDB/Parquet/HDF5/CSV with memory-safe row caps",
            "def load_verified_data(path, max_rows=MAX_PRELOAD_ROWS):",
            "    if not os.path.exists(str(path)): return pd.DataFrame()",
            "    ext = os.path.splitext(str(path))[1].lower()",
            "    size_mb = os.path.getsize(str(path)) / (1024 * 1024)",
            "    # 1. Relational / Analytical Databases (.db, .sqlite, .sqlite3, .duckdb)",
            "    if ext in ('.db', '.sqlite', '.sqlite3'):",
            "        try:",
            "            conn = connect_verified_db(path)",
            "            cur = conn.cursor()",
            "            cur.execute(\"SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%';\")",
            "            tables = [r[0] for r in cur.fetchall()]",
            "            if not tables: return pd.DataFrame()",
            "            # Pick table with largest row count or first table",
            "            best_table = tables[0]",
            "            df = pd.read_sql_query(f'SELECT * FROM \"{best_table}\" LIMIT {int(max_rows)}', conn)",
            "            return df",
            "        except Exception:",
            "            return pd.DataFrame()",
            "    if ext == '.duckdb':",
            "        try:",
            "            import duckdb",
            "            conn = duckdb.connect(str(path), read_only=True)",
            "            tables = [r[0] for r in conn.execute('SHOW TABLES').fetchall()]",
            "            if tables:",
            "                return conn.execute(f'SELECT * FROM \"{tables[0]}\" LIMIT {int(max_rows)}').df()",
            "        except Exception:",
            "            return pd.DataFrame()",
            "    # 2. Tabular files (CSV, TSV, TXT) with large-file C-engine protection",
            "    if ext in ('.csv', '.tsv', '.txt'):",
            "        nrows_arg = int(max_rows) if size_mb > 250 else None",
            "        for sep in [',', ';', '\t', None]:",
            "            try:",
            "                if sep is None and size_mb > 100:",
            "                    continue",
            "                df = pd.read_csv(path, sep=sep, engine='python' if sep is None else 'c', nrows=nrows_arg, low_memory=False if sep is not None else True)",
            "                if df.shape[1] > 1:",
            "                    return df",
            "            except Exception:",
            "                continue",
            "        try:",
            "            return pd.read_csv(path, nrows=nrows_arg)",
            "        except Exception:",
            "            return pd.DataFrame()",
            "    # 3. Columnar & Scientific Array Formats (.parquet, .feather, .h5, .npz)",
            "    if ext in ('.parquet', '.pq'):",
            "        try:",
            "            df = pd.read_parquet(path)",
            "            return df.iloc[:int(max_rows)] if len(df) > int(max_rows) else df",
            "        except Exception: return pd.DataFrame()",
            "    if ext in ('.feather', '.arrow', '.ipc'):",
            "        try: return pd.read_feather(path)",
            "        except Exception: return pd.DataFrame()",
            "    if ext in ('.h5', '.hdf5'):",
            "        try: return pd.read_hdf(path)",
            "        except Exception:",
            "            try:",
            "                import h5py",
            "                with h5py.File(path, 'r') as hf:",
            "                    keys = list(hf.keys())",
            "                    if keys: return pd.DataFrame(np.array(hf[keys[0]][:int(max_rows)]))",
            "            except Exception: return path",
            "    if ext in ('.npz', '.npy'):",
            "        try:",
            "            arr = np.load(path, allow_pickle=True)",
            "            if isinstance(arr, np.ndarray): return pd.DataFrame(arr[:int(max_rows)])",
            "            keys = list(arr.keys())",
            "            return pd.DataFrame({k: np.asarray(arr[k]).ravel()[:int(max_rows)] for k in keys if np.asarray(arr[k]).ndim == 1}) if keys else pd.DataFrame()",
            "        except Exception: return path",
            "    if ext in ('.pdb', '.ent', '.cif'):",
            "        return path",
            "    if ext in ('.pt', '.pth'):",
            "        try:",
            "            import torch",
            "            return torch.load(path, map_location='cpu')",
            "        except Exception: return path",
            "    if ext in ('.pkl', '.pickle'):",
            "        try:",
            "            import pickle",
            "            with open(path, 'rb') as f: return pickle.load(f)",
            "        except Exception: return pd.DataFrame()",
            "    try: return pd.read_csv(path, nrows=int(max_rows))",
            "    except Exception: return path",
            ""
        ]

        if has_cifar:
            lines.extend([
                "# CIFAR Convenience Loader",
                "def load_cifar100_dataset(data_dir):",
                "    try:",
                "        import torchvision",
                "        import torchvision.transforms as transforms",
                "        transform = transforms.Compose([transforms.ToTensor()])",
                "        trainset = torchvision.datasets.CIFAR100(root=data_dir, train=True, download=False, transform=transform)",
                "        testset = torchvision.datasets.CIFAR100(root=data_dir, train=False, download=False, transform=transform)",
                "        return trainset, testset",
                "    except Exception:",
                "        return None, None",
                ""
            ])

        if has_pdb:
            lines.extend([
                "# Biopython Structure Convenience Loaders & Energetics (Biophysical Modeling)",
                "def parse_pdb_structure(path, struct_id='target'):",
                "    try:",
                "        from Bio.PDB import PDBParser",
                "        parser = PDBParser(QUIET=True)",
                "        return parser.get_structure(struct_id, path)",
                "    except Exception:",
                "        return None",
                "",
                "def calculate_atomic_contacts(structure, chain_a=None, chain_b=None, cutoff=4.5):",
                "    try:",
                "        from Bio.PDB import NeighborSearch",
                "        model = structure[0]",
                "        chains = [c.id for c in model.get_chains()]",
                "        if not chains: return []",
                "        ca = chain_a if (chain_a and chain_a in model) else chains[0]",
                "        cb = chain_b if (chain_b and chain_b in model) else (chains[1] if len(chains) > 1 else chains[0])",
                "        if ca == cb: return []",
                "        atoms_b = [a for a in model[cb].get_atoms() if a.element != 'H']",
                "        ns = NeighborSearch(atoms_b)",
                "        contacts = set()",
                "        for a in model[ca].get_atoms():",
                "            if a.element == 'H': continue",
                "            close = ns.search(a.coord, cutoff, level='R')",
                "            for res_b in close:",
                "                contacts.add((a.get_parent().id[1], res_b.id[1]))",
                "        return sorted(list(contacts))",
                "    except Exception:",
                "        return []",
                "",
                "def calculate_buried_sasa(structure, chain_a=None, chain_b=None):",
                "    try:",
                "        from Bio.PDB import ShrakeRupley, Structure, Model",
                "        model = structure[0]",
                "        chains = [c.id for c in model.get_chains()]",
                "        if not chains: return {}",
                "        ca = chain_a if (chain_a and chain_a in model) else chains[0]",
                "        cb = chain_b if (chain_b and chain_b in model) else (chains[1] if len(chains) > 1 else chains[0])",
                "        sr = ShrakeRupley()",
                "        sr.compute(structure, level='R')",
                "        bound_sasa = {(r.get_parent().id, r.id[1]): getattr(r, 'sasa', 0.0) for r in structure.get_residues()}",
                "        struct_b = Structure.Structure(cb)",
                "        mod_b = Model.Model(0)",
                "        mod_b.add(structure[0][cb].copy())",
                "        struct_b.add(mod_b)",
                "        sr.compute(struct_b, level='R')",
                "        unbound_sasa_b = {r.id[1]: getattr(r, 'sasa', 0.0) for r in struct_b.get_residues()}",
                "        buried = {resid: max(0.0, u_s - bound_sasa.get((cb, resid), u_s)) for resid, u_s in unbound_sasa_b.items()}",
                "        return buried",
                "    except Exception:",
                "        return {}",
                "",
                "def calculate_coulomb_energies(structure, chain_a=None, chain_b=None, cutoff=12.0):",
                "    try:",
                "        import numpy as np",
                "        model = structure[0]",
                "        chains = [c.id for c in model.get_chains()]",
                "        if not chains: return []",
                "        ca = chain_a if (chain_a and chain_a in model) else chains[0]",
                "        cb = chain_b if (chain_b and chain_b in model) else (chains[1] if len(chains) > 1 else chains[0])",
                "        if ca == cb: return []",
                "        charges = {'ARG': {'CZ': 1.0}, 'LYS': {'NZ': 1.0}, 'ASP': {'CG': -1.0}, 'GLU': {'CD': -1.0}, 'HIS': {'CE1': 0.5}}",
                "        charged_a = [(r.id[1], r.get_resname(), q, r[at].coord) for r in model[ca].get_residues() if r.get_resname() in charges for at, q in charges[r.get_resname()].items() if at in r]",
                "        charged_b = [(r.id[1], r.get_resname(), q, r[at].coord) for r in model[cb].get_residues() if r.get_resname() in charges for at, q in charges[r.get_resname()].items() if at in r]",
                "        results = []",
                "        k_e = 332.0637",
                "        for id_a, name_a, q_a, c_a in charged_a:",
                "            for id_b, name_b, q_b, c_b in charged_b:",
                "                d = np.linalg.norm(c_a - c_b)",
                "                if d < cutoff:",
                "                    e_val = (k_e * q_a * q_b) / (4.0 * d * d)",
                "                    results.append({'chain_a_res': id_a, 'resname_a': name_a, 'chain_b_res': id_b, 'resname_b': name_b, 'dist_angstrom': float(d), 'e_coulomb_kcal_mol': float(e_val)})",
                "        results.sort(key=lambda x: x['e_coulomb_kcal_mol'])",
                "        return results",
                "    except Exception:",
                "        return []",
                ""
            ])

        for label, path in data_paths.items():
            lines.append(f'{label} = r"{path}"')
            df_label = "DF_" + label.replace("DATA_", "")
            lines.append(f"{df_label} = load_verified_data({label})")

        if data_paths:
            tabular_keys = [
                k for k, p in data_paths.items()
                if any(str(p).lower().endswith(ext) for ext in [".db", ".sqlite", ".sqlite3", ".duckdb", ".csv", ".tsv", ".parquet", ".pq", ".feather", ".h5", ".hdf5", ".npz"])
            ]
            first_label = tabular_keys[0] if tabular_keys else list(data_paths.keys())[0]
            first_df_label = "DF_" + first_label.replace("DATA_", "")
            lines.append(f"DATA_PRIMARY = {first_label}")
            lines.append(f"DF_PRIMARY = {first_df_label}")
            lines.append("DB_CONN = connect_verified_db(DATA_PRIMARY)")
            pdb_keys = [k for k, p in data_paths.items() if any(str(p).lower().endswith(ext) for ext in [".pdb", ".ent", ".cif"])]
            if pdb_keys:
                lines.append(f"DATA_PDB = {pdb_keys[0]}")
                lines.append("STRUCTURE_PRIMARY = parse_pdb_structure(DATA_PDB)")

        lines.append("# ============================================================")
        return "\n".join(lines)

    def get_data_context_for_prompt(self, data_paths: Dict[str, str]) -> str:
        """Build a rich schema context string (tables, columns, types, row counts) for the LLM prompt."""
        if not data_paths:
            return "No relevant physical datasets found in vault."

        context = ["### AVAILABLE PHYSICAL DATASETS & DATABASES:"]
        context.append("CRITICAL DATA HANDLING PROTOCOL:")
        context.append("- For .csv / .tsv / .parquet files: use pre-injected `DF_PRIMARY` / `DF_*` variables or `pd.read_csv(DATA_PRIMARY)` / `pd.read_parquet(DATA_PRIMARY)`.")
        context.append("- For .db / .sqlite / .sqlite3 relational databases: `DF_PRIMARY` is pre-loaded with the primary table (up to 500k rows), AND `DB_CONN` (`sqlite3.connect(DATA_PRIMARY)`) is pre-connected so you can execute multi-table SQL joins and aggregations via `pd.read_sql_query('SELECT ...', DB_CONN)`.")
        context.append("- For .pdb / .cif structural files: parse coordinates using `STRUCTURE_PRIMARY` / `Bio.PDB`.")
        context.append("")
        for label, path in data_paths.items():
            try:
                p = Path(path)
                stats = p.stat()
                size_mb = stats.st_size / (1024 * 1024)
                fmt_hint = ""
                ext = p.suffix.lower()
                if ext in (".db", ".sqlite", ".sqlite3"):
                    import sqlite3
                    conn = sqlite3.connect(f"file:{p.absolute()}?mode=ro", uri=True)
                    cur = conn.cursor()
                    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%';")
                    tables = [r[0] for r in cur.fetchall()]
                    t_summaries = []
                    for t in tables[:15]:
                        cur.execute(f'PRAGMA table_info("{t}");')
                        cols = [f"{r[1]} ({r[2]})" for r in cur.fetchall()]
                        try:
                            cur.execute(f'SELECT COUNT(*) FROM "{t}";')
                            rc = cur.fetchone()[0]
                        except Exception:
                            rc = "?"
                        t_summaries.append(f"Table `{t}` (rows={rc}, cols={cols})")
                    conn.close()
                    fmt_hint = f" | FORMAT=SQLite_DATABASE | Tables ({len(tables)}): " + " ; ".join(t_summaries)
                elif ext in (".parquet", ".pq"):
                    try:
                        import pyarrow.parquet as pq
                        meta = pq.read_metadata(p)
                        schema = pq.read_schema(p)
                        cols = [f"{name}:{ str( dtype ) }" for name, dtype in zip(schema.names, schema.types)]
                        fmt_hint = f" | FORMAT=PARQUET (rows={meta.num_rows}) | Columns ({len(cols)}): {cols[:60]}"
                    except Exception:
                        import pandas as pd
                        df_s = pd.read_parquet(p)
                        fmt_hint = f" | FORMAT=PARQUET (rows={len(df_s)}) | Columns ({ len(df_s.columns) }): {list(df_s.columns)[:60]}"
                elif ext in (".csv", ".tsv", ".txt"):
                    import pandas as pd
                    col_names = []
                    for sep in [None, ";", "\t", ","]:
                        try:
                            df_sample = pd.read_csv(p, sep=sep, engine="python" if sep is None else "c", nrows=2)
                            if df_sample.shape[1] > 1:
                                col_names = list(df_sample.columns)
                                fmt_hint = f" | FORMAT=TABULAR (sep='{sep or 'auto'}') | Columns ({len(col_names)}): {col_names}"
                                break
                        except Exception:
                            continue
                    if not col_names:
                        fmt_hint = " | FORMAT=CSV"
                elif ext in (".h5", ".hdf5"):
                    try:
                        import h5py
                        with h5py.File(p, "r") as hf:
                            k_info = [f"{k}:shape={getattr(hf[k], 'shape', '?')}" for k in list(hf.keys())[:30]]
                        fmt_hint = f" | FORMAT=HDF5 | Datasets: {k_info}"
                    except Exception:
                        fmt_hint = " | FORMAT=HDF5"
                elif ext in (".pdb", ".ent", ".cif"):
                    struct_info = ""
                    try:
                        from Bio.PDB import PDBParser
                        parser = PDBParser(QUIET=True)
                        st = parser.get_structure("meta", p)
                        chains = [c.id for c in st[0].get_chains()]
                        struct_info = f" | CHAINS={chains} | BIO_PDB_AVAILABLE=True"
                    except Exception:
                        pass
                    fmt_hint = (
                        f" | FORMAT=PDB_STRUCTURE{struct_info} | "
                        "MANDATORY BIOPHYSICAL PROTOCOL: Parse 3D coordinates using Bio.PDB, calculate atomic distances "
                        "across chains, compute interface contacts (< 4.5A), buried SASA, or Coulombic salt bridges. "
                        "Do NOT merely sort a CSV; perform genuine 3D structural biophysical modeling."
                    )
                elif ext in (".pkl", ".pickle"):
                    fmt_hint = " | FORMAT=PICKLE (use pickle.load)"
                elif "cifar" in str(path).lower():
                    fmt_hint = " | FORMAT=BINARY_PICKLE (CIFAR batch, use pickle.load with encoding='bytes')"
                else:
                    fmt_hint = f" | FORMAT={ext.upper().lstrip('.') or 'DATA'}"

                context.append(f"- variable `{label}`: path={path} | size={size_mb:.2f}MB{fmt_hint}")
            except Exception as e:
                context.append(f"- variable `{label}`: path={path} (Error reading meta: {e})")

        return "\n".join(context)


def resolve_data_for_hypothesis(hypothesis_statement: str) -> Dict[str, str]:
    return DataResolver().resolve_data_for_hypothesis(hypothesis_statement)

def build_data_preamble(data_paths: Dict[str, str]) -> str:
    return DataResolver().build_data_preamble(data_paths)

def get_data_context_for_prompt(data_paths: Dict[str, str]) -> str:
    return DataResolver().get_data_context_for_prompt(data_paths)

def load_verified_data(path: str):
    """Load verified tabular or structural dataset with robust delimiter sniffing."""
    import pandas as pd
    if not os.path.exists(path):
        return pd.DataFrame()
    ext = os.path.splitext(path)[1].lower()
    if ext in ('.csv', '.tsv', '.txt'):
        for sep in [None, ';', '\t', ',']:
            try:
                df = pd.read_csv(path, sep=sep, engine='python' if sep is None else 'c')
                if df.shape[1] > 1:
                    return df
            except Exception:
                continue
        try:
            return pd.read_csv(path, sep=None, engine='python')
        except Exception:
            return pd.DataFrame()
    if ext in ('.parquet', '.pq'):
        try:
            return pd.read_parquet(path)
        except Exception:
            return pd.DataFrame()
    return path

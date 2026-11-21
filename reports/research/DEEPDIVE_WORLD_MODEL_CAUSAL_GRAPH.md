# EXHAUSTIVE AUDIT: SVEL WORLD MODEL & CAUSAL GRAPH ENGINE

**Target Files Audited:**
1. `/Users/samaraldico/SVEL AI Scientist/backend/core/world_model.py` (143 KB, 3,593 lines)
2. `/Users/samaraldico/SVEL AI Scientist/backend/memory/knowledge_graph.py` (51 KB, 1,226 lines)
3. `/Users/samaraldico/SVEL AI Scientist/backend/core/state/persistence_vault.py` (5 KB, 128 lines)

---

## 1. Data Models: The Epistemic Triad
- **Fact**: SHA-256 content addressing (`SHA256(key:value)[:16]`), immutable source attribution, and `reasoning_trace` for multi-cycle self-correction.
- **Assumption**: Dual Architecture:
  - Directed Acyclic Graph (`AssumptionGraph` in `backend/discovery/assumption_graph.py`): Root = Approach Viable, Leaves = Measurable constraints. Leaf violation cascades upward to invalidate all parent branches; permanently logged in `killed_hashes` to prevent zombie revival.
  - WorldModel `Entity(type="Hypothesis")`: Subject to Epistemic Reaper reconciliation and Thanos Protocol pruning.
- **Seek**: `Entity(type="ResearchQuestion")` and `Task` priority deque.
- **Temporal Hypergraph**:
  - `Relationship`: Binary edges with `is_valid_at(timestamp)` checking `valid_until` and deprecation flags.
  - `HyperEdge`: Multi-node hypergraph connectors: $(A_1 + A_2) \xrightarrow{\text{type}} (B_1 + B_2)$.
  - `TemporalFact`: Auto-invalidation on newer timestamps ($T_2 > T_1 \implies \text{valid\_until}_1 = T_2$).

---

## 2. Causal Inference Engine: BFS Multiplier Decay
- Simulates intervention along causal links ($S \in [-1.0, 1.0]$, $C \in [0.0, 1.0]$):
  $$\mu_k = \prod_{i=0}^{k-1} (S_{v_i \to v_{i+1}} \times C_{v_i \to v_{i+1}})$$
  Accumulates downstream effect: $\text{Effect}(w) = \sum_{\pi} \mu_\pi$.
  Branch pruning threshold: halts when $|\mu_k| \le 0.1$.
- DFS causal path discovery up to `max_depth = 5`.

---

## 3. Graph Mining & REM Sleep Engine
- **PageRank**: Damped power iteration ($d=0.85$, 100 iterations) over active, non-deprecated relationships.
- **Label Propagation**: Raghavan heuristic community detection converging upon neighborhood consensus.
- **GNN Dream Phase**: Trains 4 architectures (GCN, GAT, SAGE, GIN) via validation AUC-ROC, selecting optimal representations for missing-link hypothesis generation.
- **Thanos Protocol**: Sweeps hypotheses older than 5 minutes (`age > 300s`), purging those below confidence threshold or supported by fewer than 2 independent sources.

---

## 4. Persistence Architecture & Critical Flaws
- **SQLite WAL Mode**: Thread-local cursors, 60s busy timeout, 64MB page cache, 10 progressive retries.
- **Pickle Elimination**: Complete elimination of `.pkl` files in favor of atomic `.tmp -> fsync -> replace` JSON persistence.
- **Critical Flaws Found**:
  1. `simulate_intervention(entity_id, new_state)` accepts `new_state` but never uses it in calculations (starts unconditionally at 1.0).
  2. `add_hyperedge` calls non-existent `save_hyperedge` on `KnowledgeGraph`.
  3. Missing `self.session_id` on `KnowledgeGraph` causing crashes when querying Neo4j.
  4. In-memory deletion only: `delete_entity` and `delete_relationship` never execute SQL `DELETE`, causing deleted entities to resurrect on restart.
  5. Unplayed sync outbox: `neo4j_outbox.jsonl` appends failures but is never replayed.

# EXHAUSTIVE TECHNICAL AUDIT: SVEL GNN ORACLE & GRAPH INTELLIGENCE

**Target Files Audited:**
- `/Users/samaraldico/SVEL AI Scientist/backend/graphs/gnn_oracle.py` (1,703 lines)
- `/Users/samaraldico/SVEL AI Scientist/backend/core/discovery_rigor.py` (98 lines)
- Cross-referenced: `/Users/samaraldico/SVEL AI Scientist/backend/orchestration/deep_research_orchestrator.py` (Lines 1920–2053), `backend/core/world_model.py` (Lines 1100–1250), and `svel_bible.md`.

---

## 1. PyTorch Geometric GNN Architecture Analysis

### A. Core Architecture Zoo & Encoders (`gnn_oracle.py:136–340`)
The GNN Oracle implements an ensemble of **5 graph convolution encoders** subclassing `_BaseEncoder(nn.Module)` (lines 136–148), which initializes Batch Normalization (`bn1`: $d_{hidden}$, `bn2`: $d_{out}$) and dropout ($p=0.3$):

1. **GCNEncoder** (`gnn_oracle.py:151–172`):
   - **Layers**: 2x `torch_geometric.nn.GCNConv`.
     - `conv1`: $d_{in} \to d_{hidden}$
     - `conv2`: $d_{hidden} \to d_{out}$
   - **Operations**: `conv1` $\to$ `bn1` $\to$ `ReLU` $\to$ `Dropout(p=0.3)` (MC stochastic override) $\to$ `conv2` $\to$ `bn2`.
   - **Inductive Bias**: Symmetric normalized graph Laplacian filtering. Best on dense, homophilous citation/association graphs.

2. **GATEncoder** (`gnn_oracle.py:174–199`):
   - **Layers**: 2x `torch_geometric.nn.GATConv` with multi-head self-attention.
     - Heads: 4 heads. `out_heads = max(1, hidden_channels // 4)`.
     - `conv1`: $d_{in} \to out\_heads$ with 4 heads ($4 \times out\_heads = d_{hidden}$).
     - `conv2`: $(out\_heads \times 4) \to d_{out}$ with 1 head (`concat=False`).
   - **Operations**: `conv1` $\to$ `bn1` (if $N > 1$) $\to$ `ELU` $\to$ `Dropout` $\to$ `conv2` $\to$ `bn2` (if $N > 1$).
   - **Inductive Bias**: Learns anisotropic attention weights $\alpha_{ij}$ over neighbor nodes.

3. **SAGEEncoder** (`gnn_oracle.py:201–222`):
   - **Layers**: 2x `torch_geometric.nn.SAGEConv`.
     - `conv1`: $d_{in} \to d_{hidden}$
     - `conv2`: $d_{hidden} \to d_{out}$
   - **Operations**: `conv1` $\to$ `bn1` $\to$ `ReLU` $\to$ `Dropout` $\to$ `conv2` $\to$ `bn2`.
   - **Inductive Bias**: Inductive mean neighborhood aggregation; generalizes well to unseen nodes.

4. **GINEncoder** (`gnn_oracle.py:224–259`):
   - **Layers**: 2x `torch_geometric.nn.GINConv` (Graph Isomorphism Network).
   - **Sub-MLP Architectures**:
     - `nn1`: `Linear(in, hidden)` $\to$ `LayerNorm(hidden)` $\to$ `ReLU` $\to$ `Linear(hidden, hidden)`.
     - `nn2`: `Linear(hidden, out)` $\to$ `LayerNorm(out)` $\to$ `ReLU` $\to$ `Linear(out, out)`.
   - **Operations**: `conv1(nn1)` $\to$ `ReLU` $\to$ `Dropout` $\to$ `conv2(nn2)`.
   - **Inductive Bias**: WL-1 (Weisfeiler-Lehman 1-isomorphism) graph equivalence. Uses `LayerNorm` instead of `BatchNorm1d` (lines 232–237) to prevent batch norm collapse during single-node batched inference.

5. **RGCNEncoder** (`gnn_oracle.py:309–340`):
   - **Layers**: 2x `torch_geometric.nn.RGCNConv` (Relational Graph Convolution).
   - **Basis Decomposition**: `effective_bases = min(num_bases=30, num_relations)`.
   - **Operations**: Accepts `edge_type` $(E,)$ LongTensor. Encodes distinct relation types (e.g. `CAUSES`, `INFLUENCES`, `RELATED_TO`, `SUPPORTS`, `INFERRED_LINK`).

### B. Decoders & Link Predictor (`gnn_oracle.py:265–394`)
- **DotProductDecoder** (`gnn_oracle.py:265–277`): Vectorized dot product $\hat{y}_{uv} = z_u \cdot z_v = \sum_{k=1}^{d} z_{u,k} z_{v,k}$.
- **MLPDecoder** (`gnn_oracle.py:279–304`):
  - Input: Concatenated node vectors $[z_u \,\|\, z_v] \in \mathbb{R}^{2 \cdot d_{out}}$.
  - Layers: `Linear(2 * d_{out}, d_{out})` $\to$ `ReLU` $\to$ `Dropout(0.2)` $\to$ `Linear(d_{out}, 1)`.
- **LinkPredictor** (`gnn_oracle.py:341–394`):
  - Bridges encoder and decoder.
  - Memory-safe traversal (`decode_all`, lines 366–392): For `MLPDecoder`, computes full adjacency using chunked block traversal with `BLOCK_SIZE = int(os.getenv("SVEL_GNN_BLOCK_SIZE", "512"))`, preventing $O(N^2)$ VRAM explosion on large graphs.

### C. Node & Edge Feature Pipeline
- **Semantic Feature Engine** (`gnn_oracle.py:400–484`):
  - Strategy 1: Pre-computed embeddings from `WorldModel` ($d \approx 384$ or $768$).
  - Strategy 2: Lazy-loaded shared `SentenceTransformer` (`get_shared_embedding_model()`, SBERT `all-MiniLM-L6-v2`, 384 dimensions) on node descriptive texts (`node_texts`).
  - Strategy 3: Random Gaussian noise is **strictly blocked** (lines 479–483):
    `raise RuntimeError("GNN Oracle Training Suspended: Semantic feature extraction failed. Refusing to train on random hunch manifold noise.")`
- **Edge Features & Indexing** (`gnn_oracle.py:989–1037`):
  - `edge_index`: `torch.long` tensor of shape `(2, E)`.
  - `edge_type`: `torch.long` tensor of shape `(E,)` for multi-relational graphs.

---

## 2. The "Dream Phase": Novel Edge Prediction & Manifold Exploration

The Dream Phase operates as SVEL's "Subconscious Discovery" loop (REM Sleep). It predicts edges $(u, v) \notin E_{observed}$ using **Monte Carlo Dropout Bayesian Posterior Sampling** and **Upper Confidence Bound (UCB)** exploration:

### A. Local Dream (`gnn_oracle.py:1162–1300`)
- Predicts missing connections for a designated seed entity $u$.
- Evaluates scores across all candidate targets $v \in V \setminus (\{u\} \cup \mathcal{N}(u))$.
- Runs $T = 50$ forward passes with stochastic dropout enabled (`stochastic_mode = True`, line 1199).
- Calculates mean score $\mu_{uv}$ and epistemic uncertainty $\sigma_{uv} = \text{std}(\hat{y}_{uv})$.

### B. Deep Dream (Global Discovery, `gnn_oracle.py:1302–1492`)
- **Pair Generation**:
  - Small graphs ($N^2 \le 500,000$): Uses `torch.meshgrid` to construct complete non-diagonal candidate adjacency pairs.
  - Large graphs ($N^2 > 500,000$): Rejection-samples up to 500,000 unique non-existing random pairs $(s, t)$ to avoid OOM.
- **Online Welford-like Variance Accumulation** (lines 1360–1391):
  - Accumulates $\sum \text{adj}_t$ and $\sum \text{adj}_t^2$ across $T = 50$ stochastic forward passes in 100,000-edge chunks.
  - $\mu = \frac{1}{T} \sum_{t=1}^{T} \sigma(\text{logits}_t)$
  - $\sigma = \sqrt{\max\left(\frac{\sum \text{adj}^2 - (\sum \text{adj})^2 / T}{T - 1}, 10^{-8}\right)}$
- **Bayesian Active Exploration (UCB Score)** (lines 1392–1408):
  $$\text{Score}_{UCB} = \mu + \kappa \cdot \sigma \quad (\kappa = 2.0)$$
  This explicitly values **both high confidence** and **high epistemic uncertainty**, driving the system to explore unmapped territory in the knowledge manifold.

---

## 3. Training Pipelines vs. Hallucinated Edge Generation

**7-Layer Anti-Hallucination Armor Currently in Place:**
1. **Uninitialized State Rejection** (`gnn_oracle.py:1171, 1311`): Immediately aborts if uninitialized.
2. **Anti-Random Noise Training Circuit-Breaker** (`gnn_oracle.py:479–483`): Hard `RuntimeError` if semantic embeddings fail $>50\%$ graph coverage.
3. **Internal GNN Signal Gate** (`gnn_oracle.py:1185–1190, 1318–1323`): Blocks dreaming if validation $\text{AUC} < 0.40$.
4. **Orchestrator Minimum Edge Gate** (`deep_research_orchestrator.py:1942–1945`): Enforces `MIN_EDGES_FOR_GNN = 200`.
5. **Confidence Attenuation Functions** (`gnn_oracle.py:1230–1234, 1434–1445`): $\text{Final Conf} = \text{Raw Conf} \times \text{sparsity} \times \text{quality} \times 0.85$.
6. **Physical Grounding Bridge** (`discovery_rigor.py:20–76`): Cross-checks edges with `CorrelationChecker` on physical transcriptomic matrices ($|r| < 0.35 \implies$ crushed $0.1\times$).
7. **Downstream Hallucination Suppression** (`deep_research_orchestrator.py:2011–2014`): Edges tagged `[HALLUCINATION ALERT]` suppressed from hypothesis conversion.

---

## 4. GNN Output Integration & Discovery Prioritization

Unbroken pipeline from graph topology to hypothesis:
1. **Uncertainty-Aware Prioritization** (`deep_research_orchestrator.py:1982–1986`): $\text{Rank} = \text{Confidence} \times (1.0 - \sigma)$.
2. **Formal Hypothesis Construction** (`deep_research_orchestrator.py:2016–2042`): $Y = k \cdot X$ with testable correlation $|r| > 0.40$.
3. **Novelty Verification**: Verified against prior corpus via `NoveltyChecker`.

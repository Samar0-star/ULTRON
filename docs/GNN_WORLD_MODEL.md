# Graph Neural Network World Model & Causal Graph

Language models process scientific literature as linear text tokens, obscuring non-linear, cross-disciplinary connections. ULTRON couples frontier language models with a persistent **Causal World Model** and **Graph Neural Network (GNN) Intuition Oracle**.

---

## 1. World Model Architecture

The World Model acts as the persistent cognitive substrate of ULTRON across multi-day campaigns:

* **Storage Substrate**: SQLite Write-Ahead Logging (WAL) database enabling high-throughput concurrent reads and writes from multiple worker agents.
* **Causal Directed Acyclic Graph (DAG)**:
  * **Nodes**: Empirical facts, verified literature observations, chemical formulas, binding constants, crystal lattices, and candidate molecules.
  * **Edges**: Causal relationships, stoichiometric ratios, structural symmetries, and mathematical dependencies.

---

## 2. The GNN Intuition Oracle

To generate non-obvious hypotheses, ULTRON utilizes a Graph Convolutional Network / Graph Isomorphism Network (GCN / GIN):

1. **Topology Embedding**: Literature facts and experimental results are embedded into a unified heterogeneous graph topology.
2. **Link Prediction**: The GNN performs link prediction between disparate clusters (e.g., connecting a solid-state electrolyte crystal phase with a protein docking electrostatic interface).
3. **Uncertainty Quantification**: Every predicted link includes an uncertainty score $\sigma$. High-novelty, low-uncertainty links are prioritized for experimental protocol design.

```
[Literature Entity A] ─── (Causal Link) ───► [Chemical Property B]
        │                                             ▲
        │                                             │
 (GNN Link Prediction)                     (Deterministic Physics Check)
        │                                             │
        ▼                                             │
[Literature Entity C] ─── (Observed Fact) ───► [Lattice Constant D]
```

By querying the GNN Intuition Oracle, the system generates hypotheses derived from topological proximity in structural embedding space rather than stochastic language token completion.

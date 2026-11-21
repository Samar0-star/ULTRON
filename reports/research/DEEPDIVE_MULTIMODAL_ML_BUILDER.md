# Comprehensive Audit: SVEL Multi-Modal ML Model Builder

Target Files Audited:
1. `/Users/samaraldico/SVEL AI Scientist/backend/tools/ml_model_builder_tool.py` (2205 lines, 89KB)
2. `/Users/samaraldico/SVEL AI Scientist/backend/agents/ml_model_builder_agent.py` (706 lines, 28KB)

---

## 1. The `CrossAttentionFusionModel`: 6-Modality Ingestion

### Architectural Overview & Dimensions
The `CrossAttentionFusionModel` (`ml_model_builder_tool.py:L1180-1346`) is a deep multi-modal architecture designed for GSTM Level 10/11 challenges. It integrates 6 distinct modalities, learnable missing-modality parameters, dynamic masking, and cross-attention.

Total concatenated fusion dimension:
$$\text{Fusion Dim} = \underbrace{128}_{\text{Attended DNA}\to\text{Img}} + \underbrace{128}_{\text{DNA direct}} + \underbrace{64}_{\text{Metadata}} + \underbrace{32}_{\text{Time Series}} + \underbrace{64}_{\text{Text}} + \underbrace{1}_{\text{Graph Degree}} + \underbrace{5}_{\text{Modality Mask}} = 422$$

### Modality Encoders & Ingestion Pipelines

1. **Modality 1: Image (2D CNN)** (`L1190-1198, L1262-1269`)
   - **Input**: `batch['image']` $\in \mathbb{R}^{B \times 3 \times H \times W}$, normalized to $[0, 1]$ (`L1056`).
   - **Backbone**: 3-stage Conv2d cascade (32 -> 64 -> 128) + AdaptiveAvgPool2d(1) -> Linear(128, 128).
   - **Missing Imputation**: Learnable embedding $\mathbf{e}_{\text{img}} \in \mathbb{R}^{1 \times 128}$ gated via binary mask.

2. **Modality 2: DNA Sequence (1D CNN + Multihead Cross-Attention with Image)** (`L1199-1209, L1271-1298`)
   - **Input**: `batch['dna']` $\in \mathbb{Z}^{B \times 2000}$ (fixed length 2000, mapped via $A=0, C=1, G=2, T=3, N=4$).
   - **Cross-Attention Mechanism** (`L1280-1291`): Query $\mathbf{Q} = \mathbf{f}_{\text{dna\_raw}}$, Key & Value $\mathbf{K} = \mathbf{V} = \mathbf{f}_{\text{img}}$.
   - Multihead Attention: 4 heads, $d=128$, dropout 0.2.

3. **Modality 3: Categorical Metadata** (`L882-920, L1210-1215, L1300-1309`)
   - Embeds `terrain` (16d), `solar_wind` (8d), `orbit_zone` (8d), `gap_id` (32d) -> Concatenated to 64d.

4. **Modality 4: Time Series (1D CNN + LSTM)** (`L1137-1156, L1217, L1311-1317`)
   - 100 steps, 5 channels -> Conv1d cascade -> AdaptiveAvgPool1d(10) -> LSTM(64 -> 32) -> 32d.

5. **Modality 5: Text (Char-level CNN)** (`L1158-1178, L1218, L1319-1325`)
   - ASCII character tokens $\in \mathbb{Z}^{B \times 200}$ -> Conv1d cascade -> AdaptiveAvgPool1d(1) -> 64d.

6. **Modality 6: Graph Features** (`L1024-1036, L1227, L1326-1333`)
   - Average topological node degree $\bar{d} \in \mathbb{R}^{B \times 1}$.

7. **MLP Regression Head**:
   - $\text{Linear}(422 \to 256) \to \text{ReLU} \to \text{Dropout}(0.3) \to \text{Linear}(256 \to 128) \to \text{ReLU} \to \text{Linear}(128 \to 1)$.

---

## 2. The `AdaptiveRobustLoss`: Dynamic Outlier Rejection

Computes unreduced MSE residuals $\mathbf{L} \in \mathbb{R}^B$, extracts indices corresponding to the $k = \lfloor B \cdot \alpha \rfloor$ smallest loss values using `torch.topk(loss, k, largest=False)`, and backpropagates solely on $\mathbf{L}_{\text{clean}}$. Top $(1 - \alpha)$ outliers receive exactly zero gradient.

---

## 3. Critical Failure Modes & Architectural Flaws

1. **Target Column Mismatch Bug (`L1694-1792`)**: `fit_multimodal` passes no `target_col` to `_load_data_internal`, defaulting targets to `torch.zeros(len(images))`.
2. **Unbound Variables in Agent (`L507-529`)**: `images`, `dna`, and `target_col` are referenced before assignment in `_load_multimodal_data`.
3. **Batch Size 1 Squeeze Crash (`L1345, L1358`)**: `regressor(combined).squeeze()` turns batch size 1 into a 0D scalar, breaking `loss.size(0)` and `predictions.extend()`.
4. **Phony Model Saving (`L1891-1915`)**: `save_model` writes only JSON metadata; actual `.pkl` / `.pt` PyTorch weights saving is commented out as a placeholder.

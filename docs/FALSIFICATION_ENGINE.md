# Adversarial Falsification & The Morgue

A core failure mode in AI-driven science is **confirmation bias**: language models prompted to find a discovery will hallucinate positive evidence to satisfy the user's prompt. 

ULTRON enforces strict **Popperian Falsification**: a hypothesis is never accepted simply because an LLM claims it works; it must actively survive rigorous mathematical, empirical, and adversarial destruction attacks.

---

## 1. Why Self-Evaluation Fails

Standard agentic setups ask LLMs to "evaluate" their own work using prompt chains (e.g., *"Critique your previous code and fix any errors"*).

In real autonomous experiments, this fails consistently:
* LLMs double down on initial hallucinations.
* When presented with contradictory data, models hallucinate statistical workarounds rather than refuting their own premise.
* Prompt-based guardrails leak tokens and degrade after multiple iterations.

**ULTRON's Solution**: Zero-token external mathematical falsification. Hypotheses are subjected to external code verification and adversarial red-teaming where the attacking agent is explicitly rewarded for killing the hypothesis.

---

## 2. Adversarial Attack Protocols

During an autonomous campaign, every candidate hypothesis is assaulted through five orthogonal attack vectors:

### Attack 1: Parameter Sign-Crossing & Derivative Inversion
* Tests if the claimed mathematical effect reverses or collapses when parameters are perturbed within empirical error bounds.
* If a model claims $\beta_{\text{eff}} = \beta_1 + \beta_2 \cdot \sigma$ crosses zero at a specific threshold, 2,000 bootstrap resamples are conducted to verify the crossing mathematically exists.

### Attack 2: Confounder Collinearity & Covariate Shift
* Evaluates whether the claimed correlation is an artifact of unobserved confounders (e.g., atomic mass variance masking true valence contributions).

### Attack 3: Placebo & Permutation Stress Tests
* Re-runs the simulation with scrambled target labels and randomized feature identities across 1,000–5,000 resamples.
* If the hypothesis performs equally well on randomized placebo data ($p > 0.01$), it is instantly killed.

### Attack 4: Out-of-Family Generalization Holdout
* Evaluates the candidate against distinct chemical families or structural classes absent from the training context.

### Attack 5: Statistical Significance & Effect Size Thresholds
* Mandatory statistical gates:
  * Significance threshold: $p < 0.01$
  * Effect size: Cohen's $|d| \ge 0.5$
  * Critical boundary: Welch-Z score $|Z| \ge 2.576$

---

## 3. "The Morgue": Semantic Kill-Chain Memory

When a hypothesis fails an adversarial gate, it is not simply discarded. It is recorded in **The Morgue**—a persistent database of refuted hypotheses, failure mechanisms, and mathematical contradictions.

* **Elimination of Cyclical Rediscovery**: Autonomous LLMs frequently regenerate previously failed hypotheses 30 minutes later in an execution loop.
* **Active Falsification Guidance**: The Scholar agent checks candidate hypotheses against The Morgue embeddings before scheduling experiments, ensuring 0% compute waste on known dead ends.

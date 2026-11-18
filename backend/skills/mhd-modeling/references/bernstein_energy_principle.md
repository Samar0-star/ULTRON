# Bernstein Energy Principle (1958)
CITED AS: Bernstein, Frieman, Kruskal, Kulsrud, Proc. R. Soc. London A244, 17.

## Abstract
Provides the foundational variational principle for MHD stability. A system is stable if and only if the change in potential energy δW is positive for all perturbations ξ.

## The Mathematical Foundation
The total change in potential energy is decomposed into three components:
δW = δW_plasma + δW_surface + δW_vacuum

### Plasma Term (δW_F)
The most critical term for ELM and Ballooning analysis:
δW_F = (1/2μ₀) ∫ [ |Q_⊥|² + B²|∇·ξ_⊥ + 2ξ_⊥·κ|² - μ₀(ξ_⊥·∇p)(2ξ_⊥·κ) - μ₀J_∥(ξ_⊥×b̂)·Q + γp|∇·ξ|² ] dV

### Physical Interpretation
1. **|Q_⊥|²**: Magnetic field line bending (Always stabilizing).
2. **B²|∇·ξ_⊥ + 2ξ_⊥·κ|²**: Magnetic compression (Always stabilizing).
3. **-μ₀(ξ_⊥·∇p)(2ξ_⊥·κ)**: Pressure-driven term (Destabilizing in 'bad curvature' regions where ∇p and κ are aligned).
4. **-μ₀J_∥(ξ_⊥×b̂)·Q**: Current-driven term (Destabilizing for Kink modes).
5. **γp|∇·ξ|²**: Fluid compression (Always stabilizing).

## Application to Tokamaks
In the H-mode pedestal, the pressure-driven term (ballooning) and current-driven term (peeling) compete. Suppression of ELMs requires maintaining δW > 0 by manipulating the magnetic shear or pressure profile.

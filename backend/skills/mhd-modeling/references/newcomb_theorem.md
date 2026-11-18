# Newcomb's Theorem (1960)
CITED AS: Newcomb, Hydromagnetic stability of a diffuse linear pinch, Ann. Phys., 10, 232.

## Abstract
Establishes the necessary and sufficient conditions for the stability of a cylindrical plasma (and by extension, toroidal flux surfaces) based on the solution of a second-order linear ODE.

## The Newcomb ODE
The radial displacement ξ_r satisfies:
d/dr [ f(r) dξ_r/dr ] - g(r) ξ_r = 0

### Stability Criterion
A mode (m,n) is stable if and only if:
1. The Euler-Lagrange equation has no singular points in the interval (0, a).
2. The solution ξ_r(r) that is regular at r=0 has no zeros (nodes) in the interval (0, a).

## Numerical Significance
- **Singular Surfaces**: Occur where F·B = 0 (rational surfaces q = m/n).
- **Matching Condition**: The stability index Δ' is derived from the jump in the derivative across these singular surfaces.

## ULTRON Implementation Logic
When calculating stability for a specific shot (e.g. DIII-D 123456), ULTRON must:
1. Identify all rational surfaces q=m/n in the pedestal.
2. Integrate the Newcomb ODE between surfaces.
3. Count nodes to determine if the Peeling-Ballooning limit is exceeded.

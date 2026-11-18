# Grad-Shafranov Solvers - PhD Grade
description: "Fixed and Free-boundary axisymmetric equilibrium solvers for Tokamak discovery."

## 1. The Picard Iteration Scheme
To solve Δ* ψ = -μ₀R²P'(ψ) - FF'(ψ), use the following iterative approach:
1. Initialize ψ₀(R,Z).
2. Calculate the source term S_n = μ₀R²P'(ψ_n) + FF'(ψ_n).
3. Solve the elliptic equation Δ* ψ_{n+1} = -S_n using Finite Difference or Finite Element methods.
4. Scale ψ_{n+1} to maintain constant plasma current (Ip).
5. Repeat until |ψ_{n+1} - ψ_n| < ε.

## 2. Python Implementation (Finite Difference)
```python
import numpy as np
from scipy.sparse import spdiags, linalg

def solve_gs_step(R, Z, S, dr, dz):
    """Solve one step of the GS equation on a rectangular grid."""
    nr, nz = R.shape
    # Construct the Δ* operator matrix (Five-point stencil)
    # Δ*ψ = R * ∂/∂R( (1/R) * ∂ψ/∂R ) + ∂²ψ/∂Z²
    # ... Matrix construction logic ...
    psi_next = linalg.spsolve(A_matrix, -S.flatten())
    return psi_next.reshape(nr, nz)
```

## 3. Data Integration (IMAS / OMAS)
```python
import omas

def load_imas_equilibrium(shot, run, user='public'):
    """Load standardized Tokamak data via the OMAS/IMAS interface."""
    ods = omas.ODS()
    ods.load('imas', user, shot, run)
    psi = ods['equilibrium.time_slice.0.profiles_2d.0.psi']
    return psi
```

## 4. Boundary Conditions
- Fixed-Boundary: ψ prescribed on a closed contour (separatrix).
- Free-Boundary: ψ determined by external coil currents using Green's functions G(R,Z; R',Z').

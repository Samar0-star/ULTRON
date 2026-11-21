**SKILL: Magnetohydrodynamics (MHD) — Autonomous Plasma Stability Analysis**
**Version:** 5.0 (second peer-review pass; corrected from v4.0)
**Domain:** Plasma Physics / Fusion Science
**Correction log v5.0:**
  1. Hall term sign derived explicitly from two-fluid generalized Ohm's law (was wrong in v4.0).
  2. Ion inertial length formula rewritten without square-root grouping ambiguity.
  3. `mode_numbers: Dict[str, int]` type contract no longer violated by high-n ballooning;
     introduced `mode_regime` field with consistency checks in `validate_schema()`.
  4. `validate_schema()` now checks for VMEC, HINT, *and* SPEC (was missing SPEC despite
     SPEC being listed in surrounding text and Section 7 table).
**Reading contract:** Every empirical threshold in this document is explicitly labeled
`[HEURISTIC: <provenance>]`. Every governing equation is labeled `[LAW]`.
Anything not so labeled is a definition or a structural convention.
SVEL must propagate these labels downstream into every hypothesis it generates.

---

## MANDATORY PREAMBLE — READ BEFORE ANY ANALYSIS

### On the hierarchy of MHD approximations

MHD is a moment-closure of the Boltzmann equation. Every MHD model is an approximation
valid only within a defined parameter regime. SVEL must identify that regime before
invoking any equation or threshold in this document.

**The approximation hierarchy (coarsest → finest):**
```
Ideal MHD → Resistive MHD → Extended MHD (Hall, FLR, gyroviscous) → Two-fluid → Gyrokinetics
```

**Geometry requirement — determined first:**
```
Axisymmetric (tokamak, axisymmetric mirror)  → Grad-Shafranov equilibrium (Section 2)
Non-axisymmetric (stellarator, RFP with 3D fields) → 3D equilibrium (VMEC, HINT, SPEC)
                                                       Grad-Shafranov does NOT apply.
```

**This distinction is not negotiable.** Stellarators are, in general, not axisymmetric.
The Grad-Shafranov equation cannot be used for stellarator equilibria.
SVEL must invoke VMEC or equivalent 3D solvers for any non-axisymmetric geometry.

### On the separation of physics from numerics

This document separates physics (the equations nature obeys) from numerics (the tricks
codes use to solve those equations stably). Any term added to a physical equation
for purely numerical reasons must be:
  (a) confined to the Numerical Implementation section,
  (b) labeled `[NUMERICAL ARTIFACT]` if it appears anywhere near a physics equation,
  (c) never used in a physics derivation or hypothesis.

---

## SECTION 1: GOVERNING EQUATIONS

### 1.1 Ideal MHD — Conditions of Validity

[LAW] Ideal MHD is valid when simultaneously:
  - ω ≪ ω_ci (sub-ion-cyclotron frequencies)
  - k_⊥ ρ_i ≪ 1 (wavelengths much larger than ion Larmor radius)
  - λ_mfp ≪ L (collisional: mean free path much shorter than gradient scale)
  - η → 0 (resistivity negligible on the timescale of interest)

When any condition is violated, ideal MHD must be upgraded. SVEL must check all
four conditions before proceeding and flag which, if any, are marginal.

**Ideal MHD system (conservation form, SI, no approximations beyond the four above):**

```
[LAW] ∂ρ/∂t + ∇·(ρu) = 0                                   (mass)

[LAW] ∂(ρu)/∂t + ∇·[ρuu + (p + B²/2μ₀)I − BB/μ₀] = 0      (momentum; ideal: no viscous Π)

[LAW] ∂B/∂t = ∇×(u×B)                                       (induction; ideal: no resistivity)
      with ∇·B = 0 as a constraint, not a prognostic equation

[LAW] ∂p/∂t + u·∇p + γp∇·u = 0                              (adiabatic energy; no dissipation)

[LAW] J = (∇×B)/μ₀                                           (Ampere; non-relativistic limit)
```

### 1.2 Resistive MHD — Modifications to Ideal

When resistivity η [Ω·m] cannot be neglected (Section 3 gives regime criteria):

```
[LAW] ∂B/∂t = ∇×(u×B − ηJ)     where J = (∇×B)/μ₀
```

The resistive energy equation must account for Ohmic heating and anisotropic conduction.
A correct conservative form for total energy density E = ρu²/2 + p/(γ−1) + B²/(2μ₀):

```
[LAW] ∂E/∂t + ∇·F_E = 0

      F_E = (E + p_tot)u − (u·B)B/μ₀          [ideal flux]
          + ηJ×B/μ₀                             [resistive Poynting correction]
          − κ_∥(b̂b̂)·∇T − κ_⊥(I−b̂b̂)·∇T      [anisotropic Braginskii heat flux]
```

**Note on the resistive flux term:** The term ηJ×B/μ₀ in F_E represents the work done
by the resistive electric field on the fluid. It is not the same as adding η|J|² to a
source; the full conservative form must be used to guarantee energy conservation in
discrete schemes. When implementing: verify total energy is conserved to < 0.1%
over the simulation duration. If it is not, suspect a flux discretization error, not
a physical effect.

### 1.3 Extended MHD — When to Upgrade

**Hall MHD: derivation of the correct sign from first principles**

The Hall term sign is a recurrent source of errors because it depends on how the
electric field E and current J are defined and which charge carrier is taken as
positive. The correct form is derived here explicitly so that SVEL cannot
import a sign convention without tracing it to this derivation.

Start from the two-fluid momentum equation for electrons (massless limit, m_e → 0):

```
[LAW - step 1] 0 = −e n_e (E + u_e × B) − ∇p_e − ηJ·...
               → E = −u_e × B + ηJ/σ − ∇p_e/(e n_e)    [ignoring electron pressure for now]
```

Define the current density with sign convention J = e n_e (u_i − u_e), so:

```
[LAW - step 2] u_e = u_i − J/(e n_e)
```

where u_i ≈ u (bulk ion/fluid velocity) in the single-fluid limit. Substituting:

```
[LAW - step 3] E = −(u − J/(e n_e)) × B + ηJ
                 = −u × B + (J × B)/(e n_e) + ηJ
                             ↑
                   Hall electric field: sign is +, i.e., the Hall E-field
                   opposes the J×B force (Lorentz force on current carriers)
```

Faraday's law ∂B/∂t = −∇×E then gives:

```
[LAW] ∂B/∂t = ∇ × [u × B − (J × B)/(e n_e) − ηJ]
                              ↑
                    Sign is MINUS inside the curl.
                    This is the standard form in Huba (NRL Formulary),
                    Birn & Priest "Reconnection of Magnetic Fields" (2007),
                    and Toth et al., JCP 227, 6967 (2008).
```

The version `+J×B/(n_e e)` inside the curl that appeared in v3.0 was wrong.
It corresponds to defining current as J = e n_e (u_e − u_i), i.e., with
electrons as the positive carrier — an uncommon convention that must be
declared explicitly if used. SVEL must use the form above (electrons
negative, standard SI convention) unless a hypothesis explicitly declares
an alternative sign convention and justifies it.

**Regime of relevance:**
The Hall term is order (d_i / L) relative to the ideal u×B term, where:
```
[LAW] d_i = c / ω_pi,   ω_pi = √(n_i e² / (ε₀ m_i))
```
Written without ambiguity: d_i [m] = (c [m/s]) / (ω_pi [rad/s]), and ω_pi
is the ion plasma frequency computed from ion number density n_i [m⁻³],
elementary charge e = 1.602×10⁻¹⁹ C, ion mass m_i [kg], and
ε₀ = 8.854×10⁻¹² F/m. There is no approximation or square-root ambiguity
in this expression; it is a ratio of two dimensional quantities.

The Hall term becomes dynamically important when k_⊥ d_i ≳ O(0.1) for the
mode wavenumber k_⊥ of interest. Comparing d_i to the minor radius a is
a rough trigger to check, not a threshold for automatic mode-switching.
Always compute d_i at the radial location of the mode and compare to the
mode's own perpendicular length scale.

**Gyroviscous (FLR) correction to momentum equation:**
```
[LAW] Π_gv = −(ρ/(4ω_ci))[b̂×W·(I + b̂b̂) − (I + b̂b̂)·W×b̂]
             where W = ∇u + (∇u)ᵀ − (2/3)(∇·u)I
```
Source: Braginskii, Rev. Plasma Phys. 1, 205 (1965), Table 2, ion viscosity tensor.
This term matters when ρ_i/L_⊥ ~ O(0.05) or larger.

### 1.4 Divergence-Free Constraint

```
[LAW] ∇·B = 0 at all times
```

This is a constraint on initial conditions that is preserved by the ideal induction
equation in the continuous limit. Discrete schemes do NOT automatically preserve it.
SVEL must select and enforce a divergence-control strategy (Section 4.2).

---

## SECTION 2: AXISYMMETRIC EQUILIBRIUM — GRAD-SHAFRANOV EQUATION

**Applicability:** Axisymmetric systems ONLY (tokamaks, axisymmetric mirrors).
Do not apply to stellarators, heliotrons, or any configuration with 3D magnetic fields.

### 2.1 Derivation and Exact Form

For a plasma in static axisymmetric equilibrium, ∇p = J×B reduces to:

```
[LAW] Δ*ψ = −μ₀R² dp/dψ − F dF/dψ
```

where:
```
  ψ   = poloidal magnetic flux function, defined via B = ∇ψ×∇φ/R + F(ψ)∇φ
  Δ*  = R ∂/∂R(R⁻¹ ∂/∂R) + ∂²/∂Z²   [the Grad-Shafranov operator; NOT the scalar Laplacian]
  F   = RB_φ = μ₀ I_pol(ψ)/(2π)        [poloidal current function]
  p(ψ), F(ψ)  = two arbitrary free functions specifying the equilibrium
```

Source: Grad & Rubin, Proc. 2nd UN Conf. Peaceful Uses Atomic Energy 31, 190 (1958);
Shafranov, Sov. Phys. JETP 6, 545 (1958).

The GSE is a nonlinear elliptic PDE. Existence and uniqueness depend on the choice of
p(ψ) and F(ψ). Analytic solutions (Solov'ev, Hernegger-Maschke) exist only for
specific functional forms. In practice, p(ψ) and F(ψ) are determined by experimental
profile measurements; the choice of functional form introduces a modeling uncertainty
that must be propagated into all downstream stability calculations.

### 2.2 Safety Factor

```
[LAW] q(ψ) = (1/2π) ∮_C (B_φ / (R B_pol)) dl
```

where the line integral is taken along the poloidal cross-section of the flux surface
labeled by ψ, and dl is the poloidal arc length element.

**Important:** This is a contour integral on a specific flux surface. It is NOT equal
to rB_φ/(RB_pol) except in the circular cross-section, low-β, large-aspect-ratio
limit. Using the approximate form for shaped, high-β plasmas will produce errors that
are not small. SVEL must always compute q by numerical integration around flux
surface contours, not by the simplified formula.

### 2.3 Equilibrium Validation — What to Check

These are checks that a reconstructed equilibrium is self-consistent. The numerical
tolerances given below are guidance, not laws. The appropriate tolerance depends on
the downstream application (linear stability is more sensitive than transport
modeling).

```python
def validate_equilibrium(psi_2d, R, Z, p_profile, F_profile,
                         Ip_measured_A, W_MHD_measured_J):
    """
    Validate a reconstructed equilibrium against physical constraints
    and available experimental measurements.
    
    All tolerances are labeled as heuristics with provenance.
    They may need adjustment for specific machines or reconstruction codes.
    """
    MU0 = 4 * np.pi * 1e-7
    
    results = {}
    
    # ── 1. Grad-Shafranov force balance residual ──
    # Compute Δ*ψ and compare to −μ₀R²dp/dψ − F dF/dψ.
    # Normalize residual to the peak magnitude of the RHS.
    # A residual < 1e-3 (relative to RHS peak) indicates a well-converged reconstruction.
    # [HEURISTIC: EFIT reconstruction practice; Lao et al. 1985]
    # For high-resolution equilibria (EFIT++, FIESTA), < 1e-4 is achievable.
    # The appropriate threshold depends on grid resolution and polynomial basis used.
    lhs = compute_delta_star(psi_2d, R, Z)
    rhs = compute_gs_rhs(psi_2d, R, Z, p_profile, F_profile)
    residual_rel = np.max(np.abs(lhs - rhs)) / (np.max(np.abs(rhs)) + 1e-30)
    results['gs_residual_relative'] = residual_rel
    results['gs_residual_flag'] = (
        'PASS' if residual_rel < 1e-3 else
        'MARGINAL' if residual_rel < 1e-2 else
        'FAIL'
    )
    
    # ── 2. Plasma current consistency ──
    # Ip from GSE boundary conditions should match Rogowski coil measurement.
    # Tolerance: 2% is typical EFIT accuracy for well-diagnosed shots.
    # [HEURISTIC: EFIT operational experience across DIII-D, JET, AUG]
    # Can be worse for shots with large Mirnov perturbations or current holes.
    Ip_reconstructed = compute_plasma_current(psi_2d, F_profile, R, Z)
    ip_error_pct = abs(Ip_reconstructed - Ip_measured_A) / abs(Ip_measured_A) * 100
    results['Ip_error_pct'] = ip_error_pct
    
    # ── 3. Stored energy consistency ──
    # W_MHD from equilibrium (3/2 ∫p dV) vs diamagnetic loop measurement.
    # Tolerance: 10–15% is typical; the diamagnetic loop measurement has systematic
    # errors from fast-ion pressure contributions not in the thermal pressure profile.
    # [HEURISTIC: standard experimental practice; see Shaing & Callen 1983 for corrections]
    W_MHD_recon = compute_stored_energy(psi_2d, p_profile, R, Z)
    wmhd_error_pct = abs(W_MHD_recon - W_MHD_measured_J) / abs(W_MHD_measured_J) * 100
    results['W_MHD_error_pct'] = wmhd_error_pct
    
    # ── 4. Positivity of pressure ──
    # p(ψ) must be non-negative everywhere. Negative pressure is unphysical
    # and indicates a failed reconstruction or an invalid profile parameterization.
    # [LAW: thermodynamic requirement]
    results['pressure_positive'] = np.all(p_profile >= 0)
    
    return results
```

### 2.4 MDSplus Data Acquisition — Machine-Specific Note

MDSplus node paths, tree names, and data conventions are **not portable across machines**.
The paths used on DIII-D (atlas.gat.com, tree EFIT01) are different from those used
on JET, AUG, KSTAR, and EAST. The code below illustrates the pattern for DIII-D;
it must be adapted for each machine using that machine's data dictionary or interface
documentation. Do not assume that `\PSIRZ`, `\PRES`, `\FPOL`, or any other node name
exists on a machine for which you have not verified the data schema.

Additionally, the time-indexing structure of profile arrays vs scalar diagnostics
varies across reconstructions and even across software versions of the same code.
Always inspect the shape of fetched arrays before indexing.

```python
import MDSplus
import numpy as np
import logging

logger = logging.getLogger(__name__)

# ── Machine server registry (DIII-D conventions shown; others differ) ──
# This mapping requires verification before use on any machine not in your
# primary development environment.
MACHINE_SERVERS = {
    'DIII-D': 'atlas.gat.com',
    # Other machine entries require their respective data coordinators to confirm
    # correct server addresses, ports, tree names, and node paths.
}

DIIID_EFIT_NODES = {
    # These node paths are specific to DIII-D EFIT01/EFIT02 trees.
    # Verify with GA data group before using on any other device.
    'psi_rz'    : r'\PSIRZ',     # [nR, nZ, nT] Wb/rad
    'r_grid'    : r'\RGRID',     # [nR] m
    'z_grid'    : r'\ZGRID',     # [nZ] m (DIII-D specific)
    'time'      : r'\TIME',      # [nT] s
    'p_psi'     : r'\PRES',      # pressure profile p(ψ_norm) [Pa]
    'F_psi'     : r'\FPOL',      # F(ψ) = RB_φ [T·m]
    'q_psi'     : r'\QPSI',      # q(ψ_norm)
    'Ip'        : r'\CPASMA',    # plasma current [A]
    'R_axis'    : r'\RMAXIS',    # magnetic axis R [m]
    'Z_axis'    : r'\ZMAXIS',    # magnetic axis Z [m]
    'psi_axis'  : r'\SSIMAG',    # ψ at axis [Wb/rad]
    'psi_lcfs'  : r'\SSIBRY',    # ψ at LCFS [Wb/rad]
    'W_MHD'     : r'\WMHD',      # stored energy [J] (may not exist on all trees)
}

def fetch_diiid_efit(shot: int, time_s: float, tree: str = 'EFIT01') -> dict:
    """
    Fetch DIII-D EFIT equilibrium at a given time.
    
    IMPORTANT: node paths here are DIII-D specific.
    Do not use this function for other machines without checking their schemas.
    """
    conn = MDSplus.Connection(MACHINE_SERVERS['DIII-D'])
    conn.openTree(tree, shot)
    
    def get(path):
        try:
            return np.atleast_1d(conn.get(path).data())
        except MDSplus.MDSplusException as e:
            logger.warning(f"Node {path} unavailable: {e}")
            return None
    
    psi_3d = get(DIIID_EFIT_NODES['psi_rz'])
    time   = get(DIIID_EFIT_NODES['time'])
    
    if psi_3d is None or time is None:
        raise RuntimeError(f"Cannot fetch core EFIT nodes for shot {shot}")
    
    # Locate nearest time slice. Do NOT interpolate between EFIT time slices;
    # each slice is an independent equilibrium solve. Interpolation is not valid.
    t_idx = int(np.argmin(np.abs(time - time_s)))
    
    # Inspect array shapes before indexing — they differ between EFIT versions
    def slice_profile(arr, idx):
        """Handle both time-indexed and static profile arrays."""
        if arr is None:
            return None
        if arr.ndim == 1:
            return arr          # time-independent
        elif arr.ndim == 2:
            return arr[idx]     # [nT, nPsi] → [nPsi]
        else:
            return arr[:, :, idx]  # [nR, nZ, nT] → [nR, nZ]
    
    return {
        'psi_2d'    : slice_profile(psi_3d, t_idx),
        'R'         : get(DIIID_EFIT_NODES['r_grid']),
        'Z'         : get(DIIID_EFIT_NODES['z_grid']),
        'p_psi'     : slice_profile(get(DIIID_EFIT_NODES['p_psi']), t_idx),
        'F_psi'     : slice_profile(get(DIIID_EFIT_NODES['F_psi']), t_idx),
        'q_psi'     : slice_profile(get(DIIID_EFIT_NODES['q_psi']), t_idx),
        'Ip_A'      : float(slice_profile(get(DIIID_EFIT_NODES['Ip']), t_idx)),
        'R_axis_m'  : float(slice_profile(get(DIIID_EFIT_NODES['R_axis']), t_idx)),
        'Z_axis_m'  : float(slice_profile(get(DIIID_EFIT_NODES['Z_axis']), t_idx)),
        'psi_axis'  : float(slice_profile(get(DIIID_EFIT_NODES['psi_axis']), t_idx)),
        'psi_lcfs'  : float(slice_profile(get(DIIID_EFIT_NODES['psi_lcfs']), t_idx)),
        'W_MHD_J'   : float(slice_profile(get(DIIID_EFIT_NODES['W_MHD']), t_idx))
                      if get(DIIID_EFIT_NODES['W_MHD']) is not None else None,
        'time_actual_s' : float(time[t_idx]),
        'machine'   : 'DIII-D',
        'tree'      : tree,
        'shot'      : shot,
    }
```

---

## SECTION 3: DIMENSIONLESS PARAMETERS AND REGIME IDENTIFICATION

SVEL must compute the following parameters and report them before any stability
analysis. Parameters are grouped as laws (definitions from first principles) and
heuristics (regime boundaries that are context-dependent).

```
[LAW] Lundquist number     S = τ_R / τ_A = μ₀ L v_A / η
      where τ_R = μ₀ L² / η  (resistive diffusion time)
            τ_A = L / v_A     (Alfvén transit time)
            v_A = B / √(μ₀ρ)  (Alfvén speed)

[LAW] Plasma β             β = 2μ₀p / B²   (thermal / magnetic pressure ratio)

[LAW] Normalized β         βN = β (a[m] B[T] / I_p[MA])   [Troyon normalization]

[LAW] Safety factor        q(ψ) = (1/2π) ∮ (B_φ / (R B_pol)) dl  (see Section 2.2)

[LAW] Magnetic shear       ŝ(r) = (r/q) dq/dr  [local, at minor radius r]

[LAW] Ion inertial length  d_i = c / ω_pi

      where ω_pi = √( n_i e² / (ε₀ m_i) )   [ion plasma frequency, rad/s]

      Expanded:  d_i [m] = c / √( n_i [m⁻³] · e² [C²] / (ε₀ [F/m] · m_i [kg]) )

      Constants: c = 2.998×10⁸ m/s, e = 1.602×10⁻¹⁹ C, ε₀ = 8.854×10⁻¹² F/m
      For a deuterium plasma: m_i = 3.344×10⁻²⁷ kg
      Numerically: d_i ≈ 228 / √(n_i [×10¹⁹ m⁻³])  meters  (deuterium, approximate)

      Note: use ion density n_i, not electron density n_e, unless quasi-neutrality
      (n_i ≈ n_e) is explicitly verified. For impurity-rich plasmas they differ.

[LAW] Collisionality       ν*_i = ν_ii q R / (v_th,i ε^{3/2})
      where ε = r/R is inverse aspect ratio and v_th,i = √(2kT_i/m_i)
```

**Regime thresholds — all labeled as heuristics:**

```
[HEURISTIC: Biskamp 2000, reconnection review]
  S >> 1: resistive effects slow; growth rates scale as S^{-1/3} to S^{-3/5}
           depending on current sheet geometry and reconnection model.
  No single S threshold separates "ideal" from "resistive" behavior cleanly.
  The relevant comparison is S vs the mode growth rate: if γτ_A >> S^{-1}, resistivity matters.

[HEURISTIC: dimensional estimate from whistler dispersion relation]
  Hall MHD: relevant when k d_i > O(0.1) for the mode of interest.
  d_i/a > 0.01 is a rough trigger to check, not a threshold for automatic mode-switching.
  Always verify by computing d_i at the relevant radial location and comparing to
  the mode's radial scale length, not the minor radius.

[HEURISTIC: Troyon et al. 1984, empirical database fit on circular-cross-section tokamaks]
  βN,max ≈ 2.8–4.0 for conventional aspect ratio tokamaks with feedback control.
  This is a fit to a finite experimental database, not a derived physical law.
  The coefficient varies with plasma shape (elongation κ, triangularity δ),
  wall proximity, and rotation. Do not apply as a universal number.

[HEURISTIC: empirical observation, not a theorem]
  Rational q surfaces (q = m/n) are associated with tearing modes and NTMs,
  but the presence of a rational surface is necessary, not sufficient, for
  instability. Stability depends on Δ' (tearing modes), drive (NTMs),
  and stabilizing mechanisms (rotation, ECCD, FLR effects).
  "q = 2 causes major disruptions" is too coarse. Disruptions are multifactorial.
```

---

## SECTION 4: LINEAR STABILITY THEORY

### 4.1 The Ideal MHD Energy Principle

[LAW] A plasma equilibrium is linearly stable to ideal MHD perturbations if and only
if δW[ξ,ξ] > 0 for all allowable displacements ξ. Marginal stability: δW = 0.

Source: Bernstein, Frieman, Kruskal, Kulsrud, Proc. R. Soc. London A244, 17 (1958).

```
[LAW] δW = δW_F + δW_S + δW_V

δW_F = (1/2μ₀) ∫_plasma [|Q_⊥|² + B²|∇·ξ_⊥ + 2ξ_⊥·κ|²
                           − μ₀(ξ_⊥·∇p)(∇·ξ_⊥ + 2ξ_⊥·κ)
                           − μ₀J_∥(ξ_⊥×b̂)·Q
                           + γp|∇·ξ|²] d³x

  Q = ∇×(ξ×B)     = perturbed magnetic field (ideal flux-freezing)
  κ = (b̂·∇)b̂     = field-line curvature
  ξ_⊥             = displacement perpendicular to B
  J_∥ = (J·b̂)    = parallel equilibrium current

δW_S = (1/2) ∮_S [[p + B²/2μ₀]]|ξ_n|² dS  (surface term; nonzero only at interfaces)

δW_V = (1/2μ₀) ∫_vacuum |∇×A₁|² d³x ≥ 0   (vacuum term; always stabilizing)
```

**Destabilizing mechanisms in δW_F (term by term):**

The `−μ₀(ξ_⊥·∇p)(∇·ξ_⊥ + 2ξ_⊥·κ)` term is destabilizing when pressure gradient
and curvature are aligned (bad curvature): interchange and ballooning modes.

The `−μ₀J_∥(ξ_⊥×b̂)·Q` term is destabilizing when parallel current drives kink modes.
This requires J_∥ to be large enough relative to the stabilizing field-line bending `|Q_⊥|²`.

The `γp|∇·ξ|²` term is always stabilizing (compressibility).

### 4.2 The Newcomb Equation (Kink and Tearing Mode Analysis)

For each toroidal mode number n and poloidal mode number m, stability in a
cylindrical or toroidal geometry reduces to solving the Newcomb ODE:

```
[LAW] d/dr[f(r) dξ_r/dr] − g(r)ξ_r = 0
```

where f and g are known functions of the equilibrium q(r), pressure, and current
profiles. Their explicit forms depend on the geometry (cylindrical vs toroidal).

**Newcomb's theorem (Newcomb 1960):**
The mode (m,n) is unstable if and only if the solution ξ_r(r) starting from the
axis (ξ_r → r^m near axis) has a zero (node) between r = 0 and r = a before
reaching the plasma boundary.

This is a statement about the sign change of ξ_r, not about the magnitude.
SVEL must integrate the Newcomb ODE numerically for each (m,n) of interest.
Analytic approximations (Δ' estimates from profile shape alone) are valid only for
simple current profiles and should not be used for quantitative stability boundaries.

**Tearing mode classical stability index:**
```
[LAW] Δ' = [dξ_r/dr / ξ_r]^{r_s+ε}_{r_s-ε}   as ε → 0
```
Δ' > 0: classically unstable to tearing. Δ' < 0: classically stable.
The NTM drive can overcome a negative Δ' via bootstrap current; see Section 4.4.

### 4.3 Ballooning Modes

For high-toroidal-mode-number (n → ∞) perturbations localized on a flux surface,
the stability problem reduces to the Connor-Hastie-Taylor (CHT) ballooning equation:

```
[LAW] d/dθ[(1 + (ŝθ − α sinθ)²) dX/dθ] + [α(cosθ + (ŝθ − α sinθ)sinθ) + Λ]X = 0

  θ  : ballooning angle (field-following, −∞ < θ < ∞)
  ŝ  : local magnetic shear (r/q)(dq/dr) at the flux surface
  α  : normalized pressure gradient = −q²R μ₀(dp/dψ)(2/B²)
  Λ  : eigenvalue; Λ < 0 indicates instability
```

Source: Connor, Hastie, Taylor, Phys. Rev. Lett. 40, 396 (1978).

Stability depends on the (ŝ, α) operating point on each flux surface.
The first-stability boundary (the conventional H-mode pedestal limit) and the
second-stability region (high-α, high-ŝ or reversed-shear region) must both be
mapped. The existence of a second stability region is geometry-dependent.

**SVEL must** solve this eigenvalue problem numerically at each flux surface of
interest. The stability boundary in (ŝ, α) space must be computed, not assumed
to follow a simple algebraic formula.

**FLR stabilization:** When k_⊥ρ_i ~ O(0.05–0.1), the gyroviscous term shifts
α_crit upward. The magnitude of this correction is geometry-dependent.
For ITER-grade pedestals it can be 10–30%, but this range reflects specific
parameter regimes and should not be applied universally.

### 4.4 Neoclassical Tearing Modes (NTMs)

NTMs are driven by the loss of bootstrap current inside a magnetic island.
Unlike classical tearing modes, they can be unstable even when Δ' < 0.

**Modified Rutherford Equation:**
```
[LAW] (τ_R / r_s) I_pol · dW/dt = r_s Δ'(W) + Δ'_bs + Δ'_pol + Δ'_GGJ + Δ'_ECCD
```

where each Δ' term represents a physical contribution:

```
Δ'(W)     : classical tearing stability (Rutherford, Phys. Fluids 16, 1973)
Δ'_bs     : bootstrap current drive (destabilizing when Δ' < 0)
             ~ −c_bs · β_p · (r_s/W) · (L_q/L_p)  for W >> W_d
             Requires neoclassical bootstrap coefficient c_bs from Sauter et al. 1999
Δ'_pol    : polarization current (stabilizing for small islands)
             ~ +c_pol · (W_d/W)² for W < W_d  (Fitzpatrick 1995)
Δ'_GGJ    : Glasser-Greene-Johnson stabilization (reversed shear geometry)
             (Glasser, Greene, Johnson, Phys. Fluids 18, 1975)
Δ'_ECCD   : ECCD stabilization (sign depends on current drive location relative to island)
```

**Key statements (law vs heuristic):**

```
[LAW]      NTM onset requires a seed island exceeding a threshold width W_seed.
           Below this width, polarization current stabilizes the mode.
           There is no spontaneous NTM onset from noise; a finite trigger is required.

[HEURISTIC: La Haye, Phys. Plasmas 13, 055501 (2006), multi-machine database]
           Typical NTM onset in present devices occurs at βN ~ 1.5–3.0, depending
           on q-profile, rotation, collisionality, and seed source.
           This is a database observation, not a derived threshold.
           Do not extrapolate to machines outside the database without uncertainty bounds.

[HEURISTIC: Sauter et al., Phys. Plasmas 6, 2834 (1999)]
           Bootstrap current coefficient: the Sauter formula for c_bs is derived
           from drift-kinetic theory valid for ν* < 1 (banana regime).
           It has been validated against codes (CQL3D, NCLASS) for ν* < 0.5.
           For ν* > 1 (collisional regime), use the Pfirsch-Schlüter limit instead.
```

### 4.5 ELMs — Peeling-Ballooning Instability

Edge Localized Modes arise from a coupled instability driven simultaneously by
pedestal pressure gradient (ballooning drive) and pedestal bootstrap current (peeling drive).

**Stability boundary:**
The peeling-ballooning stability boundary in (j_∥, ∇p) space must be computed
numerically using a code that accounts for full toroidal geometry, plasma shaping,
and diamagnetic stabilization. ELITE (Wilson et al., Phys. Plasmas 9, 2002)
and GS2 are appropriate codes. Analytic approximations are insufficient for
quantitative ELM threshold prediction in shaped tokamaks.

**ELM classification:**
```
[HEURISTIC: Zohm, Plasma Phys. Controlled Fusion 38, L27 (1996); 
            Connor, Plasma Phys. Controlled Fusion 40, 191 (1998)]
  Type-I: peeling-ballooning; large energy loss; occurs near ideal stability limit
  Type-II: high-n ballooning; small amplitude; found near second-stability or in
           high-triangularity, high-density conditions
  Type-III: resistive; occurs below the peeling-ballooning limit; driven by edge cooling
  
  Classification requires both the stability boundary calculation AND measurement of
  ELM frequency, energy loss, and mode structure. Do not classify based on
  growth rate or mode number alone.
```

---

## SECTION 5: NUMERICAL IMPLEMENTATION

### 5.1 Time-Step Constraints

A stable explicit time integration requires satisfying all of the following simultaneously.
Violating any one will cause the simulation to diverge.

```python
import numpy as np

def compute_stable_timestep(rho, u, B, p, dx, eta, nu, hall_enabled=False,
                             d_i=None, cfl_advective=0.4, cfl_diffusive=0.3):
    """
    Compute the maximum stable explicit timestep for resistive MHD.
    
    All CFL coefficients (0.4, 0.3) are empirical stability factors derived
    from von Neumann analysis of simple 1D model equations. They may require
    reduction for multidimensional schemes, strong shocks, or stiff source terms.
    [HEURISTIC: standard CFD practice; see Toro, Riemann Solvers and Numerical Methods]
    
    Returns:
        dt: timestep [s]
        breakdown: which constraint is limiting and by how much
    """
    MU0 = 4 * np.pi * 1e-7
    gamma = 5.0 / 3.0   # adiabatic index; adjust for different equations of state
    
    B_mag = np.linalg.norm(B, axis=-1)
    u_mag = np.linalg.norm(u, axis=-1)
    
    v_A     = B_mag / np.sqrt(MU0 * rho)          # [LAW] Alfvén speed
    v_s     = np.sqrt(gamma * p / rho)             # [LAW] sound speed
    v_fast  = np.sqrt(v_A**2 + v_s**2)            # [LAW] fast magnetosonic speed (upper bound)
    
    # Effective minimum cell size (use actual minimum in each direction for anisotropic grids)
    h = dx if np.isscalar(dx) else np.min(dx)
    
    # ── (1) Fast magnetosonic wave: dominant advective constraint ──
    dt_fast = cfl_advective * h / (np.max(v_fast) + np.max(u_mag) + 1e-30)
    
    # ── (2) Resistive diffusion: parabolic stability limit ──
    # [LAW] The resistive induction equation is parabolic in B with diffusivity η/μ₀.
    # An explicit scheme requires Δt < Δx²/(2 × diffusivity).
    if eta > 0:
        dt_resist = cfl_diffusive * h**2 / (eta / MU0)
    else:
        dt_resist = np.inf
    
    # ── (3) Viscous diffusion: parabolic stability limit ──
    if nu > 0:
        dt_visc = cfl_diffusive * h**2 / nu
    else:
        dt_visc = np.inf
    
    # ── (4) Hall term: whistler wave stability limit ──
    # The Hall term introduces whistler waves with dispersion ω = k²(d_i v_A).
    # Their phase velocity grows as k, making the Hall CFL the most restrictive
    # constraint at fine grid resolution. An explicit Hall scheme requires:
    #   Δt < Δx² / (2 d_i v_A_max)
    # This is typically far more restrictive than the ideal CFL and usually
    # requires implicit treatment (e.g., Toth et al., JCP 2008) or operator splitting.
    if hall_enabled:
        if d_i is None:
            raise ValueError("d_i must be provided when hall_enabled=True")
        dt_hall = cfl_diffusive * h**2 / (d_i * np.max(v_A) + 1e-30)
        if dt_hall < dt_fast:
            import warnings
            warnings.warn(
                f"Hall CFL ({dt_hall:.2e} s) is more restrictive than ideal CFL "
                f"({dt_fast:.2e} s) by factor {dt_fast/dt_hall:.1f}. "
                "Consider implicit Hall treatment (Toth et al. 2008).",
                RuntimeWarning
            )
    else:
        dt_hall = np.inf
    
    dt = min(dt_fast, dt_resist, dt_visc, dt_hall)
    
    return {
        'dt'            : dt,
        'dt_fast'       : dt_fast,
        'dt_resistive'  : dt_resist,
        'dt_viscous'    : dt_visc,
        'dt_hall'       : dt_hall,
        'limiting'      : min(['fast','resistive','viscous','hall'],
                              key=lambda k: {'fast':dt_fast,'resistive':dt_resist,
                                             'viscous':dt_visc,'hall':dt_hall}[k]),
    }
```

### 5.2 Divergence-Free Constraint Enforcement

Three methods exist. They are NOT equivalent and must not be conflated.

**Method A — Constrained Transport (CT):**
Evans & Hawley, ApJ 332, 659 (1988); Balsara & Spicer, JCP 149, 270 (1999).
Store B on face centers; electric field (E = −u×B + ηJ) on cell edges.
The discrete curl of the edge-centered E is computed and added to the face-centered B.
This construction guarantees ∇·B = 0 to machine epsilon at all times, independent
of the field magnitude. No cleaning is required. Suitable for structured grids.

**Method B — Generalized Lagrange Multiplier (GLM / Dedner cleaning):**
Dedner et al., JCP 175, 645 (2002).
Augment the induction equation with a scalar field ψ satisfying:
```
  ∂ψ/∂t + c_h² ∇·B = −ψ / τ_c
  ∂B/∂t = ∇×(u×B − ηJ) − ∇ψ
```
This propagates divergence errors at speed c_h and damps them on timescale τ_c.
It does not eliminate ∇·B exactly; it reduces it to O(Δx²) over time.
Suitable for unstructured meshes and AMR. More complex to tune (c_h, τ_c).

**Method C — Elliptic projection:**
Solve ∇²φ = ∇·B (a global Poisson equation), then set B → B − ∇φ.
This projects B onto the divergence-free subspace exactly, but requires a global
elliptic solve at every timestep — computationally expensive.

**Powell's 8-wave scheme** (Powell et al., JCP 154, 284 (1999)) is a different
method: it adds source terms proportional to ∇·B to the momentum and induction
equations so that monopoles are advected with the flow rather than amplified.
It does NOT solve a Poisson equation and is NOT the same as elliptic projection.
SVEL must not conflate these methods.

```python
def check_divergence_error(B, dx):
    """
    Compute normalized divergence error for monitoring purposes.
    
    The normalization |∇·B| / (|B| / Δx) gives the relative error per cell.
    This metric can make a garbage solution look acceptable if |B| is large.
    Always also report the absolute max(|∇·B|) in [T/m].
    
    [HEURISTIC: typical target values]
      CT method:   relative error < 1e-12 (machine epsilon); absolute < 1e-10 T/m
      GLM method:  relative error < 1e-4 after transient; monitor for growth
      These targets depend on grid resolution and field magnitude.
      A target appropriate at coarse resolution may be insufficient at fine resolution.
    """
    dBx_dx = np.gradient(B[..., 0], dx, axis=0)
    dBy_dy = np.gradient(B[..., 1], dx, axis=1)
    dBz_dz = np.gradient(B[..., 2], dx, axis=2)
    div_B   = dBx_dx + dBy_dy + dBz_dz
    
    B_mag   = np.linalg.norm(B, axis=-1)
    
    return {
        'div_B_abs_max'  : np.max(np.abs(div_B)),            # [T/m]
        'div_B_rel_max'  : np.max(np.abs(div_B)) / (np.max(B_mag) / dx + 1e-30),
        'div_B_rms'      : np.sqrt(np.mean(div_B**2)),
    }
```

---

## SECTION 6: HYPOTHESIS GENERATION — STRUCTURAL REQUIREMENTS

Every MHD stability hypothesis produced by SVEL must conform to this schema.
Partial completion is not accepted.

```python
from dataclasses import dataclass, field
from typing import List, Optional, Dict
from enum import Enum

class MHDTier(str, Enum):
    IDEAL      = 'ideal'
    RESISTIVE  = 'resistive'
    HALL       = 'hall'
    EXTENDED   = 'extended'    # FLR + gyroviscous + multi-fluid
    HYBRID_KIN = 'hybrid_kinetic'  # MHD + energetic particle kinetics

class GeometryType(str, Enum):
    AXISYMMETRIC     = 'axisymmetric'      # GSE applies
    NON_AXISYMMETRIC = 'non_axisymmetric'  # 3D equilibrium required

@dataclass
class MHDHypothesis:
    """
    Structured MHD hypothesis. All fields are required.
    Hypotheses with None in required fields will be rejected by SVEL validator.
    """

    # ── Identification ──
    hypothesis_id   : str
    instability_type: str       # 'kink' | 'NTM' | 'ballooning' | 'ELM' | 'RWM' | 'tearing'

    # mode_numbers: use int values for discrete modes (e.g. {'m': 2, 'n': 1}).
    # For high-n ballooning (n → ∞ limit, Connor-Hastie-Taylor equation), the
    # hypothesis concerns a continuum of toroidal modes, not a single n.
    # In that case set mode_numbers = {} (empty dict) and populate
    # mode_regime instead. Do NOT put a string where an int is expected.
    mode_numbers    : Dict[str, int]   # Empty dict {} for high-n continuum limit
    mode_regime     : str   # 'discrete_mn' | 'high_n_ballooning' | 'high_n_peeling_ballooning'
                             # If 'discrete_mn', mode_numbers must be non-empty.
                             # If 'high_n_*', mode_numbers must be empty.

    # ── Physics tier and geometry (required before any equation is invoked) ──
    mhd_tier        : MHDTier
    geometry_type   : GeometryType
    tier_justification : str    # Why this tier was selected; reference to Section 1 criteria
    validity_conditions: List[str]  # List of checked conditions (from Section 1.1)
    validity_flags  : List[str]  # Any conditions that are marginal or violated

    # ── Equilibrium provenance ──
    equilibrium_source : str    # Machine, shot/discharge, time, reconstruction code
                                # OR 'analytic: <profile specification>'
    equilibrium_is_synthetic: bool  # MUST be True if not from real experimental data
    validation_checks_passed: List[str]  # List of checks from Section 2.3 that passed
    validation_checks_failed: List[str]  # List that failed or could not be evaluated

    # ── Dimensionless parameters (all from Section 3) ──
    # Report computed values, or None if unavailable (but flag as uncertainty)
    Lundquist_S     : Optional[float]
    beta_N          : Optional[float]
    q_at_surface    : Optional[float]   # q at the relevant rational surface
    local_shear_s   : Optional[float]
    d_i_over_a      : Optional[float]
    collisionality  : Optional[float]   # ν*_i at relevant surface
    rho_i_over_L    : Optional[float]   # ρ_i / L_gradient at relevant surface
    missing_params  : List[str]         # Which params could not be computed, and why

    # ── Claim ──
    claim           : str   # Precise, falsifiable statement in scientific language

    # ── Derivation chain (minimum 4 steps; each step cites equation or data) ──
    derivation_steps: List[str]
    codes_invoked   : List[str]   # Include version numbers where known

    # ── Predictions ──
    predicted_onset_params : Dict[str, float]  # e.g. {'beta_N': 2.4} with units in key names
    predicted_growth_rate_si : Optional[float]  # γ [s⁻¹]
    predicted_growth_rate_norm : Optional[float]  # γ τ_A [-]
    predicted_frequency_Hz : Optional[float]    # None for purely growing modes

    # ── Uncertainty quantification (required) ──
    confidence      : float         # In (0.0, 1.0); never 0 or 1
    uncertainty_sources : List[str]
    uncertainty_method  : str       # 'Monte Carlo' | 'sensitivity scan' | 'expert estimate'
    sensitivity_to_profiles : str   # Qualitative assessment of how sensitive predictions
                                    # are to p(ψ), q(ψ) profile uncertainty

    # ── Falsification (required; must be specific) ──
    observable_signature    : str   # What diagnostic signal would confirm this
    diagnostic_required     : str   # Specific diagnostic system
    falsification_condition : str   # Specific measurable condition that disproves the hypothesis
                                    # Must be quantitative: "if X < Y within time T, reject"

    # ── Literature anchors ──
    analogous_experiments   : List[str]  # Real experimental precedents with source reference
                                          # If synthetic: must be labeled '[SYNTHETIC EXAMPLE]'
    key_references          : List[str]  # DOI or journal citation for each theoretical claim

    # ── Heuristics used (required declaration) ──
    heuristics_applied : List[str]  # Every empirical threshold used, with its provenance
                                     # This forces SVEL to distinguish laws from heuristics

    def validate_schema(self) -> List[str]:
        """Returns list of schema violations; empty list = valid."""
        errors = []

        # ── Confidence ──
        if not (0.0 < self.confidence < 1.0):
            errors.append("confidence must be strictly between 0 and 1")

        # ── Derivation depth ──
        if len(self.derivation_steps) < 4:
            errors.append("minimum 4 derivation steps required")

        # ── Falsification specificity ──
        if len(self.falsification_condition) < 50:
            errors.append("falsification condition is too vague (< 50 characters)")

        # ── Heuristics must be declared ──
        if not self.heuristics_applied:
            errors.append("heuristics_applied cannot be empty; declare all empirical thresholds used")

        # ── Synthetic equilibrium labeling ──
        if self.equilibrium_is_synthetic and 'SYNTHETIC' not in str(self.analogous_experiments):
            errors.append("synthetic equilibrium: analogous_experiments must be labeled [SYNTHETIC]")

        # ── Non-axisymmetric geometry: require 3D equilibrium code ──
        # Allowed codes: VMEC, HINT, SPEC (and others — add here as validated)
        _3D_CODES = {'VMEC', 'HINT', 'SPEC'}
        if self.geometry_type == GeometryType.NON_AXISYMMETRIC:
            codes_upper = ' '.join(self.codes_invoked).upper()
            if not any(code in codes_upper for code in _3D_CODES):
                errors.append(
                    f"non-axisymmetric geometry requires a 3D equilibrium code "
                    f"({', '.join(sorted(_3D_CODES))}); GSE is not applicable. "
                    f"Codes invoked: {self.codes_invoked}"
                )

        # ── mode_numbers / mode_regime consistency ──
        if self.mode_regime == 'discrete_mn' and not self.mode_numbers:
            errors.append(
                "mode_regime='discrete_mn' requires non-empty mode_numbers dict "
                "(e.g. {'m': 2, 'n': 1})"
            )
        if self.mode_regime.startswith('high_n') and self.mode_numbers:
            errors.append(
                f"mode_regime='{self.mode_regime}' is a continuum limit; "
                "mode_numbers must be an empty dict {}. "
                "Do not assign a specific integer n to a high-n ballooning hypothesis."
            )
        if self.mode_regime not in {'discrete_mn', 'high_n_ballooning',
                                     'high_n_peeling_ballooning'}:
            errors.append(
                f"mode_regime='{self.mode_regime}' is not a recognized value. "
                "Use: 'discrete_mn' | 'high_n_ballooning' | 'high_n_peeling_ballooning'"
            )

        return errors
```

---

## SECTION 7: EXTERNAL CODE INTERFACES

SVEL should not re-implement physics that is handled by validated community codes.
The following hierarchy applies. Note that code interfaces are machine-specific;
input/output formats must be verified against the current version of each code.

| Task | Recommended code(s) | Notes on limitations |
|------|---------------------|----------------------|
| Axisymmetric equilibrium | EFIT++, FIESTA, CHEASE | EFIT++ preferred for experimental reconstructions; CHEASE for high-accuracy fixed-boundary |
| 3D equilibrium | VMEC, HINT, SPEC | Required for all non-axisymmetric geometries |
| Newcomb / linear ideal | GATO, MARS-F, MISHKA | Different formulations; cross-check results |
| Peeling-ballooning (ELM) | ELITE, GS2 | ELITE requires boundary plasma; GS2 for flux-tube limit |
| Nonlinear MHD | JOREK, M3D-C1, NIMROD | Computationally intensive; requires HPC |
| Neoclassical transport | NCLASS, NEO, CGYRO | For bootstrap coefficients; match to collisionality regime |
| Fast-ion effects on MHD | NOVA-K, VENUS-LEVIS | Hybrid MHD-kinetic; required when energetic-particle β is significant |

---

## SECTION 8: KNOWN FAILURE MODES OF THIS SKILL

SVEL must flag the following conditions and escalate rather than proceed:

| Condition | Why this skill fails | Required action |
|---|---|---|
| Non-axisymmetric geometry | GSE and all axisymmetric stability tools are invalid | Escalate to 3D equilibrium (VMEC) + 3D stability (COBRAVMEC, Terpsichore) |
| S < 100 | Ideal MHD severely overestimates stability; resistive effects dominate on Alfvén timescale | Use resistive MHD throughout; ideal energy principle results are not meaningful |
| Energetic particle β comparable to thermal β | MHD equilibrium and stability modified by fast-ion pressure tensor; single-fluid fails | Escalate to hybrid MHD-kinetic or drift-kinetic approach |
| Post-disruption / current quench | MHD assumptions (Maxwellian, collisional, sub-Alfvénic) all fail simultaneously | Do not apply this skill |
| Pedestal region in H-mode | EFIT typically under-resolves pedestal (Δψ too coarse); bootstrap current uncertain | Use dedicated pedestal profile fit + high-resolution equilibrium |
| Reversed shear near q_min | Standard Newcomb integration encounters Frobenius singularity at rational surfaces in reversed shear | Use reversed-shear Newcomb formulation (Newcomb 1960 Appendix; Greene & Johnson 1962) |
| Rotation velocity approaching v_A | Static equilibrium assumption breaks down; Coriolis and centrifugal forces enter force balance | Rotational equilibrium (Blokland et al. 2005) required |

---

## SECTION 9: CANONICAL REFERENCES

**Equilibrium:**
- Grad & Rubin (1958). Hydromagnetic equilibria. Proc. 2nd UN Conf. Peaceful Uses Atomic Energy, 31, 190.
- Shafranov (1958). On magnetohydrodynamical equilibrium configurations. Sov. Phys. JETP, 6, 545.
- Lao et al. (1985). Reconstruction of current profile parameters and plasma shapes in tokamaks. Nucl. Fusion, 25, 1611.

**Stability theory:**
- Bernstein, Frieman, Kruskal, Kulsrud (1958). An energy principle for hydromagnetic stability problems. Proc. R. Soc. London A244, 17.
- Newcomb (1960). Hydromagnetic stability of a diffuse linear pinch. Ann. Phys., 10, 232.
- Connor, Hastie, Taylor (1978). Shear, periodicity, and plasma ballooning modes. Phys. Rev. Lett., 40, 396.
- Glasser, Greene, Johnson (1975). Resistive instabilities in general toroidal plasma configurations. Phys. Fluids, 18, 875.

**Tearing / NTM:**
- Furth, Killeen, Rosenbluth (1963). Finite-resistivity instabilities of a sheet pinch. Phys. Fluids, 6, 459.
- Rutherford (1973). Nonlinear growth of the tearing mode. Phys. Fluids, 16, 1903.
- Fitzpatrick (1995). Helical temperature perturbations associated with tearing modes in tokamak plasmas. Phys. Plasmas, 2, 825.
- La Haye (2006). Neoclassical tearing modes and their control. Phys. Plasmas, 13, 055501.
- Sauter, Angioni, Lin-Liu (1999). Neoclassical conductivity and bootstrap current formulas for general axisymmetric equilibria. Phys. Plasmas, 6, 2834.

**ELM / peeling-ballooning:**
- Wilson et al. (2002). Numerical studies of edge localized instabilities in tokamaks. Phys. Plasmas, 9, 1277.

**Extended MHD / transport:**
- Braginskii (1965). Transport processes in a plasma. Rev. Plasma Phys., 1, 205.

**Numerical methods:**
- Evans & Hawley (1988). Simulation of magnetohydrodynamic flows: a constrained transport method. ApJ, 332, 659.
- Dedner et al. (2002). Hyperbolic divergence cleaning for the MHD equations. JCP, 175, 645.
- Powell et al. (1999). A solution-adaptive upwind scheme for ideal MHD. JCP, 154, 284.
- Toth et al. (2008). Implicit and explicit schemes for Hall MHD. JCP, 227, 6967.
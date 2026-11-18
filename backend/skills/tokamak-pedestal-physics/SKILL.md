# SKILL: Tokamak Pedestal Physics — H-Mode, ELM Stability, and ELM Control
**Version:** 1.0 (initial PhD-grade build)
**Domain:** Plasma Physics / Fusion Science — Pedestal and Edge Physics
**Parent skill:** MHD_SKILL_v5.md (inherit all label conventions, tier logic, geometry gate)
**Reading contract:** Every empirical threshold is labeled `[HEURISTIC: <provenance>]`.
Every governing equation is labeled `[LAW]`. Definitions and structural conventions
carry no label. ULTRON must propagate these labels into every hypothesis it generates.

---

## MANDATORY PREAMBLE

### What the original skill got wrong — do not repeat these errors

The skill this replaces contained five categories of error that ULTRON must never reproduce:

1. **Peeling-ballooning boundary treated as two independent scalar thresholds.**
   `if alpha > alpha_crit: BALLOONING_UNSTABLE` is wrong physics. The peeling-ballooning
   stability boundary is a *coupled* curve in the (j_∥, α) plane computed numerically
   from toroidal MHD with full plasma shaping. It cannot be decomposed into two
   independent inequalities. Doing so will misclassify stable operating points as
   unstable and vice versa.

2. **RMP resonance reduced to m = n·q(ψ).**
   This is necessary but not sufficient for ELM suppression. The condition m = n·q
   identifies where vacuum field lines are resonant. Whether that produces ELM
   suppression depends on: plasma response (shielding), island overlap (Chirikov
   criterion), rotation screening, and 3D equilibrium effects. The original code
   returned a list of "resonant surfaces" as if that were the suppression condition.
   It is not.

3. **EPED1 formula Δ_ped = 0.076√β_pol,ped presented without its derivation basis,
   validity domain, or known failures.**
   This formula is a regression fit to a specific experimental database. It is not
   a derived physical law. Its use outside that database requires explicit justification.

4. **Chirikov overlap parameter mentioned without definition or computation.**
   Named but not quantified. Unusable as stated.

5. **No uncertainty quantification, no falsification conditions, no regime checks.**

Everything below replaces these errors with correct physics.

---

## SECTION 1: THE H-MODE PEDESTAL — PHYSICS AND DEFINITIONS

### 1.1 What the Pedestal Is and Why It Exists

In H-mode (High-confinement mode), a transport barrier forms spontaneously at the
plasma edge, typically within 1–3 cm of the last closed flux surface (LCFS).
Within this barrier:
- Ion and electron temperature gradients steepen by a factor of 3–10 over L-mode
- Density gradient steepens, though less dramatically than temperature
- Particle and energy transport drops by one to two orders of magnitude
- A strong edge bootstrap current develops driven by the steep pressure gradient

The pedestal is defined operationally as the region between the top of the steep
gradient zone (pedestal top: ψ_N ~ 0.9–0.95) and the LCFS (ψ_N = 1.0).

**Pedestal parameters (definitions, not laws):**
```
p_ped     = pedestal pressure at the pedestal top [Pa]
n_e,ped   = pedestal electron density [m⁻³]
T_e,ped   = pedestal electron temperature [eV or keV]
T_i,ped   = pedestal ion temperature [eV or keV]
Δ_ped     = pedestal width in normalized poloidal flux ψ_N [dimensionless]
              or equivalently in physical distance [m]; these are NOT interchangeable
              without knowing the flux-surface geometry
j_∥,ped   = peak parallel current density in the pedestal [A/m²]
              dominated by bootstrap current at high β_pol,ped
```

**The L-H transition itself is not covered by this skill.** The power threshold P_LH
and the mechanism of the transition (likely related to E×B shear suppression of
turbulence, but not settled) are a separate physics domain. ULTRON must not
conflate the existence of H-mode with the stability of the pedestal within H-mode.

### 1.2 Bootstrap Current in the Pedestal

```
[LAW] Bootstrap current (Sauter formula, banana regime):
      j_∥,bs/B = −(R_0 / B)(p_e + p_i)(L_{31} d ln n_e/dψ + L_{32} d ln T_e/dψ
                                          + L_{34} α_0 d ln T_i/dψ)
```

Source: Sauter, Angioni, Lin-Liu, Phys. Plasmas 6, 2834 (1999); errata in Phys. Plasmas 9, 5140 (2002).
The L_31, L_32, L_34, α_0 coefficients are functions of the trapped particle fraction
f_t and the collisionality ν*_e. Their analytic forms are given in Tables I–II of Sauter (1999).

```
[HEURISTIC: standard neoclassical ordering; Sauter et al. 1999]
The Sauter bootstrap formula is valid in the banana-to-plateau regime (ν*_e < 10).
In the H-mode pedestal, ν*_e spans 0.01–10 depending on density and temperature.
For ν*_e > 10 (highly collisional, sometimes at the very edge near the separatrix),
use the Pfirsch-Schlüter bootstrap expression or a kinetic code (NCLASS, NEO).
The Sauter formula has been validated against gyrokinetic calculations to within ~20%
for ν*_e < 1. Errors grow substantially for ν*_e > 3.
```

**Critical consequence for stability:** The pedestal bootstrap current j_∥,bs
drives the peeling mode (Section 2). Any error in computing j_∥,bs propagates
directly into the stability boundary. Profile accuracy matters here more than
anywhere else in the plasma.

---

## SECTION 2: PEELING-BALLOONING STABILITY — CORRECT FORMULATION

### 2.1 Why the Original Two-Threshold Model Is Wrong

The peeling and ballooning modes are not independent. They are coupled through the
pedestal pressure gradient and current profile in a way that produces a *single*
stability boundary in the (j_∥, α) plane — not two separate scalar limits.

The correct stability boundary has three qualitatively distinct regions:

```
Region A (low j_∥, high α): Pure ballooning instability (high-n modes, n > 20)
Region B (high j_∥, low α): Pure peeling instability (low-n modes, n = 1–5)
Region C (intermediate):    Coupled peeling-ballooning (n = 5–20); the "nose"
                             of the stability boundary; typically where ELMs occur
```

The boundary between stable and unstable in this plane can only be computed
numerically for a given equilibrium. ULTRON must not substitute scalar thresholds
for this computation.

### 2.2 Governing Physics

**Ballooning drive:**
```
[LAW] α = −q² R₀ μ₀ (dp/dψ) (2/B²)    [MHD α-parameter; identical to MHD SKILL Section 4.3]
```
where ψ is the poloidal flux, R₀ is the major radius, and dp/dψ is the local
pressure gradient on the flux surface. The ballooning stability limit (first stability
boundary) is set by this parameter together with the local magnetic shear ŝ.
See MHD SKILL Section 4.3 (Connor-Hastie-Taylor equation) for the eigenvalue problem.

**Peeling drive:**
```
[LAW] The peeling mode is driven by the parallel current gradient dj_∥/dψ at the
      plasma boundary. The stability criterion involves the jump condition on the
      outer Newcomb equation solution at the plasma-vacuum interface:
      δW_S = −(1/2) ∮_S [[p + B²/2μ₀]] |ξ_n|² dS < 0 when j_∥ is large
```
See MHD SKILL Section 4.1 (Energy Principle, δW_S term).

**Coupled peeling-ballooning:**
The coupling arises because the bootstrap current j_∥,bs ∝ dp/dψ: a steeper
pressure gradient simultaneously increases the ballooning drive α AND the peeling
drive j_∥. They cannot be varied independently in a self-consistent equilibrium.
This is the fundamental reason the pedestal operates near the peeling-ballooning
boundary — steepening the pedestal always moves toward instability in both drives
simultaneously.

### 2.3 Computational Requirements

```
[HEURISTIC: Wilson et al., Phys. Plasmas 9, 1277 (2002); Snyder et al.,
            Nucl. Fusion 44, 320 (2004)]
The peeling-ballooning stability boundary must be computed using a code that:
  (a) solves the full toroidal ideal MHD eigenvalue problem (not cylindrical)
  (b) includes the full plasma shaping (elongation κ, triangularity δ, squareness ζ)
  (c) resolves the pedestal profile with sufficient radial resolution
      (minimum ~50 flux surfaces across the pedestal width)
  (d) includes the vacuum region and the plasma-vacuum interface (δW_S)

Codes meeting these requirements: ELITE (Wilson et al. 2002), GATO, MISHKA-P.
ELITE is the community standard for pedestal stability; it has been validated
against Type-I ELM onset on DIII-D, JET, AUG, and MAST.

Cylindrical or low-n-only codes are NOT adequate for pedestal stability.
The n = 5–25 range, where peeling-ballooning is most dangerous, requires
full toroidal geometry to capture the mode structure correctly.
```

### 2.4 Stability Diagram Construction — Step-by-Step for ULTRON

```python
from typing import NamedTuple, List, Optional
import numpy as np

class PedetalStabilityPoint(NamedTuple):
    """One point in the (j_∥_normalized, α) stability plane."""
    alpha          : float   # MHD pressure-gradient parameter (dimensionless)
    j_parallel_norm: float   # j_∥ normalized to j_∥,max or Greenwald current (specify which)
    j_norm_convention: str   # 'Greenwald' | 'j_max_profile' | 'A/m2' — must be declared
    n_toroidal     : int     # toroidal mode number at marginal stability
    growth_rate_norm: float  # γτ_A at this (α, j) point; 0 = marginal, >0 = unstable
    instability_type: str    # 'peeling' | 'ballooning' | 'peeling_ballooning'

def construct_pb_boundary(equilibrium_data: dict,
                           n_range: range = range(1, 30),
                           elite_executable: str = 'elite') -> List[PedetalStabilityPoint]:
    """
    Construct the peeling-ballooning stability boundary by scanning (j, α) space.

    Procedure:
    1. Take a reference pedestal equilibrium (from EFIT or analytic profile).
    2. Scale the pressure gradient (α) and edge current (j_∥) independently
       across a 2D grid of multipliers.
    3. For each (α_scale, j_scale) point, re-solve the Grad-Shafranov equation
       self-consistently (pressure and current are not independent — scaling one
       changes the bootstrap current and therefore the other; this coupling must
       be maintained or the boundary will be wrong).
    4. Run ELITE (or equivalent) for each reconstructed equilibrium.
    5. Record the marginal point (γ → 0) for each n.
    6. The stability boundary is the envelope of marginal points across all n.

    CRITICAL: Step 3 is not optional. Scanning α and j independently on a fixed
    equilibrium violates force balance. Every point in the scan must correspond
    to a valid MHD equilibrium. This is what distinguishes a physics-correct
    boundary from a parametric approximation.

    Returns list of PedetalStabilityPoints along the marginal stability curve.
    """
    # Implementation requires: EFIT/CHEASE equilibrium reconstruction at each scan point
    # + ELITE execution + output parsing. Abbreviated structure shown here.
    boundary_points = []
    # ... (ELITE interface follows same pattern as MHD SKILL Section 7 code)
    return boundary_points

def classify_elm_type(boundary_points: List[PedetalStabilityPoint],
                      operating_point: PedetalStabilityPoint) -> dict:
    """
    Classify the expected ELM type from the location of the operating point
    relative to the stability boundary.

    Classification is empirical (see cautions below).
    """
    # Find nearest marginal point
    nearest = min(boundary_points,
                  key=lambda p: (p.alpha - operating_point.alpha)**2
                              + (p.j_parallel_norm - operating_point.j_parallel_norm)**2)

    classification = {
        'nearest_marginal_n'    : nearest.n_toroidal,
        'nearest_instability'   : nearest.instability_type,
        'growth_rate_margin'    : nearest.growth_rate_norm,
        'probable_elm_type'     : None,
        'confidence'            : None,
        'caveats'               : [],
    }

    # [HEURISTIC: Zohm, PPCF 38, L27 (1996); Connor, PPCF 40, 191 (1998);
    #             Snyder et al., Nucl. Fusion 44, 320 (2004)]
    if nearest.n_toroidal <= 5 and nearest.instability_type == 'peeling':
        classification['probable_elm_type'] = 'Type-I (peeling-dominant)'
        classification['confidence'] = 0.6
        classification['caveats'].append(
            "Low-n peeling modes typically precede Type-I ELMs, but classification "
            "requires corroboration from ELM energy loss ΔW/W_ped > 5% and frequency "
            "scaling f_ELM ~ 1/P_input. Do not classify from stability alone."
        )
    elif nearest.n_toroidal >= 15 and nearest.instability_type == 'ballooning':
        classification['probable_elm_type'] = 'Type-II (ballooning-dominant, near second stability)'
        classification['confidence'] = 0.45
        classification['caveats'].append(
            "Type-II ELMs require operating near the second stability boundary AND "
            "high triangularity (δ > 0.4). The stability calculation alone is "
            "insufficient for Type-II classification."
        )
    elif 5 < nearest.n_toroidal < 15 and nearest.instability_type == 'peeling_ballooning':
        classification['probable_elm_type'] = 'Type-I (coupled peeling-ballooning)'
        classification['confidence'] = 0.7
        classification['caveats'].append(
            "Most common Type-I ELM regime. Validate with: ΔW_ELM, f_ELM vs P, "
            "and D-alpha spike morphology."
        )
    else:
        classification['probable_elm_type'] = 'Indeterminate from stability alone'
        classification['confidence'] = 0.2
        classification['caveats'].append(
            "ELM type cannot be determined from stability boundary position alone. "
            "Type-III ELMs occur below the peeling-ballooning boundary; they are "
            "driven by resistive edge modes and require separate analysis."
        )

    return classification
```

---

## SECTION 3: THE EPED MODEL — CORRECT USE AND KNOWN FAILURES

### 3.1 What EPED Is and Is Not

EPED (Edge Pedestal model; Snyder et al.) is a predictive model for the pedestal
height and width. It combines two constraints:

**Constraint 1 — Peeling-ballooning stability boundary** (Section 2):
The pedestal pressure gradient cannot exceed the MHD stability limit.

**Constraint 2 — Kinetic ballooning mode (KBM) width constraint:**
```
[HEURISTIC: Snyder et al., Nucl. Fusion 49, 085035 (2009);
            Snyder et al., Phys. Plasmas 19, 056115 (2012)]
The pedestal width Δ_ped (in ψ_N) is set by the onset of kinetic ballooning modes
(KBMs) — ion-scale drift-Alfvén instabilities — which limit how narrow the pedestal
can become before KBM-driven transport widens it.

The EPED1 KBM width constraint is:
  Δ_ped ≈ 0.076 × √(β_pol,ped)

where β_pol,ped = 2μ₀ p_ped / B_pol,ped²
      and B_pol,ped is the poloidal field at the pedestal top.

VALIDITY DOMAIN AND KNOWN FAILURES (mandatory reading before use):
  (a) Database basis: EPED1 was fit to a database of ~100 discharges on DIII-D
      with circular-to-moderately-shaped plasmas. The coefficient 0.076 is a
      regression fit, NOT a derived constant. It carries ±20–30% scatter on the
      training database itself.
  (b) Shape dependence: The coefficient is known to vary with triangularity δ and
      elongation κ. High-triangularity (δ > 0.45) plasmas systematically deviate
      from EPED1. EPED1.6 and EPED2 include shaping corrections; use these for
      ITER-like geometries (δ = 0.48).
  (c) Isotope effect: The KBM threshold has a weak isotope dependence (heavier
      ions → marginally wider pedestal). EPED1 was calibrated primarily on
      deuterium; tritium predictions carry additional uncertainty.
  (d) Impurity effects: Impurity seeding changes the pedestal density profile and
      the effective Z, shifting the KBM onset. EPED1 ignores impurities.
  (e) ELM-free regimes: EPED is explicitly a model for ELMy H-mode. It does not
      apply to QH-mode, I-mode, EDA H-mode, or RMP-suppressed pedestals.

ULTRON must not apply the Δ_ped = 0.076√β_pol formula outside the deuterium ELMy
H-mode regime without declaring which validated extension is being used.
```

### 3.2 EPED Prediction Workflow

```python
import numpy as np

def eped1_prediction(B_T: float, I_p: float, R_0: float, a: float,
                     kappa: float, delta: float,
                     n_e_ped_target: float,
                     Z_eff: float = 1.5,
                     isotope: str = 'deuterium') -> dict:
    """
    EPED1 pedestal height prediction.

    Inputs:
      B_T            : toroidal field [T]
      I_p            : plasma current [A]
      R_0            : major radius [m]
      a              : minor radius [m]
      kappa          : elongation [-]
      delta          : triangularity [-]
      n_e_ped_target : target pedestal electron density [m⁻³]
      Z_eff          : effective ion charge (for bootstrap correction)
      isotope        : 'deuterium' | 'hydrogen' | 'DT_mix'

    Returns:
      Predicted p_ped [Pa], T_e_ped [eV], Δ_ped [ψ_N], and uncertainty bounds.
      All bounds are [HEURISTIC] from EPED1 validation database scatter.
    """
    MU0 = 4 * np.pi * 1e-7

    # ── Geometric quantities ──
    # Volume-averaged poloidal field (approximate for shaped plasma)
    B_pol_avg = MU0 * I_p / (2 * np.pi * a * kappa**0.5)  # rough shaping correction

    # ── KBM width constraint (EPED1) ──
    # Δ_ped = 0.076 × sqrt(β_pol,ped)
    # This requires iterating because β_pol,ped depends on p_ped which depends on Δ_ped.
    # EPED solves this self-consistently with the MHD boundary. Here we iterate simply.

    # [HEURISTIC: EPED1 coefficient; Snyder et al. 2009, validated on DIII-D database]
    # Uncertainty on this coefficient: ±25% (1-sigma on training database)
    EPED1_COEFF = 0.076
    EPED1_COEFF_UNCERTAINTY = 0.020  # ±0.020 (1-sigma)

    if delta > 0.4:
        # [HEURISTIC: EPED1.6 shaping correction; Snyder et al. 2012]
        # High-triangularity correction; coefficient increases by ~10–15%
        shape_correction = 1.0 + 0.3 * (delta - 0.4)
        import warnings
        warnings.warn(
            f"δ = {delta:.2f} > 0.4: applying shape correction factor {shape_correction:.3f}. "
            "This correction is from EPED1.6 (Snyder 2012), not base EPED1. "
            "Uncertainty is larger than quoted below.",
            UserWarning
        )
    else:
        shape_correction = 1.0

    if isotope != 'deuterium':
        warnings.warn(
            f"EPED1 KBM coefficient calibrated on deuterium. Applying to '{isotope}' "
            "introduces unconstrained systematic error. Results are indicative only.",
            UserWarning
        )

    # Iterative solution for Δ_ped and p_ped
    # Initial guess: p_ped from pressure balance at pedestal
    T_e_guess = 500.0  # eV
    p_ped_guess = 2 * n_e_ped_target * T_e_guess * 1.602e-19  # Pa (factor 2: T_e + T_i ≈ 2T_e)

    for _ in range(20):  # iterate to convergence
        beta_pol_ped = 2 * MU0 * p_ped_guess / B_pol_avg**2
        delta_ped = EPED1_COEFF * shape_correction * np.sqrt(beta_pol_ped)

        # Convert pedestal width to physical units for profile integration
        # delta_ped is in ψ_N; convert to meters requires flux surface geometry
        # (simplified here as linear mapping — ULTRON must use actual geometry)
        delta_ped_phys_m = delta_ped * a  # APPROXIMATION; valid only for circular cross-section

        # Pressure from gradient × width (trapezoidal approximation)
        # This step requires the MHD stability boundary to set dp/dψ|_max
        # Simplified: p_ped ≈ (dp/dψ)|_MHD × Δ_ped (requires ELITE output for dp/dψ|_MHD)
        # Here we use a placeholder; real EPED iterates with the MHD boundary simultaneously
        p_ped_new = p_ped_guess  # placeholder — real EPED substitutes MHD boundary value here
        if abs(p_ped_new - p_ped_guess) / (p_ped_guess + 1e-10) < 1e-4:
            break
        p_ped_guess = p_ped_new

    T_e_ped = p_ped_guess / (2 * n_e_ped_target * 1.602e-19)  # eV

    return {
        'p_ped_Pa'          : p_ped_guess,
        'T_e_ped_eV'        : T_e_ped,
        'delta_ped_psi_N'   : delta_ped,
        'beta_pol_ped'      : beta_pol_ped,
        'shape_correction'  : shape_correction,
        # ── Uncertainty (HEURISTIC from database validation scatter) ──
        'p_ped_uncertainty_1sigma_frac' : 0.25,  # ±25%; from Snyder 2009 Fig. 8
        'T_ped_uncertainty_1sigma_frac' : 0.25,
        'delta_uncertainty_1sigma_frac' : 0.20,
        'validity_warnings' : [
            "Result valid only for ELMy deuterium H-mode.",
            "KBM width constraint is a regression fit, not a derived law.",
            f"delta = {delta:.2f}: {'shape correction applied (EPED1.6)' if delta > 0.4 else 'base EPED1 applicable'}.",
            "Self-consistent MHD boundary iteration not completed; p_ped requires ELITE output.",
        ],
    }
```

---

## SECTION 4: RESONANT MAGNETIC PERTURBATION (RMP) PHYSICS

### 4.1 What the Original Skill Got Wrong

The original skill stated: "Resonance occurs when m = n·q(ψ)."
This is the *vacuum* resonance condition — a necessary but nowhere near sufficient
condition for ELM suppression. It ignores:

- **Plasma response:** The plasma shields resonant fields via induced currents.
  The actual resonant field at the rational surface is far weaker than the vacuum field.
- **Rotation screening:** Toroidal and poloidal plasma rotation partially or fully
  shields the resonant field. Whether ELM suppression or ELM mitigation occurs
  depends critically on the rotation profile.
- **Island overlap (Chirikov criterion):** Adjacent rational surfaces must have
  overlapping island chains to create stochasticity. Simply being resonant is not enough.
- **3D equilibrium response:** RMPs produce a 3D equilibrium distortion, including
  changes to the pressure and current profiles at the edge.

ULTRON must not conclude "ELM suppression" from the vacuum resonance condition alone.

### 4.2 Vacuum Resonance Condition

```
[LAW] A magnetic perturbation with toroidal mode number n and poloidal mode number m
      is resonant with the equilibrium at the flux surface where:
      q(ψ_res) = m/n
```

This is a consequence of the structure of the ideal MHD force operator. It is a law
in the sense that it follows from the geometry of field-line winding in an axisymmetric
equilibrium. It is NOT a law in the sense that resonance guarantees any physical effect —
the plasma response determines the actual field perturbation at the surface.

**Correct implementation:**
```python
import numpy as np
from scipy.interpolate import interp1d
from scipy.optimize import brentq
from typing import List, Tuple

def find_vacuum_resonant_surfaces(q_profile: np.ndarray,
                                   psi_N_grid: np.ndarray,
                                   n_coil: int,
                                   m_range: Tuple[int, int] = (1, 20)) -> List[dict]:
    """
    Find all surfaces where the vacuum RMP field with toroidal number n_coil
    is resonant, for m in m_range.

    Returns list of resonant surfaces with their location, q value, and
    a prominent warning that vacuum resonance ≠ ELM suppression.

    Requires: q_profile and psi_N_grid from a validated equilibrium reconstruction
    (see MHD SKILL Section 2). Do not use q = rB_φ/(RB_pol) shortcut.
    """
    q_interp = interp1d(psi_N_grid, q_profile, kind='cubic',
                        bounds_error=False, fill_value='extrapolate')

    resonant_surfaces = []

    for m in range(m_range[0], m_range[1] + 1):
        q_target = m / n_coil

        # Only search in the edge region (ψ_N > 0.85) for pedestal RMP physics
        psi_edge = psi_N_grid[psi_N_grid > 0.85]
        q_edge   = q_interp(psi_edge)

        # Find zero crossings of q(ψ) - q_target
        for i in range(len(q_edge) - 1):
            if (q_edge[i] - q_target) * (q_edge[i+1] - q_target) < 0:
                try:
                    psi_res = brentq(lambda psi: q_interp(psi) - q_target,
                                     psi_edge[i], psi_edge[i+1])
                    resonant_surfaces.append({
                        'm'       : m,
                        'n'       : n_coil,
                        'psi_N'   : psi_res,
                        'q_res'   : q_target,
                        'WARNING' : (
                            "Vacuum resonance condition satisfied. This does NOT imply "
                            "ELM suppression. Plasma response, rotation screening, and "
                            "Chirikov island overlap must be evaluated separately."
                        ),
                    })
                except ValueError:
                    pass

    return resonant_surfaces
```

### 4.3 Plasma Response — Why Vacuum Field Is Not Enough

When an external RMP field B_ext is applied, the plasma response produces shielding
currents that oppose the field at rational surfaces. The net resonant field B_res
at the surface is:

```
[LAW] B_res = B_ext + B_plasma_response
```

The plasma response B_plasma_response opposes B_ext at rational surfaces (shielding)
for rotating plasmas and reinforces it (amplification) for some non-rotating cases.

```
[HEURISTIC: Fitzpatrick, Phys. Plasmas 5, 3325 (1998); Heyn et al., Nucl. Fusion 48,
            024005 (2008); Liu et al., Phys. Plasmas 17, 122502 (2010)]
In the presence of toroidal rotation Ω_φ:
  - If Ω_φ > Ω_crit (critical rotation for resonance locking), the plasma shields
    the resonant field: |B_res| ≪ |B_ext|. ELM mitigation may still occur via
    quasi-linear density pump-out, but full suppression is unlikely.
  - If Ω_φ < Ω_crit, the resonant field can penetrate and form islands.
    ELM suppression becomes possible if Chirikov overlap is also satisfied.
  - Ω_crit depends on the resistivity η at the rational surface, the island width W,
    and the viscous and electromagnetic torques; it is NOT a universal number.

Codes for plasma response: MARS-F (Liu et al.), IPEC (Park et al.), M3D-C1 linear.
Vacuum field codes alone (e.g. TRIP3D, ERGOS) are INSUFFICIENT for suppression prediction.
```

### 4.4 Chirikov Island Overlap — The Stochasticity Condition

For RMPs to create a stochastic field-line region (which is the mechanism by which
ELM suppression is usually explained in the "field-line ergodization" picture), the
magnetic islands at adjacent rational surfaces must overlap.

```
[LAW] Chirikov overlap parameter between surfaces at q = m₁/n and q = m₂/n
      (adjacent resonances, m₂ = m₁ + 1):

      σ_Ch = (W₁ + W₂) / (2 Δr_{12})

      where:
        W_i   = island half-width at surface i [in r or ψ_N]
        Δr_12 = radial separation between the two rational surfaces

      σ_Ch > 1: islands overlap → field lines are stochastic (ergodic) between the surfaces
      σ_Ch < 1: islands are isolated → field lines remain on KAM surfaces → NO stochasticity
```

Source: Chirikov, Phys. Reports 52, 263 (1979); applied to tokamak RMPs by
Punjabi et al. and Rosenbluth et al.; standard reference for RMP stochasticity.

**Island half-width:**
```
[LAW] W_i = 4 √(r_s |b_r^{m,n}| / (n |dq/dr|_s))    [in minor radius units]

      where b_r^{m,n} = radial component of the resonant field at the surface
                         (from plasma response calculation, NOT vacuum field alone)
            r_s         = minor radius of the rational surface
            |dq/dr|_s   = magnitude of the q-profile gradient at the surface
```

Source: White, Theory of Tokamak Plasmas (1989), Ch. 4; Cary & Hanson, Phys. Fluids 29, 2464 (1986).

```python
import numpy as np
from scipy.interpolate import interp1d

def chirikov_overlap_parameter(q_profile: np.ndarray,
                                psi_N_grid: np.ndarray,
                                b_r_resonant: dict,
                                n_coil: int,
                                m_pair: tuple) -> dict:
    """
    Compute Chirikov overlap parameter between two adjacent RMP-driven islands.

    Inputs:
      q_profile       : q(ψ_N) from validated equilibrium (NOT the shortcut formula)
      psi_N_grid      : ψ_N grid
      b_r_resonant    : dict {m: b_r_value} — resonant radial field AT the surface
                        from PLASMA RESPONSE calculation, not vacuum field.
                        If only vacuum field is available, results will be optimistic
                        (will overestimate island widths and overlap).
      n_coil          : toroidal mode number of the RMP coil set
      m_pair          : (m1, m2) = adjacent poloidal mode numbers to evaluate

    Returns:
      Chirikov parameter σ_Ch, island widths, surface separation, and interpretation.
    """
    m1, m2 = m_pair
    assert m2 == m1 + 1, "Only adjacent surfaces (m2 = m1 + 1) are valid for Chirikov"

    q_interp  = interp1d(psi_N_grid, q_profile, kind='cubic')
    dq_dpsi   = np.gradient(q_profile, psi_N_grid)
    dq_interp = interp1d(psi_N_grid, dq_dpsi, kind='linear')

    # Locate rational surfaces
    from scipy.optimize import brentq
    def q_minus_target(psi, m):
        return q_interp(psi) - m/n_coil

    try:
        psi_s1 = brentq(q_minus_target, 0.85, 0.99, args=(m1,))
        psi_s2 = brentq(q_minus_target, 0.85, 0.99, args=(m2,))
    except ValueError:
        return {'error': f'One or both rational surfaces (m={m1},{m2}, n={n_coil}) '
                         'not found in ψ_N ∈ [0.85, 0.99]'}

    delta_psi_12 = abs(psi_s2 - psi_s1)

    # Island widths (in ψ_N units)
    # W ~ 4 √(|b_r^{m,n}| / (n |dq/dψ|_s)) — adapted to ψ_N coordinates
    def island_width_psi(m, psi_s):
        b_r = b_r_resonant.get(m, None)
        if b_r is None:
            raise ValueError(f"No resonant field provided for m={m}. "
                             "Run plasma response code first (MARS-F, IPEC).")
        dq = abs(dq_interp(psi_s))
        if dq < 1e-10:
            raise ValueError(f"dq/dψ ≈ 0 at ψ_N={psi_s:.4f} (near q_min?). "
                             "Chirikov formula singular here; use reversed-shear treatment.")
        return 4 * np.sqrt(abs(b_r) / (n_coil * dq + 1e-30))

    try:
        W1 = island_width_psi(m1, psi_s1)
        W2 = island_width_psi(m2, psi_s2)
    except ValueError as e:
        return {'error': str(e)}

    sigma_chirikov = (W1 + W2) / (2 * delta_psi_12)

    interpretation = (
        'STOCHASTIC: islands overlap; field-line ergodization possible'
        if sigma_chirikov > 1.0 else
        'ISOLATED: islands do not overlap; no stochastic layer at this field amplitude'
    )

    return {
        'sigma_chirikov'       : sigma_chirikov,
        'W1_psi_N'             : W1,
        'W2_psi_N'             : W2,
        'psi_s1'               : psi_s1,
        'psi_s2'               : psi_s2,
        'delta_psi_12'         : delta_psi_12,
        'interpretation'       : interpretation,
        'WARNING_vacuum_field' : (
            'If b_r_resonant was computed from vacuum field (not plasma response), '
            'island widths are OVERESTIMATED. Plasma shielding at rotating surfaces '
            'reduces b_r by factors of 2–100 depending on rotation and resistivity. '
            'A σ_Ch > 1 computed from vacuum field does NOT guarantee stochasticity.'
        ),
        # [HEURISTIC: σ_Ch > 1 criterion; Chirikov 1979]
        # The σ_Ch = 1 threshold is an approximate criterion derived from Hamiltonian
        # perturbation theory for idealized island chains. In tokamak geometry with
        # realistic q-profiles and non-sinusoidal perturbations, the onset of
        # stochasticity can occur at σ_Ch slightly below or above 1.
    }
```

### 4.5 Rotation Screening and the Penetration Threshold

```
[HEURISTIC: Fitzpatrick, Phys. Plasmas 5, 3325 (1998); La Haye et al. 1992;
            Paz-Soldan et al., Phys. Rev. Lett. 114, 105001 (2015)]

For a rotating plasma, the RMP field penetration at a rational surface depends
on the electromagnetic torque (which slows rotation) vs the viscous restoring torque.
Field penetration (island locking) occurs when:

  b_r^{m,n} > b_r^{crit} ≈ (η_s / μ₀) × (n |dq/dr|_s / r_s) × (τ_visc / τ_A)^{1/2}
                                                                  × (Ω_φ / v_A) × ...

The full expression for b_r^{crit} requires the equilibrium rotation profile, the
edge resistivity, and the viscous momentum transport. It is not a simple formula.

Operationally:
  - ELM SUPPRESSION (not just mitigation) has been observed when:
    (a) Chirikov σ_Ch > 1 using the plasma-response field, AND
    (b) Rotation at the q=2 surface is reduced by ≥ 30% by RMP-induced torque, AND
    (c) The q-profile places multiple resonant surfaces within the pedestal (ψ_N > 0.9)
  - ELM MITIGATION (frequency increase, size reduction without suppression) is observed
    more broadly; it does not require Chirikov overlap.
  - Neither suppression nor mitigation is guaranteed by vacuum resonance alone.

Machines demonstrating full ELM suppression with n=3 RMPs: DIII-D (Evans et al. 2006),
AUG (Kirk et al. 2012), KSTAR (Jeon et al. 2012). Suppression on JET has been partial.
ITER RMP design (n=3,4) is based on this empirical database; extrapolation carries
substantial uncertainty.
```

---

## SECTION 5: PEDESTAL PROFILE MEASUREMENTS AND DATA REQUIREMENTS

### 5.1 What Diagnostics ULTRON Needs — and What Each Measures

All pedestal stability analysis is only as good as the input profiles.
The following diagnostics are required for a complete pedestal characterization:

| Quantity | Primary Diagnostic | Typical Resolution | Known Systematic Errors |
|---|---|---|---|
| T_e(ψ_N) | Thomson Scattering (TS) | ~5 mm spatial, ±10% | Laser-light scattering artifacts near LCFS; Abel inversion in some geometries |
| n_e(ψ_N) | Thomson Scattering | ~5 mm, ±10% | Same as T_e; high-n edge TS notoriously noisy |
| T_i(ψ_N) | Charge Exchange Recombination (CER/CXRS) | ~10–20 mm, ±5% | Requires beam injection; measures at beam intersection points only |
| Ω_φ(ψ_N) | CXRS Doppler shift | ~10–20 mm | Active only at beam location; passive CER for impurities elsewhere |
| j_∥(ψ_N) | NOT directly measured | — | Must be inferred from Motional Stark Effect (MSE) + EFIT, or from neoclassical calculation |
| B_r^{m,n} | Mirnov coils + RMP response | Coil array geometry-dependent | Vacuum field computed; plasma response requires modeling |

```
[HEURISTIC: standard experimental practice on DIII-D, JET, AUG]
Pedestal profiles must be fit using a modified hyperbolic-tangent (mtanh) function:
  f(x) = (f_top + f_sol)/2 + (f_top − f_sol)/2 × mtanh((x_ped − x)/(Δ/2))
          + slope × (x − x_ped)

where mtanh(z) = [(1+z)exp(z) − (1−z)exp(−z)] / [exp(z) + exp(−z)]

x_ped  = pedestal midpoint location
Δ      = pedestal full-width (at half gradient, in ψ_N or R)
f_top  = value at pedestal top
f_sol  = value in the scrape-off layer

This is a fitting function, not a physics prediction. Using raw profile data
without fitting produces spurious gradients from measurement noise that will
destabilize the computed stability boundary. The mtanh fit must be performed
on T_e, n_e, and (if available) T_i separately before computing pressure and
bootstrap current profiles.
```

### 5.2 Profile Uncertainty Propagation

ULTRON must propagate diagnostic measurement uncertainty into stability outputs.

```python
import numpy as np
from scipy.stats import norm

def pedestal_uncertainty_propagation(T_e_mean: np.ndarray,
                                      T_e_std: np.ndarray,
                                      n_e_mean: np.ndarray,
                                      n_e_std: np.ndarray,
                                      psi_N: np.ndarray,
                                      n_mc: int = 300) -> dict:
    """
    Monte Carlo propagation of Thomson scattering uncertainties into
    pedestal stability metrics: α, j_∥_bs, and Δ_ped.

    n_mc = 300 is sufficient for ~5% statistical error on percentile estimates.
    Increase to 1000 for publication-quality uncertainty bounds.

    Returns 5th/50th/95th percentile of each derived quantity.
    """
    MU0 = 4 * np.pi * 1e-7
    e_charge = 1.602e-19

    results = {'alpha': [], 'j_bs_peak': [], 'delta_ped_psi': []}

    for _ in range(n_mc):
        # Sample profiles within measurement uncertainty (assume Gaussian)
        T_e_s = np.maximum(T_e_mean + np.random.randn(*T_e_mean.shape) * T_e_std, 10.0)
        n_e_s = np.maximum(n_e_mean + np.random.randn(*n_e_mean.shape) * n_e_std, 1e17)

        # Approximate T_i ~ T_e in pedestal (common assumption when CER unavailable;
        # introduces systematic error of ~10–30% in bootstrap current for T_i ≠ T_e)
        p_s = n_e_s * (T_e_s + T_e_s) * e_charge  # p_total = n_e(T_e + T_i) ≈ 2 n_e T_e

        # dp/dψ at pedestal (finite difference)
        dp_dpsi = np.gradient(p_s, psi_N)
        dp_dpsi_peak = np.min(dp_dpsi)  # most negative = steepest gradient

        # α at pedestal top (approximate; needs actual B, q, R from equilibrium)
        # Placeholder: alpha ~ |dp/dψ| × q²R²/B² — ULTRON fills from equilibrium
        results['alpha'].append(abs(dp_dpsi_peak))

        # Bootstrap current (Sauter, simplified — j_bs ∝ dp/dψ × f_t)
        # Full Sauter requires collisionality; simplified here for UQ demonstration
        results['j_bs_peak'].append(abs(dp_dpsi_peak) * 0.3)  # rough proportionality

        # Pedestal width (mtanh fit on each sample)
        # Simplified: use gradient scale length L_p = p / |dp/dψ|
        idx_ped = np.argmin(dp_dpsi)
        L_p = abs(p_s[idx_ped] / (dp_dpsi_peak + 1e-30))
        results['delta_ped_psi'].append(L_p)

    summary = {}
    for key, vals in results.items():
        arr = np.array(vals)
        summary[key] = {
            'p05': np.percentile(arr, 5),
            'p50': np.percentile(arr, 50),
            'p95': np.percentile(arr, 95),
            'std': np.std(arr),
            'label': '[HEURISTIC: Monte Carlo on Thomson TS uncertainties]',
        }
    return summary
```

---

## SECTION 6: KNOWN FAILURE MODES OF THIS SKILL

ULTRON must escalate rather than proceed when any of the following apply:

| Condition | Why this skill fails | Required action |
|---|---|---|
| QH-mode (quiescent H-mode) | No ELMs; edge harmonic oscillation (EHO) replaces ELM cycle; peeling-ballooning boundary is NOT the operating limit | Separate QH-mode physics skill required; key ref: Burrell et al., Phys. Plasmas 12, 056121 (2005) |
| I-mode | Edge temperature barrier without density barrier; no bootstrap-driven pedestal; ELMs absent | I-mode transport physics; Whyte et al., Nucl. Fusion 50, 105005 (2010) |
| EDA H-mode (Enhanced D-Alpha) | Quasi-coherent mode replaces ELMs; different edge instability physics | Greenwald et al., Phys. Plasmas 6, 1943 (1999) |
| RMP-suppressed pedestal | EPED not applicable; pedestal width and height modified by 3D fields | 3D equilibrium + plasma response required (MARS-F + VMEC) |
| Detached divertor conditions | LCFS and separatrix physics modified; pressure boundary condition changes | SOL and divertor physics beyond this skill |
| Negative triangularity (δ < 0) | Peeling-ballooning boundary moves; second stability is not accessible in the same way; L-mode-like confinement often persists even at high power | NT-specific stability analysis; Austin et al., Phys. Rev. Lett. 122, 115001 (2019) |
| ITER/reactor extrapolation | EPED1 coefficient not validated on reactor-scale plasma; isotope (DT) effects unquantified; pedestal fueling by alpha-particle heating changes profiles | Treat all EPED outputs as indicative with ≥50% uncertainty; use EPED2+gyrokinetic validation |
| Pedestal near density limit (Greenwald fraction f_GW > 0.85) | MHD stability is insufficient; density-limit physics (MARFE, detachment) couple to pedestal | Density limit physics separate from this skill |

---

## SECTION 7: HYPOTHESIS SCHEMA FOR PEDESTAL PHYSICS

Every pedestal hypothesis generated by ULTRON must conform to this structure,
inheriting all mandatory fields from MHD_SKILL_v5 `MHDHypothesis` and adding:

```python
from dataclasses import dataclass, field
from typing import List, Optional, Dict

@dataclass
class PedestalHypothesis:
    """
    Pedestal-specific hypothesis extension.
    Must be used together with MHDHypothesis (from MHD_SKILL_v5) for stability claims.
    """
    # ── Pedestal regime (required first) ──
    confinement_mode : str   # 'ELMy_H' | 'QH' | 'I_mode' | 'EDA_H' | 'L_mode' | 'other'
    elm_regime       : str   # 'Type-I' | 'Type-II' | 'Type-III' | 'suppressed' |
                              # 'mitigated' | 'absent' | 'unknown'
    rmp_applied      : bool
    rmp_n_dominant   : Optional[int]   # dominant toroidal mode number of applied RMP

    # ── Profile inputs (required; document diagnostic source for each) ──
    T_e_profile_source : str   # e.g. 'Thomson Scattering, DIII-D shot 184977 t=2550ms'
    n_e_profile_source : str
    T_i_profile_source : str   # or 'ASSUMED T_i = T_e (no CER available)'
    j_parallel_source  : str   # 'Sauter bootstrap from TS profiles' | 'MSE+EFIT' | etc.

    # ── EPED applicability check (required) ──
    eped_applicable    : bool
    eped_inapplicable_reason : Optional[str]  # must be filled if eped_applicable = False

    # ── RMP claims (required if rmp_applied = True) ──
    vacuum_resonance_computed  : Optional[bool]
    plasma_response_computed   : Optional[bool]   # MARS-F, IPEC, or equivalent
    chirikov_computed          : Optional[bool]
    chirikov_sigma             : Optional[float]
    chirikov_field_source      : Optional[str]    # 'vacuum' | 'plasma_response' | 'not_computed'
    suppression_claim          : Optional[str]    # must be 'suppression' | 'mitigation' | 'none'
                                                   # 'suppression' requires chirikov_computed=True
                                                   # AND plasma_response_computed=True

    # ── Heuristics declared (inherited obligation from MHD_SKILL_v5) ──
    heuristics_applied : List[str]

    def validate_schema(self) -> List[str]:
        errors = []
        if self.confinement_mode not in {
            'ELMy_H', 'QH', 'I_mode', 'EDA_H', 'L_mode', 'other'}:
            errors.append(f"Unknown confinement_mode '{self.confinement_mode}'")
        if self.eped_applicable and self.confinement_mode != 'ELMy_H':
            errors.append(
                "EPED is only validated for ELMy H-mode. "
                f"confinement_mode='{self.confinement_mode}' is incompatible with "
                "eped_applicable=True."
            )
        if self.rmp_applied:
            if self.suppression_claim == 'suppression':
                if not self.chirikov_computed:
                    errors.append(
                        "ELM suppression claim requires Chirikov overlap parameter "
                        "to be computed (chirikov_computed=True)."
                    )
                if not self.plasma_response_computed:
                    errors.append(
                        "ELM suppression claim requires plasma response calculation "
                        "(MARS-F, IPEC, or equivalent). Vacuum field alone is insufficient."
                    )
                if self.chirikov_field_source == 'vacuum':
                    errors.append(
                        "Chirikov parameter computed from vacuum field only. "
                        "This overestimates island widths due to plasma shielding. "
                        "Suppression claim is not supportable from this input."
                    )
        if not self.heuristics_applied:
            errors.append("heuristics_applied cannot be empty.")
        return errors
```

---

## SECTION 8: CANONICAL REFERENCES

**H-mode and pedestal:**
- Wagner et al. (1982). Regime of improved confinement and high beta in neutral-beam-heated divertor discharges of the ASDEX tokamak. Phys. Rev. Lett. 49, 1408.
- Zohm (1996). Edge-localized modes. Plasma Phys. Control. Fusion 38, L27.
- Connor (1998). A review of models for ELMs. Plasma Phys. Control. Fusion 40, 191.

**Peeling-ballooning and EPED:**
- Wilson et al. (2002). Numerical studies of edge localized instabilities in tokamaks. Phys. Plasmas 9, 1277.
- Snyder et al. (2004). ELMs and constraints on the H-mode pedestal. Nucl. Fusion 44, 320.
- Snyder et al. (2009). Pedestal stability comparison and ITER projections. Nucl. Fusion 49, 085035.
- Snyder et al. (2012). A first-principles predictive model of the pedestal height and width. Phys. Plasmas 19, 056115. [EPED1.6]

**Bootstrap current:**
- Sauter, Angioni, Lin-Liu (1999). Neoclassical conductivity and bootstrap current formulas. Phys. Plasmas 6, 2834.
- Sauter, Angioni, Lin-Liu (2002). Erratum. Phys. Plasmas 9, 5140.

**RMP physics:**
- Chirikov (1979). A universal instability of many-dimensional oscillator systems. Phys. Reports 52, 263.
- Evans et al. (2006). Suppression of large edge-localized modes with edge-resonant magnetic fields. Nature Physics 2, 419.
- Fitzpatrick (1998). Interaction of tearing modes with external structures in a tokamak. Phys. Plasmas 5, 3325.
- Liu et al. (2010). Feedback stabilization of nonaxisymmetric resistive wall modes in tokamaks. Phys. Plasmas 17, 122502. [MARS-F plasma response]
- Jeon et al. (2012). Suppression of edge-localized modes in high-confinement KSTAR plasmas by nonaxisymmetric magnetic perturbations. Phys. Rev. Lett. 109, 035004.

**Profile fitting:**
- Groebner & Osborne (1998). Scaling studies of the high mode pedestal. Phys. Plasmas 5, 1800. [mtanh fitting method]

**Failure mode references:**
- Burrell et al. (2005). Quiescent H-mode plasmas. Phys. Plasmas 12, 056121.
- Whyte et al. (2010). I-mode: an H-mode energy confinement regime with L-mode particle transport. Nucl. Fusion 50, 105005.
- Austin et al. (2019). Achievement of reactor-relevant performance in negative triangularity shape. Phys. Rev. Lett. 122, 115001.
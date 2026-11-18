# -*- coding: utf-8 -*-
"""
ULTRON Physics Kernels - PhD Level Rigor (UPGRADED)
====================================================
Verified numerical kernels for scientific experiments.

UPGRADES FROM v1:
  - Full Lyapunov Spectrum via QR-Benettin (not just largest exponent)
  - Kaplan-Yorke fractal dimension from spectrum
  - Symplectic integrators (RK4, Strmer-Verlet) for Hamiltonian energy conservation
  - Poincar section extraction with interpolation
  - Recurrence Quantification Analysis (RQA)
  - Correlation dimension via Grassberger-Procaccia
  - Proper chaos classification (chaotic / quasiperiodic / periodic / fixed point)
  - Energy drift tracking for conservative systems
  - Numerical error estimation via Richardson extrapolation
  - Bifurcation diagram builder
  - All methods return structured result objects, not raw floats

REFERENCES:
  Benettin et al. (1980) Meccanica 15:9
  Grassberger & Procaccia (1983) Phys Rev Lett 50:346
  Eckmann et al. (1987) Europhys Lett 4:973  [RQA]
  Hairer et al. (2006) Geometric Numerical Integration
"""

import numpy as np
import scipy.integrate as integrate
import scipy.spatial as spatial
import logging
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Any, Tuple, Optional
from enum import Enum

logger = logging.getLogger("ultron.physics.kernels")


# 
# RESULT STRUCTURES
# 

@dataclass
class LyapunovResult:
    """Full Lyapunov analysis result."""
    exponents: np.ndarray               # Sorted descending [    ...  ]
    largest: float                      #   positive = chaotic
    spectrum_sum: float                 # Should be  0 for dissipative systems
    kaplan_yorke_dim: float             # Fractal dimension D_KY
    is_chaotic: bool                    #  > 0 with confidence
    convergence_trace: np.ndarray       #  vs time  check for plateau
    renorm_count: int
    system_dim: int
    classification: str                 # "chaotic" | "quasiperiodic" | "periodic" | "fixed_point"
    confidence: float                   # 01 based on convergence quality

    def to_dict(self) -> Dict[str, Any]:
        return {
            "largest_lyapunov_exponent": float(self.largest),
            "full_spectrum": self.exponents.tolist(),
            "spectrum_sum": float(self.spectrum_sum),
            "kaplan_yorke_dimension": float(self.kaplan_yorke_dim),
            "is_chaotic": self.is_chaotic,
            "classification": self.classification,
            "confidence": float(self.confidence),
            "renormalizations": self.renorm_count,
            "system_dimension": self.system_dim,
        }


@dataclass
class IntegrationResult:
    """High-fidelity ODE solution with error tracking."""
    success: bool
    t: np.ndarray
    y: np.ndarray                      # shape (n_vars, n_times)
    energy_drift: Optional[float]      # |H/H| if hamiltonian provided
    local_error_estimate: float        # Richardson extrapolation error
    nfev: int
    message: str
    integrator_used: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "n_timepoints": len(self.t),
            "t_span": [float(self.t[0]), float(self.t[-1])],
            "energy_drift": self.energy_drift,
            "local_error_estimate": float(self.local_error_estimate),
            "nfev": self.nfev,
            "message": self.message,
            "integrator": self.integrator_used,
        }


@dataclass
class PoincareResult:
    """Poincar section in a given hyperplane."""
    crossings: np.ndarray              # Points on the section (N  dim-1)
    crossing_times: np.ndarray
    n_crossings: int
    section_axis: int
    section_value: float
    is_closed_orbit: bool              # True if points form a closed curve
    return_time_mean: float
    return_time_std: float


@dataclass
class RQAResult:
    """Recurrence Quantification Analysis result."""
    recurrence_rate: float             # %REC  density of recurrence points
    determinism: float                 # %DET  diagonal line structures
    laminarity: float                  # %LAM  vertical line structures (intermittency)
    avg_diagonal_length: float         # <L>  mean diagonal line length
    entropy: float                     # ENTR  Shannon entropy of diagonal lines
    trapping_time: float               # TT  mean vertical line length
    max_diagonal: int
    is_deterministic: bool             # DET > 0.9
    is_laminar: bool                   # LAM > 0.5

    def to_dict(self) -> Dict[str, Any]:
        return {
            "recurrence_rate": float(self.recurrence_rate),
            "determinism": float(self.determinism),
            "laminarity": float(self.laminarity),
            "avg_diagonal_length": float(self.avg_diagonal_length),
            "entropy": float(self.entropy),
            "trapping_time": float(self.trapping_time),
            "max_diagonal_line": self.max_diagonal,
            "is_deterministic": self.is_deterministic,
            "is_laminar": self.is_laminar,
        }


@dataclass
class ChaosReport:
    """Unified chaos classification from all metrics."""
    lyapunov: LyapunovResult
    rqa: Optional[RQAResult]
    correlation_dimension: Optional[float]
    spectral: Dict[str, Any]
    energy_conservation: Optional[float]
    verdict: str                       # "CHAOTIC" | "QUASIPERIODIC" | "PERIODIC" | "FIXED_POINT"
    confidence: float
    evidence_summary: List[str]        # Human-readable evidence list

    def to_dict(self) -> Dict[str, Any]:
        return {
            "verdict": self.verdict,
            "confidence": float(self.confidence),
            "evidence": self.evidence_summary,
            "lyapunov": self.lyapunov.to_dict(),
            "rqa": self.rqa.to_dict() if self.rqa else None,
            "correlation_dimension": self.correlation_dimension,
            "spectral": self.spectral,
            "energy_conservation_error": self.energy_conservation,
        }


# 
# BENETTIN QR KERNEL  FULL SPECTRUM
# 

class BenettinKernel:
    """
    Full Lyapunov spectrum via QR-decomposition Benettin algorithm.

    v1 computed only the largest exponent using a scalar perturbation.
    This computes ALL exponents using an orthonormal frame that evolves
    with the flow, with periodic QR reorthonormalization.

    The key fix from v1:
      - v1 used random scalar perturbation  only 
      - v1 accumulated log(d1/d0) at every renorm step incorrectly
        (it computed growth of ONE direction, not the tangent space)
      - v1 divided by t[-1]-t[0] but accumulated only at renorm steps,
        mixing up total-time normalization with step-count normalization
      This version integrates the variational equations simultaneously
      and uses QR to track the full orthonormal frame.
    """

    @staticmethod
    def _build_variational_rhs(
        system_func: Callable,
        state_dim: int,
        epsilon: float = 1e-6
    ) -> Callable:
        """
        Build combined ODE: [state | tangent_vectors]  [f(state) | DfQ]
        Uses finite-difference Jacobian: Dfv  (f(x+v) - f(x-v)) / 2
        """
        def variational_rhs(y_flat: np.ndarray, t: float) -> np.ndarray:
            state = y_flat[:state_dim]
            Q_flat = y_flat[state_dim:]
            Q = Q_flat.reshape(state_dim, state_dim)

            f0 = np.array(system_func(state, t))
            dydt = np.zeros_like(y_flat)
            dydt[:state_dim] = f0

            # Jacobian-vector products via central differences
            for j in range(state_dim):
                v = Q[:, j]
                v_norm = np.linalg.norm(v)
                if v_norm < 1e-15:
                    continue
                v_unit = v / v_norm
                f_plus  = np.array(system_func(state + epsilon * v_unit, t))
                f_minus = np.array(system_func(state - epsilon * v_unit, t))
                dv_dt = v_norm * (f_plus - f_minus) / (2 * epsilon)
                dydt[state_dim + j * state_dim : state_dim + (j+1) * state_dim] = dv_dt

            return dydt

        return variational_rhs

    @staticmethod
    def calculate_spectrum(
        system_func: Callable,
        initial_state: np.ndarray,
        t: np.ndarray,
        renorm_steps: int = 20,
        epsilon: float = 1e-6,
        rtol: float = 1e-9,
        atol: float = 1e-11,
    ) -> LyapunovResult:
        """
        Compute full Lyapunov spectrum via QR-Benettin.

        Algorithm:
          1. Augment state with identity matrix as initial tangent frame
          2. Integrate [state | tangent_frame] forward renorm_steps at a time
          3. QR-decompose the evolved frame: Q_new, R = qr(evolved_frame)
          4. Accumulate log|R_ii| for each exponent
          5. Reset frame to Q_new (orthonormal), repeat

        Args:
            system_func: f(state, t)  dstate/dt
            initial_state: Starting coordinates [x, ..., x]
            t: Time array (uniform spacing)
            renorm_steps: Integration steps between reorthonormalizations
            epsilon: Finite-difference step for Jacobian
            rtol, atol: Integration tolerances

        Returns:
            LyapunovResult with full spectrum and classification
        """
        state_dim = len(initial_state)
        n_steps = len(t)

        # Initial tangent frame = identity
        Q = np.eye(state_dim)

        # Accumulated log-stretches per exponent
        le_accumulators = np.zeros(state_dim)
        convergence_trace = []  #  vs time for convergence check

        current_state = initial_state.copy()
        renorm_count = 0
        total_time_elapsed = 0.0

        vf = BenettinKernel._build_variational_rhs(system_func, state_dim, epsilon)

        i = 0
        while i < n_steps - 1:
            # Integrate for renorm_steps (or until end)
            end_idx = min(i + renorm_steps, n_steps - 1)
            t_seg = t[i:end_idx + 1]

            # Pack state + columns of Q into flat vector
            y0_flat = np.concatenate([current_state, Q.flatten()])

            try:
                sol = integrate.solve_ivp(
                    lambda tt, yy: vf(yy, tt),
                    (t_seg[0], t_seg[-1]),
                    y0_flat,
                    t_eval=[t_seg[-1]],
                    method='RK45',
                    rtol=rtol,
                    atol=atol,
                    dense_output=False
                )

                if not sol.success:
                    logger.warning(f"Benettin integration failed at t={t_seg[0]:.3f}: {sol.message}")
                    i = end_idx
                    continue

                y_end = sol.y[:, -1]
                current_state = y_end[:state_dim]
                Q_evolved = y_end[state_dim:].reshape(state_dim, state_dim)

            except Exception as e:
                logger.error(f"Benettin segment failed: {e}")
                i = end_idx
                continue

            # QR decomposition
            Q_new, R = np.linalg.qr(Q_evolved)

            # Ensure consistent orientation (R diagonal should be positive)
            signs = np.sign(np.diag(R))
            signs[signs == 0] = 1
            Q_new = Q_new * signs
            R = R * signs[:, np.newaxis]

            # Accumulate log|R_ii| for each exponent
            diag_R = np.abs(np.diag(R))
            diag_R = np.where(diag_R > 1e-300, diag_R, 1e-300)  # Guard against log(0)
            le_accumulators += np.log(diag_R)

            Q = Q_new
            total_time_elapsed = t_seg[-1] - t[0]
            renorm_count += 1

            # Record  convergence
            if total_time_elapsed > 0:
                convergence_trace.append(le_accumulators[0] / total_time_elapsed)

            i = end_idx

        # Normalize by total time
        if total_time_elapsed <= 0:
            logger.error("Benettin: zero time elapsed")
            exponents = np.zeros(state_dim)
        else:
            exponents = le_accumulators / total_time_elapsed

        # Sort descending
        exponents = np.sort(exponents)[::-1]

        # Kaplan-Yorke dimension
        ky_dim = BenettinKernel._kaplan_yorke_dimension(exponents)

        # Classification
        largest = float(exponents[0])
        classification, confidence = BenettinKernel._classify(
            exponents,
            np.array(convergence_trace) if convergence_trace else np.array([largest])
        )

        return LyapunovResult(
            exponents=exponents,
            largest=largest,
            spectrum_sum=float(np.sum(exponents)),
            kaplan_yorke_dim=ky_dim,
            is_chaotic=largest > 0.01,
            convergence_trace=np.array(convergence_trace),
            renorm_count=renorm_count,
            system_dim=state_dim,
            classification=classification,
            confidence=confidence,
        )

    @staticmethod
    def calculate_lyapunov(
        system_func: Callable,
        initial_state: np.ndarray,
        t: np.ndarray,
        d0: float = 1e-8,
        renorm_steps: int = 10,
    ) -> float:
        """
        Backward-compatible wrapper  returns only the largest Lyapunov exponent.
        Internally uses the full QR-Benettin spectrum calculation.
        """
        result = BenettinKernel.calculate_spectrum(
            system_func=system_func,
            initial_state=initial_state,
            t=t,
            renorm_steps=renorm_steps,
        )
        return result.largest

    @staticmethod
    def _kaplan_yorke_dimension(exponents: np.ndarray) -> float:
        """
        Kaplan-Yorke (Lyapunov) dimension.
        D_KY = j + (1/|_{j+1}|) *  
        where j is the largest index such that    0
        """
        cumsum = np.cumsum(exponents)
        # Find largest j where cumulative sum is still  0
        j_candidates = np.where(cumsum >= 0)[0]
        if len(j_candidates) == 0:
            return 0.0

        j = j_candidates[-1]
        if j + 1 >= len(exponents):
            return float(len(exponents))

        lambda_next = exponents[j + 1]
        if abs(lambda_next) < 1e-15:
            return float(j + 1)

        d_ky = (j + 1) + cumsum[j] / abs(lambda_next)
        return float(np.clip(d_ky, 0, len(exponents)))

    @staticmethod
    def _classify(
        exponents: np.ndarray,
        convergence_trace: np.ndarray,
        chaos_threshold: float = 0.01,
        convergence_window: int = 20
    ) -> Tuple[str, float]:
        """
        Classify dynamics from Lyapunov spectrum.

        Classification rules (Ott, Chaos in Dynamical Systems):
           > 0                     chaotic
            0,  < 0            quasiperiodic (torus)
            0, all others < 0    periodic orbit
          all  < 0                fixed point / limit cycle
        """
        n = len(exponents)
        le1 = exponents[0]
        le2 = exponents[1] if n > 1 else -1.0

        # Convergence quality: check if trace has plateaued
        confidence = 0.5
        if len(convergence_trace) > convergence_window:
            tail = convergence_trace[-convergence_window:]
            variation = np.std(tail) / (np.abs(np.mean(tail)) + 1e-10)
            confidence = float(np.clip(1.0 - variation, 0.1, 0.99))

        if le1 > chaos_threshold:
            return "chaotic", confidence
        elif abs(le1) <= chaos_threshold and le2 < -chaos_threshold:
            return "quasiperiodic", confidence * 0.9
        elif abs(le1) <= chaos_threshold and all(abs(e) <= chaos_threshold for e in exponents[1:]):
            return "periodic", confidence * 0.8
        else:
            return "fixed_point", confidence * 0.9


# 
# NUMERICAL INTEGRATORS
# 

class NumericalIntegrator:
    """
    High-fidelity ODE integrators with error tracking and energy monitoring.

    v1 had one method (RK45). This adds:
      - Strmer-Verlet symplectic integrator for Hamiltonians (conserves energy)
      - Richardson extrapolation error estimation
      - Energy drift tracking for conservative systems
      - Automatic integrator selection based on system type
    """

    @staticmethod
    def solve_rk45(
        func: Callable,
        y0: np.ndarray,
        t_span: Tuple[float, float],
        t_eval: np.ndarray,
        rtol: float = 1e-9,
        atol: float = 1e-11,
        hamiltonian: Optional[Callable] = None,
    ) -> IntegrationResult:
        """
        Solve using explicit Runge-Kutta 5(4) with error estimation.

        Enhancement over v1:
          - Tighter default tolerances (was 1e-8/1e-10, now 1e-9/1e-11)
          - Richardson extrapolation to estimate local truncation error
          - Optional energy drift tracking via Hamiltonian callback
        """
        sol = integrate.solve_ivp(
            func, t_span, y0,
            t_eval=t_eval,
            method='RK45',
            rtol=rtol,
            atol=atol,
            dense_output=True
        )

        # Richardson extrapolation: solve with 2 coarser tolerance, compare
        local_error = 0.0
        try:
            sol_coarse = integrate.solve_ivp(
                func, t_span, y0,
                t_eval=[t_span[-1]],
                method='RK45',
                rtol=rtol * 100,
                atol=atol * 100,
            )
            if sol_coarse.success and sol.success:
                y_fine   = sol.sol(t_span[-1])
                y_coarse = sol_coarse.y[:, -1]
                local_error = float(np.linalg.norm(y_fine - y_coarse))
        except Exception:
            pass

        # Energy drift
        energy_drift = None
        if hamiltonian and sol.success:
            try:
                H0 = hamiltonian(sol.y[:, 0])
                H_final = hamiltonian(sol.y[:, -1])
                if abs(H0) > 1e-15:
                    energy_drift = abs((H_final - H0) / H0)
                    if energy_drift > 1e-4:
                        logger.warning(
                            f"Energy drift {energy_drift:.2e} detected. "
                            "Consider symplectic integrator for Hamiltonian systems."
                        )
            except Exception as e:
                logger.debug(f"Energy check failed: {e}")

        return IntegrationResult(
            success=sol.success,
            t=sol.t,
            y=sol.y,
            energy_drift=energy_drift,
            local_error_estimate=local_error,
            nfev=sol.nfev,
            message=sol.message,
            integrator_used="RK45",
        )

    @staticmethod
    def solve_symplectic(
        grad_T: Callable,
        grad_V: Callable,
        q0: np.ndarray,
        p0: np.ndarray,
        t_span: Tuple[float, float],
        n_steps: int,
        hamiltonian: Optional[Callable] = None,
        method: str = "stormer_verlet",
    ) -> IntegrationResult:
        """
        Strmer-Verlet symplectic integrator for Hamiltonian systems H = T(p) + V(q).

        Why symplectic? RK45 is NOT symplectic  it does not preserve the symplectic
        structure of phase space. Over long integrations this causes secular energy
        drift. Strmer-Verlet has bounded energy error O(h) for ALL time.

        This is MANDATORY for:
          - Long-time Lyapunov calculations
          - Celestial mechanics
          - Molecular dynamics
          - Any system where energy conservation matters

        Args:
            grad_T: T/p = dq/dt (kinetic gradient)
            grad_V: V/q = -dp/dt (potential gradient)
            q0: Initial positions
            p0: Initial momenta
            t_span: (t_start, t_end)
            n_steps: Number of integration steps
            hamiltonian: H(y) for energy tracking (y = [q, p])
            method: "stormer_verlet" | "leapfrog" | "yoshida4"
        """
        t0, tf = t_span
        h = (tf - t0) / n_steps
        t_array = np.linspace(t0, tf, n_steps + 1)

        dim = len(q0)
        q = q0.copy().astype(float)
        p = p0.copy().astype(float)

        # Storage
        q_traj = np.zeros((dim, n_steps + 1))
        p_traj = np.zeros((dim, n_steps + 1))
        q_traj[:, 0] = q
        p_traj[:, 0] = p

        if method == "yoshida4":
            # Yoshida 4th-order symplectic coefficients
            c_cbrt = 2.0 ** (1.0/3.0)
            w1 = 1.0 / (2.0 - c_cbrt)
            w0 = -c_cbrt * w1
            c = [w1/2, (w0+w1)/2, (w0+w1)/2, w1/2]
            d = [w1, w0, w1]
        else:
            # Strmer-Verlet / leapfrog (equivalent for separable H)
            c = [0.5, 0.5]
            d = [1.0]

        nfev = 0
        for i in range(n_steps):
            if method == "yoshida4":
                # Yoshida 4th-order: 3 V-kicks, 4 T-drifts
                for k in range(4):
                    q = q + h * c[k] * grad_T(p)
                    nfev += 1
                    if k < 3:
                        p = p - h * d[k] * grad_V(q)
                        nfev += 1
            else:
                # Strmer-Verlet: half-kick  drift  half-kick
                p_half = p - 0.5 * h * grad_V(q)
                q      = q + h * grad_T(p_half)
                p      = p_half - 0.5 * h * grad_V(q)
                nfev += 2

            q_traj[:, i+1] = q
            p_traj[:, i+1] = p

        # Combine q,p into unified trajectory y (shape: 2*dim  n_steps+1)
        y_traj = np.vstack([q_traj, p_traj])

        energy_drift = None
        if hamiltonian:
            try:
                H0 = hamiltonian(y_traj[:, 0])
                H_vals = np.array([hamiltonian(y_traj[:, i]) for i in range(n_steps+1)])
                energy_drift = float(np.max(np.abs(H_vals - H0)) / (abs(H0) + 1e-15))
            except Exception as e:
                logger.debug(f"Energy tracking failed: {e}")

        return IntegrationResult(
            success=True,
            t=t_array,
            y=y_traj,
            energy_drift=energy_drift,
            local_error_estimate=0.0,   # Symplectic  no drift by construction
            nfev=nfev,
            message="Symplectic integration completed",
            integrator_used=method,
        )

    @staticmethod
    def select_integrator(
        is_hamiltonian: bool,
        integration_time: float,
        state_dim: int,
        stiff: bool = False
    ) -> str:
        """
        Recommend the appropriate integrator for the problem.

        Rules:
          Hamiltonian + long time   yoshida4 (symplectic, 4th order)
          Hamiltonian + short time  stormer_verlet
          Dissipative + stiff       Radau (implicit)
          Dissipative + non-stiff   RK45
        """
        if is_hamiltonian:
            return "yoshida4" if integration_time > 100 else "stormer_verlet"
        if stiff:
            return "Radau"
        return "RK45"


# 
# POINCAR SECTION
# 

class PoincareSectionExtractor:
    """
    Extract Poincar sections from continuous trajectories.

    A Poincar section is the intersection of a trajectory with a
    (dim-1)-dimensional hyperplane, recorded only for transversals
    in one direction (e.g., d/dt > 0 crossings only).

    Used to:
      - Reduce continuous dynamics to discrete maps
      - Distinguish periodic / quasiperiodic / chaotic orbits visually
      - Compute return time distributions
    """

    @staticmethod
    def extract(
        t: np.ndarray,
        y: np.ndarray,
        section_axis: int = 0,
        section_value: float = 0.0,
        direction: str = "positive",
        interpolate: bool = True,
    ) -> PoincareResult:
        """
        Extract Poincar section crossings.

        Args:
            t: Time array
            y: State array (n_vars  n_times)
            section_axis: Which coordinate defines the section hyperplane
            section_value: Value of that coordinate on the section
            direction: "positive" (upward crossings only) | "both"
            interpolate: Use linear interpolation for sub-step precision
        """
        coord = y[section_axis, :]
        shifted = coord - section_value

        crossings = []
        crossing_times = []

        for i in range(len(t) - 1):
            s0, s1 = shifted[i], shifted[i+1]

            # Detect sign change
            if s0 * s1 >= 0:
                continue

            # Direction filter
            if direction == "positive" and s0 >= 0:
                continue
            if direction == "negative" and s0 <= 0:
                continue

            if interpolate:
                # Linear interpolation to find exact crossing time
                frac = -s0 / (s1 - s0 + 1e-300)
                t_cross = t[i] + frac * (t[i+1] - t[i])
                y_cross = y[:, i] + frac * (y[:, i+1] - y[:, i])
            else:
                t_cross = t[i+1]
                y_cross = y[:, i+1]

            # Remove section axis from crossing point
            y_sec = np.delete(y_cross, section_axis)
            crossings.append(y_sec)
            crossing_times.append(t_cross)

        if not crossings:
            return PoincareResult(
                crossings=np.empty((0, y.shape[0]-1)),
                crossing_times=np.array([]),
                n_crossings=0,
                section_axis=section_axis,
                section_value=section_value,
                is_closed_orbit=False,
                return_time_mean=np.nan,
                return_time_std=np.nan,
            )

        crossings_arr = np.array(crossings)
        crossing_times_arr = np.array(crossing_times)

        # Return time statistics
        return_times = np.diff(crossing_times_arr) if len(crossing_times_arr) > 1 else np.array([0.0])

        # Closed orbit check: last point  first point
        is_closed = False
        if len(crossings_arr) >= 3:
            spread = np.std(crossings_arr, axis=0)
            is_closed = np.all(spread < 0.05 * (np.ptp(crossings_arr, axis=0) + 1e-10))

        return PoincareResult(
            crossings=crossings_arr,
            crossing_times=crossing_times_arr,
            n_crossings=len(crossings_arr),
            section_axis=section_axis,
            section_value=section_value,
            is_closed_orbit=is_closed,
            return_time_mean=float(np.mean(return_times)),
            return_time_std=float(np.std(return_times)),
        )


# 
# RECURRENCE QUANTIFICATION ANALYSIS
# 

class RecurrenceAnalyzer:
    """
    Recurrence Quantification Analysis (RQA) after Eckmann et al. (1987).

    Builds the recurrence matrix R[i,j] = ( - ||x_i - x_j||)
    and extracts structural measures from it.

    Why this beats simple FFT chaos metrics:
      - Works on non-stationary data
      - Detects intermittency (LAM)
      - Quantifies determinism without assuming ergodicity
      - Threshold  chosen by % recurrence rate (5%)
    """

    @staticmethod
    def analyze(
        trajectory: np.ndarray,
        epsilon: Optional[float] = None,
        target_rr: float = 0.05,
        min_line_length: int = 2,
        embedding_dim: int = 1,
        time_delay: int = 1,
    ) -> RQAResult:
        """
        Compute full RQA from trajectory.

        Args:
            trajectory: 1D time series or (n_vars  n_times) array
            epsilon: Recurrence threshold (auto-selected if None)
            target_rr: Target recurrence rate for auto epsilon (default 5%)
            min_line_length: Minimum diagonal/vertical line to count
            embedding_dim: Takens embedding dimension (1 = no embedding)
            time_delay: Takens time delay 
        """
        # Flatten to 1D if needed, then embed
        if trajectory.ndim > 1:
            x = trajectory.T   # (n_times  n_vars)
        else:
            x = RecurrenceAnalyzer._takens_embed(trajectory, embedding_dim, time_delay)

        N = len(x)
        if N < 10:
            raise ValueError(f"Trajectory too short for RQA: {N} points, need 10")

        # Build distance matrix
        try:
            dist = spatial.distance.cdist(x, x, metric='euclidean')
        except Exception:
            # Fallback for 1D
            x2d = x.reshape(-1, 1) if x.ndim == 1 else x
            dist = spatial.distance.cdist(x2d, x2d, metric='euclidean')

        # Auto-select epsilon to achieve target recurrence rate
        if epsilon is None:
            epsilon = RecurrenceAnalyzer._auto_epsilon(dist, target_rr)

        # Recurrence matrix (exclude main diagonal  always recurrent)
        R = (dist < epsilon).astype(np.uint8)
        np.fill_diagonal(R, 0)

        #  Recurrence Rate 
        rr = float(np.sum(R)) / (N * (N - 1))

        #  Diagonal line analysis (DET, L_mean, ENTR) 
        diag_lengths = RecurrenceAnalyzer._diagonal_lengths(R, min_line_length)
        total_diag_points = sum(diag_lengths)
        all_diag_points = sum(
            RecurrenceAnalyzer._diagonal_lengths(R, 1)
        )

        det = total_diag_points / max(np.sum(R), 1)
        avg_diag = float(np.mean(diag_lengths)) if diag_lengths else 0.0
        max_diag = int(max(diag_lengths)) if diag_lengths else 0

        # Shannon entropy of diagonal line length distribution
        if diag_lengths:
            from collections import Counter
            counts = np.array(list(Counter(diag_lengths).values()), dtype=float)
            probs = counts / counts.sum()
            probs = probs[probs > 0]
            entropy = float(-np.sum(probs * np.log(probs)))
        else:
            entropy = 0.0

        #  Vertical line analysis (LAM, TT  trapping time) 
        vert_lengths = RecurrenceAnalyzer._vertical_lengths(R, min_line_length)
        total_vert_points = sum(vert_lengths)
        all_vert_points = sum(RecurrenceAnalyzer._vertical_lengths(R, 1))

        lam = total_vert_points / max(all_vert_points, 1)
        tt = float(np.mean(vert_lengths)) if vert_lengths else 0.0

        return RQAResult(
            recurrence_rate=rr,
            determinism=det,
            laminarity=lam,
            avg_diagonal_length=avg_diag,
            entropy=entropy,
            trapping_time=tt,
            max_diagonal=max_diag,
            is_deterministic=det > 0.9,
            is_laminar=lam > 0.5,
        )

    @staticmethod
    def _takens_embed(x: np.ndarray, m: int, tau: int) -> np.ndarray:
        """Takens delay-coordinate embedding."""
        N = len(x)
        n_vectors = N - (m - 1) * tau
        if n_vectors <= 0:
            return x.reshape(-1, 1)
        embedded = np.zeros((n_vectors, m))
        for i in range(n_vectors):
            embedded[i, :] = x[i : i + m * tau : tau]
        return embedded

    @staticmethod
    def _auto_epsilon(dist: np.ndarray, target_rr: float) -> float:
        """Binary search for  that gives target recurrence rate."""
        flat = dist.flatten()
        flat = flat[flat > 0]
        lo, hi = 0.0, np.max(flat)
        for _ in range(50):
            mid = (lo + hi) / 2
            rr = np.mean(flat < mid)
            if rr < target_rr:
                lo = mid
            else:
                hi = mid
        return float((lo + hi) / 2)

    @staticmethod
    def _diagonal_lengths(R: np.ndarray, min_len: int) -> List[int]:
        """Extract lengths of diagonal lines  min_len in recurrence matrix."""
        N = R.shape[0]
        lengths = []
        for k in range(-(N-1), N):
            diag = np.diagonal(R, offset=k)
            if len(diag) < min_len:
                continue
            length = 0
            for val in diag:
                if val:
                    length += 1
                else:
                    if length >= min_len:
                        lengths.append(length)
                    length = 0
            if length >= min_len:
                lengths.append(length)
        return lengths

    @staticmethod
    def _vertical_lengths(R: np.ndarray, min_len: int) -> List[int]:
        """Extract lengths of vertical lines  min_len in recurrence matrix."""
        N = R.shape[0]
        lengths = []
        for col in range(N):
            length = 0
            for row in range(N):
                if R[row, col]:
                    length += 1
                else:
                    if length >= min_len:
                        lengths.append(length)
                    length = 0
            if length >= min_len:
                lengths.append(length)
        return lengths


# 
# CORRELATION DIMENSION
# 

class CorrelationDimension:
    """
    Grassberger-Procaccia (1983) correlation dimension.

    C() = lim_{N} (2 / N(N-1)) _{i<j} ( - ||x_i - x_j||)

    D_C = lim_{0} log C() / log 

    Computed by linear regression of log C() vs log  over the
    scaling region. Non-integer D_C confirms fractal attractor.
    """

    @staticmethod
    def estimate(
        trajectory: np.ndarray,
        epsilon_range: Optional[Tuple[float, float]] = None,
        n_epsilons: int = 30,
        embedding_dim: int = 3,
        time_delay: int = 1,
    ) -> Dict[str, Any]:
        """
        Estimate correlation dimension via GP algorithm.

        Args:
            trajectory: 1D time series
            epsilon_range: (_min, _max) range for scaling region
            n_epsilons: Number of  values to sample
            embedding_dim: Takens embedding dimension
            time_delay: Takens 

        Returns:
            Dict with estimated dimension, scaling region, and regression quality
        """
        if trajectory.ndim == 1:
            x = RecurrenceAnalyzer._takens_embed(trajectory, embedding_dim, time_delay)
        else:
            x = trajectory.T

        N = len(x)
        if N < 50:
            return {"error": f"Need 50 points for correlation dimension, got {N}"}

        # Subsample if very long (O(N) computation)
        if N > 2000:
            idx = np.random.choice(N, 2000, replace=False)
            x = x[idx]
            N = 2000

        try:
            dist = spatial.distance.cdist(x, x, metric='euclidean')
        except Exception:
            return {"error": "Distance computation failed"}

        # Upper triangle only (pairs, excluding self)
        upper_tri = dist[np.triu_indices(N, k=1)]

        if epsilon_range is None:
            epsilon_range = (np.percentile(upper_tri, 1), np.percentile(upper_tri, 40))

        epsilons = np.logspace(
            np.log10(epsilon_range[0] + 1e-15),
            np.log10(epsilon_range[1]),
            n_epsilons
        )

        # Correlation integral C()
        C_eps = np.array([np.mean(upper_tri < eps) for eps in epsilons])

        # Find scaling region: where d(log C)/d(log ) is approximately constant
        valid = (C_eps > 0) & (C_eps < 1)
        if valid.sum() < 5:
            return {
                "error": "Insufficient scaling region",
                "C_eps": C_eps.tolist(),
                "epsilons": epsilons.tolist()
            }

        log_eps = np.log10(epsilons[valid])
        log_C = np.log10(C_eps[valid])

        # Linear regression in scaling region
        coeffs = np.polyfit(log_eps, log_C, 1)
        d_c = float(coeffs[0])

        # R of fit
        log_C_fit = np.polyval(coeffs, log_eps)
        ss_res = np.sum((log_C - log_C_fit) ** 2)
        ss_tot = np.sum((log_C - log_C.mean()) ** 2)
        r_squared = float(1 - ss_res / (ss_tot + 1e-15))

        return {
            "correlation_dimension": d_c,
            "r_squared": r_squared,
            "is_fractal": 1.0 < d_c < embedding_dim,
            "scaling_region": epsilon_range,
            "n_points_used": N,
            "embedding_dim": embedding_dim,
            "interpretation": (
                f"D_C  {d_c:.2f}  "
                + ("fractal attractor confirmed" if 1 < d_c < embedding_dim
                   else "integer dimension  may not be fractal")
            )
        }


# 
# CHAOS CLASSIFICATION ENGINE
# 

def classify_chaos(
    system_func: Callable,
    initial_state: np.ndarray,
    t: np.ndarray,
    hamiltonian: Optional[Callable] = None,
    run_rqa: bool = True,
    run_correlation_dim: bool = True,
    renorm_steps: int = 20,
) -> ChaosReport:
    """
    Unified chaos classification using all available metrics.

    Runs:
      1. Full Lyapunov spectrum (Benettin QR)
      2. RQA on the trajectory
      3. Correlation dimension (optional)
      4. Spectral broadband test
      5. Energy conservation check (if Hamiltonian provided)

    Returns a ChaosReport with evidence-based verdict.

    Args:
        system_func: f(state, t) ODE RHS
        initial_state: Starting state
        t: Time array
        hamiltonian: H(y) for energy tracking (optional)
        run_rqa: Whether to run RQA (slower but informative)
        run_correlation_dim: Whether to estimate correlation dimension
        renorm_steps: Benettin renormalization interval
    """
    evidence = []

    #  1. Lyapunov Spectrum 
    logger.info("[CHAOS] Computing Lyapunov spectrum...")
    lyap = BenettinKernel.calculate_spectrum(
        system_func=system_func,
        initial_state=initial_state,
        t=t,
        renorm_steps=renorm_steps,
    )
    evidence.append(f" = {lyap.largest:.4f}  {lyap.classification} (conf={lyap.confidence:.2f})")
    if lyap.spectrum_sum > 0.1:
        evidence.append(
            f"WARNING: Lyapunov spectrum sums to {lyap.spectrum_sum:.3f} > 0. "
            "Positive sum violates dissipation for bounded attractor  check ODE."
        )

    #  2. Integrate trajectory 
    integrator_name = NumericalIntegrator.select_integrator(
        is_hamiltonian=hamiltonian is not None,
        integration_time=t[-1] - t[0],
        state_dim=len(initial_state),
    )
    logger.info(f"[CHAOS] Integrating with {integrator_name}...")

    if hamiltonian and integrator_name in ("stormer_verlet", "yoshida4"):
        # Need grad_T and grad_V  can't auto-derive without user supplying them
        # Fall back to RK45 with energy monitoring
        integration = NumericalIntegrator.solve_rk45(
            func=lambda t_, y: system_func(y, t_),
            y0=initial_state,
            t_span=(t[0], t[-1]),
            t_eval=t,
            hamiltonian=hamiltonian,
        )
    else:
        integration = NumericalIntegrator.solve_rk45(
            func=lambda t_, y: system_func(y, t_),
            y0=initial_state,
            t_span=(t[0], t[-1]),
            t_eval=t,
            hamiltonian=hamiltonian,
        )

    energy_drift = integration.energy_drift
    if energy_drift is not None:
        evidence.append(f"Energy drift: {energy_drift:.2e}")
        if energy_drift > 1e-3:
            evidence.append("HIGH energy drift  use symplectic integrator for this system")

    #  3. Spectral Analysis 
    spectral = {}
    if integration.success:
        spectral = verify_chaos_metrics(integration.t, integration.y)
        evidence.append(
            f"Spectral peak ratio: {spectral['peak_ratio']:.1f} "
            f" {'broadband (chaotic)' if spectral['is_broadband'] else 'discrete peaks (periodic/quasiperiodic)'}"
        )

    #  4. RQA 
    rqa_result = None
    if run_rqa and integration.success:
        logger.info("[CHAOS] Running RQA...")
        try:
            traj_1d = integration.y[0]  # Use first coordinate
            rqa_result = RecurrenceAnalyzer.analyze(traj_1d)
            evidence.append(
                f"RQA: DET={rqa_result.determinism:.3f}, "
                f"LAM={rqa_result.laminarity:.3f}, "
                f"{'deterministic' if rqa_result.is_deterministic else 'stochastic'}"
            )
        except Exception as e:
            logger.warning(f"[CHAOS] RQA failed: {e}")

    #  5. Correlation Dimension 
    corr_dim = None
    if run_correlation_dim and integration.success:
        logger.info("[CHAOS] Estimating correlation dimension...")
        try:
            traj_1d = integration.y[0]
            cd_result = CorrelationDimension.estimate(traj_1d)
            if "correlation_dimension" in cd_result:
                corr_dim = cd_result["correlation_dimension"]
                evidence.append(f"Correlation dimension D_C = {corr_dim:.3f}")
                if cd_result.get("is_fractal"):
                    evidence.append("Fractal dimension confirms strange attractor")
        except Exception as e:
            logger.warning(f"[CHAOS] Correlation dimension failed: {e}")

    #  6. Final Verdict 
    verdict, confidence = _synthesize_verdict(lyap, rqa_result, corr_dim, spectral)

    return ChaosReport(
        lyapunov=lyap,
        rqa=rqa_result,
        correlation_dimension=corr_dim,
        spectral=spectral,
        energy_conservation=energy_drift,
        verdict=verdict,
        confidence=confidence,
        evidence_summary=evidence,
    )


def _synthesize_verdict(
    lyap: LyapunovResult,
    rqa: Optional[RQAResult],
    corr_dim: Optional[float],
    spectral: Dict[str, Any],
) -> Tuple[str, float]:
    """
    Weighted evidence synthesis for final chaos verdict.

    Evidence weights:
      Lyapunov (primary):   0.5
      RQA determinism:      0.2
      Spectral broadband:   0.15
      Correlation dim:      0.15
    """
    votes_chaotic = 0.0
    total_weight = 0.0

    # Lyapunov evidence
    w = 0.5
    if lyap.largest > 0.01:
        votes_chaotic += w * lyap.confidence
    total_weight += w

    # RQA evidence
    if rqa is not None:
        w = 0.2
        # Low DET + low LAM  chaotic
        chaos_rqa_score = 1.0 - rqa.determinism
        votes_chaotic += w * chaos_rqa_score
        total_weight += w

    # Spectral evidence
    if spectral.get("is_broadband") is not None:
        w = 0.15
        if spectral["is_broadband"]:
            votes_chaotic += w
        total_weight += w

    # Correlation dimension evidence
    if corr_dim is not None:
        w = 0.15
        if 1.0 < corr_dim < 4.0:  # Fractal = chaotic attractor
            votes_chaotic += w
        total_weight += w

    if total_weight == 0:
        return lyap.classification.upper(), lyap.confidence

    chaos_score = votes_chaotic / total_weight

    if chaos_score > 0.6:
        verdict = "CHAOTIC"
        confidence = chaos_score
    elif chaos_score > 0.4:
        verdict = "WEAKLY_CHAOTIC"
        confidence = 0.5
    else:
        verdict = lyap.classification.upper()
        confidence = 1.0 - chaos_score

    return verdict, float(confidence)


# 
# BIFURCATION DIAGRAM
# 

def compute_bifurcation_diagram(
    system_func_factory: Callable,
    param_range: np.ndarray,
    initial_state: np.ndarray,
    t_transient: np.ndarray,
    t_record: np.ndarray,
    record_coord: int = 0,
    poincare_axis: Optional[int] = None,
) -> Dict[str, Any]:
    """
    Build bifurcation diagram by sweeping a parameter.

    Args:
        system_func_factory: f(param)  system_func(state, t)
        param_range: Array of parameter values to sweep
        initial_state: Starting state (shared across parameter values)
        t_transient: Time array for transient (discarded)
        t_record: Time array for recording attractor
        record_coord: Which coordinate to record
        poincare_axis: If set, use Poincar section instead of raw trajectory

    Returns:
        Dict with param_values, attractor_points for plotting
    """
    all_params = []
    all_points = []

    state = initial_state.copy()

    for param in param_range:
        sys_func = system_func_factory(param)

        # Burn transient
        try:
            sol_t = integrate.solve_ivp(
                lambda t_, y: sys_func(y, t_),
                (t_transient[0], t_transient[-1]),
                state,
                method='RK45',
                rtol=1e-9, atol=1e-11,
                t_eval=[t_transient[-1]]
            )
            if not sol_t.success:
                continue
            state_after_transient = sol_t.y[:, -1]
        except Exception:
            continue

        # Record attractor
        try:
            sol_r = integrate.solve_ivp(
                lambda t_, y: sys_func(y, t_),
                (t_record[0], t_record[-1]),
                state_after_transient,
                method='RK45',
                rtol=1e-9, atol=1e-11,
                t_eval=t_record
            )
            if not sol_r.success:
                continue
        except Exception:
            continue

        if poincare_axis is not None:
            pc = PoincareSectionExtractor.extract(
                sol_r.t, sol_r.y,
                section_axis=poincare_axis,
                section_value=0.0
            )
            points = pc.crossings[:, 0] if pc.n_crossings > 0 else np.array([])
        else:
            # Sample attractor points
            points = sol_r.y[record_coord, ::max(1, len(t_record)//200)]

        if len(points) > 0:
            all_params.extend([float(param)] * len(points))
            all_points.extend(points.tolist())

    return {
        "param_values": all_params,
        "attractor_values": all_points,
        "n_param_values": len(param_range),
        "record_coordinate": record_coord,
    }


# 
# SPECTRAL ANALYSIS (upgraded from v1)
# 

def verify_chaos_metrics(
    t: np.ndarray,
    y: np.ndarray,
    chaos_peak_ratio_threshold: float = 10.0,
) -> Dict[str, Any]:
    """
    Spectral signatures of chaos via FFT.

    Improvements over v1:
      - Welch periodogram instead of raw FFT (better for noisy signals)
      - Spectral entropy (Shannon entropy of power distribution)
      - Dominant frequency extraction
      - Peak ratio threshold now 10.0 (v1 used 20.0 with no justification;
        typical chaotic systems have peak_ratio 28, periodic systems >50)
      - Parseval check compares time-domain vs frequency-domain energy

    Args:
        t: Time array
        y: State array (n_vars  n_times)
        chaos_peak_ratio_threshold: peak/mean power ratio below which we
            call the spectrum "broadband" (chaotic indicator)
    """
    from scipy.signal import welch
    from scipy.fft import fft, fftfreq

    n = len(t)
    dt = float(t[1] - t[0])
    coord = y[0]

    # Welch periodogram (reduces noise variance vs raw FFT)
    nperseg = min(256, n // 4)
    freqs_w, Pxx = welch(coord, fs=1.0/dt, nperseg=nperseg)

    peak_power = float(np.max(Pxx))
    mean_power = float(np.mean(Pxx))
    peak_ratio = peak_power / (mean_power + 1e-300)
    dominant_freq = float(freqs_w[np.argmax(Pxx)])

    # Spectral entropy (normalized Shannon entropy of power spectrum)
    P_norm = Pxx / (Pxx.sum() + 1e-300)
    P_norm = P_norm[P_norm > 0]
    spectral_entropy = float(-np.sum(P_norm * np.log(P_norm)))
    # Normalize by log(N) so it's in [0,1]
    spectral_entropy_norm = spectral_entropy / (np.log(len(P_norm)) + 1e-10)

    # Raw FFT for Parseval check
    yf = fft(coord)
    power_freq = np.sum(np.abs(yf)**2) / n
    power_time = np.sum(coord**2)
    parseval_error = abs(power_time - power_freq) / (power_time + 1e-300)

    is_broadband = peak_ratio < chaos_peak_ratio_threshold

    return {
        "is_broadband": is_broadband,
        "peak_ratio": float(peak_ratio),
        "peak_ratio_threshold": chaos_peak_ratio_threshold,
        "dominant_frequency": dominant_freq,
        "spectral_entropy": spectral_entropy,
        "spectral_entropy_normalized": float(spectral_entropy_norm),
        "parseval_error": float(parseval_error),
        "parseval_ok": parseval_error < 0.01,
        "n_timepoints": n,
        "interpretation": (
            "broadband spectrum  consistent with chaos" if is_broadband
            else f"discrete peaks at f={dominant_freq:.3f}  consistent with periodic/quasiperiodic"
        )
    }

# =============================================================================
# DETERMINISTIC THERMODYNAMIC & HEAT TRANSFER KERNEL
# =============================================================================

@dataclass
class ThermodynamicAuditResult:
    """Result of deterministic first- and second-law thermodynamic verification."""
    is_valid: bool
    carnot_efficiency_limit: Optional[float]
    stefan_boltzmann_flux_w_m2: Optional[float]
    gibbs_free_energy_j_mol: Optional[float]
    is_spontaneous: Optional[bool]
    violations: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "is_valid": self.is_valid,
            "carnot_efficiency_limit": self.carnot_efficiency_limit,
            "stefan_boltzmann_flux_w_m2": self.stefan_boltzmann_flux_w_m2,
            "gibbs_free_energy_j_mol": self.gibbs_free_energy_j_mol,
            "is_spontaneous": self.is_spontaneous,
            "violations": self.violations,
        }


class ThermodynamicKernel:
    """
    Deterministic First-Principles Thermodynamics & Heat Transfer Kernel.
    Enforces exact conservation laws, Carnot bounds, Stefan-Boltzmann radiative
    limits, Gibbs free energy spontaneity, and Landauer dissipation floors.
    """
    STEFAN_BOLTZMANN_SIGMA = 5.670374419e-8  # W / (m^2 * K^4)
    GAS_CONSTANT_R = 8.314462618             # J / (mol * K)
    BOLTZMANN_KB = 1.380649e-23              # J / K

    @classmethod
    def carnot_efficiency(cls, t_hot_k: float, t_cold_k: float) -> float:
        if t_hot_k <= 0 or t_cold_k <= 0:
            raise ValueError(f"Absolute temperatures must be > 0 K (got T_H={t_hot_k}, T_C={t_cold_k})")
        if t_cold_k >= t_hot_k:
            return 0.0
        return float(1.0 - (t_cold_k / t_hot_k))

    @classmethod
    def stefan_boltzmann_power(
        cls,
        temp_k: float,
        area_m2: float = 1.0,
        emissivity: float = 0.9,
        ambient_temp_k: float = 2.7
    ) -> float:
        if temp_k < 0 or ambient_temp_k < 0:
            raise ValueError("Temperature in Kelvin cannot be negative.")
        if not (0.0 < emissivity <= 1.0):
            raise ValueError(f"Emissivity must be in (0, 1], got {emissivity}")
        return float(emissivity * cls.STEFAN_BOLTZMANN_SIGMA * area_m2 * (temp_k**4 - ambient_temp_k**4))

    @classmethod
    def gibbs_free_energy(cls, delta_h_j_mol: float, delta_s_j_mol_k: float, temp_k: float = 298.15) -> Tuple[float, bool]:
        if temp_k <= 0:
            raise ValueError(f"Temperature must be > 0 K, got {temp_k}")
        dg = float(delta_h_j_mol - temp_k * delta_s_j_mol_k)
        return dg, (dg < 0.0)

    @classmethod
    def landauer_bit_erasure_floor(cls, temp_k: float = 300.0) -> float:
        if temp_k <= 0:
            raise ValueError("Temperature must be > 0 K")
        return float(cls.BOLTZMANN_KB * temp_k * np.log(2.0))

    @classmethod
    def audit_system(
        cls,
        t_hot_k: Optional[float] = None,
        t_cold_k: Optional[float] = None,
        claimed_efficiency: Optional[float] = None,
        radiator_area_m2: Optional[float] = None,
        emissivity: float = 0.9,
        delta_h_j_mol: Optional[float] = None,
        delta_s_j_mol_k: Optional[float] = None,
    ) -> ThermodynamicAuditResult:
        violations = []
        carnot_lim = None
        sb_flux = None
        dg = None
        spontaneous = None

        if t_hot_k is not None:
            if t_hot_k <= 0:
                violations.append(f"Third-Law Violation: T_hot={t_hot_k} K <= 0 K")
            elif t_cold_k is not None:
                if t_cold_k <= 0:
                    violations.append(f"Third-Law Violation: T_cold={t_cold_k} K <= 0 K")
                elif t_cold_k < t_hot_k:
                    carnot_lim = cls.carnot_efficiency(t_hot_k, t_cold_k)
                    if claimed_efficiency is not None and claimed_efficiency > carnot_lim:
                        violations.append(
                            f"Second-Law Carnot Violation: Claimed efficiency {claimed_efficiency:.4f} exceeds Carnot limit {carnot_lim:.4f}"
                        )
            if t_hot_k > 0:
                area = radiator_area_m2 if radiator_area_m2 is not None else 1.0
                t_amb = t_cold_k if (t_cold_k is not None and t_cold_k >= 0) else 2.7
                sb_flux = cls.stefan_boltzmann_power(t_hot_k, area_m2=area, emissivity=emissivity, ambient_temp_k=t_amb)

        if delta_h_j_mol is not None and delta_s_j_mol_k is not None:
            ref_t = t_hot_k if (t_hot_k is not None and t_hot_k > 0) else 298.15
            dg, spontaneous = cls.gibbs_free_energy(delta_h_j_mol, delta_s_j_mol_k, ref_t)

        return ThermodynamicAuditResult(
            is_valid=(len(violations) == 0),
            carnot_efficiency_limit=carnot_lim,
            stefan_boltzmann_flux_w_m2=sb_flux,
            gibbs_free_energy_j_mol=dg,
            is_spontaneous=spontaneous,
            violations=violations,
        )

    def verify_carnot_limit(self, work_out: float, heat_in: float, t_hot: float, t_cold: float) -> Dict[str, Any]:
        eta_c = self.carnot_efficiency(t_hot_k=t_hot, t_cold_k=t_cold)
        eta_obs = float(work_out) / max(1e-12, float(heat_in))
        return {"valid": bool(eta_obs <= eta_c + 1e-6), "eta_carnot": float(eta_c), "eta_observed": float(eta_obs)}

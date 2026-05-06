"""Passive observers — instrument response models. §12.2.5 / §7.

Each observer reads an evolving `SimulationResult` (the v1 trace +
spectrum + plasma state) and produces a per-observer DataFrame ready
to compare against scope / PMT / hydrophone data in the lab.

v2.0 ships five concrete observers:
  - PMTObserver           (§7.1)  — photons → photoelectrons → V(t)
  - HydrophoneObserver    (§7.2)  — far-field acoustic radiation → V(t)
  - PickupCoilObserver    (§7.4)  — Margulis transient (off by default)
  - SpectrometerObserver  (§7.3)  — time-integrated S(λ) over a gate
  - StressProbeObserver   (§13)   — STUB: returns zero-stress traces;
                                    §13 fills in the wall-stress physics

All observers reuse v1 `cavplasma.detectors` helpers — Scenario adds the
position / aperture parameterisation but does not re-implement physics.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional, Protocol, Tuple

import numpy as np


# ---------------------------------------------------------------------------
# Observer protocol (§12.2.5)
# ---------------------------------------------------------------------------
class Observer(Protocol):
    name: str
    position: Tuple[float, float, float]

    def sample(self, sim_result: Any, scenario: Any) -> Any:
        """Return a pandas DataFrame indexed by 'time' with observer-specific
        columns (e.g. V_PMT, p_rad, V_coil)."""
        ...


def _distance_from_origin(position: Tuple[float, float, float]) -> float:
    import math
    return math.sqrt(sum(p * p for p in position))


# ---------------------------------------------------------------------------
# §7.1  PMT
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class PMTObserver:
    """Photomultiplier observer (§7.1)."""
    name: str = "PMT"
    position: Tuple[float, float, float] = (0.05, 0.0, 0.0)
    aperture_radius: float = 5e-3
    QE_peak: float = 0.25
    gain: float = 1e6
    R_load: float = 50.0

    def sample(self, sim_result: Any, scenario: Any) -> Any:
        import pandas as pd
        from cavplasma.detectors import pmt_signal

        distance = max(_distance_from_origin(self.position), 1e-6)
        out = pmt_signal(
            sim_result.t,
            sim_result.bubble["R"],
            sim_result.em["S_t_lambda"],
            sim_result.em["lambda_grid_m"],
            distance=distance,
            aperture_radius=self.aperture_radius,
            QE_peak=self.QE_peak,
            gain=self.gain,
            R_load=self.R_load,
        )
        df = pd.DataFrame({
            "time": sim_result.t,
            "photon_rate_at_PMT": out["photon_rate_at_PMT"],
            "photoelectron_rate": out["photoelectron_rate"],
            "V_PMT": out["V_PMT"],
        })
        df.attrs["distance"] = distance
        df.attrs["photons_collected"] = float(out["photons_collected"])
        df.attrs["geom_factor"] = float(out["geom_factor"])
        df.attrs["QE_peak"] = float(out["QE"])
        df.attrs["gain"] = float(out["gain"])
        return df


# ---------------------------------------------------------------------------
# §7.2  Hydrophone
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class HydrophoneObserver:
    """Hydrophone observer (§7.2). Far-field bubble radiation E24."""
    name: str = "hydrophone"
    position: Tuple[float, float, float] = (0.01, 0.0, 0.0)
    sensitivity_V_per_Pa: float = 50e-6

    def sample(self, sim_result: Any, scenario: Any) -> Any:
        import pandas as pd
        from cavplasma.detectors import hydrophone_signal

        liquid = scenario.liquid
        distance = max(_distance_from_origin(self.position), 1e-6)
        out = hydrophone_signal(
            sim_result.t,
            sim_result.bubble["R"],
            sim_result.bubble["Rdot"],
            liquid.rho,
            liquid.c,
            distance=distance,
            sensitivity_V_per_Pa=self.sensitivity_V_per_Pa,
        )
        df = pd.DataFrame({
            "time": sim_result.t,
            "p_rad": out["p_rad"],
            "V": out["V"],
        })
        df.attrs["distance"] = distance
        df.attrs["sensitivity_V_per_Pa"] = self.sensitivity_V_per_Pa
        return df


# ---------------------------------------------------------------------------
# §7.4  Pickup coil — Margulis transient (off by default, §10.6)
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class PickupCoilObserver:
    """Pickup-coil observer (§7.4). Margulis transient — §10.6 contested.

    Off by default. Set `enable=True` to include the parametric pulse;
    output is still emitted (zero V trace) when disabled.
    """
    name: str = "pickup_coil"
    position: Tuple[float, float, float] = (0.01, 0.0, 0.0)
    Q_b: float = 1e-11
    pulse_duration_s: float = 1e-7
    enable: bool = False

    def sample(self, sim_result: Any, scenario: Any) -> Any:
        import pandas as pd
        from cavplasma.detectors import pickup_coil_signal

        distance = max(_distance_from_origin(self.position), 1e-6)
        out = pickup_coil_signal(
            sim_result.t,
            sim_result.bubble["R"],
            sim_result.bubble["Rdot"],
            distance=distance,
            Q_b=self.Q_b,
            pulse_duration_s=self.pulse_duration_s,
            enable=self.enable,
        )
        df = pd.DataFrame({"time": sim_result.t, "V": out["V"]})
        df.attrs["distance"] = distance
        df.attrs["enabled"] = self.enable
        return df


# ---------------------------------------------------------------------------
# Spectrometer (§7.3) — time-integrated S(λ) over a gate
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class SpectrometerObserver:
    """Time-integrated emission spectrum over a configurable gate.

    Emits a DataFrame with columns ('lambda_nm', 'S_integrated') — one
    row per wavelength bin. `gate_t_lo` and `gate_t_hi` (s) define the
    integration window; `None` ends → full trace.
    """
    name: str = "spectrometer"
    position: Tuple[float, float, float] = (0.05, 0.0, 0.0)
    gate_t_lo: Optional[float] = None
    gate_t_hi: Optional[float] = None

    def sample(self, sim_result: Any, scenario: Any) -> Any:
        import pandas as pd

        t = sim_result.t
        spec = sim_result.em["S_t_lambda"]                # shape (n_t, n_lam)
        lam_m = sim_result.em["lambda_grid_m"]
        t_lo = self.gate_t_lo if self.gate_t_lo is not None else t[0]
        t_hi = self.gate_t_hi if self.gate_t_hi is not None else t[-1]
        mask = (t >= t_lo) & (t <= t_hi)
        if not np.any(mask):
            integrated = np.zeros_like(lam_m)
        else:
            integrated = np.trapezoid(spec[mask, :], x=t[mask], axis=0)
        df = pd.DataFrame({
            "lambda_nm": lam_m * 1e9,
            "S_integrated": integrated,
        })
        df.attrs["gate_t_lo"] = float(t_lo)
        df.attrs["gate_t_hi"] = float(t_hi)
        return df


# ---------------------------------------------------------------------------
# §13 — StressProbe (full physics)
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class StressProbeObserver:
    """Wall-stress probe (§13).

    Computes the time-resolved far-field wall pressure (E24 / §13.2
    spherical-collapse shock) and the microjet impulse (§13.2 / [PC1971])
    if the bubble is within ≈ 2 R_max of this position. Output DataFrame
    columns: 'time', 'wall_pressure', 'shear_stress'. Scalars (peak
    pressure, microjet impact, n_impacts) are exposed via `df.attrs`.
    """
    name: str = "stress_probe"
    position: Tuple[float, float, float] = (0.05, 0.0, 0.0)
    near_wall_threshold_factor: float = 2.0

    def sample(self, sim_result: Any, scenario: Any) -> Any:
        import math
        import pandas as pd
        from cavplasma.material.wall_loads import (
            microjet_velocity, waterhammer_pressure,
        )

        t = sim_result.t
        R = sim_result.bubble["R"]
        Rdot = sim_result.bubble["Rdot"]
        cfg = sim_result.config
        rho_L = cfg.liquid.rho
        c_L = cfg.liquid.c
        p_v = cfg.liquid.p_v
        p_inf = cfg.ambient.p_inf

        distance = max(_distance_from_origin(self.position), 1e-6)
        if len(t) < 3:
            df = pd.DataFrame({
                "time": t,
                "wall_pressure": np.zeros(len(t)),
                "shear_stress": np.zeros(len(t)),
            })
            df.attrs["distance"] = distance
            df.attrs["peak_pressure"] = 0.0
            df.attrs["p_wh_impact"] = None
            df.attrs["n_impacts"] = 0
            return df

        Rddot = np.gradient(Rdot, t)
        Vddot = 8.0 * math.pi * R * Rdot ** 2 + 4.0 * math.pi * R ** 2 * Rddot
        wall_pressure = rho_L / (4.0 * math.pi * distance) * Vddot
        # Shear stress: rough proxy ≈ 0.5 × |wall_pressure| (Karimi 1986)
        shear_stress = 0.5 * np.abs(wall_pressure)

        # §13.2 — microjet contribution if bubble is near this surface
        R_max = float(R.max())
        p_wh = None
        if distance < self.near_wall_threshold_factor * R_max and R_max > 0.0:
            U_jet = microjet_velocity(p_inf, p_v, rho_L)
            p_wh = waterhammer_pressure(rho_L, c_L, U_jet)

        sign_change = (Rdot[:-1] > 0) & (Rdot[1:] <= 0)
        n_impacts = int(np.sum(sign_change))

        df = pd.DataFrame({
            "time": t,
            "wall_pressure": wall_pressure,
            "shear_stress": shear_stress,
        })
        df.attrs["distance"] = distance
        df.attrs["peak_pressure"] = float(np.max(np.abs(wall_pressure)))
        df.attrs["p_wh_impact"] = float(p_wh) if p_wh is not None else None
        df.attrs["n_impacts"] = n_impacts
        return df

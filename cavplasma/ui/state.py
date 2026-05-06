"""Store helpers — Scenario / ScenarioResult ⇄ dcc.Store. §15.2.

`dcc.Store` holds JSON-able data. Scenario already round-trips via
`Scenario.to_json/.from_json` (§12.9). For ScenarioResult we keep a
*compact* JSON shape suitable for the browser: scalar summary fields,
warning + suggestion lists, and downsampled bubble + plasma traces.
Full DataFrames stay server-side; the UI receives only what it plots.
"""

from __future__ import annotations

import dataclasses
import json
from typing import Any, Optional

import numpy as np

from cavplasma.scenario import Scenario, ScenarioResult


# ---------------------------------------------------------------------------
# Scenario ⇄ store
# ---------------------------------------------------------------------------
def scenario_to_store(scenario: Scenario) -> str:
    """Serialise a Scenario for `dcc.Store(data=...)`. Round-trip safe."""
    return scenario.to_json()


def scenario_from_store(payload: Optional[str]) -> Optional[Scenario]:
    """Deserialise a scenario_store payload. Returns None if empty."""
    if not payload:
        return None
    return Scenario.from_json(payload)


# ---------------------------------------------------------------------------
# ScenarioResult ⇄ store
# ---------------------------------------------------------------------------
_TRACE_DOWNSAMPLE = 2000     # max samples per trace sent to the browser


def _downsample(arr: np.ndarray, n: int = _TRACE_DOWNSAMPLE) -> list:
    if len(arr) <= n:
        return [float(x) for x in arr]
    idx = np.linspace(0, len(arr) - 1, n).astype(int)
    return [float(x) for x in arr[idx]]


def result_to_store(result: ScenarioResult) -> dict:
    """Pack a ScenarioResult into a UI-shaped JSON dict.

    Keeps:
      - summary scalars (full ScenarioSummary)
      - bubble + plasma traces (downsampled)
      - per-observer traces (downsampled)
      - regime + suggestions + caveats lists
      - erosion / transducer_lifetime / thermal_state if present

    Drops:
      - em_spectra wide-format DataFrame (too large for stores; rebuilt
        on demand from sim_result via `figures.spectrum_surface`)
      - `_v1_result` (server-side only)
    """
    s = result.summary
    payload: dict = {
        "summary": {
            "R_max": s.R_max, "R_min": s.R_min,
            "wall_mach_peak": s.wall_mach_peak,
            "rayleigh_collapse_time": s.rayleigh_collapse_time,
            "minnaert_freq": s.minnaert_freq,
            "T_peak_K": s.T_peak_K,
            "T_peak_band": list(s.T_peak_band),
            "n_e_peak": s.n_e_peak,
            "ionization_peak": s.ionization_peak,
            "Gamma_peak": s.Gamma_peak,
            "flash_FWHM_ns": s.flash_FWHM_ns,
            "photons_visible_4pi": s.photons_visible_4pi,
            "photons_uv_4pi": s.photons_uv_4pi,
            "photons_detected_PMT": dict(s.photons_detected_PMT),
            "peak_pressure_at_observer": dict(s.peak_pressure_at_observer),
            "peak_voltage_PMT": dict(s.peak_voltage_PMT),
            "regime": s.regime,
            "shape_stability_flag": s.shape_stability_flag,
            "parametric_stability_index": s.parametric_stability_index,
            "RT_index": s.RT_index,
            "min_p_minus_pa": s.min_p_minus_pa,
            "expected_wall_lifetime_hours": s.expected_wall_lifetime_hours,
            "flags": list(s.flags),
        },
    }

    # Traces (DataFrame → list-of-lists). Downsample to keep payload light.
    bt = result.bubble_traces
    payload["bubble"] = {
        "time":  _downsample(bt["time"].to_numpy()),
        "R":     _downsample(bt["R"].to_numpy()),
        "Rdot":  _downsample(bt["Rdot"].to_numpy()),
        "T_g":   _downsample(bt["T_g"].to_numpy()),
    }
    pt = result.plasma_traces
    payload["plasma"] = {
        col: _downsample(pt[col].to_numpy()) for col in pt.columns
    }

    payload["observer_traces"] = {}
    for name, df in result.observer_traces.items():
        cols = list(df.columns)
        sub: dict = {}
        for col in cols:
            try:
                sub[col] = _downsample(df[col].to_numpy())
            except Exception:                                            # noqa: BLE001
                continue
        sub["__attrs__"] = {k: _scalarise(v) for k, v in df.attrs.items()}
        payload["observer_traces"][name] = sub

    # Suggestions
    payload["suggestions"] = [
        {
            "rule_id": sg.rule_id,
            "severity": sg.severity,
            "category": sg.category,
            "message": sg.message,
            "rationale": sg.rationale,
            "dossier_ref": sg.dossier_ref,
            "suggested_change": sg.suggested_change,
            "expected_effect": sg.expected_effect,
        }
        for sg in result.suggestions
    ]

    payload["warnings"] = [
        {"category": w.category, "severity": w.severity,
         "message": w.message, "actionable_fix": w.actionable_fix}
        for w in result.warnings
    ]

    # §13 outputs (best-effort serialisation)
    if result.erosion is not None:
        e = result.erosion
        payload["erosion"] = {
            "severity": e.severity,
            "T_inc_hours": e.T_inc_hours,
            "MDPR_um_per_h": e.MDPR_um_per_h,
            "lifetime_hours": e.lifetime_hours,
            "sub_yield": e.sub_yield,
            "material_name": e.material_name,
            "observer_distance_m": e.observer_distance_m,
        }
    if result.transducer_lifetime is not None:
        t = result.transducer_lifetime
        payload["transducer_lifetime"] = {
            "grade": t.grade,
            "duty_cycle": t.duty_cycle,
            "cooling": t.cooling,
            "average_power_W_per_cm2": t.average_power_W_per_cm2,
            "steady_state_T_K": t.steady_state_T_K,
            "margin_to_Curie_K": t.margin_to_Curie_K,
            "lifetime_hours": t.lifetime_hours,
            "notes": t.notes,
        }
    if result.thermal_state is not None:
        th = result.thermal_state
        payload["thermal_state"] = {
            "delta_T_steady_K": th.delta_T_steady_K,
            "time_constant_s": th.time_constant_s,
            "P_acoustic_dissipated_W": th.P_acoustic_dissipated_W,
            "will_boil": th.will_boil,
            "T_steady_K": th.T_steady_K,
        }

    return payload


def _scalarise(v: Any) -> Any:
    """Coerce numpy scalars to plain Python so JSON serialises cleanly."""
    if isinstance(v, (np.integer, np.floating)):
        return float(v)
    if isinstance(v, np.ndarray):
        return v.tolist()
    return v

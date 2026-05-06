"""Material catalog for §13. WallMaterial presets + transducer materials.

§13.3 / §13.4.2 / §13.6 numbers, all from the cited sources. The full
`WallMaterial` dataclass lives in `cavplasma.scenario.types` (so v2.0 §12
presets continue to work without importing §13). This module only
populates the catalog and provides a `get(name)` lookup.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Optional

from cavplasma.scenario.types import WallMaterial


# ---------------------------------------------------------------------------
# Wall material catalog (§13.3 + §13.4.2)
# ---------------------------------------------------------------------------
def _make_catalog() -> dict[str, WallMaterial]:
    return {
        "borosilicate_glass": WallMaterial(
            name="borosilicate_glass",
            rho=2230.0, E=64e9,
            sigma_Y=100e6, sigma_UTS=60e6,
            Vickers_H=5.5e9, p_Y_dynamic=200e6,
            L_hard=5e-6, fatigue_limit=30e6,
            transparent=True,
            chemical_compatibility=("water", "seawater", "ethanol"),
        ),
        "fused_silica": WallMaterial(
            name="fused_silica",
            rho=2200.0, E=72e9,
            sigma_Y=120e6, sigma_UTS=70e6,
            Vickers_H=6.8e9, p_Y_dynamic=250e6,
            L_hard=5e-6, fatigue_limit=35e6,
            transparent=True,
            chemical_compatibility=("water", "seawater", "H2SO4_98"),
        ),
        "stainless_316": WallMaterial(
            name="stainless_316",
            rho=8000.0, E=193e9,
            sigma_Y=240e6, sigma_UTS=580e6,
            Vickers_H=1.7e9, p_Y_dynamic=600e6,
            L_hard=80e-6, fatigue_limit=240e6,
            transparent=False,
            chemical_compatibility=("water", "seawater", "ethanol", "H2SO4_98"),
        ),
        "stainless_304": WallMaterial(
            name="stainless_304",
            rho=8000.0, E=193e9,
            sigma_Y=215e6, sigma_UTS=505e6,
            Vickers_H=1.5e9, p_Y_dynamic=550e6,
            L_hard=80e-6, fatigue_limit=210e6,
            transparent=False,
            chemical_compatibility=("water", "ethanol"),
        ),
        "aluminum_6061": WallMaterial(
            name="aluminum_6061",
            rho=2700.0, E=69e9,
            sigma_Y=276e6, sigma_UTS=310e6,
            Vickers_H=0.8e9, p_Y_dynamic=270e6,
            L_hard=50e-6, fatigue_limit=96e6,
            transparent=False,
            chemical_compatibility=("water",),
        ),
        "aluminum_1100": WallMaterial(
            name="aluminum_1100",
            rho=2710.0, E=69e9,
            sigma_Y=35e6, sigma_UTS=110e6,
            Vickers_H=0.3e9, p_Y_dynamic=80e6,
            L_hard=50e-6, fatigue_limit=35e6,
            transparent=False,
            chemical_compatibility=("water",),
        ),
        "brass_C36000": WallMaterial(
            name="brass_C36000",
            rho=8500.0, E=100e9,
            sigma_Y=125e6, sigma_UTS=340e6,
            Vickers_H=1.1e9, p_Y_dynamic=350e6,
            L_hard=60e-6, fatigue_limit=120e6,
            transparent=False,
            chemical_compatibility=("water",),
        ),
        "titanium_6al4v": WallMaterial(
            name="titanium_6al4v",
            rho=4430.0, E=114e9,
            sigma_Y=830e6, sigma_UTS=950e6,
            Vickers_H=3.4e9, p_Y_dynamic=880e6,
            L_hard=40e-6, fatigue_limit=510e6,
            transparent=False,
            chemical_compatibility=("water", "seawater"),
        ),
        "inconel_625": WallMaterial(
            name="inconel_625",
            rho=8440.0, E=208e9,
            sigma_Y=450e6, sigma_UTS=850e6,
            Vickers_H=2.8e9, p_Y_dynamic=900e6,
            L_hard=50e-6, fatigue_limit=420e6,
            transparent=False,
            chemical_compatibility=("water", "seawater", "H2SO4_98"),
        ),
        # Sentinel for open-water / no-wall scenarios (e.g. pistol shrimp)
        "open_water": WallMaterial(
            name="open_water",
            rho=998.0, E=2.2e9,
            sigma_Y=1e6, sigma_UTS=1e6,
            Vickers_H=1e3, p_Y_dynamic=1e6,
            L_hard=1e-3, fatigue_limit=1e6,
            transparent=True,
            chemical_compatibility=("water", "seawater"),
        ),
    }


_CATALOG: Optional[dict[str, WallMaterial]] = None


def catalog() -> dict[str, WallMaterial]:
    """Return the read-only catalog of named WallMaterial presets."""
    global _CATALOG
    if _CATALOG is None:
        _CATALOG = _make_catalog()
    return _CATALOG


def get(name: str) -> WallMaterial:
    """Look up a WallMaterial by name. KeyError if not in the catalog."""
    cat = catalog()
    if name not in cat:
        raise KeyError(
            f"unknown WallMaterial {name!r}; known: {sorted(cat.keys())}"
        )
    return cat[name]


def list_materials() -> list[str]:
    """Sorted list of catalogued material names."""
    return sorted(catalog().keys())


# ---------------------------------------------------------------------------
# §13.4.2 — calibrated reference erosion bands per material (ASTM G32 / G134)
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class ASTMReference:
    """ASTM-calibrated incubation time + steady MDPR for a material."""
    name: str
    T_inc_lo_h: float           # incubation time lower bound (hours)
    T_inc_hi_h: float
    MDPR_lo_um_per_h: float     # steady MDPR lower bound (µm/h)
    MDPR_hi_um_per_h: float


_ASTM_REFS: dict[str, ASTMReference] = {
    "aluminum_1100":   ASTMReference("aluminum_1100",   0.3, 1.0, 50.0, 200.0),
    "aluminum_6061":   ASTMReference("aluminum_6061",   0.5, 2.0, 30.0, 80.0),
    "brass_C36000":    ASTMReference("brass_C36000",    1.0, 3.0, 10.0, 30.0),
    "stainless_304":   ASTMReference("stainless_304",   5.0, 20.0, 3.0, 10.0),
    "stainless_316":   ASTMReference("stainless_316",   8.0, 30.0, 1.0, 5.0),
    "inconel_625":     ASTMReference("inconel_625",     20.0, 50.0, 0.3, 1.0),
    "titanium_6al4v":  ASTMReference("titanium_6al4v",  30.0, 80.0, 0.5, 2.0),
    "borosilicate_glass": ASTMReference("borosilicate_glass", 200.0, 1000.0, 0.05, 0.1),
    "fused_silica":    ASTMReference("fused_silica",    1000.0, 5000.0, 0.01, 0.05),
    "open_water":      ASTMReference("open_water",      1e6, 1e6, 0.0, 0.0),
}


def astm_reference(name: str) -> ASTMReference:
    if name not in _ASTM_REFS:
        # Fallback: medium-hardness ductile metal
        return _ASTM_REFS["stainless_304"]
    return _ASTM_REFS[name]


# ---------------------------------------------------------------------------
# §13.6 — piezoelectric transducer materials
# ---------------------------------------------------------------------------
PiezoGrade = Literal["PZT-4", "PZT-5H", "PZT-8", "lithium_niobate", "PMN-PT"]


@dataclass(frozen=True)
class PiezoMaterial:
    """Piezo-element thermal + mechanical limits for §13.6 lifetime."""
    name: PiezoGrade
    T_curie_K: float
    max_avg_power_W_per_cm2: float
    max_pulsed_power_W_per_cm2: float
    mechanical_Q: float
    dielectric_loss: float           # tan δ at low field
    notes: str = ""


_PIEZO_CATALOG: dict[str, PiezoMaterial] = {
    "PZT-4": PiezoMaterial(
        name="PZT-4",
        T_curie_K=623.0,                 # 350 °C
        max_avg_power_W_per_cm2=8.0,
        max_pulsed_power_W_per_cm2=80.0,
        mechanical_Q=600.0,
        dielectric_loss=0.004,
        notes="Hard PZT, common in SBSL rings",
    ),
    "PZT-5H": PiezoMaterial(
        name="PZT-5H",
        T_curie_K=483.0,                 # 210 °C
        max_avg_power_W_per_cm2=2.0,
        max_pulsed_power_W_per_cm2=15.0,
        mechanical_Q=65.0,
        dielectric_loss=0.02,
        notes="Soft PZT, low-loss imaging",
    ),
    "PZT-8": PiezoMaterial(
        name="PZT-8",
        T_curie_K=573.0,                 # 300 °C
        max_avg_power_W_per_cm2=10.0,
        max_pulsed_power_W_per_cm2=100.0,
        mechanical_Q=1000.0,
        dielectric_loss=0.003,
        notes="Highest-Q hard PZT; SBSL standard. §13.6.",
    ),
    "lithium_niobate": PiezoMaterial(
        name="lithium_niobate",
        T_curie_K=1483.0,                # 1210 °C
        max_avg_power_W_per_cm2=2.0,
        max_pulsed_power_W_per_cm2=20.0,
        mechanical_Q=10000.0,
        dielectric_loss=0.0001,
        notes="High-temperature single crystal",
    ),
    "PMN-PT": PiezoMaterial(
        name="PMN-PT",
        T_curie_K=413.0,                 # 140 °C
        max_avg_power_W_per_cm2=1.0,
        max_pulsed_power_W_per_cm2=10.0,
        mechanical_Q=80.0,
        dielectric_loss=0.005,
        notes="High-d33 single crystal; low T_curie",
    ),
}


def piezo(name: str) -> PiezoMaterial:
    if name not in _PIEZO_CATALOG:
        raise KeyError(
            f"unknown piezo material {name!r}; known: {sorted(_PIEZO_CATALOG.keys())}"
        )
    return _PIEZO_CATALOG[name]


def list_piezo() -> list[str]:
    return sorted(_PIEZO_CATALOG.keys())

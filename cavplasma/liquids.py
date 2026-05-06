"""Liquid presets. §9.1 / §3.6 of the dossier supply the numbers."""

from __future__ import annotations

from cavplasma.config import LiquidProperties


_PRESETS: dict[str, LiquidProperties] = {
    "water": LiquidProperties(
        name="water",
        rho=998.2, c=1482.0, mu=1.002e-3,
        sigma=7.28e-2, p_v=2339.0,
        B_tait=3.05e8, n_tait=7.15,
        beta_BoverA=3.5, alpha_dB_cm_MHz2=0.025,
    ),
    # §3.6: seawater (35 ‰), §9.8 default for pistol-shrimp benchmark
    "seawater": LiquidProperties(
        name="seawater",
        rho=1025.0, c=1530.0, mu=1.08e-3,
        sigma=7.50e-2, p_v=2300.0,
        B_tait=3.05e8, n_tait=7.15,         # Tait values not separately tabulated; reuse water
        beta_BoverA=3.5, alpha_dB_cm_MHz2=0.025,
    ),
    # §3.6 / §4.6: glycerin
    "glycerin": LiquidProperties(
        name="glycerin",
        rho=1261.0, c=1904.0, mu=1.412,
        sigma=6.34e-2, p_v=0.13,
        B_tait=3.5e8, n_tait=7.0,
        beta_BoverA=5.4, alpha_dB_cm_MHz2=0.6,
    ),
    # §4.6: 85 % H2SO4
    "sulfuric_98": LiquidProperties(
        name="sulfuric_98",
        rho=1840.0, c=1430.0, mu=24.0e-3,
        sigma=5.5e-2, p_v=1.0,
        B_tait=3.0e8, n_tait=7.0,
        beta_BoverA=4.5, alpha_dB_cm_MHz2=0.1,
    ),
    # §4.6: silicone oil 100 cSt
    "silicone_oil_100cSt": LiquidProperties(
        name="silicone_oil_100cSt",
        rho=965.0, c=980.0, mu=0.097,
        sigma=2.09e-2, p_v=1.0,
        B_tait=2.5e8, n_tait=7.0,
        beta_BoverA=6.5, alpha_dB_cm_MHz2=1.0,
    ),
}


def preset(name: str) -> LiquidProperties:
    """Look up a named preset. Returns a frozen LiquidProperties."""
    if name not in _PRESETS:
        raise KeyError(
            f"unknown liquid preset {name!r}; available: {sorted(_PRESETS)}"
        )
    return _PRESETS[name]


def available() -> list[str]:
    return sorted(_PRESETS)

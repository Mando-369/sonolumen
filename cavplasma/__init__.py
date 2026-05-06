"""cavplasma — single-bubble cavitation plasma simulator (v1).

Implementation of cavitation_research/11_simulator_spec.md. The package
mirrors the module layout of §11.4. See README.md for the user-facing
API and dossier cross-references.
"""

from cavplasma._version import __version__

# Public API surface (populated as phases land).
from cavplasma.config import (
    AcousticDrive,
    AmbientConditions,
    BubbleSeed,
    LiquidProperties,
    NumericsOptions,
    OutputOptions,
    PhysicsOptions,
    SimulationConfig,
)
from cavplasma import (
    liquids, drive, seed, bubble_dynamics, thermal, plasma, em_emission,
    detectors, solvers, presets, visualisation,
)
from cavplasma.runner import run, sweep, SimulationResult

# v2 — Scenario layer (§12). Built on top of v1; never modifies it.
from cavplasma import scenario
from cavplasma.scenario import Scenario, ScenarioResult

# v2 — §13 material stress + §14 suggestions engine. Both plug into the
# Scenario layer via post-processing in Scenario.run(); they never modify v1.
from cavplasma import material, suggestions

# v2 — §15 UI layer. Optional dep (`pip install cavplasma[ui]`); skipped
# if Dash isn't installed.
try:
    from cavplasma import ui                             # noqa: F401
    _has_ui = True
except ImportError:
    _has_ui = False

__all__ = [
    "__version__",
    "SimulationConfig",
    "LiquidProperties",
    "AmbientConditions",
    "AcousticDrive",
    "BubbleSeed",
    "PhysicsOptions",
    "NumericsOptions",
    "OutputOptions",
    "liquids",
    "drive",
    "seed",
    "bubble_dynamics",
    "thermal",
    "plasma",
    "em_emission",
    "detectors",
    "solvers",
    "presets",
    "visualisation",
    "run",
    "sweep",
    "SimulationResult",
    # v2
    "scenario",
    "Scenario",
    "ScenarioResult",
    "material",
    "suggestions",
]

if _has_ui:
    __all__.append("ui")

"""cavplasma.scenario — v2 Scenario layer (§12).

A `Scenario` wraps `cavplasma.run()` into a one-press virtual experiment.
This subpackage builds on top of the v1 physics core; v1 modules in
`cavplasma/` are read-only dependencies.

Public surface:

    from cavplasma.scenario import Scenario, presets, observers
    s = presets.sbsl_canonical()
    result = s.run()
    print(result.summary)

The Scenario API is designed so the §13 (material stress) and §14
(suggestions engine) modules plug in without touching v1 or §12 code:
they fill `Optional` fields on `ScenarioResult` (wall_loads, erosion,
regime, suggestions, …) that v2.0 ships as `None` / `[]` placeholders.
"""

from cavplasma.scenario import observers, presets
from cavplasma.scenario.scenario import Scenario
from cavplasma.scenario.types import (
    BubblePopulation,
    Chamber,
    Distribution,
    DriveSchedule,
    ImpulsivePulse,
    ScenarioResult,
    ScenarioSummary,
    Suggestion,
    SweepSpec,
    Transducer,
    WallMaterial,
    Warning,
)

__all__ = [
    "Scenario",
    "ScenarioResult",
    "ScenarioSummary",
    "Chamber",
    "Transducer",
    "DriveSchedule",
    "SweepSpec",
    "BubblePopulation",
    "ImpulsivePulse",
    "Distribution",
    "WallMaterial",
    "Warning",
    "Suggestion",
    "observers",
    "presets",
]

"""cavplasma.material — §13 material stress, erosion, lifetime.

Public API:

    from cavplasma.material import (
        materials,                      # WallMaterial + PiezoMaterial catalogues
        predict_wall_loads,             # §13.2 — wall-pressure history
        predict_erosion_rate,           # §13.4/§13.5 — T_inc + MDPR + lifetime
        predict_transducer_lifetime,    # §13.6 — piezo depoling lifetime
        predict_thermal_equilibrium,    # §13.8 — liquid ΔT lumped capacity
        microjet_velocity, microjet_velocity_water,
        waterhammer_pressure,
    )

Plugs into the v2 Scenario layer (§12) by populating
`ScenarioResult.{wall_loads, erosion, transducer_lifetime, thermal_state}`
in `Scenario.run()`. The §14 suggestions engine reads these fields for
rules R10 (wall lifetime) and R15 (thermal runaway).
"""

from cavplasma.material import materials
from cavplasma.material.erosion import (
    ASTM_REF_IMPACT_RATE,
    ASTM_REF_PRESSURE_PA,
    ErosionPrediction,
    predict_erosion_rate,
    severity_factor,
    single_event_pit_volume,
)
from cavplasma.material.thermal import ThermalState, predict_thermal_equilibrium
from cavplasma.material.transducer import (
    TransducerLifetime,
    predict_transducer_lifetime,
)
from cavplasma.material.wall_loads import (
    WallLoadHistory,
    microjet_velocity,
    microjet_velocity_water,
    predict_wall_loads,
    waterhammer_pressure,
)

__all__ = [
    "materials",
    "WallLoadHistory",
    "ErosionPrediction",
    "TransducerLifetime",
    "ThermalState",
    "predict_wall_loads",
    "predict_erosion_rate",
    "predict_transducer_lifetime",
    "predict_thermal_equilibrium",
    "severity_factor",
    "single_event_pit_volume",
    "microjet_velocity",
    "microjet_velocity_water",
    "waterhammer_pressure",
    "ASTM_REF_PRESSURE_PA",
    "ASTM_REF_IMPACT_RATE",
]

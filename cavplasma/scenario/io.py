"""JSON save / load for `Scenario`. §12.9.

A Scenario is purely declarative — every field is a plain dataclass,
scalar, string, tuple, or dict. JSON round-trip is straightforward
modulo three things the encoder handles explicitly:

  * **Dataclass dispatch.** Every dataclass instance is tagged with a
    `"_type"` discriminator. `from_dict` uses a registry to reconstruct
    the right type; nested dataclasses (e.g. `Chamber.wall_material`)
    are decoded recursively.

  * **Tuples.** JSON has no tuple type. The encoder wraps every tuple
    in `{"_tuple": [...]}` and the decoder reverses, so
    `OutputOptions.spectrum_lambda_nm = (200.0, 1000.0, 100)`
    round-trips losslessly.

  * **Callables.** `AcousticDrive.custom_p_a` (a function) cannot be
    serialised. Encoding raises with a clear message; presets in
    `cavplasma.scenario.presets` all use named-string drive kinds
    (`sinusoid`, `tone_burst`, `impulsive`) so byte-identical round-
    trip is achievable for every shipped preset.

§12.10 acceptance criterion #6: `from_json(to_json(p)).to_json() ==
p.to_json()` for every preset (idempotent round-trip).
"""

from __future__ import annotations

import dataclasses
import json
from typing import Any

# v1 dataclasses
from cavplasma.config import (
    AcousticDrive,
    AmbientConditions,
    BubbleSeed,
    LiquidProperties,
    NumericsOptions,
    OutputOptions,
    PhysicsOptions,
)

# v2 dataclasses
from cavplasma.scenario.observers import (
    HydrophoneObserver,
    PickupCoilObserver,
    PMTObserver,
    SpectrometerObserver,
    StressProbeObserver,
)
from cavplasma.scenario.types import (
    BubblePopulation,
    Chamber,
    Distribution,
    DriveSchedule,
    ImpulsivePulse,
    SweepSpec,
    Transducer,
    WallMaterial,
)


# ---------------------------------------------------------------------------
# Type registry — every Scenario-graph dataclass must be listed here
# ---------------------------------------------------------------------------
_REGISTRY: dict[str, type] = {
    # v1
    "LiquidProperties": LiquidProperties,
    "AmbientConditions": AmbientConditions,
    "AcousticDrive": AcousticDrive,
    "BubbleSeed": BubbleSeed,
    "PhysicsOptions": PhysicsOptions,
    "NumericsOptions": NumericsOptions,
    "OutputOptions": OutputOptions,
    # v2
    "WallMaterial": WallMaterial,
    "Chamber": Chamber,
    "Transducer": Transducer,
    "SweepSpec": SweepSpec,
    "DriveSchedule": DriveSchedule,
    "ImpulsivePulse": ImpulsivePulse,
    "Distribution": Distribution,
    "BubblePopulation": BubblePopulation,
    # Observers
    "PMTObserver": PMTObserver,
    "HydrophoneObserver": HydrophoneObserver,
    "PickupCoilObserver": PickupCoilObserver,
    "SpectrometerObserver": SpectrometerObserver,
    "StressProbeObserver": StressProbeObserver,
    # Scenario itself is registered late (avoid circular import)
}


def _register_scenario_type() -> None:
    """Register Scenario in the type registry. Called from scenario.py
    after Scenario is defined to avoid a circular import."""
    from cavplasma.scenario.scenario import Scenario
    _REGISTRY["Scenario"] = Scenario


# ---------------------------------------------------------------------------
# Encode
# ---------------------------------------------------------------------------
def _encode(obj: Any) -> Any:
    """Recursively convert `obj` into JSON-safe primitives + type tags."""
    if obj is None:
        return None
    if isinstance(obj, bool):
        return obj
    if isinstance(obj, (int, float, str)):
        return obj
    if isinstance(obj, tuple):
        return {"_tuple": [_encode(v) for v in obj]}
    if isinstance(obj, list):
        return [_encode(v) for v in obj]
    if isinstance(obj, dict):
        # JSON-dict: every key must be a string. We assume Scenario dicts
        # already use string keys (validated by dataclass field types).
        return {str(k): _encode(v) for k, v in obj.items()}
    if dataclasses.is_dataclass(obj):
        cls_name = type(obj).__name__
        if cls_name not in _REGISTRY:
            # Try late registration of Scenario
            if cls_name == "Scenario":
                _register_scenario_type()
            else:
                raise TypeError(
                    f"dataclass {cls_name} is not registered for JSON serialisation"
                )
        fields_dict: dict[str, Any] = {}
        for f in dataclasses.fields(obj):
            # Skip private fields (prefixed with `_`) — they're internal back-references.
            if f.name.startswith("_"):
                continue
            fields_dict[f.name] = _encode(getattr(obj, f.name))
        return {"_type": cls_name, "_fields": fields_dict}
    if callable(obj):
        raise TypeError(
            "Cannot serialise a callable field "
            "(likely AcousticDrive.custom_p_a). "
            "Use a named drive kind ('sinusoid' / 'tone_burst' / 'impulsive') instead."
        )
    raise TypeError(f"Don't know how to serialise {type(obj).__name__}: {obj!r}")


# ---------------------------------------------------------------------------
# Decode
# ---------------------------------------------------------------------------
def _decode(node: Any) -> Any:
    """Recursively reconstruct dataclasses + tuples from `_encode` output."""
    if node is None or isinstance(node, (bool, int, float, str)):
        return node
    if isinstance(node, list):
        return [_decode(v) for v in node]
    if isinstance(node, dict):
        if "_tuple" in node and len(node) == 1:
            return tuple(_decode(v) for v in node["_tuple"])
        if "_type" in node and "_fields" in node and len(node) == 2:
            cls_name = node["_type"]
            if cls_name not in _REGISTRY:
                if cls_name == "Scenario":
                    _register_scenario_type()
                else:
                    raise ValueError(
                        f"Unknown dataclass type {cls_name!r} in JSON. "
                        "Did the file come from a newer cavplasma version?"
                    )
            cls = _REGISTRY[cls_name]
            kwargs = {k: _decode(v) for k, v in node["_fields"].items()}
            return cls(**kwargs)
        # Plain dict — decode values
        return {k: _decode(v) for k, v in node.items()}
    raise TypeError(f"Don't know how to decode {type(node).__name__}: {node!r}")


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------
def scenario_to_dict(scenario: Any) -> dict:
    """Convert a `Scenario` (or any registered dataclass) to a JSON-safe dict."""
    return _encode(scenario)


def scenario_from_dict(d: dict) -> Any:
    """Inverse of `scenario_to_dict`."""
    return _decode(d)


def scenario_to_json(scenario: Any, *, indent: int = 2) -> str:
    """Render a Scenario as a deterministic JSON string.

    `sort_keys=True` plus consistent indent + Python's float `repr()`
    inside `json.dumps` give byte-identical output for the same input.
    Per §12.10 #6, `from_json(to_json(s)).to_json() == s.to_json()`.
    """
    return json.dumps(_encode(scenario), sort_keys=True, indent=indent)


def scenario_from_json(text: str) -> Any:
    """Parse a JSON string back into a Scenario tree."""
    return _decode(json.loads(text))

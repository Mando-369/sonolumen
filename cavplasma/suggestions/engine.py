"""SuggestionsEngine + SuggestionsReport. §14.7.

Public entry point:

    from cavplasma.suggestions import SuggestionsEngine
    report = SuggestionsEngine(scenario, scenario_result).analyze()
    # report.regime — §12 RegimeLabel (and report.regime_internal — §14.2 fine)
    # report.suggestions — list[Suggestion], priority-ordered (§14.5)
    # report.caveats — list[Suggestion] of category 'caveat'
    # report.next_experiment — Optional[Suggestion]

The engine is cheap (< 100 ms per run) and pure: it reads the scenario
+ result, never mutates them. The Scenario.run() entry point in §12
attaches `report.regime`, `report.suggestions`, `report.next_experiment`
back to the result.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional

from cavplasma.scenario.types import RegimeLabel, Suggestion

from cavplasma.suggestions import regime as regime_mod
from cavplasma.suggestions.caveats import ALL_CAVEATS
from cavplasma.suggestions.rules import ALL_RULES


# ---------------------------------------------------------------------------
# Priority ordering (§14.5)
# ---------------------------------------------------------------------------
# Errors first; hardware/regime blockers next; regime-entry parameter
# rules; then optimisation; numerics; caveats last.
_PRIORITY: dict[str, int] = {
    # errors
    "R14": 0,
    "R11": 1,
    # hardware/regime blockers
    "R12": 2,
    # regime-entry parameter rules
    "R1": 10, "R2": 11, "R3": 12,
    # optimisation
    "R4": 20, "R5": 21, "R7": 22, "R6": 23,
    # safety / lifetime
    "R10": 30, "R15": 31,
    # within-regime adjustments
    "R8": 40, "R9": 41, "R16": 42, "R17": 43,
    # numerics
    "R13": 50,
    # caveats (after all action items)
    "C1": 100, "C2": 101, "C3": 102, "C4": 103,
    "C5": 104, "C6": 105, "C7": 106,
}


_SEVERITY_RANK: dict[str, int] = {"error": 0, "warning": 1, "info": 2}


def _sort_key(s: Suggestion) -> tuple[int, int, int]:
    """Caveats always last; within each group, sort by severity then rule priority.

    Per §14.5: "Caveats last — they're context, not action items." So a
    warning caveat (e.g. C7) still sorts after an info action item (e.g.
    R4) because the user reads action items first.
    """
    is_caveat = 1 if s.category == "caveat" else 0
    return (is_caveat,
            _SEVERITY_RANK.get(s.severity, 99),
            _PRIORITY.get(s.rule_id, 999))


# ---------------------------------------------------------------------------
# Report container
# ---------------------------------------------------------------------------
@dataclass
class SuggestionsReport:
    """§14.7 — output bundle returned by SuggestionsEngine.analyze()."""
    regime: RegimeLabel
    regime_internal: str
    suggestions: list[Suggestion] = field(default_factory=list)
    caveats: list[Suggestion] = field(default_factory=list)
    next_experiment: Optional[Suggestion] = None


# ---------------------------------------------------------------------------
# The engine
# ---------------------------------------------------------------------------
class SuggestionsEngine:
    """§14 rule-based reasoning over a `ScenarioResult`. Stateless."""

    def __init__(self, scenario: Any, scenario_result: Any) -> None:
        self.scenario = scenario
        self.result = scenario_result

    def analyze(self) -> SuggestionsReport:
        """Run regime classification + every rule + every caveat.

        Returns a `SuggestionsReport` with priority-ordered suggestions
        and caveats. The expensive `next_experiment` finite-difference
        sweep is *not* run here — call `suggest_next_experiment(...)`
        explicitly when needed.
        """
        regime, regime_internal = regime_mod.classify(self.scenario, self.result)

        suggestions: list[Suggestion] = []
        for rule in ALL_RULES:
            try:
                out = rule(self.scenario, self.result, regime_internal)
            except Exception as exc:                                  # noqa: BLE001
                # Never let a buggy rule crash the engine.
                out = Suggestion(
                    severity="info",
                    category="caveat",
                    rule_id=rule.__name__,
                    message=f"rule {rule.__name__} raised {type(exc).__name__}; skipped",
                    rationale="rule failure",
                    dossier_ref="§14",
                )
            if out is not None:
                suggestions.append(out)

        caveats: list[Suggestion] = []
        for cav in ALL_CAVEATS:
            try:
                out = cav(self.scenario, self.result)
            except Exception:
                out = None
            if out is not None:
                caveats.append(out)

        suggestions.sort(key=_sort_key)
        caveats.sort(key=_sort_key)

        return SuggestionsReport(
            regime=regime,
            regime_internal=regime_internal,
            suggestions=suggestions,
            caveats=caveats,
            next_experiment=None,
        )

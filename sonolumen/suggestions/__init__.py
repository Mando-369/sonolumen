"""sonolumen.suggestions — §14 rule-based reasoning engine.

Public API:

    from sonolumen.suggestions import (
        SuggestionsEngine,             # §14.7 entry point
        SuggestionsReport,             # output bundle
        classify_regime,               # §14.2 classifier
        suggest_next_experiment,       # §14.6 finite-difference suggestor
        ALL_RULES, ALL_CAVEATS,        # rule + caveat registries
    )

`Scenario.run()` calls `SuggestionsEngine(scenario, result).analyze()`
post-integration and attaches the regime + suggestions + caveats back
onto `ScenarioResult`. No v1 or §12 code mutates inside this module.
"""

from sonolumen.suggestions.caveats import ALL_CAVEATS
from sonolumen.suggestions.engine import SuggestionsEngine, SuggestionsReport
from sonolumen.suggestions.inverse_design import (
    DesignConstraints,
    DesignTarget,
    initial_design,
    refine_design,
)
from sonolumen.suggestions.next_experiment import (
    Goal,
    suggest_next_experiment,
)
from sonolumen.suggestions.regime import classify as classify_regime
from sonolumen.suggestions.rules import ALL_RULES

__all__ = [
    "SuggestionsEngine",
    "SuggestionsReport",
    "classify_regime",
    "suggest_next_experiment",
    "Goal",
    "ALL_RULES",
    "ALL_CAVEATS",
    "DesignTarget",
    "DesignConstraints",
    "initial_design",
    "refine_design",
]

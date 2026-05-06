# Section 14 — Suggestions engine (v2)

> Purpose: define the rule-based reasoning layer that turns a
> `ScenarioResult` into a list of *actionable* messages — regime
> classification, what's likely failing, what to change next, and which
> §10 caveats apply to the current run. This is what makes the UI feel
> like a "virtual scientific advisor" rather than a calculator.

The engine is intentionally *not* ML-based. It's a few hundred lines of
conditional logic anchored in the physics of Sections 2–13. Every
suggestion includes a justification pointing back to a specific section
of the dossier so the user can audit it.

---

## 14.1  Output schema

```python
@dataclass
class Suggestion:
    severity: Literal['info', 'warn', 'error']
    category: Literal['regime', 'parameter', 'hardware', 'numerics',
                      'safety', 'data_quality', 'caveat']
    message: str                          # human-readable
    rationale: str                         # cites dossier section
    suggested_change: dict | None          # parameter → new value
    expected_effect: str | None            # "T_peak +30%", etc.
    dossier_ref: str                       # e.g. "§10.1, §4.2"
```

The UI surfaces these in three groups:

- **Why this happened** (rationale for the regime classification)
- **What to change next** (concrete parameter suggestions)
- **Caveats for this run** (relevant §10 uncertainties)

---

## 14.2  Regime classification (the first thing the engine decides)

Run a discrete classifier on `ScenarioResult.summary`:

```
sub_blake          : peak rarefaction never reached Blake threshold
                     → no bubble dynamics → "no cavitation"
                     Test: min(p_∞ − p_a(t)) > P_B(R0)

linear_oscillation : Blake exceeded but R_max/R_0 < 2
                     → no inertial collapse, just pulsation
                     Test: R_max / R_0 < 2  AND  Ṙ_max/c < 0.01

stable_spherical   : R_max/R_0 in 5–20, Mach < 0.3, parametric stable
                     → "you have SBSL-like behavior"
                     Test: 5 ≤ R_max/R_0 ≤ 20  AND  Ṙ_peak/c < 0.3
                          AND parametric_stability_index < 1

violent_spherical  : R_max/R_0 > 20, Mach > 0.3, still spherically stable
                     → "strong collapse, possibly SL"
                     Test: Mach 0.3–1, parametric < 1

shape_unstable     : RT or parametric instability index > 1
                     → "expect bubble fragmentation; spherical sim is
                        an upper bound on T_peak"
                     Test: parametric_stability > 1 OR RT_index > 1

transducer_limited : requested P_A exceeds transducer
                     max_acoustic_power × Q_chamber capacity
                     → hardware blocker

over_eos           : Ṙ/c > 1 occurred — outside KME validity
                     → "switch to Gilmore + NASG"

numerical_warning  : convergence diagnostic > 5% on key outputs
                     → "tighten tolerances"
```

These classifiers are cheap (one comparison each). They run before the
expensive observer post-processing.

---

## 14.3  Parameter-suggestion rules

Triggered by the regime classifier. Pattern: each rule names the
trigger, the suggested change, the expected effect, and the dossier
reference for the rationale.

### Rule R1 — sub-Blake → increase drive
- Trigger: `regime == 'sub_blake'`
- Suggest: increase `drive.P_A` by factor 1.5
- Rationale: §3.4 — Blake threshold for current R₀. Specifically,
  current min p − P_B = X Pa, increase needed.
- Expected effect: cavitation onset.

### Rule R2 — sub-Blake → smaller nucleus
- Trigger: same as R1, alternative
- Suggest: reduce `bubble_seed.R0` by factor 2
- Rationale: §3.4 — smaller nucleus has lower P_B (per E4).
- Expected effect: cavitation onset at current drive.

### Rule R3 — linear regime → increase P_A toward inertial
- Trigger: `regime == 'linear_oscillation'`
- Suggest: increase `drive.P_A` by 50%, sweep
- Rationale: §3.7 — empirical thresholds for vigorous cavitation.
- Expected effect: R_max/R_0 grows past 5 → enters stable_spherical.

### Rule R4 — stable_spherical, low T → switch gas
- Trigger: `regime == 'stable_spherical'`, `T_peak < 8000 K`
- Suggest: change `bubble.gas_composition` from air to argon
- Rationale: §4.5 — Ar-saturated water gives 15–25 kK vs air's 5–10 kK.
- Expected effect: T_peak factor ~2× higher.

### Rule R5 — stable_spherical, low T → switch liquid
- Trigger: `regime == 'stable_spherical'`, `T_peak < 12000 K`
- Suggest: change `liquid` from water to 95% H₂SO₄ + Xe
- Rationale: §4.6 — H₂SO₄+Xe is the published peak; T_peak
  30 000–40 000 K achievable.
- Expected effect: T_peak factor ~3× higher; chemistry/safety burden up.

### Rule R6 — frequency mismatch with chamber resonance
- Trigger: `|drive.f − f_chamber_eigenmode| > f / Q`
- Suggest: set `drive.f = nearest_eigenmode_frequency`
- Rationale: §3.2 — off-resonance reduces effective in-cell P_A by
  factor (1 + (Δf · 2Q/f)²)^½.
- Expected effect: in-cell P_A increases by factor of order Q.

### Rule R7 — bubble far from Minnaert resonance
- Trigger: `|f_drive − f_Minnaert(R0)| / f_Minnaert > 0.5`
- Suggest: change `R0` to `f_drive`'s Minnaert R₀
- Rationale: §3.5 E5 — resonant bubble couples maximum energy from drive.
- Expected effect: R_max grows; collapse is more violent.

### Rule R8 — violent regime, near shape-instability boundary
- Trigger: `regime == 'violent_spherical'`, parametric stability > 0.7
- Suggest: reduce `drive.P_A` 10%
- Rationale: §10.5 — over-driving fragments the bubble, suppresses
  flash brightness despite higher predicted T_peak.
- Expected effect: more reproducible flashes.

### Rule R9 — shape-unstable regime → smaller R₀
- Trigger: `regime == 'shape_unstable'`
- Suggest: reduce `bubble_seed.R0`
- Rationale: §10.5 — smaller bubbles have shorter parametric lengths,
  more stable.
- Expected effect: regime → stable_spherical.

### Rule R10 — wall material erosion warning
- Trigger: `predicted_lifetime_hours < target_hours_user`
- Suggest: change `chamber.wall_material` to next-harder material
- Rationale: §13 — current severity factor predicts T_inc < target.
- Expected effect: lifetime ∝ severity^(−n) jumps; concrete number
  given.

### Rule R11 — transducer overdrive
- Trigger: `regime == 'transducer_limited'`
- Suggest: increase `transducer.max_acoustic_power_W` (i.e. spec a
  bigger transducer) OR increase `chamber.Q` OR use multiple
  transducers
- Rationale: §3.3, §6.4 — power-vs-amplitude geometry.
- Expected effect: numerical estimate of needed wattage.

### Rule R12 — over-EOS (Mach > 1) → switch equation
- Trigger: `regime == 'over_eos'`
- Suggest: `physics_options.bubble_eq = 'gilmore'`,
  `physics_options.liquid_eos = 'nasg'`
- Rationale: §2.3, §2.4 — KME breaks down at Mach > 0.3, Gilmore-NASG
  required for accuracy.
- Expected effect: T_peak corrected (typically *down* by 5–20%).

### Rule R13 — convergence not yet adequate
- Trigger: `convergence_diagnostic > 0.05`
- Suggest: tighten `numerics.rtol` by factor 10 (or atol by factor 100)
- Rationale: §2.6 — required for sub-ns collapse resolution.
- Expected effect: stable T_peak to < 5% across tightening.

### Rule R14 — observer position outside chamber
- Trigger: any observer position not inside chamber geometry
- Severity: error
- Rationale: physical impossibility.

### Rule R15 — bath thermal runaway
- Trigger: `predicted_steady_state_T_liquid > T_boil`
- Suggest: enable cooling jacket, reduce duty cycle, or reduce
  `transducer.max_acoustic_power_W`
- Rationale: §6.5, §13.8 — energy balance between acoustic input and
  cooling.
- Expected effect: T_liquid stable below boiling.

### Rule R16 — high humidity / vapour-dominated bubble
- Trigger: `bubble.gas_composition['H2O'] > 0.5` at peak compression
- Suggest: degas more aggressively, drop `liquid.temperature`,
  switch to lower-vapour-pressure liquid
- Rationale: §4.3 — vapour cap quenches T_peak.
- Expected effect: T_peak factor ~2× recovery.

### Rule R17 — saha vs stewart-pyatt disagreement
- Trigger: `Γ > 0.3` AND user used `'ideal_saha'`
- Suggest: switch to `'stewart_pyatt'`
- Rationale: §4.2, §10.4 — non-ideal corrections matter at Γ ~ 1.
- Expected effect: ionization fraction shifts (often +30–100%).

---

## 14.4  Caveat rules — surface §10 uncertainties relevant to this run

These don't change parameters; they remind the user what's unknown:

### Caveat C1 — peak temperature uncertainty
- Trigger: any run with `T_peak > 5000 K`
- Message: "Literature reports factor 2–3 spread on T_peak in this
  regime (§10.1). Treat the simulator's value as the centre of a band,
  not a point estimate. Suggested band: [T_peak × 0.5, T_peak × 1.5]."
- Always-on for plasma-regime runs.

### Caveat C2 — pistol-shrimp T_peak weakly constrained
- Trigger: scenario uses `pistol_shrimp` or `impulsive` mode
- Message: §10.2 — only a lower bound (5000 K) is published. Actual
  could be 5000–20000 K.

### Caveat C3 — gas content drift not modeled
- Trigger: scenario duration > 100 acoustic cycles, rectified diffusion
  enabled
- Message: §10.3 — bubble gas composition shifts to ≈ 99% Ar in air-
  saturated water over many cycles. Initial composition may not be
  the steady-state composition.

### Caveat C4 — toroidal cavitation not modeled
- Trigger: `bubble.kind == 'impulsive'` (pistol-shrimp-style)
- Message: §10.9 — real impulsive collapses are toroidal; spherical
  simulator may overestimate T_peak by ~30%.

### Caveat C5 — multi-bubble shielding not modeled in v1
- Trigger: `BubblePopulation.kind == 'cloud'` AND v < 2
- Message: §10.10 — bubble-bubble interactions suppress per-bubble
  conditions in dense clouds; current independent-ensemble approximation
  is an upper bound.

### Caveat C6 — Margulis transients are contested
- Trigger: `physics_options.include_margulis_transient == True`
- Message: §10.6 — output predicted from a parametric model with
  weak literature support. Treat predicted V(t) on coil as
  "could be this big at most," not "will be this."

### Caveat C7 — Tait EOS limits at extreme compression
- Trigger: `physics_options.liquid_eos == 'tait'` AND `Mach > 0.5`
- Message: §10.11 — Tait EOS becomes inaccurate above ~10 GPa; switch
  to NASG for collapse phase if T_peak prediction matters.

---

## 14.5  Suggestion priority and ordering

When multiple rules fire, ordering matters. Pattern:

1. Errors first (R14, etc.).
2. Hardware/regime errors that block useful results (R11, R12).
3. Parameter suggestions to *enter* a useful regime (R1–R3) take
   priority over suggestions to *optimize* within a regime (R4–R8).
4. Numerics and convergence (R13) — after the regime is at least
   sensible.
5. Caveats last — they're context, not action items.

The UI displays at most 5 suggestions at a time (top by severity, then
by expected effect size). The full list is available in a "show all"
panel.

---

## 14.6  "Next experiment" suggestions

A higher-level rule that fires after a successful run: identify the
*most informative* parameter change for the user's stated goal.

```python
def suggest_next_experiment(result: ScenarioResult,
                             goal: Literal['maximize_T', 'maximize_n_e',
                                            'maximize_photons',
                                            'maximize_lifetime',
                                            'minimize_drive',
                                            'characterize_regime']) -> Suggestion:
    ...
```

Implementation: a small finite-difference derivative of the chosen
output with respect to each free parameter (using last-completed run
+ a few quick perturbation runs), sorted by |∂output/∂param|·param,
returning the top-1.

For `goal == 'characterize_regime'` the engine instead suggests the
parameter whose current value is *most uncertain in its effect*
(highest gradient magnitude across recent runs). This is the
"information-gain" heuristic — the parameter you should sweep next to
learn the most about the system.

---

## 14.7  Running the engine

```python
report = SuggestionsEngine(scenario, scenario_result).analyze()
# report.regime: the classifier's output
# report.suggestions: list[Suggestion], priority-ordered
# report.caveats: list[Suggestion] of category 'caveat'
# report.next_experiment: Optional[Suggestion]
```

Cheap by design — should add < 100 ms to a scenario run.

---

## 14.8  Validation tests

```
test_classifier_sbsl_canonical()
    # SBSL canonical run → regime == 'stable_spherical'

test_classifier_sub_blake()
    # P_A = 0.5 atm, R0 = 1 µm in water → 'sub_blake'

test_R1_fires_on_subblake()
    # Sub-blake regime → R1 returns suggested P_A 1.5×

test_R6_fires_on_off_resonance()
    # Drive 0.95× chamber resonance → R6 fires with the eigenmode value

test_caveat_C1_always_on_for_plasma()
    # Any T_peak > 5000 K run includes C1 in caveats

test_priority_ordering()
    # Mix of rules: errors first, regime entry next, optimization last
```

---

## 14.9  Honest limits

The engine can't:
- Tell you whether your specific physical setup will work (it doesn't
  know the lab; it only knows the scenario you described).
- Predict which sonochemistry products you'll see (chemistry is v2 of
  the simulator, beyond the rules here).
- Account for impurities, microbubbles from rough walls, or any
  secondary nucleation source not in the scenario.
- Override the §10 uncertainties — it surfaces them, doesn't resolve them.

The engine's value is *consistency*: every run goes through the same
rule set, gets the same priority ordering, and surfaces the same
caveats. This is what makes "test → adjust → retest" stable enough to
draw conclusions across many runs.

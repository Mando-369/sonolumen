# Section 13 — Material stress, cavitation erosion, lifetime (v2)

> Purpose: provide the physics + parameters needed to predict how long a
> chamber, transducer face, or any wetted surface will survive a given
> cavitation regime. This is what tells the user "this 100 W
> tabletop-cell run will damage the glass in 10 hours" rather than just
> "the bubble reaches T_peak K." Inputs to the simulator's
> `material.py` module; outputs feed the §14 suggestions engine and the
> §15 UI.

---

## 13.1  Mechanism overview

When a bubble collapses near a solid surface, two distinct stress
sources hit the wall:

1. **Microjet impingement.** Asymmetric collapse near a wall produces a
   high-speed liquid jet (50–200 m/s, ~10–100 µm diameter) directed at
   the surface. Impact pressures are *waterhammer*-class:
   `p_wh ≈ ρ_L c_L U_jet / 2 ≈ 10–200 MPa` for a single event
   [PC1971, BR1994].
2. **Spherical-collapse shock wave.** Even far from walls, the rebound
   shock from a strongly collapsing bubble is order 100 MPa at 10 µm,
   decaying as ~1/r [BHL2002]. At the wall the local pressure pulse is
   1–50 MPa for tabletop-scale bubbles.

Both are very brief (sub-µs) but cumulative. The damage process is
typically:

```
Incubation phase    →    Mass loss phase    →    Steady erosion
(no measurable wear,    (pits form, depth     (∂h/∂t = constant rate
 just hardening of       grows nonlinearly,    once material exposed)
 the surface, ~0.1–      0.1–10 µm/h)
 100 hours)
```

Reference: Karimi & Martin 1986; Hattori, Karimi 2009 [HK2009].

---

## 13.2  Wall-pressure history from a single bubble (forward model)

For a bubble of radius R(t) at distance `d` from a wall:

$$
p_{\rm wall}(t) \;\approx\; \frac{\rho_L}{4\pi d}\,\ddot V_b(t - d/c_L)
\;+\; p_{\rm wh}\,\delta(t - t_{\rm jet})\cdot \mathbb{1}[d < d_{\rm jet}]
$$

where the first term is the radiated shock (E24) and the second is the
microjet contribution if the bubble collapses *near* the wall (typically
`d < 2 R_max`). The microjet condition is geometric: only "near-wall"
bubbles develop jets. For SBSL with the bubble trapped at chamber
center, the wall sees only the radiated shock; for MBSL clouds against
the cell wall, both contribute.

Microjet velocity (Plesset & Chapman 1971 [PC1971]):

$$
U_{\rm jet} \approx 8.97 \sqrt{\frac{p_\infty - p_v}{\rho_L}} \;\;\text{(near a flat wall)}
$$

For water at 20 °C and 1 atm, U_jet ≈ 90 m/s — gives waterhammer impact
pressure ≈ 67 MPa.

---

## 13.3  Single-event pit volume

A waterhammer impact on a ductile material produces a hemispherical pit
of volume

$$
V_{\rm pit} \;\approx\; \frac{(p_{\rm wh} - p_{\rm Y})^2 \cdot A_{\rm jet}^{3/2}}{H^2}
$$

where `p_Y` is the dynamic yield strength of the material, `H` the
Vickers hardness, and `A_jet` the impact area. Threshold condition:
`p_wh > p_Y` — *no pit if the impact pressure is below yield*.

Material yield thresholds (peak impact pressure required to leave a
permanent pit):

| Material               | p_Y dynamic (MPa)  | Vickers H (MPa) | Reference |
|---                     |---                 |---              |---        |
| Pyrex / borosilicate    | ~200               | 5500            | [HK2009]  |
| Fused silica            | ~250               | 6800            | [HK2009]  |
| Stainless 316           | ~600               | 1700            | [F1995]   |
| Aluminium 6061          | ~270               | 800             | [F1995]   |
| Brass                   | ~350               | 1100            | [F1995]   |
| Titanium 6Al-4V         | ~880               | 3400            | [F1995]   |

For tabletop SBSL (single bubble at chamber center, R_max ≈ 50 µm,
shock ≈ 1 MPa at 5 cm wall): **all standard materials are below yield;
no erosion in the SBSL regime.** This is why glass SBSL cells last
thousands of hours.

For MBSL or near-wall cavitation (cloud against wall, R_max ≈ 100 µm,
microjet impact ≈ 67 MPa): **Pyrex can be over yield; aluminium and
brass definitely are.** Erosion expected.

For pistol-shrimp-style impulsive jets (R_max ≈ 3 mm, jet velocity
~25 m/s, but in seawater at impulsive Bernoulli limit): wall impact
~50 MPa, comparable to MBSL.

---

## 13.4  Mean depth of penetration rate (MDPR)

After the incubation phase, the steady-state erosion rate scales as
[KK1986, FRT2009]:

$$
\dot h_{\rm MDPR} \;=\; k_e \cdot N_{\rm impact} \cdot V_{\rm pit}
$$

where `N_impact` is the impact rate (events/s/m²) and `k_e` is an
empirical material-dependent factor of order unity. In simplified form
adopted by ASTM G134 cavitation tests:

$$
\dot h_{\rm MDPR}\,[\text{µm/h}] \;\approx\; \frac{C_M}{T_{\rm inc}}\;\;
\text{after } t > T_{\rm inc}
$$

with `C_M` material-specific (calibrated, mm-class for soft materials,
µm-class for hard) and `T_inc` the incubation time.

### 13.4.1  Incubation time

From Franc & Riondet 2006 [FRT2009]:

$$
T_{\rm inc} \;\approx\; \tau_{\rm cover} \cdot \frac{H \cdot L_{\rm hard}}{(p_{\rm wh} - p_Y)^2 / \text{σ}_{\rm UTS}}
$$

where `τ_cover` is the time required for impacts to cover the surface
once (set by `N_impact · A_jet`), `L_hard` is the work-hardening layer
thickness (typically 10–100 µm for ductile metals), and `σ_UTS` is the
ultimate tensile strength.

For practical use, the simulator should expose `T_inc` and steady
MDPR as outputs and let the user judge whether the regime is
acceptable; do not hard-code a "safe" or "unsafe" threshold (because
the user's tolerance depends on cell cost vs. data value).

### 13.4.2  Reference erosion rates (calibrated)

From standardized cavitation erosion tests (ASTM G32/G134, vibratory
or jet rigs at 20 kHz, ~80 µm peak-to-peak amplitude):

| Material              | T_inc (h)  | Steady MDPR (µm/h) | Source     |
|---                    |---         |---                 |---         |
| Aluminium 1100        | 0.3–1      | 50–200              | [F1995]    |
| Aluminium 6061-T6     | 0.5–2      | 30–80               | [F1995]    |
| Brass C36000          | 1–3        | 10–30               | [F1995]    |
| Stainless 304         | 5–20       | 3–10                | [F1995]    |
| Stainless 316         | 8–30       | 1–5                 | [F1995]    |
| Inconel 625           | 20–50      | 0.3–1               | [F1995]    |
| Titanium 6Al-4V       | 30–80      | 0.5–2               | [F1995]    |
| Pyrex (extrapolated)  | hundreds   | < 0.1               | [HK2009]   |
| Fused silica          | thousands  | < 0.05              | [HK2009]   |

These are *severe* (industrial) regime numbers. Tabletop SBSL is
typically several orders of magnitude milder — multiply T_inc by
≈ 10²–10³ and divide MDPR similarly.

The simulator's job: compute the right *severity factor* from the
predicted near-wall pressure and impact rate, then scale these
calibrated numbers to the user's regime.

---

## 13.5  Severity factor

Operational severity scaling (from §13.4 + impact-rate physics):

$$
S \;=\; \left(\frac{p_{\rm wall,peak}}{p_{\rm ref}}\right)^n
\cdot \frac{N_{\rm impact}}{N_{\rm ref}}
$$

with `n ≈ 2.5–3.5` empirical (work-hardening regime; n = 2 in elastic
regime, n = 3 in plastic) and `(p_ref, N_ref)` taken from the ASTM
calibration setup. For tabletop SBSL with one bubble at 25 kHz at
5 cm from a glass wall: peak shock at wall ≈ 1 MPa (vs ASTM ~50 MPa),
N_impact ≈ 25 000 /s vs ASTM ~10⁹ /s/m² of *effective* impacts; so

```
S_tabletop_SBSL ≈ (1/50)^3 · (25000 / 10^7)
              ≈ 10^-5 · 10^-3
              ≈ 10^-8
```

Eight orders of magnitude milder than ASTM. Lifetime = T_inc · 10⁸ —
effectively infinite. Confirms that SBSL cells don't show measurable
erosion even after years.

For an MBSL bath at 1 kW with a horn 5 mm above the cell floor:
S can be ≈ 0.1 — i.e. the cell floor sees ~10 µm/h erosion of a
soft material. This is what real industrial sonotrodes wear out.

---

## 13.6  Transducer face damage

The piezo face is the worst-positioned surface — directly in the high-
intensity field, often coupled to the liquid through a thin Mylar or
metal window. Two separate failure modes:

1. **Cavitation pitting of the window** — same physics as §13.4, but
   with `d ≈ 0` so the bubble is *on* the window. Severity factor
   1–10× above bath floor.
2. **Piezo depoling under high mechanical Q** — internal heating from
   I²R losses + dielectric loss leads to T > T_Curie (~350 °C for
   PZT-4, ~210 °C for PZT-5H). Mitigated by low duty cycle and active
   cooling.

For PZT-8 (high-Q, low-loss, the SBSL standard): max electrical drive
typically 10 W/cm² average power sustained, 100 W/cm² pulsed. Beyond
that, depoling and crack formation; 50–500 hour lifetime under
sustained drive at 50 % of max power [APC, M2018].

The simulator's job is to emit a *predicted lifetime* with explicit
inputs:

- Drive duty cycle (continuous vs pulsed)
- Cooling assumption (none, water-jacket, forced air)
- Piezo material grade
- Acoustic loading (matched? mismatched?)

---

## 13.7  Wall fatigue (acoustic, non-cavitation)

Even without cavitation contact, the chamber wall is cyclically loaded
at the drive frequency. For Pyrex at 25 kHz with a Q-200 cell driven
at 1.3 atm in-cell amplitude: wall stress amplitude ≈ 0.5 MPa, well
below the ~30 MPa fatigue limit of Pyrex glass [SG2002]. Negligible
for tabletop. Becomes relevant for industrial 1 kW horns at MPa-
class wall stress.

For any high-Q resonator, the wall stress amplitude is approximately

$$
\sigma_{\rm wall} \approx P_{\rm internal} \cdot \frac{R_{\rm chamber}}{2 \cdot \text{wall thickness}}
$$

(thin-wall pressure-vessel formula). Simulator outputs σ_wall and
flags if it exceeds 10 % of the fatigue limit for the wall material —
that's the conservative threshold for indefinite-cycle operation.

---

## 13.8  Thermal stress

Acoustic energy ultimately heats the liquid (§6.5); the chamber wall
sees a thermal gradient between liquid and ambient. For typical
tabletop power densities (< 1 W/cm³ liquid), thermal stress in glass
walls < 1 MPa — well below failure. Becomes relevant for kilowatt-
class horns or HIFU at extended duty cycles.

The simulator computes ΔT_liquid(t) from a simple lumped-capacity
model:

$$
\rho_L V_L c_p \frac{dT}{dt} = P_{\rm acoustic\_dissipated} - U A (T - T_{\rm ambient})
$$

with U the overall heat-transfer coefficient (free convection ~5
W/m²·K, water-jacket cooling ~1000 W/m²·K). Output: equilibrium
ΔT and time constant.

---

## 13.9  Module API (for `material.py`)

```python
@dataclass
class WallMaterial:
    name: str
    rho: float                # kg/m³
    E: float                  # Young's modulus, Pa
    sigma_Y: float            # static yield, Pa
    sigma_UTS: float          # ultimate tensile, Pa
    Vickers_H: float          # Pa
    p_Y_dynamic: float        # dynamic yield (≈ 1.5–2× σ_Y), Pa
    L_hard: float             # work-hardening layer thickness, m
    fatigue_limit: float      # Pa (high-cycle)
    transparent: bool          # for optical observers
    chemical_compatibility: list[str]  # 'water', 'H2SO4', ...

# Built-in catalog of common materials follows §13.3 and §13.4.2

def predict_wall_loads(scenario_result, observer_position) -> WallLoadHistory: ...
def predict_erosion_rate(wall_loads, material) -> ErosionPrediction: ...
def predict_transducer_lifetime(transducer, drive, cooling) -> float: ...
def predict_thermal_equilibrium(scenario) -> ThermalState: ...
```

Outputs feed the §14 suggestions engine ("your wall lifetime is 30
hours — switch to fused silica or move bubbles further from wall")
and the §15 UI (lifetime indicator, stress heat-map overlay on the
chamber view).

---

## 13.10  Validation tests

```
test_no_erosion_in_canonical_SBSL()
    # SBSL canonical: predict S < 10^-5, lifetime > 10^4 hours

test_microjet_velocity_water()
    # Plesset-Chapman: U_jet ≈ 90 m/s for water at 1 atm; check ±5%

test_waterhammer_pressure()
    # ρ c U / 2 = 67 MPa for water + 90 m/s; check exact

test_aluminum_severe_regime()
    # 1 kW horn over Al6061: predict MDPR 30–80 µm/h after T_inc 0.5–2 h;
    # check within published bands

test_no_yield_on_Pyrex_below_threshold()
    # Pyrex, 1 MPa shock: no pit volume predicted (sub-yield)

test_transducer_lifetime_PZT8()
    # PZT-8 at 50% max drive, water-jacketed: predict > 100 h
```

---

## 13.11  What this enables

The user can now ask the UI: *"How long will my chamber survive at this
regime?"* and get a number. They can also ask: *"What's the highest
P_A I can run before erosion starts?"* — that's a sweep of the §13.5
severity factor crossing some threshold the user chooses (typically
T_inc < 100 hours = "real damage").

This is where the simulator becomes a budget tool: tests cost time,
chambers cost money, and predicting the operating envelope before
ordering parts is exactly where this layer pays off.

---

## Citation tags used in this section

- [PC1971] Plesset, Chapman, *J. Fluid Mech.* 47, 283 (1971) — microjet
  velocity for near-wall collapse.
- [BR1994] Brennen, *Cavitation and Bubble Dynamics*, Oxford UP (1995),
  Ch. 5.
- [KK1986] Karimi, Martin, *Wear* 107, 343 (1986) — incubation theory.
- [F1995] Franc, Michel, *Fundamentals of Cavitation*, Springer (2004) —
  ductile-material erosion catalogue.
- [HK2009] Hattori, Mikami, Yamaguchi, *Wear* 267, 1981 (2009) —
  ceramics & glasses.
- [FRT2009] Franc, Riondet, Karimi, Chahine, *J. Fluids Eng.* 133, 021304
  (2011) — incubation/MDPR formulas.
- [SG2002] Schott Group, *Borosilicate glass technical data*. [doc]
- [APC] APC International, *Piezoelectric Ceramics — Principles and
  Applications*. [doc]
- [M2018] Morgan Advanced Materials, *Piezo materials datasheet*. [doc]
- [BHL2002] Brenner, Hilgenfeldt, Lohse, *Rev. Mod. Phys.* 74, 425
  (2002) — collapse-shock pressures.

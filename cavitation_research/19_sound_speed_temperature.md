# §19 — Sound speed vs. temperature in water (the 74 °C maximum)

A short corollary to §17 (sound speed under pressure) and §18
(temperature/salinity coupling). The user's intuition was that
temperature might be the biggest factor for sound speed in water —
worth verifying, because the answer reveals another anomaly: sound
speed in pure water is **non-monotonic in T**, peaking at 74 °C and
then decreasing.

## TL;DR

* **In oceans, depth dominates the absolute range** (~180 m/s end-to-end
  vs. ~85 m/s for temperature, ~50 m/s for salinity).
* **In a benchtop reactor, temperature is the most accessible knob**
  with the steepest local coefficient (~4.6 m/s per °C at room T).
* **But the dependence is non-monotonic** — pure water at 1 atm has
  sound speed *maximum* at 74.17 °C (c_max ≈ 1555 m/s). Above that,
  more heat means slower sound. This is unique to water (and other
  associated liquids); gases and most simple liquids are strictly
  monotonic in T.

---

## Pure water sound speed at 1 atm

From the IAPWS-95 equation of state (Wagner & Pruß 2002), polynomial
fit (Lubbers & Graaff 1998):

| T (°C) | c (m/s) | dc/dT (m/s per K) |
|---|---|---|
| 0 | 1402.4 | — |
| 5 | 1426.2 | +4.76 |
| 10 | 1447.3 | +4.22 |
| 20 | **1482.4** | +3.51 |
| 30 | 1509.2 | +2.68 |
| 40 | 1528.9 | +1.97 |
| 50 | 1542.6 | +1.37 |
| 60 | 1551.0 | +0.84 |
| 70 | 1554.8 | +0.38 |
| **74.17** | **1555.14** | **0.00 (maximum)** |
| 80 | 1554.5 | -0.11 |
| 90 | 1550.5 | -0.40 |
| 100 | 1543.1 | -0.74 |

Two things to notice:

1. The slope **starts** at +4.76 m/s/K (very strong) and **shrinks
   monotonically** to zero at 74 °C. So the coefficient itself is
   T-dependent — quoting "4.6 m/s/K" is a 20 °C value, not a
   universal constant.
2. The peak at 74 °C is **shallow** (only ~1 m/s above the value at
   60 °C and 80 °C), but it's real and reproducible — it's been
   measured repeatedly since the 1950s and matches the IAPWS-95
   theoretical reference equation.

## Why does water peak at 74 °C?

Same root cause as the 4 °C density anomaly: hydrogen-bond
geometry. Sound speed is `c = √(K/ρ)`. As you heat water:

| Effect | T < 4 °C | 4–74 °C | T > 74 °C |
|---|---|---|---|
| Density ρ | rising (anomaly) | falling | falling |
| Bulk modulus K | rising | rising | falling |
| `c = √(K/ρ)` | rising | rising | falling |

Below 74 °C, the rise in `K` from continuing hydrogen-bond breakdown
outpaces the fall in `ρ`. Above 74 °C, normal thermal disordering
dominates: `K` falls faster than `ρ`, so `c` falls. The crossover
gives the maximum.

For comparison:
* **Air (gas)**: `c ∝ √T`. Always increases. 0 °C → 50 °C raises
  c from 331 to 360 m/s, and there's no maximum below the
  ionisation regime.
* **Most simple liquids** (alcohols, oils): `c` decreases
  monotonically with T from triple point onward — no anomaly,
  because they don't form a 3-D hydrogen-bonded network.
* **Mercury**: `c` increases very slightly with T; the temperature
  coefficient is tiny (`dc/dT ≈ -0.5 m/s/K`).

Water is genuinely unusual.

## Which knob actually moves the needle?

For the user's pattern hunt, the question is: when sweeping a
parameter to look for trends, which gives the most signal per unit
of "effort"?

**Local coefficient at standard conditions (20 °C, 35 ppt, 0 m)**:

| Variable | Slope | Equivalence |
|---|---|---|
| Temperature | 4.6 m/s per K | (1 K is the unit) |
| Salinity | 1.3 m/s per ppt | 1 K ≡ 3.4 ppt salt |
| Depth | 0.016 m/s per m | 1 K ≡ 287 m of depth |

**Total range across realistic ocean values**:

| Variable | Range | Δc | Notes |
|---|---|---|---|
| Temperature | 2 → 28 °C | +83 m/s | steep at low T, flat at high T |
| Salinity | 0 → 40 ppt | +45 m/s | linear |
| Depth | 0 → 11 km | +181 m/s | mostly linear (`0.016z`) |

So the user's intuition is half right. **Per unit change**,
temperature has the steepest coefficient at room T. But because
the *available range* of depth is so big in the ocean, depth ends
up moving sound speed by 2× as much from end to end. In a lab
reactor where you can't easily build 1 km of water column,
temperature is the dominant control — and you'd hit the 74 °C
maximum if you turned the heater up.

## How this maps onto cavplasma

Currently the simulator uses **scalar** `liquid.c = 1482 m/s` for
fresh water, **independent of `T_inf`**.

Concrete failure modes for T sweeps:

* User sets `T_inf = 60 °C` (sonochemistry-relevant temperature):
  real water has `c = 1551 m/s`, simulator still uses 1482. ~5 %
  error in Mach number, KM radiation damping, chamber resonance
  frequency.
* User sets `T_inf = 80 °C`: real `c = 1554 m/s` — same 5 % gap.
  Crucially, **going from 60 °C to 80 °C lowers `c` by 0.5 m/s**
  in reality, but the simulator says 0. So a temperature sweep
  across the maximum will not show the maximum at all.
* User sets `T_inf = 0 °C` (cold-water cavitation): real
  `c = 1402 m/s`, simulator 1482 — 5.7 % overestimate of `c` →
  Mach number underestimated → bubble looks more shape-stable
  than it really is.

**The fix is small**: in `_compose_simulation_config`, replace
`liquid.c` with a temperature-corrected value derived from the
IAPWS polynomial above. Same form as Q4 (pressure-corrected `c`)
in §17, except keyed on `ambient.T_inf` instead of `ambient.p_inf`.
v1 unchanged at 20 °C since that's where the catalog values are
calibrated.

For the ocean side, Mackenzie already gives `c(T, S, z)` — Q5/Q9 in
§17/§18 covers the seawater-aware version of the same patch.

## Open questions

* **Q11**: scalar `liquid.c` should be derived from `c(T_inf)` at
  scenario-compose time, using the IAPWS polynomial for fresh
  water and Mackenzie for seawater. ~10 lines in
  `_compose_simulation_config` plus a small lookup helper in
  `liquids.py`.
* **Q12**: combined with Q4 (pressure) and Q9 (salinity), this
  becomes `c(T, S, p)` — three orthogonal corrections to the
  single scalar. The combined patch is ~30 lines; would close the
  baseline-`c` modelling gap entirely across the cavplasma
  parameter range.

## References

* Lubbers, J. and Graaff, R. *Ultrasound Med. Biol.* **24**, 1065
  (1998) — IAPWS-95-derived polynomial for water sound speed
* Marczak, W. *J. Acoust. Soc. Am.* **102**, 2776 (1997) — sound
  speed in water 0–95 °C, alternative high-precision fit
* Wagner, W. and Pruß, A. *J. Phys. Chem. Ref. Data* **31**, 387
  (2002) — IAPWS-95 reference equation

# §17 — Sound speed in compressed water

A companion to §16 (pressure regimes). Higher static pressure makes
water stiffer faster than it makes it denser, so the speed of sound
goes up with depth. This note records the standard formulas, fact-
checks a few common claims, and (importantly) flags how sonolumen's
Tait-EOS sound-speed model already responds to depth and where the
modelling gap is.

## TL;DR

| Where | Sound speed | Notes |
|---|---|---|
| 1 atm, 20 °C, fresh water | 1482 m/s | Newton-Laplace `c = √(K/ρ)` |
| 1 atm, 20 °C, seawater | 1521 m/s | Mackenzie formula |
| Cold polar surface (2 °C) | 1456 m/s | Mackenzie |
| **SOFAR channel (~1 km)** | **1483 m/s** | Local minimum — sound trap |
| 5 km abyssal | 1543 m/s | Mackenzie |
| Mariana Trench bottom (11 km) | **~1654 m/s** | Mackenzie full form |
| Ice VII (5 GPa, room T) | ~4500 m/s | Brillouin scattering |
| Ice X (~70 GPa) | ~9000 m/s | Symmetric H-bond solid |

Pressure makes water stiffer (`K` rises) faster than it makes it denser
(`ρ` rises), so `c = √(K/ρ)` increases with depth. The dependence is
monotonic in the liquid regime, then jumps when water freezes into a
high-pressure ice phase.

## 1. Newton-Laplace, the master equation

```
c = √(K / ρ)         (Newton-Laplace, valid for any fluid)
```

* `K` = isentropic bulk modulus (Pa) — how much pressure to halve a unit
  volume
* `ρ` = density (kg/m³)

Quick sanity check at 1 atm, 20 °C: `K ≈ 2.2 GPa`, `ρ ≈ 998 kg/m³`,
so `c = √(2.2e9/998) ≈ 1485 m/s` — matches the tabulated 1482 m/s
to better than 0.5 %. ✓

The reason `c` *grows* with pressure: water's bulk modulus `K(p)`
increases roughly linearly (`dK/dp ≈ 7` for water, the Tait exponent),
while density grows much more slowly (a few % over hundreds of bar).
The numerator wins.

## 2. Mackenzie (1981) for seawater

The full empirical form used in oceanography:

```
c = 1448.96
  + 4.591  T - 0.05304 T² + 2.374e-4 T³
  + 1.340 (S - 35)
  + 0.0163 z + 1.675e-7 z² - 7.139e-13 T z³
  - 0.01025 T (S - 35)
```

with `T` in °C, `S` in psu (≈ ppt), `z` in m. The simplified form

```
c ≈ 1449.2 + 4.6 T - 0.055 T² + 0.00029 T³
    + (1.34 - 0.01 T)(S - 35)
    + 0.016 z
```

is correct to ~5 m/s at 1 km depth and ~20 m/s by 11 km. For the
deepest dive use the full equation.

> **Correction note:** an earlier draft of this dossier put Mariana
> Trench bottom sound speed at "about 1540 m/s." That's wrong by
> ~110 m/s — the trench is at ~11 km, where Mackenzie gives **1654
> m/s** (full) or **1632 m/s** (simplified). 1540 m/s actually
> corresponds to about 5 km depth in cold seawater, not 11 km. Use
> 1654 m/s for the trench.

## 3. The SOFAR channel — Snell's law in the ocean

Snell's law: a sound ray bends *toward* the slower medium. In the
ocean two effects fight each other:

* Pressure makes `c` go up with depth (~16 m/s per 1000 m via the
  `0.016 z` term)
* Temperature drops with depth in the upper ocean (each °C is worth
  ~4.6 m/s via the `4.6 T` term)

Above the thermocline, temperature wins → `c` decreases with depth.
Below the thermocline (cold abyss), pressure wins → `c` increases
with depth. They cross at ~1000 m, creating a **sound speed
minimum** — the SOFAR channel. Sound launched there refracts back
into the channel from above and below, and a low-frequency pulse
can travel **thousands of km** along it (whales, antisubmarine
listening, the 1991 Heard Island feasibility test that picked up a
57 Hz tone in Bermuda).

For sonolumen this is a chamber-design consideration only if you
ever model very large open-water configurations — irrelevant for
SBSL or pistol-shrimp scales.

## 4. High-pressure ice — sound speed jumps

Once water transitions to a solid ice phase (>1 GPa, see §16), the
acoustic story changes:

* **Two wave speeds appear:** longitudinal `V_p` (compressional) and
  transverse `V_s` (shear). Liquids only support `V_p`.
* `V_p` jumps discontinuously across the freezing line — Ice VII at
  5 GPa has `V_p ≈ 4500 m/s` (Shen et al., *Phys. Earth Planet. Inter.*
  2011), about 3× the liquid value.
* In Ice X (>70 GPa) `V_p` reaches ~9000 m/s — comparable to steel.

> **Correction note:** the original write-up said Ice VII sound speed
> is "over 3500 m/s." That's true but conservatively low; modern
> Brillouin scattering puts Ice VII at 4500–5500 m/s near the
> transition and >7000 m/s by ~30 GPa.

## 5. How this maps onto sonolumen

sonolumen uses a Tait equation of state for the liquid
(`bubble_dynamics.py:tait_enthalpy`, `tait_sound_speed`):

```
ρ(p)/ρ_0 = ((p + B)/(p_ref + B))^(1/n)
c(p)² = c_0² + (n - 1) · H(p_ref → p)
```

where `H` is the Tait enthalpy integrated from a reference pressure
to the local pressure. Inside the simulator:

* `c0 = liquid.c` — the surface (1 atm) sound speed from the liquid
  catalog (1482 m/s for fresh water, 1530 for seawater)
* `p_inf_ref = ambient.p_inf` — the user's chosen ambient

This means **the bubble-wall sound speed during collapse already
depends on local pressure** — when `p_L` spikes to GPa during
collapse, `tait_sound_speed` returns elevated `C` and the
Keller-Miksis radiation term gets the right damping. ✓

### Modelling gap (worth knowing)

The far-field reference pair `(c0, p_inf_ref)` is mismatched: `c0` is
the speed at 1 atm even when `p_inf_ref = 10 MPa`. So when you crank
the slider to 1 km depth, the simulator integrates Tait enthalpy from
10 MPa to whatever local pressure, but the *baseline* `c0` is still
the surface value. The actual sound speed at 10 MPa should be ~1660
m/s, not 1482.

Concrete consequences for depth sweeps:
* Mach number `Rdot/c0` is overestimated by the ratio of true to
  baseline `c` — at 1 km depth that's ~12 % (using 1482 instead of
  1660). The shape-stability and parametric-instability indices are
  therefore slightly pessimistic.
* Far-field radiation damping (`Rdot/c` in the KM denominator) is
  similarly overestimated; collapses look slightly more dissipative
  than reality.
* These both go the same direction — the deep-ocean simulation is
  conservative. T_peak / flash photon estimates should only be
  *bigger* in reality than what the simulator returns.

The fix is small: have `Scenario._compose_simulation_config` derive
`liquid.c` from `liquid.c_surface` plus the Tait correction at the
selected `p_∞`:

```python
# Pseudocode for the patch
c_at_pinf = sqrt(c_surface² + (n-1) * H(p_atm → p_inf))
```

Doesn't break v1 because v1 uses 1 atm everywhere — `c_at_pinf =
c_surface` whenever `p_inf = 1 atm`. Tracked as Q4 below.

## 6. Useful patterns for sweeping

For the user's interest in finding scaling laws across depth:

* **Sound speed scales weakly with pressure**: `c(p_∞) / c(1 atm)
  ≈ ((p_∞ + B) / (p_atm + B))^(1/(2n))` — for water (`B ≈ 296 MPa`,
  `n = 7`), going from 1 atm to 100 MPa raises `c` by ~13 %, not the
  10× the bulk modulus suggests. Most of the bulk-modulus increase
  is offset by density rise.
* **Minnaert frequency scales with `√p_∞`** (already correct in the
  simulator via `bubble_dynamics.minnaert_frequency`, which uses
  `ambient.p_inf` directly): going from surface to 1 km
  multiplies the natural bubble frequency by `√(10 MPa / 0.1 MPa) =
  10×`. The drive frequency `drive.f` and chamber resonance need to
  scale together if you want to keep the bubble on resonance during
  a depth sweep.
* **Mach-number proxies should drop with depth** once `c0` is
  corrected — current sweeps will show the regime classifier
  flipping to "marginal" earlier than it should at depth, until Q4
  is fixed.

## Open questions

* **Q4** (this dossier): wire `liquid.c` to scale with `ambient.p_inf`
  via the Tait-derived `c(p)`; small patch in `_compose_simulation_
  config` or in `liquids.py` so v1 behaviour at 1 atm is unchanged.
* **Q5**: add the Mackenzie equation to `liquids.py` as a separate
  helper for seawater so the UI's "Liquid: seawater" path can show
  sound speed as a function of depth in the headline panel — pure
  diagnostic, not used in the ODE integration.
* **Q6**: add a depth slider that automatically computes
  `p_inf = p_atm + ρ_seawater · g · z` plus updates `liquid.c` and
  `liquid.rho` consistently. Cleaner UX than asking the user to
  juggle log-pressure values mentally; also self-documents the
  "you are at 1 km" framing.

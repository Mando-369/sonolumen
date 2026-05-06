# §18 — Pressure ↔ temperature ↔ salinity coupling in water

Companion to §16 (pressure regimes) and §17 (sound speed). The user
asked three deep questions:

1. How do temperature and salinity affect pressure / compressibility?
2. Does compressing water heat it up?
3. What happens to the famous 4 °C density anomaly under pressure?

This note answers each, then ties it back to what cavplasma actually
models and where the current EOS stops being faithful.

## TL;DR

| Effect | Magnitude | cavplasma response |
|---|---|---|
| Adiabatic compression heating (20 °C surface → 1 km depth) | +0.15 K | not modelled (bulk liquid T fixed) |
| Same to Mariana Trench depth (~110 MPa) | +1.6 K | not modelled |
| Compression at 0 °C → **cools** water | -0.04 K/MPa | not modelled |
| Salinity shift of T_md (per ppt salt) | -0.21 K | not modelled |
| Pressure shift of T_md (per MPa) | -0.21 K | not modelled |
| **T_md disappears entirely** | above ~27 MPa | not modelled |
| Ice Ih melting point depression | -74 mK/MPa near 1 atm; **-22 °C at 209 MPa** | not modelled |
| Freezing-induced pressure (rigid container) | up to ~180 MPa before Ice III takes over | not modelled |

For SBSL near room T and 1 atm, none of these matter. For the
deep-ocean / cold-water / high-salinity sweeps the user is hunting
for patterns in, several do — flagged at the end as Q7–Q10.

---

## 1. Does pressure heat water up? (Adiabatic compression)

For an isentropic compression:

```
(∂T / ∂p)_S  =  α T / (ρ · c_p)
```

where `α` is the volumetric thermal expansion coefficient. The sign
is the interesting part — water's `α` is *negative* below 4 °C, so
**compressing cold water cools it**, the opposite of every other
common fluid.

Computed from tabulated property data:

| T (°C) | α (1/K) | (∂T/∂p)_S | ΔT for 0 → 100 MPa |
|---|---|---|---|
| 0 | -68 × 10⁻⁶ | **-4.4 mK/MPa** | **-0.44 K (cooling)** |
| 4 | 0 | 0 | 0 (anomaly point) |
| 10 | +88 × 10⁻⁶ | +5.9 mK/MPa | +0.59 K |
| 20 | +207 × 10⁻⁶ | +14.5 mK/MPa | +1.45 K |
| 50 | +461 × 10⁻⁶ | +36.1 mK/MPa | +3.6 K |

So:
* At room T, going from sea surface to 1 km depth (10 MPa) heats the
  water by ~0.15 K. To Mariana (~110 MPa) heats by ~1.6 K. Real
  thermometers measure this — it's why the deep abyss is slightly
  warmer than the strict adiabatic-cooling prediction would say.
* At 0 °C (e.g. the bottom of an ice-covered Antarctic polynya),
  pressure-driven compression *cools* the water. This is one of the
  drivers of bottom-water formation: cold dense water sinks, gets
  slightly colder by adiabatic compression, gets even denser, sinks
  further. A positive feedback loop that helps drive the global
  thermohaline circulation.

For *very fast* adiabatic compression — like the 100-ns bubble
collapse in cavplasma — the gas inside heats by orders of magnitude
(thousands of K). That's already modelled by the Toegel reduced-ODE
in `bubble_dynamics.py`. The bulk liquid heating is the *outside*
effect, which the simulator currently ignores (Q7).

## 2. Salinity — what salt actually changes

Salt (NaCl + Mg, K, Ca sulphates) does three things to water:

| Property | Pure water (1 atm, 20 °C) | Seawater 35 ppt | Direction |
|---|---|---|---|
| Density ρ | 998.2 kg/m³ | 1025 kg/m³ | + 2.7 % |
| Sound speed c | 1482 m/s | 1521 m/s | + 2.6 % |
| Bulk modulus K | 2.20 GPa | 2.36 GPa | + 7 % |
| Compressibility κ | 4.55 × 10⁻¹⁰ /Pa | 4.24 × 10⁻¹⁰ /Pa | -7 % (less compressible) |
| Freezing point | 0 °C | -1.9 °C | -1.9 K |
| Heat capacity c_p | 4182 J/kg·K | 3993 J/kg·K | -4.5 % |

Salt water is denser, stiffer (higher bulk modulus), less
compressible, and freezes lower. The reason is mostly geometric —
ions disrupt the open hydrogen-bonded structure of water, packing
molecules slightly closer.

For cavplasma, the `liquids.preset("seawater")` already encodes the
correct ρ, c, μ at surface conditions (`liquids.py` line 19).
What's *not* encoded: how those scalars change as you sweep p_∞.
Same gap as §17 Q4.

## 3. The 4 °C density anomaly — and what kills it

Pure water at 1 atm has **maximum density at +3.98 °C**, not at 0 °C.
It's the reason ice floats, lakes freeze top-down, and freshwater fish
survive winters.

The anomaly comes from a competition: as you cool water from above
20 °C, two things happen at once:
1. Normal thermal contraction (molecules vibrate less → pack closer)
2. Hydrogen-bond ordering (molecules align tetrahedrally → take up
   *more* space, like a partial ice lattice)

Above 4 °C, (1) wins → density rises as you cool. Below 4 °C, (2)
wins → density *falls* as you cool. The crossover is the maximum.

**Both salt and pressure kill it.**

| Condition | T_md (°C) |
|---|---|
| Pure water, 1 atm | +3.98 |
| Pure water, 10 MPa (~1 km) | +1.9 |
| Pure water, 20 MPa (~2 km) | 0.0 |
| Pure water, 27 MPa (~2.7 km) | meets freezing — anomaly **disappears** |
| Pure water, 100 MPa | (no max; ρ monotone in T) |
| Seawater 35 ppt, 1 atm | -3.4 (below freezing of -1.9 → buried) |
| Seawater 35 ppt, 10 MPa | -5.5 (deeply buried) |

The pressure shift is `dT_md/dp ≈ -0.21 K/MPa`. The salinity shift
is `dT_md/dS ≈ -0.21 K/ppt` (Caldwell 1978). Two coincidentally
equal slopes; either one moves the maximum down, both together push
it well below freezing.

**Two consequences worth understanding:**

1. **Oceans don't freeze top-down.** At 35 ppt salinity, T_md is
   already below the freezing point at the surface, so cold ocean
   water keeps getting denser as it cools right up to the freezing
   line. No 4 °C density-max trap, no thermal stratification flip.
   Sea ice forms by surface freezing of *less salty* water, then
   floats because it's less dense than the salty brine it leaves
   behind.

2. **Below ~3 km depth in fresh water (or any depth in the ocean),
   the anomaly doesn't exist.** Density just rises monotonically as
   you cool. So in deep-cavitation experiments the simulator's
   constant-density-with-T assumption is *more* defensible at depth
   than it is at the surface — pressure has done you a favour.

## 4. The melting curve — pressure delays freezing of normal ice

The Clausius-Clapeyron equation for the Ice Ih → liquid line:

```
dT_m / dp = T · ΔV / L_fusion
```

with `ΔV = -90.7 cm³/kg` (liquid is 9.1 % denser than ice — that's
the "ice floats" part), `L_fusion = 333.55 kJ/kg`, and `T = 273.15 K`,
gives **-74 mK/MPa** at 1 atm. The slope steepens as you climb the
curve:

| p (MPa) | T_m (Ice Ih, °C) | Slope dT/dp (mK/MPa) |
|---|---|---|
| 0 | 0.00 | -74 |
| 10 | -0.7 | ~-75 |
| 50 | -3.6 | ~-80 |
| 100 | -8.8 | ~-95 |
| 150 | -14.3 | ~-115 |
| 200 | -19.2 | ~-150 |
| 209 | -22.0 | (slope diverges; triple point Ih/III/liquid) |

So pressure **delays** freezing of the familiar low-pressure ice
form. This is also anomalous — for almost every other substance,
high pressure stabilises the solid phase (squeezing molecules into
the densest packing). Water is unusual because the low-pressure
ice (Ih) is *less* dense than the liquid; pressing actively
disfavours it.

**Above 209 MPa, Ice III takes over.** Ice III *is* denser than
liquid water, so its melting line has the conventional positive
slope. Same for Ice V (>335 MPa), Ice VI (>619 MPa), and so on.
The Ice Ih anomaly lives only in the ~ -22 °C to 0 °C wedge below
209 MPa.

> **Two consequences worth knowing:**
> 1. **Glaciers flow at their base.** A 2 km ice sheet (~18 MPa
>    base pressure) lowers its melting point by ~1.3 K; a thin film
>    of liquid water lubricates the ice-rock interface, and the
>    glacier slides.
> 2. **Pipes burst from the inside out.** Water in a sealed pipe
>    cooling through 0 °C tries to expand 9 % to become Ice Ih.
>    With nowhere to go, pressure builds in the unfrozen pocket
>    until either the pipe yields (~10 MPa for copper) or pressure
>    reaches ~180 MPa, at which point Ice III nucleates instead and
>    *contracts*. Most pipes give up well before the Ice III line.

## 5. How this maps onto cavplasma

What's currently modelled (correctly):

* Bubble-interior compression heating during collapse (Toegel
  reduced ODE in `bubble_dynamics.py`)
* Local liquid sound speed at the bubble wall via Tait enthalpy
  (handles GPa transients)
* Liquid density `ρ`, sound speed `c`, viscosity `μ`, vapour
  pressure `p_v`, surface tension `σ` from `liquids.py` —
  catalogued at standard conditions (1 atm, 20 °C)

What's *not* modelled:

* Bulk-liquid temperature change due to ambient pressure shift —
  `ambient.T_inf` is held constant. At depth, the actual liquid is
  ~1 K warmer than user-specified for room T and p_∞ ~ 100 MPa.
* Density shift `ρ(T, p)` — pure thermal expansion. For sweeping
  T over 0–50 °C this is a 5 % effect; for sweeping p_∞ to 100 MPa
  it's a 4 % effect. Not separately tracked; flat ρ is used.
* Sound speed `c(T, p)` baseline (Q4 from §17 — same gap).
* Salt-corrected `ρ`, `c`, `μ`, `c_p`, freezing point. The
  `seawater` preset has the right surface values but doesn't
  recompute when T or p_∞ moves.
* The 4 °C density anomaly. The Tait EOS is monotone in p; it has
  no temperature term at all. So if the user sets `T_inf = 4 °C`
  and sweeps `p_∞`, the simulator will not show the density
  inversion — which doesn't exist above ~27 MPa anyway, but does
  exist near the surface.
* Latent heat of vaporisation around the bubble wall when collapse
  drives the wall above 100 °C — this is partly handled via the
  Toegel water-vapour cap, but not as full latent-heat balance.
* Phase transitions of the liquid itself (Ice Ih, Ice III, ...).
  Tait extrapolation past 1 GPa is unphysical. Already noted in §16.

## Open questions

* **Q7**: implement adiabatic-compression heating of the bulk
  liquid — small correction to `ambient.T_inf` based on p_∞ and a
  representative `α(T_inf)`. ~10-line patch in
  `_compose_simulation_config`. Keeps bulk T realistic when the
  user sweeps p_∞ over orders of magnitude.
* **Q8**: replace the scalar `liquid.rho` with `liquid.rho_at(T, p)`
  derived from the Tait EOS plus a thermal-expansion polynomial.
  Density at depth is currently flat; this would close the gap at
  the few-percent level.
* **Q9**: implement the Mackenzie correction for sound speed in the
  seawater path (`liquid.c_at(T, S, p)`); §17 Q4/Q5 already track
  this.
* **Q10**: warn the user if `(T_inf, p_∞)` falls inside an ice
  phase region (Ih, III, V, VI, VII). Pure check — the simulator
  shouldn't refuse to run, but the validate() call should add an
  `'liquid_phase'` category warning so the regime card flags
  "you're below the Ice III line; the Tait EOS extrapolation is
  not physical here."

These are nice-to-haves, not blockers — none of them flip the sign
of the depth-sweep patterns the user is hunting. They'd just shave
the ~5 % systematic errors from the asymptotic limits.

## References

* Caldwell, D.R. *Deep-Sea Research* **25**, 175 (1978) — T_md vs.
  salinity and pressure
* Wagner, W. and Pruß, A. *J. Phys. Chem. Ref. Data* **31**, 387
  (2002) — IAPWS-95 reference equation for pure water
* Bridgman, P.W. *Proc. Am. Acad. Arts Sci.* **47**, 441 (1912) —
  high-pressure ice phase boundaries
* Mackenzie, K.V. *J. Acoust. Soc. Am.* **70**, 807 (1981) — sound
  speed empirical formula
* Wagner, W. and Saul, A. *J. Phys. Chem. Ref. Data* **23**, 515
  (1994) — Ice Ih melting and sublimation curves

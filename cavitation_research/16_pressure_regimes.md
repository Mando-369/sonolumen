# §16 — Pressure regimes: from waterjets to black holes

A reference for sweeping `p_∞` across many orders of magnitude in
`sonolumen`. Originally drafted to answer "what's the maximum pressure
inside a 1-meter sphere?" — useful framing for choosing the
`p_∞` slider value (`sonolumen/ui/layout.py:_ambient_controls`,
range 30 kPa → 100 MPa) and for understanding when the
simulator's water EOS stops being valid.

## TL;DR

| Regime | Pressure | What happens | sonolumen valid? |
|---|---|---|---|
| Industrial waterjet | ~0.4 GPa (60 kpsi) | Steel cutting, abrasive blasting | ✓ |
| **sonolumen slider max** | **0.1 GPa (14.5 kpsi)** | **Bottom of bathyal ocean (~10 km)** | ✓ |
| Plastic collapse, maraging-steel sphere | 1.4–2.8 GPa | Sphere yields, "flows" | partial |
| Ice VI threshold (room T) | ~1 GPa | Liquid → solid Ice VI | ✗ EOS limit |
| Ice VII threshold (room T) | ~2.1 GPa | Solid hot ice | ✗ |
| Ice X (symmetric H-bond) | ~70 GPa | Proton-symmetric crystal | ✗ |
| Diamond-anvil cell record | 770 GPa | Superionic solid (O lattice + mobile H⁺) | ✗ |
| 1-m sphere → black hole | ~3.4 × 10²⁶ kg | Schwarzschild radius reached | ✗ |

The sonolumen slider stops at 0.1 GPa, an order of magnitude below
where water stops being a fluid. That keeps the Tait EOS
(`sonolumen/liquids.py`) valid across the full sweep range. Anything
above 1 GPa needs a different liquid model — the simulator will run
but the answers stop being physical.

---

## 1. Engineering limit — strongest sphere you can build

For a thick-walled sphere of inner radius `a` and outer radius `b`
under internal pressure, full-section plastic collapse (Tresca yield
criterion, perfectly-plastic solid) is:

```
P_collapse = 2 · σ_y · ln(b/a)
```

> **Correction note:** an earlier version of this dossier dropped the
> leading factor of 2. The standard plasticity result (Hill, *The
> Mathematical Theory of Plasticity*, ch. 5) and Lamé thick-sphere
> elastic-plastic analysis both give `2 σ_y ln(b/a)`. Without the 2 you
> get the elastic limit *at the inner wall only*, which is conservative
> by a factor of 2 — that's the source of confusion in popular
> write-ups.

For a 1-m **inner** diameter, 0.5-m **wall thickness** (so `a = 0.5 m`,
`b = 1.0 m`, `b/a = 2`):

| Material | σ_y (yield) | P_collapse (Tresca) | Bar | psi |
|---|---|---|---|---|
| Mild steel (4140) | 0.7 GPa | 0.97 GPa | 9,700 | 141 k |
| Maraging steel (300-grade) | 2.0 GPa | 2.77 GPa | 27,700 | 402 k |
| Ti-6Al-4V (annealed) | 0.88 GPa | 1.22 GPa | 12,200 | 177 k |
| Ti-6Al-4V (aged ELI) | 1.1 GPa | 1.52 GPa | 15,200 | 221 k |
| Inconel 718 | 1.1 GPa | 1.52 GPa | 15,200 | 221 k |

The "rule-of-thumb" 15,000–20,000 bar (217–290 kpsi) you'll see quoted
for industrial-grade thick spheres corresponds to a **safety-factored**
value at ~50 % of `P_collapse` for maraging or Ti — that's the regime
real pressure vessels operate in (ASME BPVC, plus fatigue + fracture
toughness derating). Run them at the bare Tresca limit and the sphere
yields; cycle them anywhere near it and they fail by fatigue cracking
in <10⁴ cycles.

For sonolumen, this matters when validating the chamber pick: §13's
wall-stress observer (`StressProbeObserver`) reports peak wall pressure
during collapse; a borosilicate sphere maxes out around ~50 MPa
(steady) and survives only if collapse spikes stay short. Once
ambient `p_∞` itself exceeds ~10 % of the collapse limit, the steady
hoop stress alone eats the chamber's safety margin and the §13 caveat
should fire (it doesn't yet — see open question Q1 below).

---

## 2. Phase-change limit — when water stops being a liquid

Even a perfect-strength sphere can't push water past a phase
transition without changing what's inside. Room-temperature
boundaries (from the IAPWS-95 phase diagram and the high-pressure
experimental literature):

| Phase | P (room T) | Notes |
|---|---|---|
| Liquid water | < 1 GPa | Tait EOS valid; sonolumen operates here |
| Ice VI | 0.6–2.2 GPa | Tetragonal, denser than liquid |
| Ice VII | 2.1–60 GPa | Cubic, "hot ice" — solid at +100 °C |
| Ice X | 60–~150 GPa | Symmetric O–H–O bonds (no longer molecular) |
| Superionic ice | >150 GPa, T > ~2000 K | O lattice + diffusing H⁺ |

The 1 GPa Ice VI / 2.1 GPa Ice VII / 70 GPa Ice X numbers are
correct to about ±20 %. Above 1 GPa your "water pump" is a mechanical
ram crushing solid crystal, not pumping liquid — none of the
cavitation physics in `sonolumen/bubble_dynamics.py` applies, because
there's no longer a free surface for bubble dynamics to live on.

> **Note on terminology:** the original write-up's summary table had
> "metallic super-conductor" at ~10⁸ psi. That's two phenomena
> conflated — superionic ice (proton-conducting solid, ~10²–10³ GPa) is
> *ionic* conductance, not a Cooper-pair superconductor. Metallic
> water is a separate prediction at ~10³ GPa, and metallic
> *hydrogen* (totally different substance) at >400 GPa. Corrected in
> the table above.

---

## 3. Material limit — diamond anvil cells

Diamond anvil cells (DACs) compress sub-millimetre samples between
two diamond tips. The peak pressure scales as 1/diamond-tip-area, so
the practical record climbs as fabrication shrinks the tip.

* Standard DAC, 300-µm culet → 100–300 GPa
* Beveled DAC, 50-µm culet → 400 GPa
* Double-stage / nano-diamond DAC → **770 GPa** (Dubrovinskaia et al.,
  *Sci. Adv.* 2016) ≈ **111.7 million psi**, verified.
* Toroidal DAC → ~1 TPa (recent claims, not yet uncontested)

770 GPa puts the sample into the superionic regime *if the
temperature is high enough* (typically >2000 K, achieved in DACs by
laser heating). Below that temperature you get Ice X — still solid,
still molecular at the bond level, but with the proton sitting
symmetrically between two oxygens.

These pressures are 10⁴ × larger than anything sonolumen's water EOS
is calibrated for. The static ambient pressure inside the bubble at
collapse can transiently spike into this regime (~GPa peak gas
pressure in a strong SBSL collapse, by `bubble_dynamics.py` output),
but it lasts ~ns and the gas is the high-pressure phase, not the
liquid.

---

## 4. Theoretical limit — black hole

Schwarzschild radius: `R_s = 2 G M / c²`. Solving for the mass that
turns a 1-m sphere into a black hole:

```
M = R_s · c² / (2 G)
```

with `G = 6.674e-11 m³/(kg·s²)`, `c = 2.998e8 m/s`.

| Sphere size | Required mass | Earth masses |
|---|---|---|
| `R_s = 0.5 m` (1 m diameter) | 3.37 × 10²⁶ kg | **56.4** |
| `R_s = 1.0 m` (1 m radius)   | 6.73 × 10²⁶ kg | **112.7** |

> **Correction note:** the original write-up said "0.00033 Earth
> masses" — that's wrong by ~5 orders of magnitude. 0.00033 M_⊕ ≈
> 2 × 10²¹ kg has a Schwarzschild radius of ~3 µm, not 1 m. The
> simplest way to remember the scale: a 1-m black hole needs roughly
> Saturn's mass squeezed into a basketball.

For context: 56 Earth masses is about 1/6 of Jupiter, or about
1/30,000 of the Sun. The pressure required to compress that into a
1-m sphere is, indeed, "infinite" in any practical sense — long
before that point the matter degenerates through:

1. Electron degeneracy (white-dwarf state) at ~10⁹ Pa (gas) /
   ~10²² Pa (degenerate electron pressure for ~10⁶ kg/m³)
2. Neutron degeneracy (neutron-star state) at ~10³⁴ Pa
3. Schwarzschild collapse at the limit above

None of which sonolumen will ever simulate. The relevant takeaway is
just: **pressure has gravitating mass-energy** (T_μν in general
relativity), so even a notional "infinite-strength" container has a
finite limit set by GR.

---

## How to use this in sonolumen

* **Slider range** (`p_∞` log scale, 30 kPa → 100 MPa) covers
  vacuum experiments through Mariana Trench depths, all in the
  liquid-water regime where the Tait EOS is valid.
* **Above ~1 GPa**, swap the liquid (`liquids.py`) for an Ice VI/VII
  EOS — not implemented; would be a research extension if you ever
  want to model "deep-Earth" cavitation in mantle inclusions or
  diamond-anvil cell experiments.
* **§13 wall-stress observer** uses the wall pressure during collapse
  to compute fatigue lifetime; the chamber materials catalogued in
  `sonolumen/material/materials.py` all have `sigma_UTS` ≤ 2 GPa, so
  any peak transient above ~1 GPa instantly fails the chamber
  regardless of cycle count.
* **Pattern-finding sweeps** (the user's question that started this
  note): pistol-shrimp T_peak scales roughly as p_∞^0.3 across the
  full slider range, flash FWHM as p_∞^-0.6. SBSL has additional
  drive-amplitude coupling — log-log sweep both at fixed depth and
  fixed drive to separate the two power laws.

## Open questions

* **Q1:** §13 caveat for static-ambient stress alone is not yet
  wired — only collapse-spike stress is checked. Add a simple
  `if p_inf > 0.1 * sigma_UTS` warning in `material/wall_loads.py`.
* **Q2:** Beyond 100 MPa, the Tait EOS extrapolates but isn't
  calibrated. Quick check against IAPWS-95 reference data for
  density and sound speed up to 1 GPa would tell us how big the
  modelling error is at the edges.
* **Q3:** Hydrostatic depth gradient over chamber height
  (`Δp = ρ g h`): for a 10-cm chamber at 1 km depth, Δp ≈ 1 kPa over
  10 MPa average — totally negligible. Note this in the §12 spec
  so we don't accidentally add a depth-gradient model later when
  it's irrelevant.

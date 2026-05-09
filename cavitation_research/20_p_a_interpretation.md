# §20 — What does `P_A` mean in sonolumen?

This note answers a recurring user confusion: "I got a 'stable_spherical'
hit but the off-resonance R6 warning is still firing — is the
simulation result real or not?"

## TL;DR

sonolumen's `drive.P_A` is **the at-bubble pressure amplitude** (the
pressure the bubble actually feels), not the transducer's output.
The simulator assumes you have a transducer powerful enough to
deliver `P_A` at the bubble *no matter the frequency*. So the
simulation result is real **for that effective P_A** — but R6's
off-resonance warning tells you whether that effective P_A is
achievable in a real chamber.

For an off-resonance drive, the chamber Q-response attenuates the
transducer output by `√(1 + (2Q · Δf / f)²)`. So if the simulator
reports stable SBSL at `P_A = 2 atm` driving 10 kHz off-resonance
(693× attenuation), your real-world transducer would need to output
**1386 atm ≈ 140 MPa** for the bubble to actually feel 2 atm. That's
beyond any practical piezo.

The headline panel now shows this attenuation factor + required
transducer P_A whenever the drive is outside every chamber mode's
bandwidth, so users can spot "stable in simulator, infeasible in
hardware" hits at a glance.

## Two interpretations of `P_A`

There are two consistent ways to define `P_A` in a bubble-dynamics
solver:

**(A) Transducer output** — `P_A` is the source-side pressure
amplitude. The chamber response (Q-amplification on resonance,
Q-attenuation off-resonance) and the spatial standing-wave shape
both modify it before it reaches the bubble.

**(B) At-bubble pressure** — `P_A` is the effective pressure the
bubble feels at its position, after the chamber has done whatever
it does. The user is responsible for engineering the transducer +
chamber to deliver this.

sonolumen uses interpretation **(B)**. This was a deliberate
modelling choice — it lets users specify "I want the bubble to feel
1.32 atm" without needing to know the transducer-chamber transfer
function. The standing-wave-factor in `field.py` handles the spatial
part (centre vs off-centre), but the *frequency-response* part is
implicitly assumed to be 1.0 — i.e., your transducer compensates.

## Why R6 fires anyway

The §12 `validate()` off-resonance check enumerates the chamber's
geometric modes (sphere: `f_n = n·c/(2R)`, etc.) and tests whether
the drive is inside any of their Q-bandwidths. If not, R6 reports:

* The closest mode and its bandwidth
* The frequency offset Δf
* **The Q-attenuation factor** = `√(1 + (2Q·Δf/f)²)`
* **The required transducer P_A** = stated `P_A` × attenuation
* A feasibility comment when required P_A exceeds 50 atm
  ("exceeds practical piezo capacity")

So R6 is not saying *"the simulation result is wrong"*. It's saying
*"to deliver the at-bubble P_A you specified, your transducer needs
to be Q-times louder than the value you set — check feasibility."*

The simulator's reported regime is consistent with the at-bubble
P_A. The R6 warning is consistent with the transducer-output
interpretation. Both are right, both for different things.

## When the geometric Q-bandwidth is too strict

The pure-fluid radial eigenmodes (sphere: `f_n = n·c/(2R)`) come
from solving the wave equation with rigid wall boundary conditions
and no transducer coupling. Real SBSL chambers diverge from this in
several ways:

1. **Transducer-coupled mode shapes.** A piezo ring glued to the
   sphere wall imposes a forced mode shape that's a hybrid of the
   pure radial mode and the wall vibration pattern. The effective
   resonance shifts a few percent.
2. **Structural compliance.** A glass sphere isn't infinitely rigid;
   it has its own breathing mode. Coupling between the fluid mode
   and the wall mode shifts both.
3. **Multi-mode operation.** Most real SBSL setups don't use the
   geometric fundamental — they use the n=2 or n=3 radial mode,
   which has higher Q-bandwidth and is easier to tune.
4. **Lower effective Q.** The published Q values for SBSL chambers
   (~1000–10000) usually refer to the chamber's main loaded
   resonance — but the *unloaded* fluid Q can be much higher. R6
   uses `chamber.Q` as an effective number, which the user should
   set conservatively.

The SBSL canonical preset (26.5 kHz drive, 5 cm sphere, fluid mode
n=2 at 30.6 kHz) is technically off-resonance against the geometric
n=2 by Δf = 4.1 kHz at Q=1000 → attenuation 267×. R6 fires for it
too. In a real experiment this preset works because of the points
above; in sonolumen's geometric model, R6 is technically correct
about the mismatch and the user should know.

## When R6 is loud vs quiet

The R6 message tags feasibility based on the required transducer P_A:

| Required transducer P_A | R6 tone |
|---|---|
| < 10 atm | "warning" — borderline, your transducer might handle it |
| 10–50 atm | "feasible only with high-power transducer" |
| > 50 atm | "exceeds practical piezo capacity" |

So a 1.3 atm at-bubble drive at 5 % off-mode (atten ~5×) requires a
6.5 atm transducer — fine. A 2 atm at-bubble drive at 5 kHz off the
nearest mode (atten ~700×) requires a 1400 atm transducer —
impossible.

## Why we don't auto-attenuate `P_A`

Tempting fix: just multiply `P_A` by `1/atten` automatically when
the drive is off-resonance, so the simulator sees the real
at-bubble pressure. This would break SBSL canonical (which is
off-resonance against the geometric model but works in real
chambers), and would conflate two distinct sources of error
(modelling assumptions in the geometric eigenmode vs. user's
choice of transducer drive level).

Better: keep `P_A` as the at-bubble pressure (the explicit user
contract), and surface the chamber's Q-attenuation as a separate
informational quantity so the user can check feasibility.

## Open questions

* **Q13**: a `chamber.transducer_coupling: float` field that the
  user can set to bypass R6's geometric Q-attenuation calculation
  for cases where the real chamber supports modes that the
  geometric model misses. Defaults to `1.0` (use geometric model).
* **Q14**: a "transducer-realistic" toggle in the UI that, when
  enabled, applies the Q-attenuation to `P_A` directly — converting
  sonolumen to interpretation (A). Useful for designing real
  experiments rather than exploring parameter space. Off by default.
* **Q15**: if the user specifies `transducer.max_acoustic_power_W`
  and validate() detects an off-resonance drive, also compute the
  transducer's actual maximum at-bubble P_A given the Q-attenuation
  and warn loudly if the user's stated P_A would require exceeding
  the transducer's rated capacity.

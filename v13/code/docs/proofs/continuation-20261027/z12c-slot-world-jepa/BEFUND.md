# WP-Z12c BEFUND: slot-wise World-JEPA on real file actions

Verdict: **Z12C_SLOT_WORLD_JEPA_PASS** (prereg `PREREG.md`, committed and pushed 205a0c4 before the run; fresh seeds
201, 202, 203). Data: `v13/bench-results/z12c-slot-world-jepa-20261027/z12c.json`.

| criterion | result | threshold | |
|---|---|---|---|
| C1 counterfactual retrieval, covered | .910 pooled (.918 / .900 / .913) | >= .80, each >= .70 | PASS |
| C2 held-out (op, slot) combinations | .950 pooled (.884 / .975 / .992); controls .07 | >= .70 and control + .30 | PASS |
| C3 controls (covered) | no action .192, shuffled .195 | <= .40, gap >= .30 | PASS |
| C4 no collapse | effective rank 6.1-7.0 of 8, min std 1.03 | >= 3, >= .05 | PASS |
| C5 confidence vs error | Spearman -.589 (all queries) | <= -.30 | PASS |
| C6 attribution JEPA | own-only SELF .929, world-only WORLD 1.00, nothing-happened SELF .942 | .90 / .90 / .80 | PASS |
| C7 action-free control | balanced .520 vs JEPA .965 | control <= JEPA - .20 | PASS |

Same data, Z12b monolithic model (information only): covered .753, held-out .143.

## What it shows
- The Z12b failure was the design, not the idea: with one shared encoder/predictor per slot and the action given as
  "which operation happens to this slot", operations compose with slots they were never taken on (.95 vs .14 for the
  monolithic model on the same data), and covered retrieval rises from .75 to .91.
- Untouched slots share one input, so "nothing happened" is predicted almost exactly (untouched threshold ~.003):
  false alarms when nothing happened drop from 38 % (Z12b) to 6 %, world changes are still always caught.
- With no action information anywhere, the control can only say "something changed", so it calls almost every own
  action WORLD_INVOLVED (own-only SELF .98 only because it also misses world changes: world-only WORLD .05); balanced
  .52 = chance. The action is what makes attribution work, which Z12b's control design could not show.
- Confidence now includes the model's own typical error per operation; it ranks errors clearly (-.59).

## Weak spots (honest)
- Seed 201 alone: own-only SELF .849 (< .90; the criterion is pooled), held-out .884. The 99th-percentile thresholds come
  from ~350 clean validation rows, so per-operation thresholds are noisy.
- Labels: 11-25 % of queries are SIMULATION_UNCERTAIN; no criterion was set on the labels themselves.
- Given slot split (objects are known), no slot interactions, synthetic content, cloud machine only. Not wired into the
  runtime; Z12a exact hash prediction stays the runtime attribution path until a phone run and a wiring package exist.

## Next
Phone run (NumPy only, ~1 min fit per model on the cloud CPU); a world with interacting objects (e.g. move/copy between
slots) needs message passing between slot latents; wiring as SHADOW observer next to the Z12a corollary.

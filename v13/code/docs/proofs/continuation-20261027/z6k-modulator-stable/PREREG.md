# WP-Z6k PREREG: per-sample typed modulator with a stable measuring instrument (G-MODULATOR-SPECIFICITY-001)

Written 2026-10-27 after the Z6j verdict and its exploratory learner diagnosis, before embedding pool seed 53 and before any
run on seeds 231-250. Script `scripts/z6k_modulator_stable.py`.

## Why
Z6j (`Z6J_SAMPLE_MODULATOR_FAIL`): the single-pass learner's last iterate swings between .63 and .98 even with clean labels,
so a one-snapshot accuracy cannot separate arms (Z6f has the same instrument). Nothing else changes: same arms (incl.
`v13_sample` = `neuromod.sample_factor`), label sources, mixes, shift, learner, step size and encoder as Z6j.

## Changes to the instrument only
- Metric: mean held-out accuracy over the last four checkpoints (events 450/500/550/600, all after the shift).
- 20 seeds (231-250), fresh pool seed 53. Seed-win thresholds become >= 15/20 (instead of 4/5).
- Reported ceiling arm `clean_oracle` (all labels true, weight 1). Last-iterate numbers are reported, not judged.

## Criteria (all for `Z6K_SAMPLE_MODULATOR_PASS`), same thresholds as Z6j
- M1 self_heavy: v13_sample >= each of scalar_sample, human_sample, outcome_sample + .03, higher in >= 15/20 seeds.
- M2 self_heavy: v13_sample >= gradient_only_matched + .03, higher in >= 15/20 seeds.
- M3 balanced: v13_sample not more than .02 below any per-sample control or gradient_only_matched.
- M4 v13_sample >= .70 in both mixes.
- M5 v13_sample >= v13 (path gate) + .03 in both mixes, higher in >= 15/20 seeds.
- M1-M3 pass but M4 or M5 fails: `Z6K_SPECIFIC_BUT_WEAK`; else `Z6K_SAMPLE_MODULATOR_FAIL`.
This is the last attempt on this design: if it fails, the gate stays red and the next step is a different learner, not
another reading of the same data. No default change; runtime learners do not use per-sample weights yet.
Claim limit: simulated label sources and mix, one learner kind, cloud.

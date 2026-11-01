# WP-Z6j BEFUND: typed modulator per sample (G-MODULATOR-SPECIFICITY-001)

Verdict: **Z6J_SAMPLE_MODULATOR_FAIL** (prereg `PREREG.md`, committed 7610c41 before embedding pool seed 47; seeds 211-215).
Data: `v13/bench-results/z6j-modulator-sample-20261027/z6j.json`.

Mean final accuracy on the held-out quarter (labels after the shift):

| arm | balanced | self_heavy |
|---|---|---|
| v13_sample (new, per sample) | **.568** | .540 |
| scalar_sample | .499 | .458 |
| human_sample | .491 | .378 |
| outcome_sample | .549 | **.556** |
| gradient_only | .566 | .404 |
| gradient_only_matched | .476 | .321 |
| v13 (path gate, Z6f) | .544 | .408 |
| v13_datamix | .419 | .574 |

- M1 FAIL (self_heavy: beats scalar +.08 and human +.16, but not outcome-only, −.016)
- M2 PASS (+.22 over same-budget gradient)
- M3 PASS (balanced: no loss against any control)
- M4 FAIL (.57/.54, needs .70)
- M5 FAIL (vs path gate: +.13 self_heavy, but only +.02 balanced)

## What it shows
- Per-sample typing goes in the right direction (best or near-best in both mixes, clearly better than scalar reward and
  the same-budget gradient), but it does not separate from "learn only from real outcomes".
- **Diagnosis (exploratory, after the verdict):** the measuring learner itself is unstable. With *clean* labels only, the same
  learner reaches .97 on some seeds but its last iterate jumps between .63 and .98 (seed 212: .91 → .90 → .96 → .63 over the
  last four checkpoints). Many arms land on identical values (.506, .475, .481): snapshots of a majority-class swing, not
  learned differences. So the Z6f note "the encoder is the bottleneck" is not supported: Needle features carry the route
  boundary; the single-pass, last-iterate learner with step .5 does not hold it. Differences of a few points between arms
  in Z6f and Z6j are inside this noise.

## Next
WP-Z6k: same comparison with a stable measuring instrument decided before the run (fresh pool, more seeds, accuracy averaged
over the last checkpoints instead of one last iterate). No default changed; runtime learners do not use per-sample weights yet.
Claim limit: simulated label sources and mix, one learner kind, cloud.

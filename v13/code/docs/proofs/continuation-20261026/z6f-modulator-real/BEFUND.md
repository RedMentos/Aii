# WP-Z6f BEFUND: typed modulators with the real encoder (G-MODULATOR-SPECIFICITY-001)

Verdict: **Z6F_MODULATOR_REAL_FAIL** (prereg `PREREG.md`, committed 15c3675 before embedding the real pool; seeds 201-205).
Data: `v13/bench-results/z6f-modulator-real-20261026/z6f.json`. Real Needle embeddings of 640 German questions, real
scaffold self-labels (accuracy .38), real Neuromod gate.

Mean final accuracy on the held-out quarter (new labels after the shift):

| arm | balanced | self_heavy |
|---|---|---|
| v13 (typed gate) | .384 | .286 |
| scalar_reward | .408 | .269 |
| human_only | .410 | .260 |
| outcome_only | .374 | .286 |
| gradient_only | .555 | .314 |
| gradient_only_matched | .430 | .253 |
| v13_datamix (reported) | **.646** | **.543** |

M1-M4 all FAIL: the typed gate does not beat scalar / human-only / outcome-only, not the same-budget gradient, loses
up to .17 to plain gradient in the balanced mix, and stays far below .70.

## What it shows
- The Neuromod gate sets one plasticity budget per path from the signals that recently reached it. In a path that
  mixes clean and wrong label sources it cannot tell the samples apart, so typing the channels changes almost nothing
  (budget .29-.35 either way). The synthetic 5/5 win in ablation99 came from paths that each had one dominant source.
- The per-sample data-mix guard (v13_datamix) is what actually helps (+.26 over the gate in both mixes): filtering by
  source beats scaling the learning rate.
- Absolute accuracy is low for every arm: 600 updates on Needle features do not reach the route boundary well (as in
  Z6b/Z6c, the encoder is the bottleneck).

## Next
Credit the modulator to the sample (source-typed per-sample weight) or route by source into separate paths before
claiming the gate; keep the data-mix guard on. Claim limit: simulated label sources and mix, one learner kind, cloud.

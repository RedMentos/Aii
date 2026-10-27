# WP-Z6k BEFUND: per-sample typed modulator, stable instrument (G-MODULATOR-SPECIFICITY-001)

Verdict: **Z6K_SAMPLE_MODULATOR_FAIL** (prereg `PREREG.md`, committed 9039028 before embedding pool seed 53; seeds 231-250).
Data: `v13/bench-results/z6k-modulator-stable-20261027/z6k.json`. Metric: mean held-out accuracy over the last four checkpoints.

| arm | balanced | self_heavy | v13_sample wins (self_heavy, of 20) |
|---|---|---|---|
| v13_sample (per sample) | .561 | **.524** | – |
| scalar_sample | **.570** | .407 | 18 |
| human_sample | .525 | .461 | 13 |
| outcome_sample | .511 | .486 | 11 |
| gradient_only_matched | .394 | .261 | 20 |
| v13 (path gate) | .406 | .311 | 19 (balanced 16) |
| v13_datamix | .499 | .470 | – |
| clean_oracle (ceiling) | .823 | .823 | – |

- M1 FAIL: better than every control on average (+.12 scalar, +.06 human, +.04 outcome), but only 13/20 and 11/20 seeds
  against human-only and outcome-only (needs 15/20).
- M2 PASS (+.26 over the same-budget gradient, 20/20).
- M3 PASS (balanced: −.009 vs scalar, inside −.02).
- M4 FAIL (.56/.52; the learner reaches .82 with clean labels).
- M5 PASS: **per sample beats the path gate** by +.16 (balanced, 16/20) and +.21 (self_heavy, 19/20).

## What it shows
- The Z6f diagnosis is confirmed with a stable instrument: crediting the modulator to the sample instead of the path is
  the right fix (+.16/+.21), and typed per-sample weights are clearly better than a scalar reward when wrong sources are
  frequent (self_heavy) and than plain gradient at the same budget.
- They are not yet clearly better than simply "only learn from humans" or "only learn from real outcomes": the typing
  keeps those two good sources but also gives a little weight to self labels (scaffold, 38 % right), which costs about as
  much as the extra data brings.
- Absolute level stays far below the clean-label ceiling (.52-.56 vs .82): with these label mixes the wrong labels still dominate.
- G-MODULATOR-SPECIFICITY-001 stays red. As preregistered, this design is not re-read again.

## Next
Runtime learners take one budget per job; a per-sample weight path (learning_worker sample weights from `sample_factor`)
would be the build step, with the self-label weight as the open question (§63 gives internal_crosscheck .2). No default changed.
Claim limit: simulated label sources and mix, one learner kind, cloud.

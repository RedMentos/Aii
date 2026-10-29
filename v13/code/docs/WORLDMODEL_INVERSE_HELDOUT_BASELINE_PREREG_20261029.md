# World-Model inverse majority baseline — preregistration (2026-10-29)

Parent review commit: `20363b1f3052276254d23878feeb2f92adeff2ca` (PR #1139). Canon blob `218464b12a2d27d92524c751922fa8e1c3fb0ea7` remains binding and unchanged. This is a review-only candidate; do not merge into a frozen source cohort or promote any gate.

## Hypothesis and observed code before test

`v13/code/v13/world_model.py` uses a hashed held-out split for inverse accuracy, but its `inverse_majority_baseline` currently computes `max(counts of all observations) / n`. This uses held-out labels to select and evaluate the baseline, while the trained inverse readout is evaluated only on held-out rows. A legitimate majority classifier must choose the most frequent **training** action, then score that frozen choice on the held-out action labels.

## Fixed controls (software/synthetic only)

1. `n=48` with every training action `simple` and every held-out action `both`: old baseline >0; correct train-only held-out baseline **0.0**.
2. `n=48` with all actions `simple`: baseline **1.0**.
3. `n=48` with every training action `simple`, held-out alternating `simple`/`both`: baseline **heldout_simple / heldout_n**, not all-data frequency.
4. Source fit, heldout inverse accuracy, heldout size and training counts must remain unchanged. No changes to `transitions`, `_split`, registered cohorts, forward fit, confidence, gates, model/source/seed pins.

First commit tests only; run focused tests and preserve the genuine RED. Then change the single baseline calculation and rerun focused plus original World-Model tests. Raw evidence, SHA256, CI exits, and an independent review must be retained. No native/Redmi/causal utility claim; Age0 RECORD_ONLY, STEP2 UTILITY_FAIL, B3 L1 FAIL, Body-JEPA UNAVAILABLE, LP3 FAIL, jepa_weight0, V13 INCOMPLETE.

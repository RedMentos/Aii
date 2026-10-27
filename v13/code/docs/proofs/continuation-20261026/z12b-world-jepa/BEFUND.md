# WP-Z12b BEFUND: action-grounded World-JEPA on real file actions

Verdict: **Z12B_WORLD_JEPA_FAIL** (prereg `PREREG.md`, committed 03a4646 before the run; seeds 101, 102, 103).
Data: `v13/bench-results/z12b-world-jepa-20261026/z12b.json`. Per seed: 3600 training transitions with the world process
running, 150 states x 6 counterfactual actions executed for real in folder copies, 300 attribution intervals.

| criterion | result | threshold | |
|---|---|---|---|
| W1 counterfactual retrieval, covered actions | .769 pooled (.752 / .805 / .749) | >= .80, each >= .70 | FAIL |
| W2 controls | no action .197, shuffled .188 (JEPA +.57) | <= .40, gap >= .30 | PASS |
| W3 no collapse | effective rank 14.0-14.4 of 16, min std 1.07 | >= 4, >= .05 | PASS |
| W4 confidence vs error | Spearman -.20; all held-out queries SIMULATION_UNCERTAIN | <= -.30 and all | FAIL |
| W5 attribution JEPA | own-only SELF .846, world-only WORLD 1.00, nothing-happened SELF .62 | .90 / .90 / .80 | FAIL |
| W6 no-action control worse | control balanced .968 vs JEPA .923 | control <= JEPA - .20 | FAIL |

## What it shows
- The latent model really uses the action: it picks the right real outcome among 6 executed alternatives in 77 % of
  cases, controls without action information sit at chance (~.19), and an observation-space ridge model also stays at
  chance (.20) because the effect of an action depends on the state (it is not linear).
- Combinations of operation and slot never seen in training are not composed (.27 retrieval, error 3-6x higher). The
  confidence labels every one of them SIMULATION_UNCERTAIN, so the model says when it does not know; within covered
  actions the confidence ranks errors only weakly (-.20).
- Attribution: world changes are always caught (1.00), but the model raises false alarms: 38 % of intervals where
  nothing happened and 15 % of own actions are called WORLD_INVOLVED. Noop thresholds are tiny (.008-.012) and the
  predictor's noop output is not exactly identity on states slightly off the training distribution.
- W6 is also a design weakness of this prereg: the per-operation threshold hands the action identity to the no-action
  control, so in this world (one change per interval) the control attributes as well as or better than the JEPA.
  Z12a's exact hash prediction remains the better attribution path here.

## Dev-seed history (not evidence)
Dev seed 7 found the counterfactual-state distribution bug and that without the inverse-dynamics head the latent drops
the slot the action changed (~.5 -> ~.8). Both fixed before the prereg commit.

## Next
Compositional action input (per-slot latent or slot-equivariant predictor) for held-out combinations; attribution
should keep the exact corollary (Z12a) and use the learned model only where no exact prediction exists. Claim limit:
small synthetic-content file world on the cloud machine, NumPy SHADOW module, not wired into the runtime, no phone run.

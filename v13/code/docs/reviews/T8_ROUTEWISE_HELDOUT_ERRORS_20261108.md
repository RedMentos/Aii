# T8 route-wise held-out error candidate — 2026-11-08

Owner: GPT. Review-only child of T8 #1595, source parent `bb84365ed95cfa30a85c8e7d56fc124ffb0db9bd`. Original resume base `5e964146579deb22c5ba89a2a03a52a9e4d8aab8` remains untouched. No production integration.

## Why
The previous T8 candidate exposed missing training action coverage, but still only published pooled forward MAE. This adds an independently inspectable per-route held-out forward MAE and matched training-mean baseline, with `UNMEASURED` (no held-out observations), `MEASURED_TRAIN_SUPPORTED`, or `MEASURED_UNSEEN_TRAIN_ACTION` evidence labels. No route score is extrapolated where data are absent. Prediction dimensions and finite evidence are checked before aggregation.

## Scope / gates
Uses existing deterministic train/holdout split, original ensemble predictions and targets; does not refit, change model seeds, register new cohorts, adjust confidence, grant execution authority, or modify native/Redmi evidence. STEP2 UTILITY_FAIL, B3 L1 FAIL, Body-JEPA UNAVAILABLE, World-JEPA SHADOW, jepa_weight=0 and full-scope incomplete remain unchanged.

## Test evidence
Three unittest cases committed: unseen action/undefined action and exact error values; invalid prediction shape/nonfinite; invalid split/nonfinite targets. No exact-source full-repository execution or privacy scan is claimed. Direct container Git DNS failed earlier; connector remote readback is required. No native model calls were started.

## Next commands
`PYTHONPATH=v13/code python -m unittest v13/code/tests/test_world_model_heldout_action_support.py v13/code/tests/test_world_model_heldout_route_errors.py -v`
Run adjacent T8 fit/consumer tests, verify privacy CLEAN with `python v13/code/scripts/public_repo_privacy_scan.py --base bb84365ed95cfa30a85c8e7d56fc124ffb0db9bd --head codex/t8-routewise-eval-20261108`, then independently review the exact `fit` consumer and compare with resume before integration. Never promote a gate from synthetic diagnostic metrics.

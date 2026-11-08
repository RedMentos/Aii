# T8 world-model held-out action support — 2026-11-08

Owner: GPT, isolated review-only branch `codex/world-model-heldout-support-20261108`, based on independently verified resume SHA `5e964146579deb22c5ba89a2a03a52a9e4d8aab8`. This is separate from the BP6 review chain and does not modify any existing frozen source registration.

## Problem and implementation
The T8 world model reports pooled forward/inverse held-out metrics even when a route present in held-out observations is completely absent from the training split. A pooled score in that case cannot establish generalization for the unseen route. The candidate adds `heldout_action_support` to report exact train/holdout counts for all four canonical C5 actions, list unseen held-out routes, and a diagnostic support flag. The function rejects incomplete/overlapping/out-of-range split indices and invalid action labels. `fit` now includes the diagnostic under `metrics.heldout_action_support`; existing split, model parameters, prediction, confidence, source admissions and authority are unchanged.

## Evidence / limits
Focused regression cases are committed for unseen and supported actions and invalid split/label inputs. **No full checkout or local import of the exact source was executed in this run**; direct network access from the container is DNS-blocked, but GitHub connector remote writes/readback work. No model fit or native/Redmi execution is claimed. This is software candidate metadata only, not proof of world-model utility or causal action prediction. STEP2 UTILITY_FAIL, B3 L1 FAIL, Body-JEPA UNAVAILABLE, World-JEPA SHADOW, jepa_weight=0 and incomplete architecture remain unchanged.

## Next commands
From a full checkout at this review branch: `PYTHONPATH=v13/code python -m unittest v13/code/tests/test_world_model_heldout_action_support.py -v`; run adjacent world-model fit/consumer tests and the repo privacy scan with base `5e964146579deb22c5ba89a2a03a52a9e4d8aab8`. Independently review that missing route support never promotes a gate. Then evaluate the true causal/world-model utility experiments without modifying preregistered cohorts.

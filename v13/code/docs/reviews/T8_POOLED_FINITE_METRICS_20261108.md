# T8 pooled held-out metric validation — 2026-11-08

Review-only child of PR #1597 (`24529694621db129560cca6bfff0dd575dcb523b`). Owner: GPT, isolated branch `codex/t8-pooled-metrics-finite-20261108`.

## Change
The previous routewise helper guarded nonfinite per-route errors, but `fit()` still computed pooled forward MAE and baseline MAE without a finite-result guard. Finite large opposite numbers can overflow on subtraction or aggregation and could otherwise be persisted in a FITTED state. New `pooled_heldout_errors()` validates shape, finite inputs, baseline from training rows only, and finite outputs. `fit()` calls this helper before writing state. No gate changes or model/cohort edits.

## Test and evidence
Added `test_world_model_pooled_finite.py` for normal expected values, overflow of finite opposite predictions, overflow of finite training baseline, and invalid inputs/shapes. Tests have NOT been executed in a complete checkout; do not label them passing. The remote GitHub blobs were saved via the connector. Software review candidate only; no native or Redmi evidence.

## Negative gates
STEP2 UTILITY_FAIL, B3 L1 FAIL, Body-JEPA unavailable, jepa_weight=0 and whole-system incomplete remain unchanged. No change to frozen registrations, model weights or learning authority.

## Next exact commands
`PYTHONPATH=v13/code python -m unittest discover -s v13/code/tests -p 'test_world_model_pooled_finite.py' -v`
`PYTHONPATH=v13/code python -m unittest discover -s v13/code/tests -p 'test_world_model_heldout*.py' -v`
`python v13/code/scripts/public_repo_privacy_scan.py --base 24529694621db129560cca6bfff0dd575dcb523b --head codex/t8-pooled-metrics-finite-20261108`
Then full T8 consumer tests, independent review and integration dependency check against current resume and active owners. Avoid competing native jobs.

# T8 held-out arithmetic integrity — 2026-11-08

Owner: GPT; review-only child of PR #1596, parent commit `6f737e76585096d2e3319b6071f2cfe1ed5afee5`. Original integration branch `codex/resume-20261106` remains untouched.

## Defect and candidate
`heldout_route_errors` checked that predictions and targets were individually finite, but subtraction of two large finite floats could overflow to infinity; subtracting signed integer arrays could wrap before `abs`. The candidate converts operands to float before subtracting, checks the resulting per-target MAEs are finite, and raises `T8_NONFINITE_HELDOUT_ERROR` otherwise. Three new software regression cases cover finite-input overflow, integer-wrap avoidance and ordinary expected values. This does not alter training, cohorts, held-out partition, model weights or permissions.

## Verification boundary
Local NumPy 2.3.5 arithmetic smoke: opposite finite float maxima produce nonfinite subtraction, detected by the new guard; int64 max vs -2**63 yields ~1.8446744e19 rather than wrapping to 1. This is **not** an exact-repository test run. Source and regression tests were published via GitHub connector; remote readback hashes should be checked. No native model, Redmi or full suite execution. Negative STEP2, B3, Body-JEPA, World-JEPA and learning gates remain unchanged.

## Next exact commands
`PYTHONPATH=v13/code python -m unittest discover -s v13/code/tests -p 'test_world_model_heldout*py' -v`
`python v13/code/scripts/public_repo_privacy_scan.py --base 6f737e76585096d2e3319b6071f2cfe1ed5afee5 --head codex/t8-finite-heldout-errors-20261108`
Then run T8 consumer and full suite on exact repository source, independently review metric overflow and branch ancestry before integrating #1595/#1596 and this candidate. Also assess pooled `fit` metrics for the same overflow hazard in a separate package.

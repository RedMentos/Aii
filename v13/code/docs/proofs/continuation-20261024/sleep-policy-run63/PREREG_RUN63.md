# Run63 prereg — fail-closed Sleep policy finite mix and quiet-hour validation

2026-10-24. Base Run62 PR95 845863efac747e87593a1dc663ac5b40f4746f6b. Own minimal validation-only diff in `v13/code/v13/sleep.py`, `v13/code/tests/test_sleep_policy_finite.py` and `v13/code/docs/proofs/continuation-20261024/sleep-policy-run63/*`. No other owner's files or native jobs.

Source observation before test: `validate_policy` accepts NaN and Infinity in `mix` because `v<0` and `sum(...)<=0` do not reject nonfinite values; `ReplayQueue.sample` then evaluates `int(NaN)` or NaN quota. Also `quiet_hours` treats booleans as integer hours. The existing policy setter can parse user-supplied `nan` and `inf` via float(), making this reachable from an operator command.

Proposed narrow fix: reject non-finite numeric mix entries and non-finite or overflowed total; reject bool hours; reject malformed non-mapping mix with ValueError. Do not change valid mix weighting, defaults, policy limits, user permissions, learning or Sleep C decay. Preserve original invalid-input reproduction. Tests: NaN/Inf/-Inf mix, sum overflow, negative/zero mix, valid fractional mix unchanged, quiet-hour booleans rejected, Python -O. Full production integration and privacy scan remain pending if full checkout inaccessible.

Original gates unchanged: STEP2 UTILITY_FAIL, B3 L1 FAIL, Body-JEPA UNAVAILABLE, jepa_weight=0, V13 INCOMPLETE. No model/Redmi utility claim.

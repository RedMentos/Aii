# WP-Z12b independent review: train-bound confidence and malformed query evidence

Preregistered 2026-10-27 UTC, before test-only RED and source changes.
Review-only child of PR #746 at exact head `13355020dc13b45bc4096446b65568bd50f4e385`.
File ownership: `v13/code/v13/world_jepa.py`, new `v13/code/tests/test_world_jepa_coverage_integrity.py`, this proof folder and dedicated review workflow. No other owner branch is edited.

## Problem and hypothesis
`WorldJEPA.confidence(X,A,counts)` currently treats caller-supplied `counts` as evidence of fitted action coverage. A query for an action absent from `fit` can pass `counts=[1000]` and obtain `MODEL_SIMULATION` if disagreement/OOD are small. NaN/Inf/negative/bool counts and malformed one-hot actions can also enter confidence. This breaks the observed-action support contract of §7.2 and the uncertainty label, independently of predictive quality.

## Locked test plan
1. RED deterministic 3-action train-only fixture with 8 samples each for actions 0/1 and **zero** samples for action 2. Stub only predictor spread=0 and OOD=0 to isolate confidence, not claim learned utility. Supplied counts 1000 must not create support for action 2 or inflate observed action 0 beyond 8.
2. RED invalid counts (NaN, +Inf, negative, bool), invalid action rows (all zero, multi-hot, NaN), nonfinite state and spread/OOD: all must return finite zero and `SIMULATION_UNCERTAIN` for invalid rows. Batch shape mismatches may raise ValueError, never silently broadcast to confidence.
3. Preserve original `test_world_jepa.py` and run focused tests on clean GitHub Actions with source SHA, privacy/diff checks, raw exits, no model download. Run full software suite if focused passes. No native, Redmi, learning or gate promotion.

## Allowed implementation
Derive exact one-hot training action counts in `fit`; treat caller counts only as a conservative upper bound, never as proof. Reject malformed evidence per row, validate batch dimensions, bound confidence to [0,1]. Keep seed, model weights, predictor, EMA, loss, original cohort, `CF_MIN` and default SHADOW unchanged.

## Negative gates
LP1 NO_ATTRIBUTABLE_GAIN, LP2 ALIGNS_NO_GAIN, BJ1 NO_SIGNAL, STEP2 UTILITY_FAIL, B3 L1 FAIL, `jepa_weight=0`, Age authority 0, no Redmi, whole V13 incomplete. An improved confidence guard is not learned World-JEPA utility.

# Anchor U5 finite-weight fail-closed review — preregistration (2026-10-29)

## Parent, ownership, scope
Independent review-only child of scorer head `a0051c548ca861485015b51b9908a8d69ed4625e`, itself a review child of PR #1090. This package owns only `v13/code/v13/anchor.py`, `v13/code/tests/test_anchor_finite_review_20261029.py`, this note and isolated source-only CI. Does not touch registered model cohorts, model weights, seed hashes, learning age, or active native owners.

## Original code defect
`anchor.policy(nov, stab)` performs arithmetic on unvalidated values. Nonfinite novelty/stability can become nonfinite `multiplier`; `for_batch` multiplies a nonfinite or negative `trainer.cfg['anchor_weight']` and, in ACTIVE mode, proposes an invalid training override. A valid explicit human ACTIVE selection is **not** permission to apply an invalid numeric coefficient.

## RED-first test plan
1. Reject boolean, NaN, infinity, negative and >1 novelty/stability at `policy` before any proposed multiplier.
2. In a minimal isolated ACTIVE and SHADOW `for_batch`, reject nonfinite, boolean and negative base anchor weights, while `None` remains an unmeasured/nonapplied sentinel.
3. Valid finite [0,1] novelty/stability and finite nonnegative base weight preserve the old bounded policy and existing ACTIVE/SHADOW behavior.
4. Run focused `tests.test_anchor` + new tests, full software suite, compile, privacy scan and diff check; archive original raw outputs and hashes. No native inference or training.

## Claim limits
This is software numerical admission only. It cannot prove learned utility, retention, or Android/Redmi behavior. Keep Age0 RECORD_ONLY, STEP2 UTILITY_FAIL, B3 L1 FAIL, Body-JEPA UNAVAILABLE, jepa_weight0, V13 incomplete. Existing failed attempts remain intact.

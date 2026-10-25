# Run380 preregistration — AG8 regression shield must use complete finite metrics and exact deltas

2026-10-25. Owner: independent AG8 `v13/code/v13/agi/self_improve.py` package. Parent: verified Run379 review head `9675eea132b1833abe0fbc6e0d3e31813b94e3d5` (PR #374; not main). Active Run377 Context OS, Run378 B3, Run373 native owners untouched. No model, seed, cohort, Age, learning mode, user permissions, human approval or generation manifest changes.

## RED-first hypotheses

`SelfImprovement.evaluate` computes candidate minus baseline deltas rounded to four decimals **before** comparing to `retention_max_delta` and `MIN_GAIN`. A raw unseen regression -0.02004 is rounded to -0.0200, so a proposal can become PENDING_USER despite exceeding a .02 shield. A raw gain +0.00996 rounds to +0.0100, falsely meeting MIN_GAIN .01. The same path silently ignores absent axes, NaN/Inf values (which can bypass comparisons) and one-sided forgetting rates. AG8 is a proposal/approval guard; invalid evidence must never produce a request.

Preregister actual Runtime/SQLite RED tests using `SelfImprovement.propose(... origin='USER')` and deterministic evaluator callbacks: (1) threshold regression -0.02004 with overall +.04 -> SHIELD_FAIL; (2) gain .00996 -> SHIELD_FAIL; (3) NaN unseen, Inf forgetting, missing unseen, boolean axis, one-sided forgetting -> ValueError, proposal stays PROPOSED and no request; (4) valid complete metrics +.03 with unchanged unseen -> PENDING_USER only, approval still explicit and does not apply settings. Include inherited `tests.test_growth.G8SelfImprove` and any source-bound AG8 tests available. Use actual SQLite request count and no model. RED expected on at least the two boundary assertions and invalid evidence cases, inherited green.

## GREEN candidate

Validate baseline and candidate dicts, required `overall/seen/unseen` metrics as exact int/float, finite and in [0,1], and optional forgetting.rate either present in both or neither and finite [0,1]. Reject invalid data before state mutation or request creation. Use unrounded deltas for gating and recording; retain original regression threshold, MIN_GAIN, human approval, status shape and age rights. No automatic application. Reject bool and nonfinite; no silent fallback to missing axes. Run exact-head workflow, inherited AG8, compileall, privacy scan; preserve RED and GREEN raw artifacts and all original negative blueprint gates.

## Claim limit

Software safety of AG8 comparison only, not evidence that any self-improvement algorithm learns or that RSI/AGI exists. No Redmi/native/STEP2/B3/Body-JEPA/jepa_weight promotion. After GREEN, prioritize an actual measured learning/utility package; do not continue an endless series of guards.
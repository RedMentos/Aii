# WP-Z12b World-JEPA action-support / numeric confidence contract — preregistration

Date: 2026-10-27 UTC. Owner: GPT-6 continuation; review-only child of PR #746 exact original parent `13355020dc13b45bc4096446b65568bd50f4e385`. World-JEPA is SHADOW and not runtime-wired. No model/seed/cohort/source replacement.

## Problem / prospective RED

`WorldJEPA.confidence(X,A,counts)` currently trusts arbitrary caller-supplied action counts. A never-observed action can receive positive confidence by claiming a large count even though its predictor was not trained for that action. NaN, infinity or negative counts can also yield nonfinite or negative confidence. An invalid/multi-hot action should never inherit coverage. `fit` should reject nonfinite/mismatched/empty transition arrays before optimizer work.

## Implementation contract

Keep `confidence(X,A,counts)` public signature and existing valid finite one-hot callers. Bind action coverage to observed **fit** rows; caller counts may only lower, never raise, effective counts. Invalid counts/actions fail closed to finite confidence 0 and `SIMULATION_UNCERTAIN`; invalid or unfit model arrays raise `ValueError` before training/inference. Preserve zero-action negative-control training (it must not gain one-hot coverage). Preserve existing seeds, network, EMA, optimizer, ensemble, thresholds and model/age gates.

## Tests / acceptance

Prospective RED: deterministic patched predictor/ood with action 1 never seen but supplied 1000 samples; malformed counts (NaN, infinity, negative), multi-hot and all-zero actions, and malformed fit input. RED must be recorded before implementation. GREEN: focused `python -m unittest -v tests.test_world_jepa`, `py_compile`, `git diff --check`, public privacy scan against original parent, and if feasible full `unittest discover -s tests -p 'test_*.py' -q`. Save source-bound raw exits and exact commit; no native/Redmi/causal utility or Age promotion.

## Scope / open gates

This only hardens the SHADOW confidence interface; it is not calibrated probability and does not prove World-JEPA counterfactual utility. LP1 NO_ATTRIBUTABLE_GAIN, LP2 ALIGNS_NO_GAIN, BJ1 NO_SIGNAL, STEP2 UTILITY_FAIL, B3 L1 FAIL, `jepa_weight=0`, Age authority 0, Redmi unmeasured and full V13 incomplete.

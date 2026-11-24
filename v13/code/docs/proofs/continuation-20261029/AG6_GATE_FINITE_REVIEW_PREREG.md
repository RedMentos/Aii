# AG6 numeric gate admission — preregistered 2026-10-29

## Parent, scope and hypothesis
- Review-only child of PR #1114 exact parent `f428a171cd595ed053d0c7e16801ce415bf1e4a0`. PR #1114 remains focused GREEN/full RED because two historical frozen source-identity tests fail; this package must not rewrite those pins or promote gates.
- File ownership: `v13/code/v13/agi/weights.py`, new `v13/code/tests/test_ag6_gate_finite_review_20261029.py`, this prereg and dedicated CI only. No frozen models, source/seed cohorts, age/learning policy or production merge.
- Hypothesis: AG6 `WeightConsolidation.gate` accepts Python booleans, out-of-range rates, negative KL and non-boolean drift PASS values as if measured quality; nonfinite values can cause JSON persistence failure after a human-approval request has already been created.
- Expected RED on original code: boolean overall can produce PENDING_USER, negative KL or forgetting can pass, learned recall >1 can pass, string drift `"false"` is truthy; nonfinite baselines/config can throw during persistence.
- Desired GREEN: every present quality metric must be typed finite, with [0,1] bounds for rates and nonnegative KL/delta; malformed evidence deterministically becomes GATE_FAIL with an error-field list, no approval request, and restart-safe state. Valid control continues to PENDING_USER (human approval still required). Missing optional metrics retain existing semantics; no silent gate promotion.
- Proof: persist this prereg before tests, preserve original RED raw and hashes, apply a narrow fix, run focused + full software tests, compile, privacy/diff checks, preserve raw and verify exact head. Do not erase original failures. Tests use synthetic Store and trainer only; no actual weights or Redmi.
- Original negative gates remain Age0 RECORD_ONLY, STEP2 UTILITY_FAIL, B3 L1 FAIL, Body-JEPA UNAVAILABLE, LP3 FAIL, jepa_weight0, AG6 unapproved and V13 incomplete.

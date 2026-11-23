# Preregistration: C3 native stream bounded collection (2026-10-29)

Review-only child of PR #1145 at `71fe7978d5dca6a134ced0c645346b291b97d92c`. No source/model/cohort/seed/Canon changes at registration.

## Observed code defect and falsifiable witness
`scripts/ask_verified_budget.py::query` uses `"".join(runner.generate(...))` despite the explicit bounded C3 operator lane. `max_tokens` is passed to the runner, but this Python consumer imposes no independent output-size bound and does not validate chunk types. A malfunctioning or substituted generator can produce arbitrarily large text or a non-string chunk. A long whitespace prefix followed by `615 Euro.` can still be admitted as `FINAL` by the exact numeric source guard.

## Frozen software checks before source edit
1. A normal multi-chunk `615 Euro.` output remains accepted and joined byte-for-byte.
2. More than 32,768 generated Python characters (even if only whitespace plus a correct amount) returns no answer and cannot produce `FINAL`.
3. A non-string generated chunk returns no answer.
4. Integrated Runtime/Memory fake-native generator must unload C3 exactly once and return `UNVERIFIED_NATIVE_ANSWER`, not `FINAL`, for an oversized output.

No new model call, approval, learning, native permission, age change or tool authority. Native resource usage is not proven by this software guard. Original failing tests are retained; do not weaken the registered witness to obtain green.

## Implementation hypothesis
Add a bounded incremental collector with a hard maximum of 32,768 characters and reject non-string chunks, without changing `max_tokens`, source revalidation, model pins, C3 runner, exact-source lane, or final answer content on valid short streams.

## Claim limits
Software/fake-native only; not real C3 Linux inference, not Redmi, not STEP2/B3/Body-JEPA/LP3/whole V13 utility. Age0 RECORD_ONLY, STEP2 UTILITY_FAIL, B3 L1 FAIL, Body-JEPA UNAVAILABLE, LP3 FAIL, jepa_weight 0, V13 INCOMPLETE.

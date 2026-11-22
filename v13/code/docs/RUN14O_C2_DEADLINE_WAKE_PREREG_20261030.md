# Run14O prereg — C2/JEF deadline-one-body wake must respect selected hemisphere (2026-10-30)

Review-only child of Run14M PR #1330 at `98b5c634627b01fa34a178fad4c0ee8c4d1eecc0`. This preregistration is committed before tests or source changes. Canon blob `218464b12a2d27d92524c751922fa8e1c3fb0ea7`, current `v13/code/v13/effort.py` blob `436fd88a20c673504a21fa0ddc2615cc110508af`, existing `test_effort.py` blob `fc832c65b0d724bff87a00761663bd1262347678`. All previous C2/STEP2/native cohorts, negative gates, and source pins remain frozen.

## Concrete failure and minimal fix

When the requested effort wakes `both`, the planner already records a preferred `one_body` (detail or gist). In GREEN resources with a 2–<4-second observer window, `constrain` currently hardcodes `ceiling='detail'` for deadline one-body fallback, so **a gist-preferred plan wakes B1_DETAIL instead of B2_GIST**. This is a deterministic control bug independent of model quality. Preserve the resource/age/observer ceilings and change only deadline fallback to the generic `one` ceiling, which `cap_wake` already resolves to the plan's `one_body`. Do not alter adaptive scoring, learned wake, the fixed user modes or model routing elsewhere.

## Test-first acceptance

- Original source must RED on gist-preferred both-wake under 3-second deadline: expected `gist`, actual `detail`. The detail-preferred control remains `detail`.
- Gist/detail choices preserve `DEADLINE_ONE_BODY`, `wake_ceiling='one'`, `max_reentry=0`, Age0 depth and no tool/verify authority. Under 1-second deadline both must be `none`; observer-off and RED resource remain `none`; resource ORANGE still selects the preferred one body.
- User-forced `detail` and `gist` modes remain unchanged; learned wake may not exceed the one-body ceiling.
- Existing `test_effort`, `test_resource_modes` and C3 uncertainty wake regressions GREEN, source-only; no native/model invocation or Redmi measurement. Preserve original RED and GREEN raw ZIP, hashes, CRC, private permitted backup and remote source verification.
- This is a **software control correctness** fix, not a measured improvement in Z6a/Z6e wake utility. Earlier Z6a/Z6e failure, STEP2 UTILITY_FAIL, B3 NO_PROMOTION, Body-JEPA UNAVAILABLE, Age0 RECORD_ONLY, jepa_weight0, no Redmi and whole V13 incomplete remain unchanged.

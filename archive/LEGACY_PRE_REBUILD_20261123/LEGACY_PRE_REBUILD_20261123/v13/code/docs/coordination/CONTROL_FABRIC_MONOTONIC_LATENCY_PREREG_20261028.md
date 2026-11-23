# WP-T14 control-fabric latency monotonicity prereg — 2026-10-28

Review-only independent branch `assistant/v13-control-fabric-monotonic-latency-20261028`, parent PR #826 exact `0cc5e59fc1c91a71b0b232b42f70668c562d9d2b`. Owner GPT-6, only `v13/control_budget.py`, new negative tests/workflow/docs; no changes to live JEF authority, native models, frozen Runtime or Canon.

## Reproducible issue
`control_budget.durations` sorts stage marks by **timestamp**, not canonical stage order. A malformed FINAL turn with `routing=10`, `native_answer=1`, `finished=11` can misattribute nine seconds of control time to the body and make the measured control budget look artificially small. Nonfinite, bool and negative marks also pass the numeric filter. A configured WP-T14 limit could be reported PASS on invalid evidence.

## Registered tests/acceptance
1. RED-first tests: reject reversed canonical stage marks and nonfinite/bool/negative marks, including a latency report that must not PASS with one invalid FINAL record and one valid record.
2. Source fix: compute stage durations only from canonical `STAGES` order with finite, nonnegative, real (not bool) cumulative marks. Invalid marks produce no durations, and are counted separately by `latency`.
3. `report` with configured limits and any invalid stage marks must be `INCOMPLETE_EVIDENCE` rather than PASS. With zero valid turns and configured latency cap, `NO_DATA` remains, unless invalid marks exist (then `INCOMPLETE_EVIDENCE`). No limits still `NO_LIMITS` with invalid count disclosed.
4. Preserve existing valid stage measurements and p95 tests. Run independent focused and full Linux software regression, raw RED/GREEN and private backup. No Redmi thermal/energy claim or gate promotion.

This is measurement integrity only, not native execution or control-budget calibration. The Canon does not yet set numeric WP-T14 limits. Negative gates unchanged.

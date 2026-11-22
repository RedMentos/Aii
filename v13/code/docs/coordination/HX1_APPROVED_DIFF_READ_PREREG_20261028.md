# HX1 persisted-value-to-approved-diff read binding — preregistration 2026-10-28

Review-only child of PR #809, exact verified parent `4bd69282647d260efe815b6f57b72ed675fef588`; parent Linux software Actions `40610977438` SUCCESS. Do not merge into production. Own only `v13/code/v13/agi/harness.py`, new focused regression test, this prereg/handoff and branch-scoped CI. PR #810 A1 work is a separate sibling and is not overwritten.

## Problem and falsifiable test

`HarnessLibrary._effective()` currently rechecks live AG8 approval for the persisted proposal ID but does **not** bind the persisted override's target and value to the approved proposal's `diff`. After an approved apply, a malformed/corrupted persisted active value (or previous-chain value) may be served by SHADOW `resolve`, `overlay`, `manifest_fields`, and `report` despite not being the approved text. An unrelated approved proposal ID may also be substituted for a target.

Tests use actual Runtime/SQLite, no native weights: (1) mutate the active value after a valid approval and verify fallback to a prior *still-approved* value, not the substituted value; (2) mutate a stored previous value and verify default rather than serving it; (3) substitute an approved proposal for a different target and verify fail-closed; (4) unaffected approved target survives and restart does not restore unauthorized value. Preserve no writes to updates and Age0/learning authority.

Expected test-only RED: at least one failure on parent source. Source fix must check approved canonical `candidate(proposal['diff'])` per target/value while rechecking the durable approval; malformed diff fails closed. Do not rewrite active records or silently roll back. Regression test + complete Linux software suite + privacy/diff/compile; preserve original RED raw logs and hash-bind GREEN source. Any failure is evidence, not gate promotion.

Acceptance: tests PASS without changing original gates or live consumers. STEP2 UTILITY_FAIL, B3 L1 FAIL, Body-JEPA UNAVAILABLE, LP3 heldout 0/12, jepa_weight=0, Age0/RECORD_ONLY, whole V13 incomplete. Native and Redmi not measured here. Next substantive work after review: B1/B2 complementarity and C3/B3 receiver prerequisites. Budget remaining UNKNOWN.

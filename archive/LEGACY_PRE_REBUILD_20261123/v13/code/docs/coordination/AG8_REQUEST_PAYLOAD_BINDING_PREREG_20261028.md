# AG8 durable human-request payload binding — preregistration 2026-10-28

Independent review-only child of GREEN PR #811 exact `e2773e06075486ce8ed54c1fffec92f4200ec44c` (Actions `40612498319` SUCCESS: 20 focused, 2108 full Linux software, privacy CLEAN). This is distinct from LP3 PR #812 and integration PR #813. Own only `v13/code/v13/agi/self_improve.py`, new Runtime/SQLite tests, branch CI and this handoff. Do not change existing request/proposal schemas, age rights, cohorts or registered scores.

## Hypothesis and expected RED

`require_approved_origin` verifies the current durable AG8 proposal snapshot and that its request row has status APPROVED, but reads **only status** from the human request. `SelfImprovement.evaluate` had persisted an immutable request payload containing `proposal`, `kind`, `diff`, `shield`. If the AG8 proposal state is subsequently changed while the request remains approved, the approval check can authorize a different diff/shield than the human approved. HX1 may then serve an altered persisted value and HX3 may continue exposing a lesson under a changed proposal. This is a persistence-integrity test, not a claim of external database adversary access.

Preregistered tests with actual Runtime/SQLite: (1) approve+apply a harness target and record HX3 evidence, then change the saved AG8 proposal diff and matching HX1 active value without changing the original human request payload; `HarnessLibrary.resolve` must return default and HX3 lookup must refuse the changed approval; (2) change only request payload's proposal ID/kind/diff/shield while leaving APPROVED status and the AG8 state intact; `require_approved_origin` must reject; (3) a separate intact approval remains valid across restart. Test-only RED expected on current source, preserving raw ZIP.

Narrow GREEN fix: read request `kind,payload,status` and require kind `SELF_IMPROVEMENT`, exact `proposal` ID, `kind`, `diff`, `shield` equality with the saved approved AG8 proposal; reject malformed JSON/rows. Preserve human workflow, no auto-approval, no live consumer, no schema migration. Run focused and full Linux software suite, compile/privacy/diff; close raw ZIP, SHA256, private Library readback. A passing synthetic test does not prove native/Redmi/JEPA/STEP2/B3 utility.

Negative gates unchanged: STEP2 UTILITY_FAIL, B3 L1 FAIL, Body-JEPA UNAVAILABLE, LP3 heldout 0/12, jepa_weight=0, Age0/RECORD_ONLY, whole V13 incomplete. Budget remaining UNKNOWN.

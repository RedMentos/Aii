# WP-T14 persisted row integrity — closed software review (2026-10-27)

## Scope / owner
- Review-only PR #763, child of PR #761 exact `5458dce977ad22f82fb1749811c512bb543782fc` (NOT main).
- Prereg `3d7ef39e42b2ef1d5cb1d6ecfb0988ab85a697ef`, original source blob `aa29c4eb39b5fdc87c58ac3838acd3dd2818281c`.
- Minimal source `8db18820d0cc9358779ebdc058eaeab24e2cfcd9`, blob `f2beff6b2b3df4c1a98a4763e6ec93e17a8dabfa`; new test module `test_control_budget_row_integrity_review.py`. Existing finite-stage-mark validation and budget thresholds untouched.

## Fault / remediation
Persisted `messages.metadata` containing valid JSON `null`, arrays, strings, bool or numbers caused `latency()` to call `.get` on a non-dict and crash. Nonfinite/bool/negative/non-numeric `created` could crash the hourly span or contaminate the latency denominator. The fix skips malformed rows after JSON/type and finite timestamp validation; valid stage durations and limits remain unchanged.

**Preserved harness mistake:** initial test-only workflow Actions `40567120559` and first GREEN `40567157273` both reported SUCCESS but their unittest command omitted the new row-integrity module. These are **not** valid RED/GREEN proofs. A separate source-unchanged RED replay branch `codex/automation11-control-row-red-replay-20261027` fixed the test command. Actions **40567310226 expected FAILURE** at exact `000d05be0f6949ca7473ffdcca6319dc44af3d4b`: **11 tests, 5 failures + 7 subtest errors**, INSTALL/COMPILE/PRIVACY/DIFF exits0; original ZIP artifact `12763073628`, SHA256 `9aaa6359b761dc6d413945d5e9304fe2322cfc7ea0f984c9f705c1a0c950d2a6`.

Corrected GREEN Actions **40567321217 SUCCESS** at `81ae3eefed324206f2a526fa98287b0c861a883b`: **11/11 PASS**, all INSTALL/UNIT/COMPILE/PRIVACY/DIFF exits0, privacy CLEAN; artifact `12763597238`, ZIP SHA256 `86afd60e446a91ca8636e0935bfd7a494723c7220f9ad7f0227c8fc3747d9496`.

Full source-wide Actions **40567197603 SUCCESS** at `37a84f23b38d825069abf71f5a9e31c4b5219fb3`: **1947 tests OK (1 skipped)**, INSTALL/UNIT/COMPILE/PRIVACY/DIFF exits0, privacy CLEAN; original artifact `12763856707`, ZIP SHA256 `2e55b4b4a17a6b6cc214df271256c29dd9b14ab046cc578dcb7e23f94a2cb71b`. Full CI ran before the corrected focused workflow commit; tested source blob was identical `f2beff6...`.

All original RED/GREEN/FULL raw ZIPs privately saved under `/V13-Checkpoints/2026-10-27/Automation11ZG-Control-Row-Integrity/`, ZIP CRC/HEAD checked, and re-materialized SHA256 byte-identical. No genuine Redmi/thermal/energy measurement; synthetic persisted-row fixtures only.

## Gates and exact next command
`cd v13/code && PYTHONPATH=.:tests python -m unittest -v tests.test_control_budget_row_integrity_review tests.test_control_budget_finite_marks_review tests.test_control_budget`

Independent frozen-runtime owner review of PR #763 required before integration. No threshold changes, no model/seed/registered cohort changes, no Age promotion. LP1 NO_ATTRIBUTABLE_GAIN, LP2 ALIGNS_NO_GAIN, BJ1 NO_SIGNAL, STEP2 UTILITY_FAIL, B3 L1 FAIL, jepa_weight0, Age authority0, Redmi unmeasured and V13 incomplete remain.

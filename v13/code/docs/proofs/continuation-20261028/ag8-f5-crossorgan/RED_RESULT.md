# AG8 × Sleep policy F5 chain — RED-first result (2026-10-28 UTC)

Parent PR #802 at `990ea980b1a31db860702e74c6dada70f9ace8d5` was still under combined full CI when this independent AG8 test was preregistered. No production AG8 source has been changed on this branch.

## Test-design correction preserved
Initial test `baf16153256ae494afcb69e88a8e4a6338485af1` used NaN and unexpectedly passed on old AG8 source (Actions 40606992412: 2/2 PASS, old AG8 blob `0f71e36b9542f1aa3aa57db734c448c305dfb48b`). The old path fails closed indirectly on NaN serialization; this did **not** prove the intended missing-score vulnerability. Original raw artifact `12781066001`, ZIP SHA256 `bb51912314f2bd50f53ca713d88ed28448cd4e98592c0479f67220bbac91ece2` is retained in private Library `/V13-Checkpoints/2026-10-28/Automation13-F5-AG8-Integration/AG8_INITIAL_TEST_DESIGN_GREEN_40606992412.zip`. Do not erase or relabel it as RED.

Corrected test-only commit `a82189dec40c44d8b22b1f95bd4188f1811b5aa6`, test blob `c9326c8224f585e400399b9ba4dbae87cb682a60`, uses missing `unseen` score. Actions `40607142697` at that exact head: **2 tests, 1 PASS, 1 expected FAIL** (`AssertionError: ValueError not raised`), `FOCUSED_EXIT=1`, `INSTALL=COMPILE=PRIVACY=DIFF=0`, source AG8 blob unchanged `0f71e36b9542f1aa3aa57db734c448c305dfb48b`. Raw artifact `12781590886`, ZIP SHA256 `4a43a2abaf72bb1219916441ad7061626984fe080194761ca8523474d0276756`, CRC PASS, private Library `/V13-Checkpoints/2026-10-28/Automation13-F5-AG8-Integration/AG8_RED_40607142697.zip`.

## Scope and next
The observed RED is a synthetic Runtime/SQLite AG8 shield bypass: incomplete evaluator metrics did not raise, allowing the approval request path. It does not show automatic Sleep policy application. After PR #802 combined CI GREEN, import the exact previously verified PR #790 source blob `4ff5ee079653488d9117380c6b7435df38966824` and test blob `0d07e975513b3adb4c24d3244314a13ba0e73926`, rerun focused and full software tests on the integrated branch. No native/Redmi/learning/age promotion. STEP2 UTILITY_FAIL, B3 L1 FAIL, Body-JEPA UNAVAILABLE, jepa_weight=0, V13 incomplete.

# Run11 WP-T14 control-fabric latency monotonicity — closed RED/GREEN checkpoint (2026-10-28)

Owner GPT-6; review-only child of PR #826 exact `0cc5e59fc1c91a71b0b232b42f70668c562d9d2b`, no parent/main mutation. Prereg `971ef42d815ca22963def9918e65619dd15d30dd` before RED test `0e9f850d903fc1f4d419d4b7fd89f97a84b1f7e2`, workflow `3da87a6927ecca15f682f848068b4e79da7e7f2e`.

## Reproduced bug / fixed behavior

Original `control_budget.durations` sorted stage marks by timestamp rather than canonical STAGES order. Malformed marks (`routing=10`, `native_answer=1`) assigned nine seconds to body, hiding control latency. NaN/inf/bool/negative timestamps were accepted. Original `report` could PASS configured control limits based on incomplete/invalid FINAL rows.

RED Actions `40625310146`: **7 expected assertion failures** in new negative tests (including subtests), 4 existing budget tests pass, install/compile/privacy/diff exit 0; ZIP SHA256 `b531d2c5cece7d777436ba5780cfbbd4d5b216cd867a33062bb544135c433ee0`, CRC and internal hashes verified.

Source fix `d992ffc76c0bc7f27f202139af6e7bf6a44fe8b7` uses canonical STAGES order, finite nonnegative numeric (not bool) timestamps, and rejects nonmonotonic sequences. Latency reports `invalid_stage_marks` and configured limits return `INCOMPLETE_EVIDENCE` if malformed marks are present. No limits remain `NO_LIMITS`; existing valid latency tests unchanged. Test-clarity commit `e7993c6550f39e5573c0d92b0823418132276627`.

GREEN Actions `40625450599`: **7/7 focused PASS**, install/compile/privacy/diff exit 0, privacy CLEAN. Source Git blob `476b7da24c84ee853e4bd07f981312169b1390f8` (original `c5fa3b7df09e8e7156ff36d801966004bc794d37`). ZIP SHA256 `382a6c041e242b314157a35703e74fa7d97cbdb238c37bf1fad69e0e22aa0309`, CRC/internal SHA256 verified.

Private persistent Library backup, both re-materialized byte-exact:
`/V13-Checkpoints/2026-10-28/Run11-Control-Fabric-Monotonic/RED-40625310146.zip`
and `GREEN-40625450599.zip`.

## Remaining evidence and exact next action

Only Linux software measurement integrity. No real Redmi thermal/energy, no numeric WP-T14 Canon calibration, no native inference or JEF learned routing utility claim. STEP2 UTILITY_FAIL, B3 L1 FAIL, Body-JEPA UNAVAILABLE, jepa_weight=0, Age0 RECORD_ONLY. Full suite and independent review required before integration.

Exact repeat: `cd v13/code && PYTHONPATH=.:tests python3 -m unittest -v tests.test_control_budget_monotonic_20261028 tests.test_control_budget`; then `PYTHONPATH=.:tests python3 -m unittest discover -s tests -p 'test_*.py' -q` in pinned isolated Linux environment. Next: integrate only after independent review with current PR #826 descendants and re-run full cross-organ suite; preserve invalid evidence counts and original negative gates. No changes to other owners' files.

Actual platform budget remaining UNKNOWN. This checkpoint is intermediate.

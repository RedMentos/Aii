# HX134 request revocation + evidence freshness integration prereg (2026-10-27)

Review-only child of current HX134 durable AG8 approval-snapshot review PR #788 at `72b48d1b89bb73c8ffd6d7434a0e75242db349c3`, not main. Independent prior art **PR #163** (`codex/hx-approval-evidence-run133-20261025`, `6c8543ad25804003bcc859fdd1b9fe6136f66637`) already demonstrated these counterexamples and a compatible fix on an older HX chain; its verified Actions run `40154851577` succeeded. This package **reconnects** those missing guarantees to the current HX134 chain without overwriting the older owner's branch.

## Falsifiable gaps on current branch

- `require_approved_origin` checks the durable AG8 proposal snapshot but not the separate persisted human request row's **current status**. After an approved request is changed to REJECTED, the unchanged proposal snapshot can still be used by `HarnessLibrary.apply` and `ExperienceLibrary.record`.
- `ExperienceLibrary.lookup` trusts ACTIVE status without checking whether its evidence file changed or became unreadable since the last explicit `verify()`. A stale lesson remains available until manual verification.

## Test-first acceptance

1. Test-only RED: after legitimate AG8 approval, change only its request row to REJECTED and verify both HX writers reject; after recording an experience, change/delete its evidence and verify `lookup` excludes it **without** explicit `verify()`, persisting STALE status. Use independent `test_hx_approval_run133.py` prior cases where compatible.
2. GREEN: query request status on each approval use; fail closed if absent/rejected. Refresh stale evidence before returning HX3 lookup; unreadable evidence counts stale. Preserve exact prior approval snapshot and generation gates, no extra live consumer.
3. Run focused HX and full Linux software suites, compileall, privacy scan and diff check. Preserve original RED/GREEN/full raw logs and hashes, verify private backup.
4. Preserve Age0, SHADOW authority0, STEP2/B3/LP1/LP2/BJ1 negatives and `jepa_weight=0`. No native/Redmi or production merge.

Owner GPT independent reviewer. Allowed paths: `v13/code/v13/agi/{self_improve,experience}.py`, `v13/code/tests/test_hx_approval_run133.py`, dedicated workflows and coordination. Parent PR #788 and prior PR #163 unchanged. Next command: `cd v13/code && PYTHONPATH=.:tests python -m unittest -v tests.test_hx_approval_run133 tests.test_harness_hx`.

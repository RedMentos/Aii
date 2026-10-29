# Run135 independent fail-closed error-contract review — 2026-10-29

Scope: isolated review child of PR #1035 at exact parent `c716263d4f1e047f8ce716b9f65ac34ee4fce3fd`. This branch does not modify production AgeControl, runtime, model sources, registered cohorts, seed/model hashes, or original raw evidence. No native/model/Redmi run is claimed.

## Observed RED, preserved

GitHub Actions run `40817217068` (job `123262923637`) at parent exact head `c716263d4f1e047f8ce716b9f65ac34ee4fce3fd` failed focused tests (47 of 48 succeeded). Original run remains RED, original raw artifact `12873337727` remains on GitHub; artifact ZIP upload SHA256 as reported by Actions: `956da230a6248ef7cd013cec722bda1f67a81b106e56fa7d5e5d5ff4ee16929e` (not independently rehashed here). The failing `test_invalid_finite_evidence_does_not_mutate_age` expected `AGE_EVIDENCE_COMPETENCE_NOT_FINITE_UNIT`, but the exact imported Run131 source deliberately raises `AGE_METRIC_INVALID:competence` for boolean `competence=True`. Existing Run131 focused tests already assert the `AGE_METRIC_INVALID` contract. This is a test expectation mismatch, not evidence that the invalid value was accepted. No gate promotion.

## Correction and checks

Only `v13/code/tests/test_run135_age_step2_crosschain.py` assertion text is corrected to the actual existing fail-closed `AGE_METRIC_INVALID:competence` error contract; no exception type or validation behavior weakened. New test Git blob `db272249cef1e531fd6a7337ea3810fe696fe455`. The branch-local workflow is retargeted to this review branch, pins the new test Git blob, and compares privacy/diff against the exact parent head. The original PR #1035 branch is not modified. The unchanged frozen 42-row Run116 source/tool, imported Run131/132 donor hashes, original model/seed hashes, Age0 ceilings, and negative gates remain bound by the workflow.

At this checkpoint, the new branch's exact-head GitHub Actions result is **PENDING**, not GREEN. Independently verify the completed Actions run's original ZIP CRC, inner SHA256SUMS, source/fixture hashes, 48 focused tests, full suite, privacy/diff, and unchanged negative gates before accepting this correction. Parent Run134 #1034 original Actions `40816811249` reports SUCCESS (independent raw audit still required).

## Continuation

Owner: this review branch only. Next command: inspect `https://github.com/RedMentos/Aii/actions/workflows/v13-run135-age-step2-crosschain.yml` filtered to branch `codex/run135-age-error-contract-review-20261029`; download the exact-head raw artifact and independently verify CRC/SHA256SUMS, exits, 42-row replay, privacy and negative gates. If GREEN, proceed to the next independent canonical package; do not merge production or promote STEP2, B3, Body-JEPA, LP3, jepa_weight or Age rights.

Gates remain: Age0 RECORD_ONLY, STEP2 UTILITY_FAIL, B3 L1 FAIL, Body-JEPA UNAVAILABLE, LP3 FAIL, jepa_weight=0, Redmi UNMEASURED, V13 incomplete. Public GitHub review branch is the only backup claimed for this correction; no rejected Drive destination was used.

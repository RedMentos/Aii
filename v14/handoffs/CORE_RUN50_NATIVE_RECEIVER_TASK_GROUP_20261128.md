# Core & Harness — Run 50 handoff

Date: 2026-11-28T01:20:34.966Z
Repository: RedMentos/Aii
PR: #2572 — https://github.com/RedMentos/Aii/pull/2572
Branch: `core/v14-native-receiver-kv-consumer-20261127-run1`
Code/test SHA: `8fd25ead80cc9262bed120cf50f8d46af722b1ce`
Base SHA: `a47907c4a0603e602581c6462ecb845211eb0445`

## Implemented

The native receiver Runtime consumer now:
1. Requires the bridge-returned `task_group_id` to equal the exact staged matrix receipt ID.
2. Reports K/V and teacher-forced information-use evidence for only that current task group, separately from the aggregate ephemeral cohort.
3. Keeps the single-group holdout result insufficient; synthetic K/V is downgraded to unavailable.
4. Removes only the current ephemeral group on post-bridge failure and does not mark the run complete before provenance/evidence validation succeeds.

The integrated-native builder → recovery builder → stage builder → RuntimeDeploy pin chain was rebound and read back.

## Tests

- CI #46092260865: 20/20 focused Runtime-consumer tests PASS on Python 3.13 and 3.14.
- CI #46092260774: staged/integrated FAIL, 235 passed / 18 failed / 10 skipped / 2 errors / 44 subtests. Failures are the QA-owned record-only controller-guard source pin; two migration assertions also see PARTIAL vs UPDATED.
- CI #46092260797: two migration PARTIAL-vs-UPDATED failures.
- CI #46092260884: one Lab Age stage failure at the same QA guard.
- CI #46092260776: owner-read PASS; Python 3.14 stage startup fails at the same QA guard.
- CI #46092260800: RuntimeDeploy offline integrity PASS on Python 3.11/3.14.
- CI #46092254655: offline bridge security PASS.
- Source-pin chain readback: PASS.
- LOCAL_LINUX full Aii checkout: BLOCKED / NOT_RUN; GitHub DNS could not resolve.
- Native GGUF and Redmi: NOT_RUN / REDMI_UNVERIFIED.

## Ownership / next step

QA owns the stale record-only guard pin and migration expectations. Core must not change those files. QA rebinds/fixes, then staged/integrated is rerun. Core continues the P0 normal-turn B1/B2→C4→C3 and fastpath work in parallel. Native matrix execution requires an actually available local environment, an already-present pinned GGUF and separate local-TTY approval. B3 remains OFF; PR remains DRAFT / NOT_RELEASED.

# V13 JEPA/Memory checkpoint — 2026-11-10 13:32 CET

## Branch and dependency
- PR #1681: https://github.com/RedMentos/Aii/pull/1681
- Branch: `jepa/atomic-online-world-validation-20261110`
- Base: `codex/v13-online-world-atomic-cursor-20261109-hour11` (already implemented co-located `processed_ids` inside predictor NPZ).
- Other JEPA PRs #1673 (fail-closed sidecar mismatch) and #1677 (batch prevalidation) were inspected; this PR intentionally combines their protections on the preexisting atomic-Codex implementation, **not** an independent replacement for either. Coordinate before merge.

## Concrete fixes
1. `v13/code/v13/online_world.py`: reject missing/stale legacy cursor and any processed-ID count inconsistent with learned `model.seen` (bounded by T8 MAX_ROWS), before accepting runtime state. An embedded atomic cursor is authoritative when present. Distinguish mismatch from an absent clean initial state.
2. Same module: encode and validate every newly admitted committed T8 row before the first observe/gradient update, preserving all-or-nothing validation for malformed late rows.
3. `v13/code/tests/test_online_world_atomic_batch.py`: four focused regression cases (bad late row causes no partial learning, embedded cursor beats stale sidecar after restart, missing legacy cursor rejected, legacy cursor ahead of weights rejected).
4. `.github/workflows/v13-online-world-atomic-batch.yml`: minimal Python 3.11 + NumPy test job.

## Evidence and limitations
- Source file updates and commits are remotely persisted; no successful local test or GitHub Actions run was available when written. Container git clone failed with `Could not resolve host: github.com`; connector can read/write repo but does not execute tests.
- `LOCAL_ONLINE_PLASTICITY_NOT_FULL_JEPA`: this code trains a bounded numeric predictor, not the JEPA encoder or GGUF weights. No Android/Termux runtime measurement, no learned-utility claim.
- Atomic NPZ snapshots with embedded IDs are present in the Codex base, but a robust crash-injection suite, recovery from corrupted current NPZ, rollback semantics for partially committed writes, and end-to-end T8 provenance tests remain open.
- Existing STEP2 UTILITY_FAIL, B3 L1 FAIL and Age0 authority gates unchanged. No risky active-model promotion.

## Next action
1. Verify PR #1681 Actions CI; fix any red results on this branch.
2. Review Codex base atomic snapshot code, reconcile with #1673/#1677 and compare actual current PR heads. No blind merge.
3. Add crash-injection and partial-write durability tests; measure replay/retention on disjoint T8 transitions and memory/time overhead in a constrained CPU environment.
4. Coordinate runtime integration and local hardware tests with Core/QA; never label Redmi performance verified from Linux CI.

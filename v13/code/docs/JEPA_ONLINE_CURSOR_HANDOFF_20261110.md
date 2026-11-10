# JEPA/Memory checkpoint — 2026-11-10

## Source and scope
- Base: `codex/v13-integrated-online-jepa-20261109` (NOT `main`).
- Read `v13/AGENTS.md`, root `AGENTS.md`, Canon v10.16.1, ROADMAP, user decisions, BUILD_STATE and historical HANDOFF_CURRENT. Other agents own Body/JEF/Android/Perception; this candidate only touches OnlineWorld and a new regression test.
- Branch: `jepa/online-world-cursor-recovery-20261110`; draft PR #1673.

## Reproduced logic defect (code-level)
`OnlineWorld.update` saves predictor weights/counters first, then cursor IDs in a second atomic file. Interruption after the first replacement leaves the model with one more gradient update than the cursor. On restart, the same committed T8 row would be trained twice. Conversely, restoring a newer cursor with older model silently skips a training row. Independent atomic replaces are not an atomic *pair*.

## Candidate mitigation
`OnlineWorld.__init__` now compares `min(model.seen, MAX_ROWS)` to the count of persisted cursor IDs and rejects duplicates. Inconsistent pairs fail closed with `ValueError`; the candidate deliberately does not attempt automatic rollback or change any GGUF/JEPA promotion gates.

Added `v13/code/tests/test_online_world_cursor_recovery.py` with five regression cases: fresh model; model-ahead crash; cursor-ahead crash; consistent model+cursor restart with zero new transitions; duplicate action IDs. Tests are **committed but NOT YET EXECUTED**: the current tool environment cannot reach GitHub via local git clone, and no Actions run was returned for the head at check time. No synthetic tests or hardware proofs are claimed as passed.

## Limitations / next steps
- This is a fail-closed detection, not two-file atomicity or automatic recovery. Proper follow-up: bind action-ID journal/cursor to predictor snapshot under one atomic checkpoint or use a transaction log; test crash injection at each write boundary and replay idempotence.
- If a historical checkpoint/cursor pair is already inconsistent, loading will now fail and require explicit operator recovery. Do not delete state or silently retrain. Maintain backup of both files.
- Verify the new test under project CI and compare against other active JEPA branches before integration. Full V13 suite, Android native overhead, retention, full WorldJEPA and GGUF weight plasticity remain UNVERIFIED by this change.
- Existing historical negative gates STEP2 UTILITY_FAIL and B3 L1 FAIL remain unchanged.

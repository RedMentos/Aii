# Run624 prereg — bounded fair Sleep A digest across >8 sessions

2026-10-27 UTC. **Exact review base** Run623 PR618 head `608d7be0b214e66771ae70cba2d61c8b3a95a6a5` (not main). This package owns only `v13/code/v13/sleep_offline.py`, a new `test_run624_sleep_session_fairness.py`, its dedicated workflow and scoped proof files. No edits to frozen Canon, model hashes, source cohorts, approval/age rights or unrelated agent files.

## Observed source defect and hypothesis

Current `sleep_offline.digest` selects only the eight sessions with newest FINAL assistant IDs (`ORDER BY last DESC LIMIT 8`). With nine or more sessions and ongoing traffic in the newest eight, an older session's undigested FINAL turns can be skipped forever. A per-session 64-turn drain is insufficient if the session is never selected. Hypothesis: retain a bounded newest-session fast lane while round-robin selecting remaining sessions by stable session ID with a persisted cursor. Revisit stale/deferred pairs only through the existing source-validating history path.

## Frozen checks (before implementation)

- Construct >=12 actual isolated SQLite Runtime chat sessions with FINAL user/assistant pairs. First digest visits <=8; after two digest cycles **all 12** have one exact, source-valid digest entry; no duplicates after repeated cycles.
- Keep the newest four sessions eligible on each cycle while older sessions rotate; continue to drain after fresh turns in hot sessions.
- Persist round-robin cursor across Runtime restart, visit all >=17 sessions in bounded cycles, preserve current active chat and source isolation.
- Corrupt cursor type/size fails closed before a digest state write. Read-only digest view, fact authority 0, no model or training.
- Existing Run609/610/612 and `test_sleep_offline` SQLite tests must pass unchanged. Source-only exact-head CI, privacy scan and SHA-closed raw output. Record original RED against the exact Run623 source, then patched GREEN, with separate exits.

This is a functional Context OS/Sleep A liveness fix, not a semantic utility, native training, STEP2/B3, Body-JEPA, or Redmi acceptance claim. Original gates remain FAIL/UNAVAILABLE.

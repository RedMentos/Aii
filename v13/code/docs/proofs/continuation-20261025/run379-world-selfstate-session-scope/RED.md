# Run379 RED evidence (pre-production patch)

2026-10-25 22:09 UTC; PR #374, independent review branch `codex/world-selfstate-session-scope-run379-20261025`, exact checked-out HEAD `9c4f2c4805649113ad5601d7ba341fe70a31bfd2`; GitHub Actions run **40238849034**, job **121306108635**. Workflow check failed **as expected**, not infrastructure failure.

Actual Runtime/SQLite unittest: **12 tests, 11 PASS, 1 FAIL** in 0.661s. `test_cross_session_accounting_terminal_and_restart` failed on its first cross-session assertion: session A expected 1 unfinished action but `WorldState.self_state()` reported 3 (global A+B). Single-session baseline PASS; inherited `tests.test_world_state` and `tests.test_world_multiaction_recovery_run343` PASS. `compileall` PASS; official privacy scan CLEAN. No model/native/Redmi inference was executed.

GitHub Actions uploaded immutable RED raw evidence artifact **12615932337** (5 files), at run 40238849034. Runner source SHA256: `v13/code/v13/world.py` = `f7d0a1af971565b6ac8d3ff5b5f6451dd068808ef21419b0e64c7e78cba7e9e3`; new test = `3377216f1b246e83838b41c78900ebb04240646a94c7ebcfd94589761e2430f9`. The raw artifact is in GitHub Actions retention (30 days); **not** yet independently downloaded or privately backed up. Do not claim private-byte verification. Existing negative blueprint gates unchanged.

Next command: patch only `WorldState.self_state` unfinished SQL with `JOIN events e ON e.id=a.event_id WHERE e.session_id=? AND a.status IN (...)`, binding `(r.session,)`, then rerun exact workflow, inspect raw log, privacy scan, and checkpoint GREEN.
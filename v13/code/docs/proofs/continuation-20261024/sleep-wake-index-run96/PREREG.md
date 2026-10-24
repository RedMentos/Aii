# Run96 — idle wake must see new source-bound corrections

Base: Run95 PR #127 checkpoint `8a43aed3bb6782bbea4fe3b3dd7d584e6aceb11a`. Run94 World Model remains independently owned and untouched.

Owner: `v13/code/v13/sleep.py` only `SleepRuntime.tick`, new `tests/test_sleep_wake_index_run96.py`, isolated `.github/workflows/v13-run96-sleep.yml`, this proof folder. No canonical/registered cohort/shared workflow edits.

Hypothesis: a new human correction writes a durable `replay` row in `Memory.feedback`, but `SleepRuntime.tick` consults only previously persisted `SLEEP_REPLAY_SCHEDULE` and fails to post `REPLAY_DUE` after wake idle threshold. Thus first correction can wait until the full Sleep interval despite wake replay policy.

Preregistered RED: real Runtime/SQLite correction, empty persisted schedule, forced idle tick with dispatch mocked (no job run), expect `REPLAY_DUE` and durable index. Controls: disabled policy and busy foreground must not schedule or index; CAS conflict must fail closed rather than post unpersisted due. Four tests plus inherited Sleep/age tests.

Narrow candidate after RED: bounded sync of new replay rows on idle wake check, persist with CAS before scheduler post; on CAS failure reload only persisted schedule. No native, no background authority change, no user/age gate promotion.

Evidence: Linux software/SQLite only. STEP2 UTILITY_FAIL, B3 L1 FAIL, Body-JEPA UNAVAILABLE, jepa_weight=0, Z6a/Z8 FAIL, full V13 INCOMPLETE.

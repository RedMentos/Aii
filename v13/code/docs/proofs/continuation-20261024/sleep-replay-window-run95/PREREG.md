# Run95 — Sleep replay bounded-window fairness (test-first)

Base: Run93 branch `codex/context-exact-quotes-run93-20261024` @ `b54342c1278f78f509359b6daa8dd644e6f3a5d9`. Run94 is concurrently owned by another branch, so **no World Model files** are touched.

Owner: `v13/code/v13/sleep.py` only `ReplayQueue.sync`; new `tests/test_sleep_replay_window_run95.py`, isolated workflow `.github/workflows/v13-run95-sleep.yml`, and this proof folder. No shared handoff or canonical source edits.

Hypothesis: `SELECT ... ORDER BY r.created LIMIT MAX_ITEMS+1` chooses oldest replay entries, permanently excluding newly added human corrections once 2048 historical entries exist. Also `len(rows)>MAX_ITEMS` prevents stale-item retirement, potentially allowing schedule state to grow beyond MAX_ITEMS.

Predeclared RED checks: real SQLite with 2051 replay/event rows; newest three must be in schedule and due, oldest excluded, state <= MAX_ITEMS. Separate equal-created timestamp case must deterministically select newest by id. Existing Sleep A/B/C and age/default gates must remain unchanged.

Narrow candidate after RED: select newest bounded rows with deterministic tie-break; preserve chronological insertion among selected entries; retire outside-window entries without modifying original replay table or any sources; bound schedule size. No native/Redmi/utility claims.

Proof level: Linux software/SQLite only. STEP2 UTILITY_FAIL, B3 L1 FAIL, Body-JEPA UNAVAILABLE, jepa_weight=0, Z6a/Z8 FAIL and full V13 INCOMPLETE remain. Keep failed logs and CI run ids.

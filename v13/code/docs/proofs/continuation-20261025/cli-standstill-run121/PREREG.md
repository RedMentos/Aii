# Run121 — persisted standstill vs real CLI ask (preregistered RED)

2026-10-25 UTC. Exact base: Run120 PR #151 head `c7b8ebf5b9373de7d855d93ba4f97c32224fe1f6`, successful Actions run 40146585260. Owner: `v13/code/v13/__main__.py` (CLI only), new `tests/test_cli_standstill_run121.py`, new workflow and this Run121 proof directory. No Runtime/standstill/Store/Canon/model/registered-cohort edits. Other active owner files excluded.

## Hypothesis and test-first counterexample

`python -m v13 --home H ask 'Kopiere exakt: ...' --no-observers` calls `r.submit` and loops `while not r.idle()`. A persisted `:pause` or `:stillstand` intentionally keeps the queue unprocessed, so this user-facing CLI can hang indefinitely, create an unrequested queued turn and falsely imply progress. Test with **real** Runtime + SQLite, close, spawn a new OS process with a five-second timeout; expect exit 2, empty stdout, zero new queued turns, persistent pause/standstill unchanged. Explicit local release must restore successful exact-copy CLI. First run is expected RED; preserve CI raw log and exact head before editing.

Narrow planned fix: refuse `ask` when paused **before** accepting a turn, and refuse a paused transition during waiting without producing FINAL. No automatic resume or clearing human stop. Preserve original negative gates: STEP2 UTILITY_FAIL; B3 L1 FAIL; Body-JEPA UNAVAILABLE; jepa_weight=0; DS2 H2 FAIL; V13 INCOMPLETE. Linux software/SQLite only, no native/Redmi evidence.

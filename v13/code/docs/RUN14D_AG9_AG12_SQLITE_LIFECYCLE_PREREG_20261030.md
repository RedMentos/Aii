# Run14D prereg — real SQLite Age0 AG9/AG12 lifecycle and operator evidence (2026-10-30)

Owner GPT-6 scheduled continuation. Review-only child of Run14C combined AG9/AG12 branch at `bcdfaf324a1019222f6cc7c951438ea89be4dbc4`. Scope: new `tests/test_ag9_ag12_sqlite_lifecycle_run14d.py`, isolated Actions workflow and scoped checkpoint only. No Runtime, Store, Operator, Canon, cohort, model or scorer modifications.

## Required actual software path
Use a temporary real `Runtime(home)` with SQLite Store and `Operator(r).run(':growth eval')`, not an in-memory Store double. Record legitimate AG9 calibration outcomes, query malformed component read-side and assert abstain/no extra Store writes, evaluate AG12 with a deterministic oracle answer but NaN confidence and assert zero credited accuracy; verify `:growth eval` shows that exact diagnostic run and `:growth status` exposes the same read-only state. Close Runtime and reopen the same home; verify persisted AG9/AG12 state, original source/cohort hashes and Age0 `RECORD_ONLY`, no model/native/tool calls, no age/weight promotion. Add finite-confidence control where oracle remains correct, including after restart. Failures must remain visible; do not silently skip if no model or native runner is present.

Exact acceptance: test-first focused cases must fail on original AG9/AG12 source where invalid component throws or NaN falsely scores, then pass on the combined candidate; separate Linux-software-only source pins, compile, privacy, raw SHA256SUMS and private byte backup. No automatic production integration, STEP2/B3/Body-JEPA/JEPA/Redmi or whole-system promotion. The ongoing Run14C unfiltered full-suite remains independently required and must not be waived.

Next: add real-Store test and workflow, run candidate CI; preserve any failed attempts, verify original raw and private backup, update checkpoint and continue canonical implementation.

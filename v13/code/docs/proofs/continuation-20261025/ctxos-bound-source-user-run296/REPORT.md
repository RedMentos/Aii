# Run296 — source-verified Context OS user layout (software only)

2026-10-25 UTC. Base verified PR295 `22f88f982e3681d2701295a806f4e8ffc38f635f`; tested exact code head `3552709a56f6757b214d1a50bab8338375105965`; draft PR296. Independent owner: `v13/code/v13/context_os.py`, new 10-case Runtime/SQLite test, dedicated CPU workflow, this proof. No PR284 Runtime or PR293 output adapter changes. No model/seed/registered cohort/Canon/approval/age changes.

## Concrete implementation

New `source_bound_user` Context OS layout is **not the default**. The existing default `append_only` and SHADOW mode remain. Only explicit operator layout + ACTIVE and declared `consecutive_user` template capability can apply it. A learned `ACTIVE_VIEW` correction must carry an exact current `matched_query` and the existing approved relevance marker; the planner rechecks source topic/entity, a conservative `relevance>=0.5` floor, live SQLite memory and F1/F5 HumanDecision/feedback/source bytes through `Memory._verified_rows`, same-session or explicit global scope, and rejects conflicting active values, forgery, forgotten/deleted sources and ambiguous matches.

When exactly one current correction survives all checks, the planner moves it (not duplicates it) from the system volatile layer into a separate JSON-quoted **user-context** message immediately before the actual query. It keeps the other volatile layers and history in order, records the source ref in `ContextPlan.bound_source_refs` **and** `ContextPlan.provenance`, respects compaction and budget, and preserves actual Store integrity. No learned permission, native parameter or output authority is gained. Without a verified current source, the layout falls back to existing legacy; this **does not** prove the legacy path cannot leak a stale source, and is not an output verifier.

## Evidence and gates

- Independent local Linux Python 3.13: **71/71 PASS** across new 10-case Runtime/SQLite/lineage tests and existing Context OS, warm authority, memory F1/F5 and recall regressions. One initial local attempt included a nonexistent test module; corrected the selection without altering a test. A test-first local Runtime mock initially lacked `retrieval_score`, corrected to match actual memory packet shape. No native model was launched by these tests.
- Exact-head GitHub Actions Run296 `40202057893`: **71/71 PASS**, official privacy CLEAN, raw exit codes 0/0. Closed raw artifact `12602072005` ZIP SHA256 `969d9b21480aa7fbd2c8445819cf5e2f979200461b1409256cb47c17d9201187`.
- Focused source-bound workflow `40202057891` same exact code head: **401/401 PASS** and extracted Phone **114/114 PASS**, source manifest **1012 files**, privacy CLEAN; outer artifact `12602426239` ZIP SHA256 `2689fc13e85111d8c8b80eda3dfe6f042a08316c86cbcab28c68597aa932e032`, inner Phone ZIP SHA256 `ed63537fdf899d0747646c281719cc863123da1b6dbe81a5445dd8e83123b466`. These are Linux software/source packaging, not Redmi tests.
- Raw software and source ZIPs stored in private Library `/V13-Inquisition/Proofs/Run296/`. Raw ZIP was materialized back and byte/SHA256 matched. Source ZIP was also materialized back and independently verified SHA256 plus byte equality (`2689fc13e85111d8c8b80eda3dfe6f042a08316c86cbcab28c68597aa932e032`).
- Exact Git blobs: Context OS `f4811bc25b7947a0aa00d47b259909e1a8fdf2f0`; new test `f696bf94290092fa9dd18000a7a3afb45f0ec3a3`; workflow `fec93c3e380b1549a85586f7e2fbbee2b52516af`. Canon SHA256 unchanged `3423906b01b24443fcef733fb5c7ef47296963df63e603d8f843c99d544877ee`.

## Why this is not a native acceptance

Run295 actual native B1 prompt-only user-source arm copied `400 Euro` into unrelated questions and another project. The new layout adds an **upstream verified relevance and source gate**, but no actual native B1 call used this integrated layout in Run296. A fake runner in the Runtime test proves message wiring and SQLite integrity only. No hallucination reduction or B1 semantic utility is claimed.

Next: separately preregister a serialized pinned native end-to-end `tests/integration_retrieval.py` replay with this opt-in layout and actual template probe; preserve the original system-only audit as a negative gate, add a separate user-source delivery audit and native wrong-topic/entity output checks before any production enable. Do not edit the registered cohort or original acceptance thresholds.

Unchanged: `STEP2 UTILITY_FAIL`, `B3 L1 FAIL`, `Body-JEPA UNAVAILABLE`, `jepa_weight=0`, Redmi UNMEASURED, V13 INCOMPLETE.

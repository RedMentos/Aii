# Run72 — read-only C3 schema callback mutation boundary (2026-10-31)

**Scope:** isolated review-only child of Run71 PR #1431, exact parent `6fa7c9c277bf271b5e3a17c4d4e1a3f57cdaefc7`. Source under review: `v13/code/v13/jef_c3_schema_source_recheck_shadow.py` Git blob `18aaaa86f416a1df9a703b86b9d12215ad1c00c5`. Preserve Run71 donor SHA, Run70 seed743 model and native scientific RED unchanged.

**Observed defect (source review):** the callback guard compares only counts in six SQLite tables, the source envelope, and source hashes. A callback can UPDATE an unrelated existing Store row, or UPDATE then restore it, without changing any table count or bound source. The current guard can report `FORMATTER_MATCH_SHADOW` despite the side effect. A callback may also write through another SQLite connection.

**Plan / verification fixed before code:** add a diagnostic SQLite mutation epoch around callback: connection `total_changes`, `PRAGMA data_version`, and `in_transaction`, alongside the existing footprint and source checks. Add real-Store tests for same-connection unrelated UPDATE, UPDATE then restore, and second-connection committed mutation, plus unchanged pure-callback acceptance and existing negative cases. Return only a fail-closed SHADOW verdict; no claim that detection rolls back side effects or makes arbitrary callbacks safe. No runtime activation, no user-visible output, no learning or TTY authority.

**Evidence levels:** this is software/SQLite integration, not native C3, Redmi, semantic utility, B3 or JEPA. Run70 SOURCE_SCHEMA 3/6 RED, full-suite 4 FAIL/66 ERROR/28 SKIP, Age0 RECORD_ONLY, STEP2 UTILITY_FAIL, B3 NO_PROMOTION, Body-JEPA UNAVAILABLE, World-JEPA SHADOW, jepa_weight=0, whole V13 incomplete.

**Owner:** GPT-6; only the isolated branch's adapter, tests, CI workflow and this checkpoint. No changes to other owners' branches. **Next:** patch, run tests, retain raw evidence, verify remote bytes, independent review; then move to a different substantive Canon package.

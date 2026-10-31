# Run72 — read-only C3 schema callback mutation boundary (2026-10-31)

**Scope:** isolated review-only child of Run71 PR #1431, exact parent `6fa7c9c277bf271b5e3a17c4d4e1a3f57cdaefc7`. Source under review: `v13/code/v13/jef_c3_schema_source_recheck_shadow.py` Git blob `18aaaa86f416a1df9a703b86b9d12215ad1c00c5`. Preserve Run71 donor SHA, Run70 seed743 model and native scientific RED unchanged.

**Observed defect (source review):** the callback guard compares only counts in six SQLite tables, the source envelope, and source hashes. A callback can UPDATE an unrelated existing Store row, or UPDATE then restore it, without changing any table count or bound source. The current guard can report `FORMATTER_MATCH_SHADOW` despite the side effect. A callback may also write through another SQLite connection.

**Plan / verification fixed before code:** add a diagnostic SQLite mutation epoch around callback: connection `total_changes`, `PRAGMA data_version`, and `in_transaction`, alongside the existing footprint and source checks. Add real-Store tests for same-connection unrelated UPDATE, UPDATE then restore, and second-connection committed mutation, plus unchanged pure-callback acceptance and existing negative cases. Return only a fail-closed SHADOW verdict; no claim that detection rolls back side effects or makes arbitrary callbacks safe. No runtime activation, no user-visible output, no learning or TTY authority.

**Evidence levels:** this is software/SQLite integration, not native C3, Redmi, semantic utility, B3 or JEPA. Run70 SOURCE_SCHEMA 3/6 RED, full-suite 4 FAIL/66 ERROR/28 SKIP, Age0 RECORD_ONLY, STEP2 UTILITY_FAIL, B3 NO_PROMOTION, Body-JEPA UNAVAILABLE, World-JEPA SHADOW, jepa_weight=0, whole V13 incomplete.

**Owner:** GPT-6; only the isolated branch's adapter, tests, CI workflow and this checkpoint. No changes to other owners' branches. **Next:** patch, run tests, retain raw evidence, verify remote bytes, independent review; then move to a different substantive Canon package.

## Terminal software evidence / persistence

Original Actions **41183059853** at exact HEAD `583d75170a2e2cf41efdb8b361c2c55e2d1bd72c`: terminal **SUCCESS**. Real SQLite Store tests: source-recheck **14/14**, schema→C5 DRAFT **7/7**, Run71 cross-adapter **3/3**; total **24/24**. All nine required stage exit receipts zero, privacy CLEAN, compile/diff PASS, Canon and source/test Git blob pins exact. No native model invoked. Raw original artifact ID **13034879796**, ZIP SHA256 **`ba8de3e17028ec4d7dfa4b65c2d5df5b4caa9d10c8a06eef37f0ab624a818112`**, CRC PASS, **20/20** SHA256SUMS entries verified. Original GitHub artifact saved privately at `/V13-Checkpoints/2026-10-31/Run72-C3-Callback-Mutation/ORIGINAL_ACTIONS_41183059853_SHA_BA8DE3E1.zip`; re-materialized Library bytes compared **identical** (SHA and `cmp`).

Source blob `1d7c89dd80cf827c6f7f1efd3377bd28aa955e78`, test blob `e510d31398fafcfda9b0459bb59f1569e668227e`, both fetched from remote and matched CI pins. **Review caveat:** this guard detects SQLite changes on the observed connection and committed changes from other SQLite connections, but does not prevent the callback's side effects or detect arbitrary filesystem/in-memory mutation. It is not a security sandbox; no callback should receive untrusted Store access. No production activation, native utility, STEP2/B3/JEPA/Redmi or whole-system promotion.

**Next command:** independently review branch diff against parent `6fa7c9c277bf271b5e3a17c4d4e1a3f57cdaefc7`; if approved, integrate only after Run71 owner review. Continue independent JEF/C2/B1/B2 semantic utility and native learning packages. **Remaining platform budget:** UNKNOWN.

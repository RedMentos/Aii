# Run647 — AG5 curiosity error exactly once per source event (2026-10-27)

Review-only child of Run646 PR647 exact head `27b27d6a2d8699c112a6eee093e2edcc7e1007cd`. Run644 had corrected false zero-error on missing or abstaining FINAL answers, but duplicate `goal_turn` calls still appended independent AG5 errors and visits for the same source event, distorting rolling learning-progress and novelty used by later Age-gated practice. The new `Curiosity.observe_once` atomically persists both region update and event/session/region receipt in one SQLite transaction. First terminal outcome wins, even across reopen; distinct events still count. `Curiosity.observe` for explicitly unbound/synthetic observations is unchanged.

## Preregistered original RED

Prereg `536d8a15086654741e31fa05381df254786def67` and tests `04ab6b53780d38180f19900c859661d4b7dba90e` preceded source. Actions `40443594644` at `f9e405d1f6eb91557eaf1a222855de86c5492ff8`: 64 tests, **3 FAIL and 10 ERROR** (seven parameterized invalid-error subtest errors plus three missing-method errors). Duplicate ERROR gave 2 visits and duplicate FINAL gave 2 visits; ERROR→FINAL falsely appended a success proxy. Original ZIP artifact 12707532731, SHA256 `dc3a0457d44b4c0f9a8dc567676d0d9168caa3bf3bf714fa7c3e525444cb18ca`, CRC/source/exit checked.

## Exact GREEN and durable proof

Atomic source commit `7bd859a91645d501b72342dc67223e15d2ea9bf5`; Actions `40443706220`: **64/64 PASS**, compile PASS, privacy CLEAN. Tests include same-event duplicate ERROR/FINAL, first terminal status, restart, session/region isolation, invalid numeric errors, forced post-update serialization rollback, distinct-event positive control, Run644/Run645/Run646 and adjacent JEF/growth regressions. Original ZIP artifact 12707078420 SHA256 `77d8757331c8194add90b3da78267c5a52b2a2c3cbd19468fa979e038bdc9974`, CRC/source/exit checked. Both original raw ZIPs saved in private Library `/V13-Checkpoints/2026-10-27/Run647/` and read back byte-identically.

## Limits / next

Software-only SQLite evidence, not native inference, semantic correctness, Android or AGI. Does not change whether a later FINAL might separately complete a goal; only AG5 learning-error accounting is event-once. No age/approval/model/cohort changes. Full suite remains RED on parent (4335 tests, 5 FAIL, 73 ERROR); STEP2 UTILITY_FAIL, B3 L1 FAIL, Body-JEPA UNAVAILABLE, `jepa_weight=0`, Redmi UNMEASURED and V13 INCOMPLETE remain. Independent integration review required. Next priority: substantive World-JEPA/Body/C3 utility and source-disjoint native tests, respecting concurrent owners.

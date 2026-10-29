# Sleep S7 user-event cursor overflow handoff — 2026-10-29

## Lineage and closed original RED
- Review-only child of PR #1113 exact parent `f21e965cba76f314ecc8444d23cd2e67e759f567`. Own `v13/code/v13/history.py`, `sleep_offline.py`, new test, prereg, CI, handoff and branch-scoped BUILD_STATE only. No production merge.
- Prereg `779917e9c16058a39160fe9b838b2846f1b5c004` before test `25837a4fa05b38805bbfd06b44eaba1c6fe688fc`.
- Original RED Actions `40909086524` exact `05c21f21f7c9e09ff2c6097198a8d7a92d73c4d6`: 3/3 FAIL (130 reverse completions, late first predecessor, revoked source), digest returned zero after all answers FINAL. Raw artifact `12913380462` SHA256 `452e10bbd6b68bf0cbed16bb7013bef5edc659c213e3289d16c999214442ae0b`, CRC and 5/5 SHA256SUMS verified; privacy exit0. Private Library backup `/V13-Checkpoints/2026-10-29/Automation10-Review/S7_USER_CURSOR_ORIGINAL_RED_40909086524_SHA452e10.zip` saved.
- Candidate `20256768658bf62534a84422e5e689f031108fab` history event-ID lineage selector; `ddef564e46d4266c3a4c6d28c670b369cbcbb842` S7 user cursor. New `user_until` migrates from legacy safe assistant high-water. Up to 64 oldest user events per run, source-valid FINAL pairs only, no crossing pending predecessor, 8 sessions and 96 entries unchanged.
- Source-only Actions `40909329351` at `ef7b6bc811a14b1dad744d2c00cac8373f3cb7ad` pending at handoff. Parent PR #1113 software full GREEN at its exact head is distinct evidence; not inherited as proof for this patch.

## Next commands
1. Fetch Actions run `40909329351` and artifact, verify HEAD, focused/full/compile/privacy/diff exits, SHA256 ZIP/CRC/internal SHA256SUMS. Focused command is workflow-owned and must include `tests.test_sleep_user_cursor_overflow_20261029`, `tests.test_sleep_interleaved_final_20261029`, session fairness, backlog, Context OS/Sleep source integration and `test_sleep_offline`.
2. Correct any focused failures; review old `until` migration, revoked source handling, assistant duplicates, session fairness and restart. Never weaken native_history source/rule validation or fabricate native evidence. Preserve all failed attempts.
3. Keep PR #1118 draft. No merge without review and exact-head verification. Continue independent blueprint work.
4. Negative gates: Age0 RECORD_ONLY, STEP2 UTILITY_FAIL, B3 L1 FAIL, Body-JEPA UNAVAILABLE, LP3 FAIL, jepa_weight0, AG6 unapproved, V13 incomplete.

## Follow-on source integrity review (CI pending)
- Source `11d4ac333fc6d2808e75d33baffd71d7a7bba357` revalidates all 96 retained digest entries in bounded event-ID batches rather than a latest-message window that loses old users under reverse FINAL ordering. `422bea2a25ec49f0289c3750cc764bfd98d8b544` preserves valid unrelated entries if one cached row is malformed. `bd22e2cdf81ecd92f8a2dd58e2370a3f23614bd5` fixes malformed selector input handling. New tests `a4863db0cbd76b3b11dc110ffdb27a05456cf5b6`, `72db6ef710f5ab03d5f53b1b4de74ac84eacb7a3` require 96 source-valid visible entries and malformed-entry isolation. Workflow `ef77208c4312a6deb7a8d5e3da9705902ba2381b` includes history.py trigger.
- Several source-only CI runs were triggered by sequential review commits. The original `40909329351` tests an earlier source snapshot; only a run whose exact HEAD contains the final test commit can verify the final candidate. No source-only GREEN claim until raw checks close. Preserve all intermediate raw results and negative gates.

# Independent AG5+World merge-candidate follow-up — guide regression (2026-10-27)

Base exact PR #665 head `763476dd368909e4feff133310872ad5eaf75dc2`; new child review branch only. Original disposable Actions `40458296328` at that head performed exact 3-conflict resolution (RESOLVE0, EXPORT0, FOCUSED 84 tests PASS/2 SKIP, COMPILE0, PRIVACY CLEAN) but broad merged suite **RED**: 4424 tests, 7 FAIL, 73 ERROR, 28 skipped. The known AG5 parent baseline was 5 FAIL/73 ERROR. Two additional FAIL entries are duplicate discovery of `test_phone_halt.GuideTests.test_every_operator_command_is_explained`: the World `:ersetze` command was grafted into operator HELP but not the AG5 user guide `docs/BEFEHLE.md`. The original ZIP artifact `12714150443` SHA256 `f6fe7cb6c8735bf66d68d09b5b88e743c941b30376bbd53e1aaf17d4a1e2499d` was CRC checked, HEAD/exits examined, privately backed up and byte reverified.

## Acceptance

- Extend exact-stage resolver to insert one clear `:ersetze route|list|undo` guide entry into `docs/BEFEHLE.md` on the **disposable merged tree**, with exact anchor and fail-closed if unexpectedly changed. Also align `:effort detail|gist` documentation.
- Preserve all three original conflict-stage SHA checks and the AG5 operator idle locks, bounded chats, language control, World shadow hard bans and native forecast fixture. No model/source cohort changes.
- New isolated CI: exact 3-conflict disposable merge and resolver, focused integration regression including `tests.test_phone_halt`, `tests.test_route_supersede`, `tests.test_language_operator_run620`, `tests.test_operator_config_atomic_run623`, `tests.test_world_console_shadow`, `tests.test_toolforecast`; compile and privacy scan; raw ZIP retained.
- Do not claim full-suite green, production merge or AGI. Existing historical 5 FAIL/73 ERROR remain negative until separately resolved; no two-parent remote merge commit. This package removes one **new** regression, not all baseline failures.

Next command: run isolated disposable merge CI and compare raw focused exits, exact conflict set and stage blobs. Owner: GPT-6 independent AG5/World review, no edits to PR #665 or Claude branches.

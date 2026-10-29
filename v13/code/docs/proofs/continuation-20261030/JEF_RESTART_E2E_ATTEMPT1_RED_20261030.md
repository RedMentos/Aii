# JEF restart E2E first attempt — preserved RED (2026-10-30)

- Branch: `codex/v13-jef-restart-e2e-20261030-auto11e`, tested commit `e1e700a841ceaa3e813fe618c27d3afd9fe07740`.
- CI run `40972362311`: **failure**; artifact `12941315884`; downloaded ZIP SHA256 `530597ab865a9942264456c4b48e385f26cc7da687f92842f45865f9cc9e090f`. ZIP CRC and 18/18 internal SHA256SUMS verified.
- Raw focused suite: 36 tests, 1 FAIL, all other tests PASS. Failure at `test_duplicate_receipt_and_chat_scope_survive_actual_restart`: test incorrectly expected a new chat ID after `Runtime(home)` restart. Actual Runtime deliberately restores `last_session`; no model or learning failure was shown.
- Correction commit `a21cee08572399eceb6fbd89ed54d7dd22d1b59d`: assert preserved chat and receipt after restart, then explicitly call `:new` before testing foreign-session refusal. This keeps both original behavioral invariants and does not change runtime code.
- No gate promotion. The original failed raw is retained and must not be rewritten.

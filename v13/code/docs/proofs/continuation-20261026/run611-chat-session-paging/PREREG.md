# Run611 — persistent Termux chat list paging (frozen before edits)

2026-10-26 UTC. Owner GPT automation11. New distinct **persistent chat UI** functional package, child of verified Run610 PR605 remote head `8b1d9fa485e62c4f0ed0d14def853c202945b493`; not a Sleep/B3 helper. No active native job acquired.

## Observed gap

Current `:chats` runs `SELECT * FROM sessions ORDER BY created DESC` without any bound or cursor. After many saved conversations it materializes all sessions on the Android device and has no way to page to older chats. Tied created timestamps are not deterministically ordered. `:search` already supports bounded message-ID paging (Run600), but chat list does not.

## Frozen acceptance

1. Default `:chats` returns at most **50** newest sessions ordered by `created DESC,id DESC`. `:chats --before <Chat-ID>` fetches the next at most 50 strictly older than the identified cursor session, using lexicographic (created,id) keyset paging. No missing/duplicate IDs across 71+ sessions, including timestamp ties; exhausted page returns `[]`.
2. Preserve explicit access to the old full listing via `:chats all` (unbounded only on direct local user request); all returned rows preserve original `id,title,created` shape. No session switches, no mutation of persisted last_session; paging works across restart.
3. Missing, unknown, malformed, oversized and extra arguments fail closed without any mutation. `:open`, `:search`, `:export chat` unchanged. No model/age/tool permission required for local read-only listing.
4. Real Runtime/SQLite tests including >70 chats, equal timestamps, restart and original Run600/217/89 tests; source-only Actions CI and independent raw/sha/privacy checks. Keep any failures.
5. No model/native/Redmi evidence, no promotion of STEP2/B3/Body-JEPA/jepa_weight or full V13.

Owned `v13/code/v13/operator.py` narrow `:chats` path, `v13/code/tests/test_run611_chat_session_paging.py`, proof folder, new source-only CI workflow. Preserve Canon and all original cohort hashes. Next command: `cd v13/code && python -m unittest -v tests.test_run611_chat_session_paging tests.test_run600_chat_history_navigation tests.test_multichat_backup_restore_run217 tests.test_phone_chat_sessions_run89`.

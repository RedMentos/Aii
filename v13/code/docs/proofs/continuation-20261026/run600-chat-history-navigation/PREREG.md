# Run600 prospective registration — persistent chat history navigation

UTC date: 2026-10-26. Owner: GPT automation11. Base: PR594 verified remote head `1b04791e0bfb30c4fec4a76e5b953dd3f41da2d6`; review-only branch `codex/automation11-run600-chat-history-navigation-20261026`. This is a new functional UI package, not a reinterpretation of frozen SourceHandoff.

Problem: `:search` exposes no message ID and cannot page beyond 30 hits. `:export chat` only exports the currently open session; exporting a previous chat requires switching active state. These limit sustained, persistent Termux use.

Files owned: `v13/code/v13/operator.py`, `v13/code/docs/BEFEHLE.md`, new `v13/code/tests/test_run600_chat_history_navigation.py`, new isolated `.github/workflows/run600-chat-history-navigation.yml`, this proof folder. No changes to canonical SSOT, model, source cohort manifests, existing proof bytes or other owners.

Proposed: retain old `:search <Text>` semantics but include message `id`, accept optional trailing `--before <positive message id>` with strict parsing and literal SQL LIKE escaping. New `:export chat [json|md] [Chat-ID]` exports an explicitly named existing chat from its independent WAL snapshot without changing current session or last_session. Keep legacy no-ID form unchanged. Never invoke models, tools, learning, age changes or external communications.

Acceptance: real SQLite/Runtime/Operator tests for >30 cross-session matches, cursor no-duplicates and literal %/_ escaping, malformed cursors, legacy search, current and historical JSON/MD export, invalid IDs, active session/last_session stability and restart. Run existing chat export/WAL tests, compileall, public privacy scan and SHA-closed CI raw. Exact source head and tests recorded; no native/Redmi claim.

Negative gates preserved: STEP2 UTILITY_FAIL, B3 L1 FAIL, Body-JEPA UNAVAILABLE, jepa_weight 0, V13 INCOMPLETE. Full unfiltered Run596 suite remains RED 4 FAIL/65 ERROR and is not reclassified. No user data in public artifacts.
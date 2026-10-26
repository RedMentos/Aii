# Run612 — user-visible Sleep A digest backlog status (preregistered)

2026-10-26 UTC. Owner GPT automation11. Child of verified Run611 PR606 exact `b292302dff5b3c425e97010bc5460e4cf83eaac2`. Distinct user-visible Context OS/Sleep operational feature; no native/model/learning work.

## Observed functional gap

Run609 oldest-first Sleep A processes at most 64 completed assistant turns per cycle and retains deferred IDs. The local user command `:sleep digest` shows source-verified digest text, but neither it nor `:sleep status` exposes whether the backlog is drained. Users cannot tell whether to schedule another `:sleep run a`, especially after a restart or v1 migration. This is a real operational usability gap for long sessions.

## Frozen acceptance

1. Add read-only local command `:sleep digest status` returning the **current session only** with bounded counts: processed cursor, retained entries, deferred IDs, unscanned assistant rows, unscanned FINAL assistant rows, legacy backfill flag, `has_work`, 64-turn per-cycle cap and `fact_authority=0`. Do not expose source text or fabricate validity; unscanned counts explicitly are **not** source-validated facts.
2. Before digest with 4 source-valid turns, status reports 4 unscanned; after one digest 0; after another turn 1; after restart remains consistent. Legacy cursor_version missing must report backfill required/has_work even when no rows above its cursor, without mutating stored state.
3. Invalid persisted state (wrong cursor/pending/entries shape) fails closed; no digest/migration triggered by status. Existing `:sleep digest`, `:sleep run a`, `:sleep status`, Sleep A gating, cancellation and 64/128 limits unchanged.
4. Real SQLite/Runtime and operator tests, existing Run609/610 Sleep tests, privacy, SHA-closed source-only CI; preserve failures. No native or Redmi proof and no gate promotion.

Owned narrow `v13/code/v13/sleep_offline.py`, `v13/code/v13/sleep.py`, `v13/code/v13/operator.py` HELP only, new tests/proof/workflow child. Original Canon, model hashes and all Age/approval gates untouched. Next command: `cd v13/code && python -m unittest -v tests.test_run612_sleep_backlog_status tests.test_run610_sleep_partial_pair tests.test_run609_sleep_digest_backlog tests.test_sleep_offline`.

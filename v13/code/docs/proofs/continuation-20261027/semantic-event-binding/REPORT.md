# WP-N8 semantic event-bound one-shot snapshot — review checkpoint

Date 2026-10-27 UTC. Owner GPT-6 continuation. Review-only child of PR #743 exact original parent `736a75756e8095c97b9ce738c68c2c4ae3fbde62`; prereg `a73e91daa392533a28f7887d30e0f8c7a8998cb4` before tests and runtime patch.

## Counterexample and repair

PR #742 clears old semantic snapshots in `Memory.recall`, but `Runtime._turn` skips that call for fixed-policy responses. `episodes.observe_turn` previously checked only query text digest, so a repeated identical fixed-policy turn could consume the previous event's embedding. This is a cross-event provenance failure in A1/WP-N8 boundaries, not an altered stored human fact.

`SemanticKeys` now accepts an optional current-event getter, captured at similarity-call entry; `semantic_memory.attach(runtime)` supplies `runtime.turn_event`. Only a completed successful similarity call publishes `event_id` with its query vector. `episodes.observe_turn` requires both matching event ID and digest, then consumes the snapshot once (identity-safe clear). Direct synthetic callers without an event ID remain usable for relevance tests but cannot supply episode semantic authority. Frozen `runtime.py`, model files, cohorts, learning/age gates and SSOT unchanged.

## Evidence

- First test-only RED `2cb39fb743af139125f20b2794c353cc4c875d53`, Actions `40540915462`: 31 tests, 1 expected FAIL + 1 expected ERROR, other four exits 0. Artifact `12749838465`, ZIP SHA256 `17475f612a766e52c2f002b2e99126e6cd86fda05b5f94be3c41c3666e7fdb24`, CRC clean, private backup.
- Extended test-only RED `b6f576b3c4f9da994b2fcec9bb7fec819f31da0a`, Actions `40540996042`: 32 tests, 1 expected FAIL + 2 expected ERROR (cross-event stale consumption, missing event binding, missing attachment binding), INSTALL/COMPILE/PRIVACY/DIFF 0, UNIT 1. Artifact `12750777193`, ZIP SHA256 `ef81616729bc7bc04536e0ef67a1352a14789dc90cb3190fbb1ed2a558165bd3`, CRC clean, private backup.
- GREEN source commits `5a4282bedea5660d8c9df5d5a4a6ee6a5db84ae3` (semantic event binding) and `52e2a859e0acd2bdfe9900a8feb6b570ef853a77` (episode one-shot consumer). Focused Actions `40541387673` **PENDING**, no PASS claimed.
- Full software workflow source `83a385f003b32b53ec6730365007d4709d1a10bb`, Actions `40541490277` **PENDING**, no PASS claimed.

Private artifacts under `/V13-Checkpoints/2026-10-27/Automation11N-Semantic-Event/`; public GitHub contains only synthetic tests, source, and nonprivate proof metadata.

## Gates / next

LP1 NO_ATTRIBUTABLE_GAIN; LP2 ALIGNS_NO_GAIN; BJ1 NO_SIGNAL; STEP2 UTILITY_FAIL; B3 L1 FAIL; `jepa_weight=0`; Age authority 0; Redmi unmeasured; V13 incomplete. No model/native or learned utility promotion. Next: inspect exact-source focused and full-suite raw exits, preserve failures and private byte-exact backup, independent review child PR; continue separate canonical work only after a verified checkpoint.

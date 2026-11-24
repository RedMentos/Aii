# Run117BZ BUILD_STATE — Sleep digest bounded oldest-first backlog

2026-11-01 UTC. Review-only child of Run117BY PR #1554 at exact parent `b0c47f8de311989a86415274d785d59f362b9988`. Owner: isolated Run117BZ branch; original Canon, frozen model/seed/cohort/runner hashes, prior native evidence and original negative gates unchanged.

## Functional repair

The existing `sleep_offline.digest()` read only the newest 64 turns and then set `until` to the newest FINAL assistant ID. If more than 64 turns accumulated between sleep cycles, earlier turns were silently skipped forever. Added bounded **oldest-first** paging to `history.native_history(..., after_id=...)` with the same source/rule/deletion validation, and changed Sleep to advance its cursor only through the scanned terminal assistant boundary. A pending assistant blocks cursor advancement until it becomes terminal; invalid/revoked sources never become digest facts. New `backlog_sessions` telemetry signals catch-up work still pending. Per-cycle work stays bounded at 128 message rows per session; existing 96-entry retention and all TTT/learning gates unchanged.

New real SQLite tests: 70-turn catch-up 64+6 with no duplicate, odd page boundary with a revoked source, pending-answer completion without skipped later turns, and typed/source-valid forward cursor. Existing Sleep/ContextOS live digest, TTT lineage and replay atomicity regressions included. Software only; no model or Redmi execution.

## Closed proof

- Terminal [Actions 41255065480](https://github.com/RedMentos/Aii/actions/runs/41255065480) SUCCESS at exact CI source `dff9c63ab3208b6c4f43da290fd46940ad3db0ff`.
- Original artifact `13062910495` 3,888 bytes SHA256 `5f13532858d02aa095c1842cef3610629d0261b2ffc6ea90d5c0dc86ef7b9ed3`. Independently downloaded: ZIP CRC PASS, **16/16** SHA256SUMS with exact coverage, **7/7** stage exits zero, **20/20** software tests PASS, py_compile PASS, privacy CLEAN, diff check PASS.
- Source blobs: `history.py` `867d06c230ed3860f12cb7d256579c07cb214e91`, `sleep_offline.py` `953fe609c105a9d22b6414085f123aae46f3a56d`, new tests `509abe0666881c952ff2c921975c961adc6cbe81`, Canon `218464b12a2d27d92524c751922fa8e1c3fb0ea7` unchanged.
- Private Library backup `/V13-Checkpoints/2026-11-01/Run117BZ-Sleep-Digest-Backlog/RAW_41255065480_sha5F135328.zip`; re-materialized and compared byte-identical to original.

## Negative gates, next work

Age0 RECORD_ONLY, STEP2 UTILITY_FAIL, B3 NO_PROMOTION, Body-JEPA UNAVAILABLE, World-JEPA SHADOW, `jepa_weight=0`, no native model, Redmi, parametric learning, output/tool authority or whole-system completion. The new paging API is additive; existing tail callers remain unchanged. No approval to activate learning or higher ages is inferred.

Exact independent review command: `cd v13/code && python -m unittest -v tests.test_run117bz_sleep_digest_backlog tests.test_sleep_offline tests.test_sleep_digest_live_lineage_run208 tests.test_sleep_ttt_source_lineage_run207 tests.test_sleep_replay_enqueue_atomic_run12i`. Next integration step: run broader ContextOS/Memory/Sleep suite on this branch and investigate any RED without changing preregistered evidence; then measure actual on-device long-session backlog when Redmi is available. Current execution budget UNKNOWN.

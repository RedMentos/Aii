# Run117CB BUILD_STATE — fair bounded multi-session Sleep digest

2026-11-01 UTC. Review-only child of Run117CA PR #1556 at parent `efe863b14d1204c95621297fa36d888981ec2b2c`. Owner: isolated Run117CB branch. Canon and all frozen model/seed/runner/cohort artifacts unchanged.

## Functional repair

The previous Sleep `SESSIONS_MAX=8` query selected only the eight **most recently active** sessions, potentially starving older sessions forever when there were more than eight. Replaced the permanent newest-eight filter with a per-cycle bounded scheduler: enumerate sessions with FINAL assistant messages, filter those whose newest FINAL exceeds their persisted digest cursor, order by oldest pending cursor then deterministic session ID/last, and process up to eight. New `deferred_sessions` count records remaining unselected sessions; `backlog_sessions` continues to record incomplete per-session turn pages. No change to exact source validation, digest authority, 96-entry retention, learning/TTT gates or native model execution.

Three real Store tests: 10 sessions caught up 8+2, 12 sessions with four already-processed sessions becoming busy while four unseen sessions still get processed, and persisted restart with source revocation. Existing Run117BZ 70-turn backlog, Run117CA live ContextOS/C3, Sleep, lineage and ContextOS regressions rerun.

## Closed evidence

- Terminal [Actions 41255524536](https://github.com/RedMentos/Aii/actions/runs/41255524536) SUCCESS at source `9526618436928e388c33ed02f0b7fd0616553604`.
- Original artifact `13061949961`, 4,797 bytes, SHA256 `5e4184b41d73b2597a028cbb8f694a64b8df803a0171115031851fa7b8489ba0`. Independently downloaded ZIP CRC PASS, **16/16** inner SHA256SUMS exact coverage, **7/7** stage exits zero, **49/49** software tests PASS, py_compile PASS, privacy CLEAN, diff check PASS.
- Source blob `sleep_offline.py` `55cc54a510501ba4b1465254beaecd9ec81ec6db`; test blob `adc3143a9622797fb4f374154d2e0663ec3ba6b7`; history blob `867d06c230ed3860f12cb7d256579c07cb214e91`, Canon blob `218464b12a2d27d92524c751922fa8e1c3fb0ea7` unchanged.
- Private Library backup `/V13-Checkpoints/2026-11-01/Run117CB-Sleep-Session-Fairness/RAW_41255524536_sha5E4184B4.zip` re-materialized byte-identical to original ZIP.

## Limits and next command

This is a software source-valid fairness improvement, **not** native Sleep learning or Redmi measurement. Age0 RECORD_ONLY, STEP2 UTILITY_FAIL, B3 NO_PROMOTION, Body-JEPA UNAVAILABLE, World-JEPA SHADOW, `jepa_weight=0`, no new output/tool/learning authority, whole-system incomplete. The scheduler enumerates all FINAL sessions to select eight; a very large Store still needs measured Redmi CPU/memory cost and bounded indexing before claiming long-term scaling.

Exact review command: `cd v13/code && python -m unittest -v tests.test_run117cb_sleep_session_fairness tests.test_run117bz_sleep_digest_backlog tests.test_run117ca_sleep_context_consumer tests.test_sleep_offline tests.test_sleep_digest_live_lineage_run208 tests.test_sleep_ttt_source_lineage_run207 tests.test_context_os tests.test_context_sleep_f5_crossorgan_20261028`. Next package: measure long-session/multi-session overhead and validate independent source-revocation/restart under load; otherwise return to higher-priority STEP2 and Body-JEPA utility gaps. Remaining platform budget UNKNOWN.

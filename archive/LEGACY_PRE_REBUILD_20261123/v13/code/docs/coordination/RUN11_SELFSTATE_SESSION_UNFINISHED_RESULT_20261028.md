# Run11 F3 SelfState session-local unfinished actions — GREEN review candidate (2026-10-28)

**Owner:** GPT-6, draft PR #864 child of #863. Prereg `777dfd5ba28bd9c25705aea1fa54a0ef99031a38` preceded test/source. Production/main, Canon, models, native source pins, Age/approval untouched.

## Problem and actual RED

`SELF_MODEL:<session>` was keyed by session but counted all `DISPATCHED`/`OUTCOME_UNKNOWN` actions globally, falsely reporting old-session pending work as current. Source-pinned synthetic Runtime/SQLite [RED 40645249350](https://github.com/RedMentos/Aii/actions/runs/40645249350): 11 focused tests, 2 expected failures, 9 PASS (including all four #863 multi-action tests). Raw ZIP SHA256 `f65557826513356bc623cc3c8edd28e20c71358dfb1a305bc548bdcf07ee62b3`, CRC/16 hashes and private Library byte-exact readback. An intermediate [40645398569](https://github.com/RedMentos/Aii/actions/runs/40645398569) was RED only for the pre-update workflow source pin; raw ZIP SHA256 `b9a0bab2cd728090ab5cc44eec3aa43c05235d594f6e7fd2aa81f44be476a86e` retained in private Library.

## Change and GREEN

`world.py` blob `13f77eb3956ea1e4545234ee2eecc1bf56b60c60`: `unfinished_actions` now joins `actions` to `events` and binds `e.session_id` to current runtime session. Other self model fields unchanged. New two-test synthetic Store/Runtime regression blob `bdeae71f380ab7d83f61acdf6adf69780b7e0745`: old DISPATCHED and OUTCOME_UNKNOWN do not leak, FINAL no longer pending, restart retains scope.

[GREEN Linux software 40645410037](https://github.com/RedMentos/Aii/actions/runs/40645410037) at exact source head `d82292fe80a3b0706a21a1010335be0328c41461`: **11 focused PASS; 2225 full PASS, 1 skipped**, all BLOBS/INSTALL/FOCUSED/FULL/COMPILE/PRIVACY/DIFF exit0; privacy CLEAN. Artifact ID `12797084487`, ZIP SHA256 `b4128bf8a0c5be79f838ecbfb2d641f1397dc49e592b61f85c524901b44155f5`, CRC and 16/16 internal SHA256SUMS verified, private Library `/V13-Checkpoints/2026-10-28/Run11-SelfState-Session/SELFSTATE_SESSION_GREEN_40645410037_shab4128bf8.zip` re-materialized byte-exact.

Parent #863 evidence files copied with exact blobs; no source change to #863. Separate #865? Cross-chain World atomic/receipt review child branch `assistant/v13-run11-world-receipt-crosschain-20261028` now imports historical tests; do not claim integrated or passing until its own source-pinned CI completes.

**Limit:** synthetic Linux software only; no native model or Redmi, no production/main merge. All negative gates unchanged: STEP2 UTILITY_FAIL, B3 L1 FAIL, Body-JEPA UNAVAILABLE, LP3 heldout FAIL, jepa_weight0, Age0 RECORD_ONLY, canonical_architecture_complete=false, user_full_scope_complete=false. Remaining platform budget UNKNOWN.

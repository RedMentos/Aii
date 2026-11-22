# Run12I — Sleep replay provenance atomicity (2026-10-30)

Owner: GPT-6; draft PR #1265, review-only child of #1264. Source changes are **branch-scoped**, not production-integrated. Canon unchanged.

## Concrete bug reproduced

`ReplayQueue.enqueue` in original `sleep.py` blob `903da6af1a23f82929a637389e98d6b4a966f3f4` first committed an entry in SQLite `replay`, then separately called `Store.add_packet('ReplayItem', p)`. A real SQLite trigger rejecting `ReplayItem` insertion reproduced **1 orphan replay row and 0 packets** after an exception. A future Sleep queue rebuild could then treat the row as a replay candidate without its original typed provenance packet.

The candidate `sleep.py` blob `90d5361d1f8ad34c2311e870572a1d40146e4ca0` constructs and validates the exact same `ReplayItem` before any write, then commits the `replay` row and `packets` row in one `Store.tx` transaction. Any SQL failure rolls back both. Source, event, replay ID, fact_write_authority=0, clock semantics and typed schema remain unchanged. No model weights, learning rights, Age or production activation are touched.

## Original evidence and tests

- Source snapshot Actions **41050102442** at `d25ec02cb4b76d5ebe800ab1ec62da716a0e7878` exported 1,139 tracked Python/source paths, no models/private data. Original source snapshot ZIP SHA256 `7f3610c457ec42f168b46c74e0010ac8901adeb18079418722a9b7a2852492b2`; inner SOURCE.tar SHA256 `8941a85cf148614462ffe446203281a48e37a4a3ac3ef13c81bbcfba9782cff5`.
- Locally reproduced original orphan with real Store/SQLite. New 5/5 local SQLite tests PASS (injected packet trigger, packet preflight failure, FK failure, duplicate ID, restart/source binding).
- GitHub Actions **41050457385**: **SUCCESS** at exact tested HEAD `c8d700cc0c26e7125f1b839e24c1f1ecff1dcca5`. **53/53** tests PASS (5 new + 48 existing Sleep/Context). Original-vs-new SQLite trigger replay PASS: `ORIGINAL_ORPHAN_REPLAY_ROWS=1`, `PATCHED_ORPHAN_REPLAY_ROWS=0`. PINS/VENV/DEPS/TEST/COMPILE/REVIEW/PRIVACY/DIFF all EXIT0; privacy CLEAN.
- Original artifact **12974776212**, ZIP SHA256 `8c66d86907b88ee97fbfc87610c695bb9c55b8703428bda4f41bd90a982388f6`, 60,550 bytes, CRC PASS, **21/21** manifest hashes. Private Library backup `/V13-Checkpoints/2026-10-30/Run12I-SleepReplayAtomic/V13_Run12I_Sleep_41050457385.zip` re-materialized and independently compared byte-exact.
- Source pins: `sleep.py` 90d5361d, test 2583ff75, `store.py` 0779d986, `contracts.py` a9c9b828, Canon 218464b1. All exact Git blobs verified in raw CI. Frozen registered source/model/seed cohorts remain unchanged.

## Limitations and continuation

Software/SQLite only; no native model inference, measured retention utility, Redmi run, production integration or whole-system completion. No unfiltered full-suite claim; historical source-pin REDs remain open. Age0 RECORD_ONLY, STEP2 UTILITY_FAIL, B3 NO_PROMOTION, Body-JEPA UNAVAILABLE, `jepa_weight=0`, Redmi UNMEASURED.

Next command: independently review source diff and cross-organ Sleep consumers; keep draft/no auto-merge. Continue an independent canonical JEF/Body/Context utility package while device-native paths are blocked; do not treat this integrity repair as a completion gate.

# Run11 World F4 receipt/atomic cross-chain reconciliation — prereg 2026-10-28

**Owner:** GPT-6, independent review-only candidate child of #864 at `378c2d676668eb878822a8cfd764f94c32dac1f6`. Parent #863 multi-action GREEN source and #864 session-local candidate retained. Production/main, Canon, models, registered source/model/seed cohorts, native jobs, approval and Age gates untouched.

## Current regression and historical evidence

Current `world.py` blob `13f77eb3956ea1e4545234ee2eecc1bf56b60c60` contains recent duration validity and same-event per-action recovery, but lacks the previously implemented *atomic* `ModulatorPacket` + `PredictionOutcome` SQLite write boundary and strict source-bound receipt verification. On a divergent historical review chain, PR #345 Run349 proved atomicity, PR #418 Run420 handled malformed packet restart, PR #422 Run424 rejected forged action receipts, and PR #430 Run431 kept valid receipts visible under a 140-row corrupt flood. Historical #430 source blob `e26416301e3ff56339ab73c5cc7f46d66b9c66f7` is **not** automatically production-integrated.

## Acceptance and ownership

1. First import exact historical synthetic Runtime/SQLite regression tests for atomic crash injection, malformed/forged persisted receipts and bounded valid view, with original Git blobs and no new runtime change. Source-pinned CI must preserve original RED.
2. Reconcile only the verified receipt/atomic transaction and robust materialized view/recovery functions into current `world.py`. Keep **newer** #861 duration policy: invalid completed duration is observed as raw unscored, never as valid timing or digital learning; keep `invalid_timing_sample_count` and current `_valid_duration` semantics. Keep #863 same-event recovery and #864 session-local unfinished count. Never replace entire file with older version.
3. Verify focused historical + new tests, complete Linux software suite, compile/privacy/diff and exact source/model blobs. Preserve all original failures and closed raw hashes. No native inference, no Redmi proof or new training/approval authority.
4. Independent review must inspect receipt SQL against forged sibling action IDs, malformed JSON, stale state and concurrent observation; any unresolved edge remains a negative gate, not silent promotion.

**Expected outcome:** software integrity candidate only; no STEP2/B3/Body-JEPA/LP3/jepa_weight/Age/whole-system promotion. Negative gates: STEP2 UTILITY_FAIL, B3 L1 FAIL, Body-JEPA UNAVAILABLE, LP3 heldout FAIL, jepa_weight0, Age0 RECORD_ONLY, Redmi unmeasured.

**Next exact command:** import historical test blobs from PR #345/#418/#422/#430 to new test paths, run focused RED workflow before implementation; preserve source/test hashes and raw artifact. Cross-review remains mandatory.

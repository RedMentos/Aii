# Sleep S7 interleaved FINAL chronology handoff — 2026-10-29

## Frozen lineage and original RED
- Parent review PR #1112 at exact `ccb46a3350c9344515ba2272d782451af4771381`, child of #1111/#1110/#1109; review-only, not production.
- Prospective prereg `6e2eed0a268d2d73f7dda5fb942431f721f92490` remotely verified before tests/implementation. Own `sleep_offline.py` and `test_sleep_interleaved_final_20261029.py` only; no `history.py`, `context_os.py`, Canon, models, cohorts, seeds, learning/age policy edits.
- Original test-only RED `40903712242` at `ed0d40d4ab00ff7cbe832578daf9af814dbb8b0d`: 3/4 failed as expected for reversed assistant completion, delayed predecessor, and cancelled predecessor; duplicate-assistant negative control passed. Raw artifact `12910113154`, ZIP SHA256 `be4fc54bc27f4ac02be5b08ce63b2909d47779407c0982ec7c493e5ecd369d1b`, CRC verified, privacy CLEAN.
- First event-aware candidate `d3248ac9cbe221d38dbde83760388eeb770938f2` grouped bounded scanned messages by event_id, sorted valid digest entries in user chronology. A new counterexample found an irreversible skip: user1,user2,assistant1 FINAL leaves user2 pending; advancing to assistant1 id crosses the pending user row.
- Original counterexample RED `40904025948` at `fa7a18d454dd66c0b8d4acb183480c506054b895`: 1/5 focused tests failed (expected watermark bug), other 4 passed. Raw artifact `12909149295`, ZIP SHA256 `fddad7c31dcb051fe9657dda05346999ae5bfad5aed5da5bfff772cb8e866908`, CRC verified, privacy CLEAN.
- Watermark repair `97b0cac9a5d4f5b2a828985588dba9cc8f9ac5e9` tracks earliest incomplete/invalid scanned row and advances only through complete settled pairs whose assistant ID precedes that barrier. Final answers and cancelled/failed terminal answers are distinct; source/rule validation still delegated to unchanged `native_history`; S7 fact authority stays zero.
- Exact-head focused/full CI pending. Never claim GREEN without verifying raw and exact HEAD.

## Next and limitations
1. Run `PYTHONPATH=.:tests:scripts python -m unittest -v tests.test_sleep_interleaved_final_20261029 tests.test_sleep_digest_session_fairness_20261029 tests.test_sleep_digest_backlog_20261029 tests.test_contextos_sleep_source_integration_20261029 tests.test_sleep_offline tests.test_history_lineage` from `v13/code`; full `python -m unittest discover -s tests`; privacy/diff and compileall.
2. Review edge cases: more than 64 simultaneously interleaved messages can place an early assistant beyond the bounded scan; this remains a separate open limitation, not a solved claim. Check restart and revoked source on interleaved data.
3. Persist verified raw, request independent review before any merge. Continue other canonical work if device/native path blocked.
4. Age0 RECORD_ONLY, STEP2 UTILITY_FAIL, B3 L1 FAIL, Body-JEPA UNAVAILABLE, LP3 FAIL, jepa_weight0, AG6 unapproved, Redmi sustained unmeasured, V13 incomplete.

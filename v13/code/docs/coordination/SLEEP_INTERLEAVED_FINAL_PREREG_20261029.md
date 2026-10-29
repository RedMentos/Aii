# S7 interleaved FINAL chronology prereg — 2026-10-29

## Frozen before test
- Parent review PR #1112 exact source head `ccb46a3350c9344515ba2272d782451af4771381`; upstream PR #1111/#1110/#1109. No production merge, no model or phone evidence.
- Bug hypothesis: S7 `digest` assumes adjacent (user,assistant) message IDs. Two legitimate FINAL turns whose assistants complete in reverse order are permanently blocked by the pairwise scanner, even though `native_history` can verify their event/source lineage.
- Original RED test cases: two interleaved FINAL events with reversed assistant completion; incomplete first event must not allow later FINAL to skip ahead; later completion must recover both in original user chronology; cancelled first event must not enter digest but may permit later FINAL; duplicate assistant must not promote corrupt event.
- Intended fix: group at most `2*TURNS_MAX` scanned rows by event_id in first-user order, advance high-water only across complete settled event groups (exactly one FINAL user + one terminal assistant with user id before assistant id). Reuse unchanged `native_history` for source/rule revocation, sort digest entries by user message id rather than assistant completion id, preserve all original bounds/age/authority gates.
- Owned source `v13/code/v13/sleep_offline.py`, new `tests/test_sleep_interleaved_final_20261029.py`, new CI/handoff only. Do not modify `history.py`, `context_os.py`, frozen cohorts, Canon, model hashes or seeds.
- Evidence: prereg -> test-only original RED with raw SHA256SUMS -> implementation -> exact-head focused/full software CI with raw closure, privacy/diff checks. No native/Redmi, no promotion of STEP2/B3/Body-JEPA/LP3/jepa_weight; Age0 RECORD_ONLY.

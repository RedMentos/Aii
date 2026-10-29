# S7 pending-session fairness prereg — 2026-10-29

## Locked baseline
- Parent review PR #1111, exact base `b02c7161524b515a78aad08741922c527e4efdd7` (combines verified PR #1109 donor and PR #1110 paged S7 candidate; parent integration CI may still be pending).
- Canon v10.16.1 and user decisions unchanged; default Age0 RECORD_ONLY, all original FAIL gates retained.
- Bug hypothesis: `sleep_offline.digest` chooses latest eight FINAL-assistant sessions *before* testing their per-session high-water; when >8 sessions exist, an older pending session is never selected while newer eight are already digested. This violates source-preserving backlog catch-up across sessions.
- Prospective RED: nine real Store sessions, one FINAL source-valid turn each, two S7 calls; old code digests eight then zero and never reaches ninth. Negative control: a later new turn in an already processed session must not starve the ninth; revoked source must never be surfaced.
- Proposed fix after RED: enumerate pending sessions with FINAL answers, schedule bounded `SESSIONS_MAX` oldest undigested high-water first (stable tie by last/id), do not change per-session `TURNS_MAX`, native_history validation, fact authority or training rights. No source/model/seed cohort modifications.
- Owned files: `v13/code/v13/sleep_offline.py`, `v13/code/tests/test_sleep_digest_session_fairness_20261029.py`, new CI/handoff only. Existing PR #1110 tests, history.py and Context OS source restoration are unchanged.
- Evidence: test-only original RED workflow and later exact-head focused/full software workflow, raw SHA256SUMS and privacy/diff check. No native or Redmi claim. Do not promote STEP2/B3/Body-JEPA/LP3/jepa_weight.

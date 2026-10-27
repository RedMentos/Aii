# Queued Dream cached-verdict F5 revocation — preregistered RED-first review

UTC 2026-10-28. Owner GPT-6 separate review. Parent PR #798 exact source `fa1f7f5f3fa4b5cc553c6ad0bab006fa7825d3a6` (Run275 F5 anchor/neighbor checks, Actions 40603608415 pending at preregistration). Parent is a review branch, not production. No production edits until parent CI passes.

## Observed static gap / falsifiable hypothesis

`SleepCycle.validate_hypotheses` stores `hypothesis_checks[replay_id]={verdict,at}` and skips **all** previously non-UNVERIFIED verdicts forever, even after F5 HumanDecision/feedback revocation. The newly reconciled `check_hypothesis` verifies live F5 when invoked, but this cache may bypass that verification after a previously SUPPORTED result. Test actual Runtime/SQLite queued Dream route hypothesis with a real supporting human correction, confirm initial SUPPORTED, then revoke anchor or supporting neighbor and call validation again without changing the clock. Expected: stale anchor retires, revoked neighbor no longer supports. Include a restart/persisted schedule case and valid control. Original tests/REDs remain.

## Narrow intended change (only after RED and parent GREEN)

Make cached SUPPORTED hypotheses eligible for bounded live F5 revalidation, preserving the daily throttle for UNVERIFIED and the already-retired STALE/CONTRADICTED behavior; never increase fact-write authority. Avoid a new cache mechanism that guesses revocation from source IDs; use existing Run275 live validator and bounded `dream_max` budget. Preserve exact current Sleep A, Sleep B seed, Run275, Memory and ContextOS sources, original tests and model/seed hashes. Capture focused/full Linux software CI, privacy, raw exits and private backup. No native/Redmi, learning, Age or gate promotion: STEP2 UTILITY_FAIL, B3 L1 FAIL, Body-JEPA UNAVAILABLE, jepa_weight=0, whole V13 incomplete. Do not auto-merge.

Next: add tests only and collect RED, await parent exact CI GREEN, then narrow code change, independent review and full suite.

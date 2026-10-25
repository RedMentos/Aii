# Run312 preregistration — F FastForward exactly-once outcome learning

Date: 2026-10-25. Owner: assistant/fastforward-exact-once-run312-20261025.
Immutable starting point: 300e0aab05b81833300645137275e05d7982d237 (Run310 branch-scoped checkpoint).
File ownership: only `v13/code/v13/fastforward.py`, `v13/code/tests/test_fastforward_outcome_once_run312.py`, this proof directory, and dedicated `.github/workflows/run312-fastforward-outcome-once.yml`. No Runtime, Store, other organ, Canon, model/seed, registered cohort or shared status files.

## Defect hypothesis (RED-first)
`FastForward.learn(event_id, ...)` updates F_FAST_FORWARD weights, n, replay and neuromod for every invocation, without remembering the outcome's event identity. A replayed terminal event (after restart or concurrent call) can count twice and distort predictor weights. Existing replay buffer is capped at 256; it cannot be the sole durable receipt. This is a software/SQLite outcome-consistency defect, not a native JEPA or measured utility claim.

## Frozen acceptance tests
1. Same event+exact payload called twice: second returns original result; F state/version, n, replay and weights unchanged.
2. Same event+changed observed payload: fail closed (ValueError), original state unchanged.
3. After >256 distinct other events and a Runtime restart, first event replay still cannot train again.
4. Two concurrent same-event calls on the same SQLite Store produce one learning update and matching results.
5. One N10 modulator emission at most for a duplicate eligible event, preserving prior no-N10 behavior before predictor warmup.
6. Distinct events continue to learn and existing predictor, proceduralization, sleep CAS and Run300 latency tests remain green.
7. No new table/schema; an atomic SQLite state/receipt transaction ensures no crash gap. Retain existing Age/approval/SHADOW semantics.

## Evidence and gates
Commit this preregistration before RED tests. Run dedicated CPU GitHub Actions at exact head with pinned isolated numpy/prompt-toolkit, real Runtime/Store SQLite and official privacy scan; retain raw RED and GREEN logs and SHA256. No model downloads/native/Redmi claims. Keep STEP2 UTILITY_FAIL, B3 L1 FAIL, Body-JEPA unavailable, jepa_weight=0 and whole-system incomplete. Full Run310 failure (2864 tests, 2 FAIL, 36 ERROR) is a separate open integration issue and must not be concealed.

## Resume
Create tests + dedicated CI on this review branch, observe RED, patch only FastForward, observe GREEN, close raw hashes and remote commit; then continue another independent canonical package.
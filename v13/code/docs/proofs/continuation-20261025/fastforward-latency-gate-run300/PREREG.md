# Run300 — FastForward procedural READY requires finite, positive, strictly better latency estimate

Owner GPT-6 automation; base Run299 checkpoint `4720f08fd363a8d63155cc98664cc31684112f46`, PR #298. Owned: `v13/code/v13/fastforward.py`, new `v13/code/tests/test_fastforward_latency_gate_run300.py`, `.github/workflows/run300-fastforward-latency-gate.yml`, this proof directory. Run299 Sleep CAS, Run298 WorldModel, Run297 native Context OS owner are not altered.

## Problem
`FastForward.record_turn()` treats missing `predicted_fast_s=None` as proof that the procedural fast route is faster, and accepts negative/equal predicted latency as non-inferior. After enough shadow agreement it can mark READY and, if the user activates it, skip body passes without any valid latency advantage estimate. The Canon proceduralization goal requires latency reduction as well as accuracy retention.

## RED / GREEN acceptance (fixed before source edit)
1. Actual Runtime/Store SQLite: compile five observed successes, then ten matching shadow successes without any fast latency prediction. Remain SHADOW, never READY, even after explicit human ACTIVE mode and restart.
2. Invalid predictions (negative, zero, NaN, infinity, boolean) and exactly equal latency must not promote READY; valid finite positive strictly lower prediction retains the existing READY path.
3. Gate report explicitly labels latency as **predictor estimate, not measured fast execution**; no Canon G-PROCEDURALIZATION-004 promotion from software-only shadow checks. Existing `test_fastforward_reflex`, `test_fastforward_sleep_cas_run299` and sleep regressions stay green; official privacy scan CLEAN.
4. Preserve RED failure logs/artifact and GREEN raw tests/hashes. No changes to Runtime, Age, model weights, source/seed cohorts, Canon, or original negative gates.

This is software policy correctness with synthetic timing, not a native/Redmi measured speedup. Next: independently verify, checkpoint, then continue other canonical work.

# Research & Perception handoff — RAW EAR duplex ordering, target-turn idempotency and FD-VAD research

**Date:** 2026-11-23
**Owner:** Research & Perception
**PR:** [#2448](https://github.com/RedMentos/Aii/pull/2448) — updated in place; remains DRAFT
**Branch:** research-perception/v14-audio-duplex-bridge-20261123-run21
**Current branch head:** 25aa818b916a6ae046ee5d8996aa450c8a5855b6
**Base/release ancestor:** 8d93236c753f0194224c19edc7411d8d7082b1d6

## Defects addressed

Boss review identified two races in the prior bridge:

1. Distinct valid audio packets could target the same still-active turn. The replay guard keyed only by audio event/packet/receipt, while duplex.record overwrote pending and interrupted by target.
2. The bridge set cancel_event before persisting the handoff. A worker could finish and the next turn could attempt duplex.handoff before the pending relation was durable.

## Implementation readback

- duplex.py code update commit: d2abefa145857629168d3630c350f27a37573ed6; blob 49d345c2310647b1186162154c926db08b27ce98.
- audio_duplex_bridge.py code update commit: b4bb25537e82b3922403b0c62f66b6726cade8a9; blob 93ead41c3d53e13295399911a430fb64d7676862.
- regression-test update commit: c0ea2a939870100d3d4d42ded7fc8d0de0600560; blob 71261ef996f5d0da25cf1ebc57df3cee9d70623a.
- race evidence/handoff commit: 2b6b6b0ba06eac7481194ea34ec37cb7e70ea507.
- research ledger R-118 commit: 25aa818b916a6ae046ee5d8996aa450c8a5855b6.
- Store CAS + first-writer-wins now prevents a second interrupt/revise from replacing the existing target-turn relation.
- A per-Runtime re-entrant lock serializes audio publication/rollback with the next-turn handoff reader. The bridge commits pending/interrupted state before setting cancel_event; Store I/O stays outside Runtime.lock.
- If the target turn changed during Store I/O, only the exact unconsumed relation is rolled back before the handoff reader proceeds.
- duplex.handoff consumes pending state with CAS. A telemetry failure after a durable commit no longer makes the caller believe the commit failed.

## Tests and exact evidence

- LOCAL_LINUX CPython 3.13.5: isolated Store/CAS/lock harness 2/2 PASS (first-writer target ownership; handoff reader waits until publication/rollback completes).
- LOCAL_LINUX CPython 3.13.5: concurrent two-writer CAS check PASS — exactly one distinct event claimed the same target turn and one was rejected.
- These are isolated contract harnesses, not the repository's full Runtime pytest suite.
- Full local Aii checkout is unavailable; full repository pytest and the three newly added Runtime regressions are NOT_RUN locally.
- Exact branch-head GitHub Actions for prior code head 3bc655fc70e5232619b42d800b2ecdcbdb564b13: push run 45262253132 and PR run 45262261597 both ended startup_failure with no jobs; exact check-runs count was 0. This is not a test PASS or code failure diagnosis. The prior parent b8ea0bea had green audio/staged/consumer workflows, but those results do not cover this patch.
- Latest ledger addition R-118 fully reviews FD-VAD arXiv:2609.35791 (2026-09-16 preprint), its MIT code/checkpoint, WavLM MIT, Qwen2.5 Apache-2.0 and Smart Turn BSD-2-Clause. It is a research proposal only: its 0.5B + WavLM bundle (~1.5 GB on disk), PyTorch stack, English-only data and A100 timing make it unsuitable as a direct Redmi model candidate.
- PR #2448 remains DRAFT / NOT_RELEASED pending independent review and actual exact-head test execution.

## Canon / product effect

- Canon: A4 temporal voice/prosody, A5 PerceptPacket source/consent, §4A.4 full-duplex timeline, §4A.5 non-STT-only voice path, STEP 9/11.
- Existing Runtime turn and Store/SQLite are the consumer. This is a caller-supplied PCM bridge, not an Android microphone provider and not a new Runtime turn from PCM.
- Research proposal: keep acoustic voice_onset separate from semantic Continue/Stop endpointing; consider a small trainable A4 head with confidence/K gating only after source-bound consent and playback-state gates. No endpoint model is implemented by this paper review.
- The patch changes no model, weight, Age, learning permission, device permission, user data or release branch.

## Device and deployment boundary

- Latest available authenticated phone receipt in the shared handoff is still installed SHA 8d93236c753f0194224c19edc7411d8d7082b1d6, auto-updater enabled, Runtime/Dashboard UP_TO_DATE.
- The same-day sanitized #1904 diagnostic says Runtime STOPPED_BY_USER, autostart false, model process stopped; preserve that state. No restart, CHAT_SEND, UPDATE_REQUEST, shell, LOG_PAGE or model change was made.
- This PR candidate is not installed. No Android AudioRecord/Oboe provider, APK, microphone permission, audible playback, native model, Redmi chat or device test is claimed.

## Next

Boss/QA: independently review the first-writer and commit-before-cancel protocol; get exact-head CI to execute (the current Actions startup_failure runs had no jobs); then coordinate Core/QA's signed user-started AudioRecord provider. Keep microphone capture OFF until its permission, lifecycle, revocation and zeroization gates pass.
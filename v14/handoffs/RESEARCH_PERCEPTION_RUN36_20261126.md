# Research & Perception — Run 36 (2026-11-26)

## Checkpoint

- Branch: research-perception/v14-raw-ear-next-delta-20261125-run13
- Code checkpoint SHA: d7988f2e1031910a1013db44b24b81ce6ee784d0
- Latest documentation checkpoint: 96df4cff9da506408e48d93e8e6a2f5a64d09fad
- Existing draft PR: https://github.com/RedMentos/Aii/pull/2498
- Whole-canon evidence destination: https://github.com/RedMentos/Aii/issues/1984
- Release base verified by compare: gpt6/v13-private-remote-bridge-20261111 at 8d93236c753f0194224c19edc7411d8d7082b1d6; PR #2498 is 92+ commits ahead of this base, not released.

## Implemented

Added v13/code/v13/audio_event_expectation.py and wired it into audio_voice_cues.consume_pcm16_voice_window().

- Predicts only the timing of existing heuristic VOICED/IMPULSIVE activity-class onsets.
- Requires three prior intervals before a timing-confidence proxy can emit omission.
- A valid FINAL non-target/SILENCE window must cross the expected time window; late onsets can record a missed expected window. Continuous activity fulfils an expected window once.
- UNCERTAIN and PROVISIONAL are censored. Capture gaps and chronology discontinuities reset; consent rotation and explicit source/generation reset clear state.
- Bounded to 16 source/generation streams and 8 intervals per class; state is process-local and ephemeral.
- A4 novelty contribution is capped at 0.05. No external_interrupt, C3, speaker identity, source truth, action/learning authority or weight path is changed.
- Optional registry failure is fail-closed and must not break the primary RAW EAR path.
- No PCM, transcript, embedding or training example is persisted.

This is a timed acoustic-activity statistics shadow. It is not a semantic event recognizer, calibrated probability, neural predictor, persistent learner, or JEPA replacement.

## Tests and source integrity

- LOCAL_LINUX CPython 3.13.5 scratch prototype: py_compile PASS; 11/11 isolated unit tests PASS. The scratch file's Git blob differs from the pushed module blob; these are prototype-only results, not exact-repository execution.
- Full local Aii checkout: BLOCKED (no checkout mounted; git ls-remote/raw GitHub DNS failed).
- Exact-head GitHub workflows for code checkpoint d7988f2:
  - #45728258860 staged context/integrated regression: QUEUED at last poll
  - #45728258868 runtime deployment integrity: QUEUED
  - #45728259057 RAW EAR/libfvad comparison: QUEUED
  - #45728258965 RAW EAR optional NumPy backend: PENDING
- Perception integrated builder blob: 18f9177be26720f0daa41dd21123238ffb249d47.
- SOURCE_BLOBS manifest contains 14 direct dependencies; exact GitHub readback audit: 14/14 expected blob SHAs match actual current blobs.
- The repository test now asserts every source pin against Git's blob-hash formula and verifies that both temporal predictor modules are included.

## Cross-team blocker

Core/QA-owned termux_runtime_recovery_candidate_20261121.py still expects old integrated_audio_context_candidate_20261121.py blob 831080bceec90711bd42e0fa4eba47c669975c98, while Perception's exact current builder blob is 18f9177be26720f0daa41dd21123238ffb249d47. Do not weaken or bypass the pin. Core/QA must update the recovery builder pin, then recompute stage_integrated_candidate.py BUILDER_SHA and runtime_deploy.py STAGER_SHA256 in dependency order. Rerun staged/integrated and two-checkout migration afterward.

## Research

R-163 records Yamada & Chao, arXiv:2510.14382, as ABSTRACT_ONLY. Full paper/methods/code/license were not verified; no reuse. It is a research lead for separating event identity and event timing prediction, not evidence for this implementation.

## Device / release

- REDMI_UNVERIFIED. No connected authorized Redmi or Android microphone/AudioRecord test was available.
- Last board receipt #767 is stale: installed 8bf44cb, auto-update enabled, CI_WAIT before final b20e9 green CI. No fresh private owner-read receipt arrived in this run.
- GitHub push is not deployment. No release SHA; NOT_RELEASED.
- No model/weight swap, permission change, update request, Termux command or device mutation was performed.

## Next

1. Poll the exact-head RAW EAR CI runs and fix any measured failures.
2. Coordinate Core/QA's exact recovery→stager→deployer pin rebind; rerun staged/integrated and migration tests.
3. Add frozen/held-out acoustic controls against persistence, no-event-predictor, shuffled timing, silence/noise, uncertain/censored windows and consent reset.
4. Keep the new signal SHADOW/capped until held-out attention utility and source/voice retention are demonstrated.

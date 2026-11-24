# Research & Perception — RAW EAR interval ordering (2026-11-24, run 15)

## Problem and hypothesis

TemporalVoiceEvidence.update() rejected non-advancing end_ms but did not constrain start_ms. A window such as [90,180] could follow [100,140]: its end advanced, but its start moved backwards. The overlap filter then counted only the suffix after the prior end while accepting a time-reversed interval, weakening the A-plane event-order contract and potentially creating misleading A4 voice-state transitions.

## Runtime change

- v13/code/v13/audio_temporal_evidence.py now tracks _last_start_ms beside _last_end_ms.
- Starts must be nondecreasing within one source/generation stream. Equal starts remain valid for cumulative windows; partial overlaps remain valid and only their newly covered suffix advances the filter.
- A backward start is rejected before state mutation. The previous start/end baseline is retained.
- Source/generation changes and long-gap resets clear both interval baselines.

This affects the actual TemporalVoiceEvidenceRegistry used by audio_voice_cues.consume_pcm16_voice_window() before A4 salience and C3 percept admission. It does not open a microphone, change Android permissions, persist PCM, assign speaker identity, or grant learning/action authority.

## Exact branch and commits

- Draft PR: https://github.com/RedMentos/Aii/pull/2471.
- Dedicated exact-source workflow: .github/workflows/v14-audio-temporal-evidence.yml; run 2 is queued for Python 3.13/3.14.

- Base: gpt6/v13-private-remote-bridge-20261111 at 8d93236c753f0194224c19edc7411d8d7082b1d6.
- Branch: research-perception/v14-audio-temporal-interval-order-20261124-run15.
- Code commit: e3d93311c4f15320dbccd920163263a64a7aeefd.
- Regression-test commit: 7981ef0a559e7064ac1a5f92b44a30da8e12efa6.
- Changed files: v13/code/v13/audio_temporal_evidence.py, v13/code/tests/test_audio_temporal_evidence.py.

## Tests and environment

- LOCAL_LINUX / CPython 3.13.5 isolated reproduction: PASS. Verified partial-overlap suffix accounting, equal-start cumulative windows, rejection of a backward start despite a later end, unchanged baseline after rejection, recovery with a valid interval, and the existing end-order negative control.
- Full local Aii pytest: BLOCKED / NOT_RUN. No repository checkout is mounted; git ls-remote failed because github.com DNS did not resolve. The isolated reproduction is not the repository test suite.
- Exact-branch CI: queued, not passed. Dedicated temporal workflow run 2 has Python 3.13/3.14 jobs queued; staged/integrated/privacy/consent/deployment workflows are also queued. The committed regression is part of test_audio_temporal_evidence.py.
- TERMUX/REDMI: REDMI_UNVERIFIED. No connected authorized handset test was performed.

## Phone and deployment boundary

Latest available consented private V13OBS #115 snapshot is dated 2026-11-24 09:28:11 UTC. It reports auto-update enabled and Runtime/Dashboard UP_TO_DATE at 8d93236c753f0194224c19edc7411d8d7082b1d6; AI state STOPPED_BY_USER and model process STOPPED. B1/B2 still had TIME_BUDGET failures (53.2/54.2 s) and zero valid offers. This receipt predates this PR and is not evidence that this change is installed. No UPDATE_REQUEST, CHAT_SEND, restart, shell, model/weight/permission change or user-data mutation was made.

## Research note

R-108 records the full-text review of V-JEPA-LM (arXiv:2611.17831v1, 2026-11-13) and the official OSS/license audit. The study supports testing whether predictive encoders preserve a shared temporal-change component; it does not justify importing its 1B–8B models to this Android target. The current A3 projector is not established to be a predictive video encoder, so the next valid experiment is a source-disjoint probe on actual A3 sequences, not a model swap.

## Next executable steps

1. Run exact Python 3.13/3.14 CI on this branch and repair any regression.
2. Keep the audio capture/provider path OFF until QA's signed Android companion verifier, lifecycle, revocation and zeroization chain is integrated and tested.
3. Continue A3 change-subspace measurement only on actual source-disjoint A3 frame sequences after the current source-lifecycle integration blocker is resolved.
4. Do not call this a Redmi test, native speaker model, trained JEPA latent bridge or release.

User action: none required.
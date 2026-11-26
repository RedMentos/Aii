# Research & Perception Run 44 — session-local relative-information proxy

Date: 2026-11-26
Owner: Research & Perception
Repository: RedMentos/Aii
Branch: research-perception/v14-audio-temporal-window-order-20261126-run41b
PR: https://github.com/RedMentos/Aii/pull/2527 (DRAFT / NOT_RELEASED)
Base: #2524 at b298719af8faf75811d03d486de7725395a590b0

## Code
- \`v14/experiments/audio_feature_set_probe.py\`: adds \`evaluate_relative_incremental_information()\` and includes its result in \`evaluate_feature_set()\`.
- \`v14/experiments/test_audio_feature_set_probe.py\`: adds four regression tests and session IDs to the synthetic fixture.
- Source commit: \`f4c0648af9d84dae8b8e11ab00431f24413d96a6\`; source blob \`aeb63ea214fac0d68a7f8bcf9e4701247406ceb1\`.
- Test commit: \`c0d68f97e250fecb036dd0f445c9b733bc2ce76e\`; test blob \`75e4bf6fa4a7e0de528484ddc5be16e6dca24d8d\`.

## Method
The current FINAL A4/A5 feature tuple is evaluated for incremental information about a later, separately sourced action outcome, conditioned on the goal and a coarse session-local history state. The history state consists of the last prior feature tuple plus a capped count of prior windows in a 5,000 ms window. Only prior windows that ended before the current interval are admitted. Session boundaries reset history. A within-session × goal permutation null preserves those marginals.

This is a discrete plug-in proxy, **not the exact rIMI estimator** in Heintz et al. It does not use Gaussian-copula MI, EEG, human attention labels, or the full history of model prediction scores. R-166 remains ABSTRACT_VERIFIED only; the full paper was not read.

## Local scratch evidence
Environment: LOCAL_LINUX / CPython 3.13.5.
- Equivalent proxy compiled: PASS.
- Six assertions: PASS (four-session information result, session reset, stratified shuffle negative, per-session consistency, single-session rejection, non-monotonic chronology rejection).
- Synthetic fixture: 128 records, 4 sessions × 32; proxy rIMI 1.000; incremental MI 0.64995 bits; remaining conditional action entropy 0.64995 bits; conditional self-dependence 0.55702 bits; no-history goal-conditioned CMI 0.96568 bits; 128-permutation p=0.00775; shuffled p95 0.71029; history nonempty fraction 0.96875.
- This was a scratch-equivalent implementation, not the exact repository module/test run. Full Aii checkout, full pytest and native build NOT_RUN because no checkout is mounted and GitHub DNS is unavailable locally.

## Exact CI at checkpoint
- Feature-set workflow 45780338189: QUEUED.
- RAW EAR comparison 45780338123: IN_PROGRESS.
- Staged/integrated 45780338096: IN_PROGRESS.
- RuntimeDeploy integrity 45780338147: QUEUED.
- Previous shared staged/integrated run 45774358076 failed at the Core-owned recovery audio-builder pin: expected \`831080bceec90711bd42e0fa4eba47c669975c98\`, current Perception composer blob \`f9a0ed7d1a4312361c4c6c6c397744b0e13ef4f0\`.

## Product boundary
- Canon path: A4 RAW EAR / A5_AUDIO PerceptPacket / active-attention evidence evaluation.
- Status: WIRED_SYNTHETIC_DIAGNOSTIC / NOT_RUNTIME_WIRED / REDMI_UNVERIFIED.
- No normal Runtime/attention/JEPA/C3 consumer was changed. No real microphone, raw user audio, model/weight change, Android permission or device action.
- B3 OFF; P0 normal chat and B1/B2 valid-offer delivery OPEN; NOT_RELEASED.

## Next
1. Poll exact CI for the new head.
2. Core/Integrator composes #2527 with #2525/#2524 and repairs the recovery → stage → RuntimeDeploy audio-builder pin chain; Perception does not edit Core-owned files.
3. After a normal-turn revocable AudioConsentLease exists and a legitimate separately consented outcome cohort is available, evaluate source/session-disjoint holdouts plus drift and switch-focused controls.
4. Keep this probe diagnostic-only; do not change attention policy, train JEPA or request microphone access from these results.

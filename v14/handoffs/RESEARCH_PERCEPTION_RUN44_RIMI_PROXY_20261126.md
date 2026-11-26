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


## Exact CI completion addendum (2026-11-26)

Tested code/test head: \`c0d68f97e250fecb036dd0f445c9b733bc2ce76e\`.
- Feature-set workflow [45780338189](https://github.com/RedMentos/Aii/actions/runs/45780338189): 14/14 PASS on Python 3.13 and 3.14, including actual A4 RAW EAR extractor → A5 PerceptPacket integration.
- RAW EAR comparison [45780338123](https://github.com/RedMentos/Aii/actions/runs/45780338123): 9/9 PASS on Python 3.13 and 3.14.
- RuntimeDeploy offline integrity [45780338147](https://github.com/RedMentos/Aii/actions/runs/45780338147): PASS on Python 3.11 and 3.14; not a deployment.
- Shared staged/integrated [45780338096](https://github.com/RedMentos/Aii/actions/runs/45780338096): FAIL; staged 16 failed / 237 passed / 10 skipped / 2 errors / 47 subtests; integrated 1 failed. Exact source-pin mismatch confirmed by readback: Perception composer blob \`f9a0ed7d1a4312361c4c6c6c397744b0e13ef4f0\`; Core recovery blob \`b44fe9a21412c570a5f19472719972a53b3447d8\` expects \`831080bceec90711bd42e0fa4eba47c669975c98\`.
- This is a Core-owned integration blocker; no Core recovery/stage/deployer file was changed by Perception.
- Status: DRAFT / NOT_RELEASED / REDMI_UNVERIFIED. No device, microphone, model, weight, permission or data action.


## R-166 full-text review correction (2026-11-26)

The full 12-page author-hosted PDF has now been read. The paper is an August 2026 preprint; no peer-reviewed venue was identified. It defines rIMI over AAD prediction score vectors \(f(n)\), attended-speaker state \(y(n)\), and prior scores \(f_{past}(n)\); uses a five-second stacked score history for short windows and Gaussian-copula/GCMI estimation; and recommends a ≥5-minute temporal buffer (ideally separate sessions), switch-focused evaluation and confound controls. Dataset: AV-GC, 13 participants, 64-channel EEG, 10-minute trials with a switch after 5 minutes. The study is specific to EEG-based attended-speaker decoding.

**Important scope correction:** the Run 44 proxy uses acoustic cue tuples and later action outcomes, not AAD prediction scores and attended-speaker labels. It is not paper rIMI; its feature-history dependence term is not paper CSD. The code now uses the key \`conditional_feature_history_dependence_bits\` and explicit \`metric_scope\`. The proxy remains synthetic-only and diagnostic-only. A faithful rIMI implementation requires a real A4 score vector, trusted attended-state/outcome labels, full prior-score history and temporally/session-disjoint evaluation. No attention or JEPA policy change.


## Corrected metric-scope code checkpoint

Current code/test head: \`ef61d48f93621cb3d7813628eb96203eea2be1ee\`; source commit \`a7b39e36f7bf44ad30c04759dc8771cda5373b4d\`; source blob \`d8dc5a2e155fe6ac7322e994645f4f20425375f9\`; test blob \`3d34aa8ab552d03724dd829e7b8703f19a0df664\`. The output key is now \`conditional_feature_history_dependence_bits\`, and \`metric_scope\` explicitly states acoustic features → later action outcome, not AAD attention scores. Fresh exact CI is pending on this head. Previous 14/14 CI on c0d68 is historical, not a pass on ef61d. R-166 is now FULL_TEXT_REVIEWED; the current proxy is not paper rIMI or CSD.

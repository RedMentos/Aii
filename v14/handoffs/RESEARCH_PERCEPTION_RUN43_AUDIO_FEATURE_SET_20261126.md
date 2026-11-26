# Research & Perception Run 43 — A4/A5 source-bound feature-set probe

Date: 2026-11-26
Owner: Research & Perception
Repository: RedMentos/Aii
Branch: `research-perception/v14-audio-temporal-window-order-20261126-run41b`
PR: https://github.com/RedMentos/Aii/pull/2527 (DRAFT / NOT_RELEASED)
Exact head at checkpoint: `0e1837a042aadee3b5e94301e10fd2b4eaa3a8b5`
Base: #2524, `b298719af8faf75811d03d486de7725395a590b0`

## Code
- `v14/experiments/audio_feature_set_probe.py` blob `02cd6cdcd04942b144b46bf96134547c6bf91d12`
- `v14/experiments/test_audio_feature_set_probe.py` blob `11c6dbcb039ccf369c39580dd6f9fc423cc634f3`
- `.github/workflows/v14-audio-feature-set-probe.yml` blob `f85368894807a4c9c610059ff01f1083556df093`
- Module commit `04abfa48429e64c01f561bc502a80e724a221cc5`; test commit `5bc0d13ab351701b2d30e2bc4737b7b51bc04672`; workflow commit `0e1837a042aadee3b5e94301e10fd2b4eaa3a8b5`.

The probe accepts FINAL A5_AUDIO PerceptPackets enriched with A4 RAW EAR cues and a separately sourced later goal/action outcome. It validates packet/source/provenance hashes, generation, temporal order, finality, non-authority and separate outcome provenance. It rejects raw PCM, transcript text, provisional packets, duplicate bindings, cross-generation cohorts and authority-bearing inputs. It computes conditional MI between the feature set and future action given goal, per-feature baselines, joint gain over best single, feature self-predictability and within-goal shuffled-outcome permutation controls.

The test includes a real A4 extractor → A5 PerceptPacket roundtrip using the repository's `audio_ear.observe_pcm16`, `audio_percept_contract.audio_percept_packet` and `audio_voice_cues.extract_voice_cues`. CI verifies the exact producer blob pins.

## Local tests
Environment: LOCAL_LINUX / CPython 3.13.5 scratch package.
- `python -m py_compile audio_feature_set_probe.py test_audio_feature_set_probe.py`: PASS.
- `python -m unittest -v test_audio_feature_set_probe`: 9 PASS, 1 SKIP. The skipped test is the actual repository A4/A5 integration because the full Aii checkout is not mounted.
- The full Aii local checkout/pytest/native build was NOT_RUN because the repository is not mounted and GitHub DNS cannot resolve from this environment.
- The exact fetched module/test blob hashes match the locally tested files.

Synthetic fixture result (not human or runtime evidence):
- 64 records / 2 goals.
- Joint goal-conditioned CMI: 1.000 bits.
- Pitch-only, prosody-only and goal-only MI: 0.
- Joint gain over best single: 1.000 bits.
- 64 within-goal time permutations: median 0.05857 bits, p95 0.15711 bits, empirical p 0.01538.
- Pitch/prosody self-MI: 0.00458 / 0.01483 bits.
- No JEPA training, model update, persistence, attention-policy change or action authority.

## CI at last poll
- Feature-set exact workflow: 45773372374 IN_PROGRESS.
- RAW EAR comparison: 45773372422 IN_PROGRESS.
- Shared staged/integrated: 45773372390 IN_PROGRESS.
- RuntimeDeploy integrity: 45773372351 QUEUED.
Do not inherit parent/previous-head CI as exact-head proof. Poll these exact run IDs and record final outcomes separately.

## Research
R-165 full-text review: Griffith, Hess & McDermott, *Optimized feature gains explain and predict successes and failures of human selective listening*, Nature Human Behaviour 10, 937–959 (2026), published 2026-03-13, peer-reviewed, CC BY 4.0. It supports studying cue/goal-conditioned feature gains in a bounded binaural cocktail-party task, but is not evidence for general JEPA, online learning or Android.
R-166 abstract-only: Heintz et al., *Why Performance Metrics Overpromise in Auditory Attention Decoding* (arXiv:2608.14250, 2026-08-14). It motivates relative/incremental MI because temporal dependence and feature drift can inflate accuracy/ITR; full text not reviewed.

No external code, checkpoints, datasets or model weights were reused.

## Product / device status
- P0 correct/fast normal chat and B1/B2 valid-offer delivery remain OPEN.
- The probe is not imported into normal Runtime, attention, JEPA or a production learning path.
- No microphone/AudioRecord provider, real audio, native GGUF cohort, gradient/parameter change, Android action or Redmi test.
- B3 remains OFF.
- Last available private V13OBS #115 snapshot is historical (2026-11-24 09:28 UTC): updater reported enabled/UP_TO_DATE at `8d93236c753f0194224c19edc7411d8d7082b1d6`, but AI STOPPED_BY_USER. No fresh authenticated receipt; REDMI_UNVERIFIED.
- NOT_RELEASED. No UPDATE_REQUEST, CHAT_SEND, restart, model/weight/permission/data mutation.

## Next owner/action
1. Poll exact feature-set and shared CI runs above.
2. Core refreshes the recovery → stage → RuntimeDeploy audio-builder source pin to the exact Perception blob and reruns staged/integrated tests. Perception does not edit Core-owned files.
3. Core wires a normal-turn caller holding a revocable AudioConsentLease through A4 admission and the complete C3 generator.
4. Perception adds history-aware rIMI, source/session-disjoint held-out outcomes and drift/shuffle controls before any attention-policy proposal.
5. Only after a real Android provider, OS consent, revocation and zeroization are independently proven may microphone capture be tested. No model swap or weight learning is implied.

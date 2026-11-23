# Research & Perception — current-base rebase handoff

**Date:** 2026-11-23  
**Release-development base:** `gpt6/v13-private-remote-bridge-20261111` @ `fb563d771fe2d493c4ec25abe94280981d24ef5c`  
**Branch:** `research-perception/v14-speaker-history-current-20261123-run5`  
**Code commit:** `c6d46c15c084194b605579e477ca7d475431ad75`  
**Status:** candidate branch only; no merge, release or device deployment.

## Why this rebase exists

- Perception PR #2433 was still based on `dfa3945b2bbfdb65d932db74e02f402435494e84`, 42 commits ahead / 72 behind the current release-development HEAD. Its current head was `acc68d6113eb320d283cfa0150230b40273d6e96`; exact-head CI for the final negative-prediction-error test was queued, not passed.
- Earlier code-tested head `cdc7bcc` had focused A4 source-outcome Python 3.13/3.14 PASS and offline-bridge security PASS. Those results are historical evidence for that exact code head, not a pass for this rebased commit.
- PR #2369's optional Teacher Ear/FASTDIAR work is included in the #2433 source snapshot; the lazy optional-module import/fail-closed consent behavior is retained. The rebase avoids preserving the stale stacked PR bases.

## What is now on the current base

Fourteen code/test/workflow paths were copied from the reviewed Perception source tree onto the current release-development tree without importing stale shared handoff/board files:

- `attention.py`: source-bound A4 outcome receipt and policy update; runtime.py already calls `Attention.source_outcome()` after final output (current consumer at line 643). It only scores exact hash-matching delivered **text** spans; this is not an audio-outcome learner.
- `neuromod.py`: transactional `signal_in_transaction` path and canonical `ModulatorPacket.path_id` contract.
- `audio_speaker_evidence.py` + `audio_voice_cues.py`: only VOICED embeddings can seed/update speaker-reference history. SILENCE, UNVOICED_NOISE, IMPULSIVE and UNCERTAIN embeddings are suppressed from speaker anchors; RAW EAR novelty remains separate. No speaker identity is assigned.
- `audio_teacher_ear.py`: optional caller-supplied timed ASR hypothesis with independent local-teacher and transcript opt-ins; ephemeral, unverified, no model load, no transcript persistence, no truth/learning/action authority.
- `audio_fastdiar_adapter.py`: diagnostic wrapper around caller-supplied 192-D frame embeddings and a locally hashed checkpoint. It does not run FASTDIAR inference, VAD, clustering or identity assignment. The upstream code is MIT at the pinned revision, but the checkpoint-weight license remains unspecified.
- Regression tests and three focused workflows for A4 source outcomes, FASTDIAR adapter and RAW EAR comparison were carried over.
- Research ledger appends R-110 on time-series JEPA evidence and R-111 on SPIN/GPA-style online continual-learning optimization; neither changes the preregistered M1 cohort or adopts a new optimizer.

## Exact source identities

Git blob IDs (SHA-1, **not** file SHA-256):
- `attention.py`: `ecaf39b1b8ea0edad7f4a39774230b3cbed1d5eb`
- `neuromod.py`: `fbb02147cbcfff10896736a20838fbce08d7409b`
- `audio_voice_cues.py`: `1fc3ac7b6624fcd0d1aef52a77ae6221fdf43288`
- `audio_speaker_evidence.py`: `08b17a39923e0f59a5dbbb9f173954936e59f85a`
- `audio_teacher_ear.py`: `5a26193c94c864e6ad3af55def59bae040e59f35`
- `audio_fastdiar_adapter.py`: `f2ebf6d4629777162c04d8f981b7b8c7e11c727e`

The prior Perception CI printed SHA-256 for the unchanged `attention.py` bytes as `58e68ce790c8754a4b5362e3e26f3ffbbdfe3455db99534ea518d1f58c5c280e`. Core must recompute/verify that digest on the new exact head before changing its allowlist.

## Verification state

- **LOCAL_LINUX full repository:** BLOCKED / NOT_RUN. This execution environment has no mounted Aii checkout; `git ls-remote` failed because github.com DNS did not resolve. No local compile or repository pytest is claimed.
- **Historical focused CI:** A4 source-outcome tests passed on Python 3.13 and 3.14 on the earlier code-tested head `cdc7bcc`; offline-bridge security passed on that same head. The later negative signed-error regression was added after that head.
- **Current rebased head:** exact-head CI must run and be reviewed; no PASS is claimed yet.
- **Integration blocker:** the Core-owned `record_only_controller_guard_20261116.py` still pins the previous `attention.py` bytes. Core must rebind that allowlist and all dependent recovery/stage/deployer pins bottom-up. The staged audio composer also needs the exact new `audio_voice_cues.py` source pin. Do not weaken fail-closed hashes or edit Core-owned guards from this lane.
- **REDMI_UNVERIFIED:** no Android microphone/AudioRecord provider, MediaProjection, APK/Termux test or native speaker/ASR inference was run. Last authenticated device receipt #775 recorded `dfa3945` installed, auto-update enabled and no runtime error; it does not cover this candidate or prove useful chat/audio behavior.
- **Deployment:** NOT_RELEASED. No UPDATE_REQUEST, manual command, model download/swap, permission change or user-data mutation.


## R-111 research note — SPIN / GPA-style online continual learning

- Full arXiv HTML review completed for Wu, Wang and Lin, *From Generic to Dedicated: A Novel Optimizer for Online Continual Learning*, arXiv:2610.27835, submitted 2026-10-20 (preprint).
- SPIN couples a fast plasticity iterate and slow stability iterate, evaluates gradients at their parameter interpolation, and slowly moves the stability iterate toward the updated fast iterate. The paper's Appendix G explicitly connects the construction to Generalized Primal Averaging (GPA); do not treat it as a wholly new primitive.
- Reported CIFAR-100 examples: GSA AAA 45.40→51.37 and MOSE final accuracy 46.95→48.33 under AdamW→SPIN-AdamW; mean relative forgetting 30.83→28.63 across the 11 methods. These are paper results from GPU/ResNet-18 experiments, not V14 or Android evidence.
- The paper reports extra optimizer-state memory (SPIN-SGD 240.75 MB / 1.13 ms per step versus SGD 155.86 MB / 1.04 ms on its CIFAR-100 setup). The authors list this overhead and the quasi-steady-state assumptions as limitations.
- No official code repository, code license or checkpoint/weight license was found by exact paper-title/arXiv-ID GitHub search. Nothing was imported or downloaded.
- Candidate only: after the existing JEPA/adapter baseline, compare AdamW, AdamW+EMA and GPA/SPIN on a small adapter with matched parameter/compute/memory budgets, source/session-disjoint sequential shifts, retention, gradients, parameter diffs, RSS/PSS, restart and rollback. No optimizer adoption or live weight change is authorized.

## Next owners

1. **Core:** recompute and rebind the attention/audio source pins and downstream recovery/stage/deployer hashes on this branch; retain the exact-source allowlist.
2. **QA:** run the exact Python 3.13/3.14 focused, staged/integrated, migration, privacy and consent-revocation workflows; test the missing-Teacher-Ear acoustic-only fallback and negative controls.
3. **Perception:** after integration is green, add a source/session-disjoint A4 outcome retention ablation. Keep microphone capture OFF until a verified Android provider and separate device consent exist.
4. **Boss:** sync the verified branch/PR and next action into the shared board and `V14_USER_NEXT_ACTION.md`. Those Boss-owned files were deliberately not overwritten in this lane.

**User action:** none required.

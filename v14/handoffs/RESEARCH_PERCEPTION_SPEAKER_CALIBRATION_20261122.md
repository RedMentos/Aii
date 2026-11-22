# Research / Perception handoff — RAW EAR speaker calibration

Date: 2026-11-22
Owner: research-perception
PR: https://github.com/RedMentos/Aii/pull/2349
Branch: research-perception/v14-speaker-calibration-runtime-20261122
Code/test checkpoint SHA: 097b2713c063548330c303c3060074de3f838cdb (the code-bearing commit whose selected CI gates passed). Handoff file first commit: 00edc5d96382296e775ed01cc1f4c376c5894ca6. Research-ledger CI follow-up: 7d49e679d9f829a88c6fe6a81b5f513b416cd9e0.
Base: gpt6/v13-private-remote-bridge-20261111 @ c4eb82deec915f65894c20d6ebbaf0ebf58fa335

## Product gap addressed

RAW EAR speaker embeddings previously exposed cosine similarity and caller-provided thresholds, but the caller's calibration label was not evidence. The A4 speaker-change decision therefore stayed DEFER. This patch adds an offline calibration report builder and a local opt-in loader; it does not identify speakers.

## Changed paths

- v13/code/v13/audio_speaker_calibration.py
- v13/code/v13/audio_speaker_evidence.py
- v13/code/v13/audio_voice_cues.py
- v13/code/tests/test_audio_speaker_calibration.py
- v13/code/tests/test_audio_speaker_evidence.py
- .github/workflows/v14-raw-ear-fastpath.yml
- .github/workflows/v14-raw-ear-vad-comparison.yml
- v14/V14_RESEARCH_LEDGER.md

## Test evidence

- LOCAL_LINUX, CPython 3.13.5: py_compile of the new module and test file PASS.
- LOCAL_LINUX, CPython 3.13.5: 12 calibration-only pytest tests PASS. Fixtures are synthetic; these validate deterministic splitting, threshold logic, model/temporal binding, artifact integrity, manifest allowlisting and negative controls only.
- LOCAL_LINUX full Aii integration: BLOCKED. No repository checkout was mounted and github.com DNS resolution failed. Do not describe the repository integration tests as locally passed.
- CI at code head 097b2713c063548330c303c3060074de3f838cdb: RAW EAR fastpath PASS, 128 tests on CPython 3.13.18 and 128 on 3.14.10 (including the calibration suite); VAD/WebRTC/libfvad comparison PASS on 3.13.18 and 3.14.10; consent-revocation QA PASS, 42 tests on 3.13.18; prosody-to-attention PASS, 66 tests on 3.11.18 and 3.13.18; public privacy scan PASS; private bridge tests PASS, 39 tests on 3.12.16. The later handoff/ledger-only commits triggered another run; the staged-context integration workflow was still pending when recorded. Read the current PR checks before any merge decision.
- TERMUX / Redmi: REDMI_UNVERIFIED. No authorized phone connection or microphone capture was available.

## Runtime behavior and safety

- Calibration builder defaults to SYNTHETIC_TEST; that artifact is rejected by the runtime loader.
- REAL_LOCAL is a caller declaration, not independently proven by the code. A real artifact must record dataset id/revision/license/use basis and an opaque SHA-256 authorization reference, pass source/session/speaker-disjoint held-out FAR/FRR gates, and be explicitly listed in the local models/speaker_calibration/approved.json manifest.
- The local manifest is owner-controlled opt-in, not a cryptographic signature. Hashes detect corruption/replacement but do not authenticate the owner or prove license/consent.
- The artifact stores metrics/digests only, not PCM, vectors or speaker labels. Loader is read-only, bounded, symlink-rejecting and offline.
- With an approved, model- and temporal-matched artifact, the runtime may emit CHANGE_OR_OVERLAP or CONTINUITY as an A4 hint. It cannot assign identity or grant learning/action authority.
- No calibration artifact is installed. No model or dataset was downloaded. Production speaker-change remains DEFER/OFF.

## Research

CAM++ (Interspeech 2023; full 5-page paper reviewed) is a possible English speaker-embedding candidate: 7.18M parameters, 1.72G FLOPs, 0.73% EER on VoxCeleb1-O and 6.78% on CN-Celeb under the paper's conditions. Those are speaker-verification results, not diarization/overlap or Redmi evidence. The official 3D-Speaker code repository is Apache-2.0, but the exact English checkpoint weight license was not verified in this run. sherpa-onnx is an Apache-2.0 Android/arm64-capable runtime candidate; no target AAR/model/ABI benchmark was run. No download or swap is proposed.

## Next executable action

1. Read exact PR #2349 checks and repair any failure.
2. Have Boss/Integrator review the calibration manifest and A4 consumer path; keep this PR draft until that review is complete.
3. Only after a separately licensed or locally owner-consented dataset and pinned model checkpoint are available, run a real source/session/speaker-disjoint calibration and report held-out FAR/FRR.
4. Only then measure feature extraction, TTFT/RTF, RSS/PSS and memory on authorized Redmi hardware. Do not enable the local manifest before those gates.

No user action is required now.


## Exact-head follow-up — 2026-11-22

- Current PR head after latest code, test, research and handoff updates: 8c51f86dfdf7dbe5392a8d594e7605527dc37a7a.
- Directory-race hardening: module commit 80bb94cc6a6438edfa121709beaf529f21e1681c; regression test commit f6ccc3a61b80b4d0f8545fa8ebb128da634b94a9. The loader now opens home, models and speaker_calibration as no-follow directory descriptors and reads approved.json plus the calibration artifact relative to the pinned directory descriptor. This prevents a directory rename/symlink replacement after validation from redirecting the reads.
- LOCAL_LINUX, CPython 3.13.5: isolated reproduction of the exact directory-descriptor helper behavior PASS — after opening the directory, replacing its path with a symlink did not redirect manifest/artifact reads; final-component symlink rejection PASS. This is an isolated helper reproduction, not the repository pytest suite.
- LOCAL_LINUX full repository tests: BLOCKED — no Aii checkout is mounted and GitHub DNS resolution is unavailable. No full local compile/pytest claim.
- CI on exact code commit f6ccc3a61b80b4d0f8545fa8ebb128da634b94a9: public privacy scan PASS; RAW EAR vs WebRTC/libfvad comparison PASS. RAW EAR fastpath, consent-revocation, prosody-to-attention were IN_PROGRESS at last read; staged-context/integrated regression was QUEUED. Earlier exact integration head 77a459e9ad3cd77255c38c2ebe8d901e8872a92a failed because the Core-owned integrated_audio_context_candidate_20261121.py still pinned audio_voice_cues.py to the pre-PR blob. The Core/Integrator pin update is still required; see PR #2349 comment 7081848688. Do not mark the PR merge-ready based on the focused audio checks.
- The same branch's audio research entries are R-084 (speaker calibration/CAM++), R-085 (S2SND-v2, full paper reviewed) and R-086 (streaming diarizer adaptation/identity retention, full paper reviewed). R-078 now also records the exact pinned llama.cpp internal token-embedding extraction seam. Shared team IDs R-080 through R-083 remain reserved for the JEPA receiver, Hypnos, receiver-aware latent communication and JEPA-TTT sequence. No checkpoint or dataset was downloaded; no model swap.
- Cross-agent B3 evidence: PR #2346 focused B3 paired-tap workflow passed, but staged/deploy/migration workflows failed on stale Core-owned pins for the changed recovery builder and Cognition source. See PR #2346 comment 7081892589. No native latent coupling or Redmi proof is established.
- TERMUX / Redmi: REDMI_UNVERIFIED for all new calibration changes. No calibration artifact is installed; speaker-change remains DEFER/OFF. No authorized microphone capture or Android test was run.

## Next executable actions

1. Core/Integrator must rebind the exact audio composer/recovery/stage/deployer pins for PR #2349, and the B3 recovery/observer pins for PR #2346, from exact file bytes.
2. Read the completed exact-head CI runs for f6ccc3a61b80b4d0f8545fa8ebb128da634b94a9; repair any Perception-owned failure, but do not absorb Core-owned files without coordination.
3. Keep #2349 and #2346 DRAFT until staged, migration and deployment gates pass; then obtain independent Boss review.
4. Only after separately authorized real data and a pinned, licensed embedding checkpoint exist, run source/session/speaker-disjoint calibration and temporal-identity retention evaluation. No user action is required now.


## CI status correction — exact code commit f6ccc3a61b80b4d0f8545fa8ebb128da634b94a9

The queued Perception checks completed successfully:

- RAW EAR fastpath / A5-A4-C3 consumer tests: **129 passed** on CPython 3.13 and **129 passed** on CPython 3.14. Exact command: python -m pytest -q -s tests/test_audio_ear_voice_cues_v14.py tests/test_audio_speaker_evidence.py tests/test_audio_speaker_calibration.py tests/test_audio_input.py. This includes the new directory-replacement race regression and the existing calibration negative controls.
- Pre-processing consent-revocation QA: **42 passed** on CPython 3.13.
- Prosody-to-attention A4/C3 regression: **66 passed** on CPython 3.11 and **66 passed** on CPython 3.13.
- WebRTC/libfvad VAD comparison: **9 passed** on CPython 3.13 and **9 passed** on CPython 3.14; native libfvad unit checks also passed in both jobs.
- Public privacy scan: **PASS**.
- Staged-context/integrated regression run 45042292782 remained QUEUED at the last read. It is still the merge blocker; the earlier exact integration head failed on the stale Core-owned audio composer pin. No full staged or deployment acceptance is claimed.

These are GitHub Linux CI results, not local repository execution or Android evidence. The isolated LOCAL_LINUX directory-FD reproduction remains a separate PASS; full local Aii checkout remains BLOCKED and Redmi remains REDMI_UNVERIFIED.


## Research-ID and receiver-space correction — 2026-11-22

- Boss/JEPA coordination reserves R-080 for the JEPA receiver, R-081 for Hypnos, R-082 for receiver-aware latent communication and R-083 for JEPA-TTT. This branch's audio entries were renumbered to R-084 (speaker calibration/CAM++), R-085 (S2SND-v2) and R-086 (streaming diarizer adaptation/retention). R-078 now includes the exact llama.cpp input-embedding extraction finding. Do not reuse R-080–R-083.
- Exact llama.cpp revision b29c606e28a01b1bc8c1351026a0fa6e616bf6c4 exposes input injection and output embeddings publicly, but not the input token-embedding table. An internal helper in src/llama-model.cpp reads model->tok_embd and dequantizes it; a row-only extractor using ggml_backend_tensor_get plus ggml_type_traits could provide the receiver input target space, but this is an internal ABI and not yet implemented or Android-tested. Core was notified on PR #2350 comment 7081998715.
- The current native receiver still consumes raw sender final-state taps and measures only input-effect/hidden-output metrics. The B3 Bridge remains a task-logit head, not a receiver-input projector. No semantic latent communication or native Redmi acceptance is claimed. The next true latent step requires a pinned row-only receiver input-embedding extractor, source-span-aligned paired training, source-disjoint holdout, then a receiver task-output comparison against zero/shuffle/no-message/symbolic controls.


## Final staged-integration result — 2026-11-22

Run 45042292782 has now completed with **FAIL** in both staged jobs:

- integrated-regression job 137269202505: 1 failed, at tests/test_staged_integrated_regression_20261111.py::test_single_staged_tree_runs_selected_integrated_regressions, exact error: ValueError: audio source blob changed: v13/audio_voice_cues.py.
- staged-runtime job 137269202708: 16 failed, 234 passed, 10 skipped, 2 errors, 47 subtests passed. All reported failures cascade from the same exact source-pin mismatch in Core's integrated_audio_context_candidate_20261121.py. Two migration tests report PARTIAL instead of UPDATED because staging cannot complete.
- This is the previously reported cross-owner pin mismatch, not a failure in the Perception RAW EAR/calibration tests. The exact composer still expects blob b18e450162b062b09368a12b1ca18924ed8c5025, while the Perception branch audio_voice_cues.py blob is 80bd30a129e26131d55f8de0202aa0d62f7c100d.
- Keep PR #2349 DRAFT and NOT_RELEASED. Do not rebase or edit Core-owned composer/recovery/stage/deployer files without the Core/Integrator owner. The targeted Perception CI is green; staged integration is not.

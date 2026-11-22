# Research / Perception handoff — RAW EAR speaker calibration

Date: 2026-11-22
Owner: research-perception
PR: https://github.com/RedMentos/Aii/pull/2349
Branch: research-perception/v14-speaker-calibration-runtime-20261122
Verified branch HEAD at handoff creation: 097b2713c063548330c303c3060074de3f838cdb
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
- CI at head 097b2713c063548330c303c3060074de3f838cdb: v13-private-remote-bridge-tests PASS; public privacy scan PASS. RAW EAR fastpath, VAD comparison, consent revocation and prosody-to-attention workflows were still running when this handoff was written; read the PR checks before any merge decision.
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

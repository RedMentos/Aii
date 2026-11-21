# Research & Perception — optional Silero VAD integration checkpoint

**Date:** 2026-11-21  
**Owner:** Research & Perception  
**Branch:** `research-perception/v14-raw-ear-consent-commit-guard-20261121`  
**Base:** `840a53ab19d0d9609e649f00b25e840465a15bcf`  
**Status:** candidate code; not released; Redmi unverified.

## Functional change

- New `v13/code/v13/audio_silero_vad.py` adds a caller-owned 16 kHz mono PCM16 Silero ONNX stream adapter.
- It follows the upstream streaming input contract: 64-sample context + 512-sample frame, recurrent state (2,1,128), 32 ms frame cadence.
- It keeps at most 511 incomplete samples in process memory, resets on source change, generation change, timestamp discontinuity or explicit consent reset, and emits bounded scalar VAD metadata only.
- `from_onnx()` requires an explicit local file, expected SHA-256 and model revision; it refuses symlinks, oversized files and hash mismatch. It never downloads a model. CPUExecutionProvider is forced with one intra-op and one inter-op thread.
- The existing RAW EAR V3 consumer accepts an optional stream object. When present, its VAD evidence is added beside (not instead of) pitch, prosody and non-speech cues, affects A4 salience and appears in the bounded C3 admission summary. Consent revocation resets the supplied stream.
- No microphone permission, capture, transcript, speaker identity, learning authority or action authority is added.

## Research / licensing

- Silero VAD upstream: MIT. Official source wrapper and README inspected.
- sherpa-onnx: Apache-2.0; official docs list Android arm64 VAD examples. Silero weights remain separately MIT-licensed.
- VoxRT alternative rejected for now: Kotlin wrapper Apache-2.0 but native runtime binary proprietary.
- No third-party code or weights imported. No ONNX Runtime dependency added to project requirements.

## Exact local checks

- LOCAL_LINUX Python 3.13.5, NumPy 2.3.5, pytest 9.0.2:
  - `python -m py_compile audio_silero_vad.py test_audio_silero_vad.py` — PASS
  - `pytest -q test_audio_silero_vad.py` — **12 passed**
- Tests use a fake ONNX session; no real Silero weights or ONNX Runtime were installed.
- Full Aii checkout unavailable because `git ls-remote https://github.com/RedMentos/Aii.git` fails DNS resolution. Full local repository tests are BLOCKED, not passed.
- CI and integrated Runtime tests are pending until this exact branch head is pushed.

## Evidence boundary

This is a **WIRED_SYNTHETIC_CANDIDATE**, not real-model inference, Android-native execution, microphone capture, or Redmi proof. No model download, model swap, permission change, device update or user-data mutation occurred. Official Age and learning gates are unchanged.

## Next integration

1. Core rebinds its staged A5 overlay to the exact new `audio_voice_cues.py` blob and preserves text/audio PerceptPacket separation.
2. Boss reviews the existing-module change; strict safe-additive rejection is not bypassed.
3. QA may propose a separate explicit, owner-consented Redmi microphone/VAD measurement only after a model artifact is separately approved and locally hash-verified.
4. Compare Silero vs RAW EAR V3 vs libfvad/WebRTC on the same licensed 16 kHz corpus before any default or production activation.

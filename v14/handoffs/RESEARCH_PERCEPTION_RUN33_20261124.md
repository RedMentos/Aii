# Research & Perception — Run 33 — 2026-11-24

**Started:** 2026-11-24 03:28:35 UTC (runtime-provided start)  
**Completed:** UNKNOWN at checkpoint; this handoff records the latest verified state, not a claim that the full run reached a platform limit.  
**Repository:** RedMentos/Aii  
**Working branch:** `research-perception/v14-audio-duplex-bridge-20261123-run21`  
**Base:** `gpt6/v13-private-remote-bridge-20261111` at `8d93236c753f0194224c19edc7411d8d7082b1d6`  
**PR:** [#2448](https://github.com/RedMentos/Aii/pull/2448), OPEN / DRAFT / NOT_RELEASED  
**Exact current branch HEAD:** `c7db1809370fae5ae5a49287e76cba0deedf80e7`

## 1. Implemented change

The optional RAW EAR speaker-consumer benchmark had become incompatible with the tightened schema-v3 registry: `SpeakerChangeEvidenceRegistry.update()` now requires `current_chunk_sha256`, but `benchmark_raw_ear_backends.py` did not supply it.

Commit `b85b60a7c656469023878236687a60fec514d5be` fixes the benchmark by generating a deterministic one-second, 16-kHz PCM16 fixture, hashing those exact bytes with SHA-256, including the digest in the synthetic embedding batch, and passing the same digest to the registry update. This preserves the production source-binding contract instead of inserting a placeholder hash.

Commit `c7db1809370fae5ae5a49287e76cba0deedf80e7` adds research record R-124. The work board was updated at `0fd436d4e61e33e914ceda2712b1b2c2158c0707` for V14-006 and V14-018.

## 2. Exact test evidence

### LOCAL_LINUX

- Environment: Python 3.13.5, Linux 6.18.57, x86_64.
- Deterministic PCM fixture check: PASS — 32,000 bytes, stable 64-character SHA-256 across repeat computation.
- Full repository checkout/test suite: BLOCKED — no Aii checkout is present in the local container and repository DNS/network access is unavailable. The local snippet check is not represented as a repository test.

### GitHub CI — exact head `c7db1809370fae5ae5a49287e76cba0deedf80e7`

- `V14 RAW EAR optional NumPy backend`: PASS, 128 tests on Python 3.13 and 128 on Python 3.14. The synthetic speaker-registry benchmark also completed for five iterations:
  - Python 3.13: median 0.9579 ms, p95 0.9940 ms.
  - Python 3.14: median 0.9118 ms, p95 0.9259 ms.
  - `device_benchmark=false`; this measures the synthetic registry consumer only, not neural speaker-model inference.
- `V14 RAW EAR audio duplex bridge`: PASS, 179 tests on Python 3.13 and 179 on Python 3.14.
- `V14 RAW EAR prosody-to-attention regression`: PASS on Python 3.11 and 3.13.
- `V14 RAW EAR pre-processing consent revocation QA`: PASS.
- `V13 runtime deployment integrity`: PASS on Python 3.11 and 3.14.
- `V14 RAW EAR vs WebRTC/libfvad comparison harness`: PASS on Python 3.13 and 3.14.
- `V13 staged context and integrated regression`: FAIL before the staged consumer can run.
- `V14 Core same-turn B1/B2/C4/C3 and source-read revocation`: Python 3.13 failed in the final staged fair-budget composition; the Python 3.14 job was still in progress at the last poll.

### Exact integration blocker — Core-owned source pins

The staged builder `v13/code/scripts/integrated_audio_context_candidate_20261121.py` still expects three old Git blob hashes. Current blobs on exact head `c7db180...` are:

| Source | Expected by staged builder | Current exact blob |
|---|---|---|
| `v13/audio_voice_cues.py` | `b18e450162b062b09368a12b1ca18924ed8c5025` | `e46a47bb93615126c8ee149baebfb6df9813fbee` |
| `v13/audio_speaker_evidence.py` | `37aa9c392bbb68d60ccff9749c75b41b8783c539` | `25474bb202c1209800f5c8a73e36aeca5555efd6` |
| `v13/audio_temporal_evidence.py` | `098ce2ec6bb0b744166d711a3401b7acf0252de1` | `e258f5dfecbf79d6f1a9d3adbfaf60631bb9d140` |

The exact failure is `ValueError: audio source blob changed: v13/audio_voice_cues.py`. This blocks the staged A5/A4/C3 path and many downstream staged tests. The script is owned by Core/Integrator; Research & Perception did not overwrite it. Core/Integrator must rebind the reviewed pins and rerun the staged/integrated workflows.

## 3. Current speaker-evidence contract and user effect

- The current speaker registry keeps bounded embeddings in process-local RAM, scopes state by source/generation/consent receipt, and only allows voiced frames to seed reference history.
- The tests include 1-s/2-s reference-timestamp invariance (10- and 20-frame lookbacks), non-voiced negative controls, receipt-epoch reset, exact current-PCM hash matching, and no vector persistence.
- The registry still reports `CURRENT_PCM_SHA256_MATCH_ENCODER_UNATTESTED`: the digest binds the declared batch to the PCM chunk but does not prove that an encoder actually generated the supplied vectors. Similarity remains diagnostic and uncalibrated; identity, learning, and action authority remain false.
- The change fixes a broken synthetic benchmark and gives passing focused CI. It does not add a speaker model, microphone provider, calibrated diarization, or a new user-visible voice capability.

## 4. Research note R-124

The official sherpa-onnx API exposes `SpeakerEmbeddingExtractor`; the project documents Android `arm64-v8a` speaker-diarization packages and uses Apache-2.0 for its runtime code. A separate model-license audit is still required.

The WeSpeaker official model documentation states that VoxCeleb pretrained weights follow CC-BY-4.0. The sherpa-onnx release lists `wespeaker_en_voxceleb_resnet34_LM.onnx` at 26,530,550 bytes (~26.5 MB); the LM variant is intended to improve longer-audio performance (>3 s). This is a research candidate only.

Upstream sherpa-onnx issue #4201 (opened 2026-11-14) documented severe CAM++ embedding dependence on audio length modulo 2 seconds in sherpa-onnx 2.0.1; the same report found WeSpeaker ResNet34-LM and 3D-Speaker ERes2Net stable in its test sweep. Upstream commit `1d9d23a` (2026-11-19) corrected CAM++ export pooling with `count_include_pad=False`. Exact cached model-asset provenance after the exporter fix is not proven.

Important interface caveat: sherpa's documented extractor returns an utterance/chunk embedding. It must not be silently inserted into the current 80-ms frame-vector contract. A future adapter needs a separate chunk-level or genuinely streaming contract, source/PCM/model provenance, reset and retention tests, and actual model measurements.

No model was downloaded, no user audio was used, and no weights were swapped.

## 5. Deployment, platform and Canon status

- **Release:** NOT_RELEASED. PR #2448 remains OPEN/DRAFT. A GitHub push is not deployment.
- **Updater:** no new update request was sent; no current-head installation receipt was obtained.
- **TERMUX/REDMI:** REDMI_UNVERIFIED. No connected handset was used; no microphone capture, sherpa native model load, `dir_fd`/`/proc/self/fd` Android check, ARM64 RSS/latency measurement, or Android UI/control test was performed.
- **Canon paths touched:** A5/RAW EAR speaker evidence, A4 salience/novelty diagnostics, STEP 9 VOICE_AUDIO research, and the speaker-registry synthetic benchmark. B1/B2 delivery, C3 basic-chat correctness, B3 trained latent receiver, Android microphone, speech effector/vocoder, and active weight learning remain unaccepted and were not changed by this checkpoint.

## 6. Next executable work

1. Core/Integrator rebinds the three exact source pins above and reruns staged/integrated CI on the same candidate head.
2. Research & Perception then builds an opt-in sherpa speaker-embedding adapter with a separate chunk-level contract; no model download until the user explicitly approves the experiment, and no productive model swap without a second explicit approval.
3. On authorized Termux/Redmi, verify descriptor support and real native model load only after the code path is CI-clean; collect RSS, latency, and negative-control evidence. Until then, keep REDMI_UNVERIFIED and keep speaker decisions at DEFER.

**User action:** none. No model, weight, permission, data, or installed-app change is requested.

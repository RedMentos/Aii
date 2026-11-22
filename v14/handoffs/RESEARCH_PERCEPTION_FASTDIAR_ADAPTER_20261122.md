# Research & Perception handoff — FASTDIAR frame adapter

Date: 2026-11-22
Base: `gpt6/v13-private-remote-bridge-20261111` at `c4eb82deec915f65894c20d6ebbaf0ebf58fa335`
Branch: `research-perception/v14-fastdiar-frame-adapter-20261122`

## Research basis

- Full paper read: Torgashov & Köpüklü, *FASTDIAR: Frame-Level Speaker Encoder for Streaming Diarization*, arXiv:2610.02941v1, submitted 2026-10-02; preprint, not peer-reviewed evidence.
- Official repo: `microsoft/fastdiar`, release tag `v0.1.0`, commit `e7f9bbccf98865216f48a04868d74f1d53c8734e`.
- The official README states that `fastdiar-embed` writes a float16 `(n_frames, 192)` matrix, one embedding per 80-ms frame. The streaming encoder has a causal two-second past; the diarizer adds a fixed 960-ms output delay.
- Paper scaling table reports 2.7M parameters for Small; the v0.1.0 README reports 2.4M. Keep the discrepancy visible rather than choosing one number.
- Repository code license is MIT (LICENSE blob `9003ea9e9eace590d66dfa2941266e463d75606c`). The release attaches checkpoints, but no separate checkpoint-weight license is stated in the inspected README/LICENSE/NOTICE. **Weights are not cleared by this review.**
- The pinned dependency stack includes PyTorch 2.13, torchaudio 2.11, torchcodec 0.15, NumPy, SciPy, Silero VAD, pyannote and other packages. This is not a Termux-ready dependency set. Reported CPU timings use an AMD Threadripper PRO 5995WX, not ARM/Redmi.

## Implemented

`v13/code/v13/audio_fastdiar_adapter.py` wraps an already-produced FASTDIAR frame matrix into the existing `v14.raw-ear-speaker-embeddings/1` contract:

- 192 dimensions, 80-ms frame step, 10-frame / 800-ms lookback;
- caller-supplied source, generation, immutable model revision and actual checkpoint SHA256;
- explicit first-frame timestamp; no inferred or relabelled sample times;
- strict finite-value, dimension, frame-count, timestamp and SHA validation;
- no model loading, downloads, audio decoding, clustering, persistence or dependency additions;
- no confidence threshold or calibration. A4 therefore remains `DEFER`; identity/learning/action authority stay false.

The adapter feeds the existing `consume_pcm16_voice_window` A5→A4→C3 consumer. The regression uses synthetic vectors only and checks that the consumer receives measured similarity while still deferring any speaker decision and persisting no vectors.

## Evidence boundary

- LOCAL_LINUX CPython 3.13.5 x86_64: exact adapter source `py_compile` PASS; isolated adapter unit suite **4/4 PASS**, including real NumPy float16 `(12,192)` input, dimension/non-finite/bool negatives, frame bounds, pinned revision and checkpoint SHA validation. Minimal import stubs were used because the full Aii checkout is unavailable; this does not count as a local A5/A4/C3 integration run.
- GitHub CI: pending exact-head pull-request workflow, including the real `consume_pcm16_voice_window` consumer regression.
- Full local Aii checkout: unavailable in this worker because GitHub DNS resolution fails.
- FASTDIAR model inference, weight-license clearance, ARM ABI, Termux, Android microphone and Redmi timing/quality: NOT_RUN / REDMI_UNVERIFIED.
- No model/weight/dependency download, installed-model change, permission change, or deployment.

## Next steps

1. Resolve FASTDIAR checkpoint-weight license and redistribution terms before any download.
2. Only after separate explicit user approval, evaluate a local checkpoint on a source-disjoint, consented dataset; compare no-model, current heuristic and FASTDIAR Small with overlap/noise/silence negatives, confidence-gate ablation, retention and latency.
3. Keep RAW EAR original PCM at its actual capture rate; FASTDIAR's 16-kHz feature view must use a separately validated anti-aliased resampler, not relabelled or block-averaged samples.
4. Integrate the adapter with the calibrated artifact path only after #2349's Core-owned composer pin chain is repaired and exact staged CI passes.


## GitHub checkpoint

- PR: https://github.com/RedMentos/Aii/pull/2361 (DRAFT / NOT_RELEASED), directly based on release HEAD c4eb82.
- Code SHA: `21962aba86dbf9a502ed4a6b567d761293ca2c17`; test SHA: `3d698fed4259df7795b64041787baa30c2bfbfa4`.
- The PR branch has advanced through documentation-only board/ledger/next-action/handoff commits after the code/test commits. The exact tested adapter SHA (`21962aba...`) and test SHA (`3d698fed...`) remain unchanged; inspect the live PR for its current branch head.
- LOCAL_LINUX isolated adapter tests 4/4 PASS. Exact PR CI is still pending; do not treat the adapter as fully integrated or deployed.
- Release c4eb82 has 21/21 listed Actions workflow runs SUCCESS and private V13OBS #115 confirms c4eb82 installed, but the latest device metadata still shows the existing B1/B2/C3 functional failures. No new audio or model test was run on the phone.

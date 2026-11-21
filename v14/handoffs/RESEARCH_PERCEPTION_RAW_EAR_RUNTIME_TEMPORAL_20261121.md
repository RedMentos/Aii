# Research & Perception handoff — RAW EAR temporal runtime state + VAD comparator

Date: 2026-11-21 11:00 CET  
Queue: V14-006 / Research & Perception  
Base: 944713cecf01751c1585ce46f6622214c31a820b on gpt6/v13-private-remote-bridge-20261111  
Branch: research-perception/v14-raw-ear-runtime-temporal-state-20261121  
Status: candidate implementation; exact CI pending; NOT_RELEASED; REDMI_UNVERIFIED

## Functional change

1. consume_pcm16_voice_window(..., temporal_state=None) previously used a stateless salience fallback. It now obtains a per-Runtime TemporalVoiceEvidenceRegistry by default. The registry:
   - keys state by (source_id, generation_id);
   - uses an RLock and a 16-stream LRU cap;
   - removes older generations for the same source;
   - stores only scalar evidence and timestamps, never PCM, transcript, speaker or user text;
   - clears runtime-held and explicitly supplied temporal state after failed consent rechecks;
   - exposes reset_runtime_temporal_voice_states for stream teardown/revocation.
   Explicit caller-supplied TemporalVoiceEvidence remains supported.
2. The offline comparator now reports onset/offset from actual smoothed state transitions at the end of the state-changing 40 ms window, with signed early/late delay. It can retune the libfvad instance when direct callers change sample rate and rejects PCM tails that would be discarded by the 20 ms hop.
3. The WebRTC Python wrapper is test-only. No VAD dependency, native library, model, weight or Android permission was added.

## Exact test status

- LOCAL_LINUX exact Aii checkout: BLOCKED — this worker has no repository checkout and git ls-remote fails because DNS cannot resolve github.com. No local exact-source compile or pytest PASS is claimed.
- GitHub CI: pending on the exact candidate head after push.
- Prior #2177/#2187 tests and comparator scratch measurements are historical evidence for earlier code only; they are not counted as this candidate's tests.
- TERMUX/REDMI: REDMI_UNVERIFIED. No connected phone, native microphone, Bionic build, RSS/PSS/CPU/battery, installed SHA or deployment receipt.

## Consumer and Canon boundary

- The function is a real adapter consumer: source-bound AudioPerceptPacket → temporal A4 salience modulation → bounded C3 admission candidate.
- The normal staged Runtime overlay in Core PR #2158 still pins the older V1 audio adapter. Core must update its exact source pin to the new V3 blob and preserve the existing text PerceptPacket while carrying audio_context through QueryPacket/OfferPacket. Acceptance still requires B1/B2 offers, C4 focal delivery and C3 consumption on the same event.
- This does not provide microphone capture, ASR, speech decoding/vocoder, full duplex, learned audio weights, native JEPA latent coupling or Android UI/device control.

## Research / licensing

- dpirch/libfvad commit 532ab666c20d3cfda38bca63abbb0f152706c369: BSD-3-Clause plus separate WebRTC PATENTS grant/termination text; C API, Autotools, make check.
- daanzu/py-webrtcvad-wheels release 2.0.14.post1, commit 726a8c72ce8b33b2df7ecd292372690fea2bad0c: MIT wrapper; bundled WebRTC-derived C needs its own provenance/patent review. PyPI lists manylinux/musllinux aarch64 wheels for CPython 3.13/3.14, not Android/Bionic tags.
- Android's official Bionic source confirms the Android libc/dynamic linker distinction. Do not infer Termux compatibility from Linux ARM64 wheels.
- No external code or dependency is imported into the product.

## Next executable step

Read exact PR CI. If green, ask Boss/QA to review the producer and have Core update #2158's adapter blob pin plus the QueryPacket/OfferPacket consumer. Then run the exact staged/integrated tests and, only with authorized device access, build/test a Bionic libfvad candidate and measure native microphone latency/resources. No user action is needed for this repository-side checkpoint.

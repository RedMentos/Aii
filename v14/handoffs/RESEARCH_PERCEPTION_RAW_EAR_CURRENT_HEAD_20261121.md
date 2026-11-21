# Research & Perception handoff — RAW EAR consent and current-base CI repair

**Date:** 2026-11-21 16:58 CET  
**Queue:** V14-006 — Research & Perception  
**Base:** `9d8f91960c568be7fe7dcf894555ce7250f635f4` (`gpt6/v13-private-remote-bridge-20261111`)  
**Branch:** `research-perception/v14-raw-ear-consent-current-20261121-run12`  
**Tested code/test tree:** `17f273395a869fd7469110773a5fe777a522909b`  
**Status:** REBASED_CANDIDATE / CI_GREEN_EXCEPT_SAFE_ADDITIVE / NOT_RELEASED / REDMI_UNVERIFIED

## What changed

This branch carries the exact RAW EAR candidate source and tests from the prior #2226 work onto the latest shared V14 base, without copying stale shared board/workplan/coverage snapshots. It includes:

- `v13/code/v13/audio_voice_cues.py` blob `9cae3b93388ea2c488e5af37a544ed0df5727f07`: bounded PCM16 pitch/voicing/energy/prosody/non-speech cues; source-bound AudioPerceptPacket; one linearizable consent lease across PCM processing, transactional Store persistence, temporal evidence, A4 attention and bounded C3 admission. The provider lease is authoritative and is not reacquired through a non-reentrant `consent_check` callback.
- `v13/code/v13/audio_temporal_evidence.py` blob `098ce2ec6bb0b744166d711a3401b7acf0252de1`: per-source/generation attack/release state, bounded 16-stream LRU registry, explicit reset and concurrency-safe first initialization.
- `v13/code/v13/audio_silero_vad.py` blob `95b6f586efb75910c2bc2f9105d711cd1ca1a87c`: optional caller-owned 16 kHz Silero ONNX stream adapter, 64-sample context + 512-sample frames, recurrent state, bounded incomplete PCM tail, source/generation/timestamp reset, explicit local file + SHA/revision checks, CPU-only single-thread configuration. No model is fetched.
- Regression tests cover silence/single-frame provenance, temporal reset/retention, A4/C3 delivery, optional VAD, Store rollback, pre-lease revocation, revocation serialization through A4/C3 and a normal non-reentrant provider lock.
- `v14/experiments/raw_ear_vad_compare.py` and its tests compare RAW EAR with WebRTC/libfvad using the same temporal smoother and event-transition timestamps; the native libfvad build is test-only and pinned to `dpirch/libfvad@532ab666c20d3cfda38bca63abbb0f152706c369`.

## CI workflow defect repaired

The old #2226 workflows targeted the prior QA branch, so the new release-base PR could silently skip dedicated gates. This branch now:

- includes the current `gpt6/v13-private-remote-bridge-20261111` target in consent, prosody/A4 and VAD PR filters;
- runs the consent suite on Research/Perception pushes and when its producer source changes;
- makes the privacy scan compare against the actual PR base ref (or the current V14 base on push);
- includes the Silero source/tests and comparator artifacts in privacy-scan path filters.

The strict safe-additive policy is not bypassed. Because this change modifies existing Runtime code and workflow files, independent Boss review is still required.

## Exact current-head CI evidence — SHA `17f273395a869fd7469110773a5fe777a522909b`

- Consent/revocation and non-reentrant provider-lock suite: **29 passed** on GitHub Actions CPython 3.13.18 (run `44922430577`).
- RAW EAR temporal + producer + optional Silero + A4/C3 regressions: **53 passed** on CPython 3.11.18 and **53 passed** on CPython 3.13.18 (run `44922430566`).
- VAD comparator: **8/8 passed** on CPython 3.13 and 3.14. Pinned native Linux libfvad build/check: **13 PASS / 0 FAIL / 0 ERROR** in each matrix job (run `44922430576`).
- Staged Runtime regression: **251 passed / 10 skipped / 47 subtests passed**; recovery shell syntax PASS (run `44922430553`).
- Integrated regression: **424 passed / 3 skipped / 58 subtests passed**, 6 warnings; no test failure (run `44922430553`).
- Privacy scan, model-lab, offline-bridge-security and same-repository integration-queue contract: PASS. The queue classified PR #2233 as `review_only_paths`; it did not merge or dispatch a release.
- Strict safe-additive validation: FAIL by policy because this candidate modifies existing Runtime modules and adds workflow files outside the validator's inert-module/test/handoff scope. No bypass; independent Boss review required.

**LOCAL_LINUX:** exact-source compile/pytest BLOCKED. Python 3.13.5 and Git 2.47.3 are present, but no Aii checkout is available and `git ls-remote` fails with `Could not resolve host: github.com`. GitHub Actions evidence is not a local checkout test.

**TERMUX/REDMI:** REDMI_UNVERIFIED. No current authenticated device receipt yet. Private read-only requests HEALTH #415, PIPELINE_STATUS #416 and DIAGNOSTICS #417 were issued; all three had no response at last readback. No microphone capture, native model inference, installed SHA or updater deployment is claimed.

## Research reviewed

- FD-VAD, arXiv:2609.35791v1 (2026-09-16), full text and official repository/model card reviewed. The TurnBench result (0.853 EOT recall at FP 0.097) has 1,019 ms median commit latency and is gated by at least 1 s post-speech silence; the separate 190 ms / 2% false-interruption operating point is not the TurnBench latency. The official repo is MIT, but the ~1.5 GB offline bundle combines WavLM (MIT), Qwen2.5-0.5B (Apache-2.0) and a ~119 MB adapter; its actual inference path uses PyTorch/torchaudio/Transformers/PEFT. English-only, A100 latency only. Do not download or replace RAW EAR.
- S4VAD, arXiv:2609.11110v1 (2026-09-10), full text reviewed. It reports 39.3 ms onset latency on LibriSpeech and 114.3 ms on AVA-Speech; XNNPACK hardware timing is on Apple M4 Max 64 GB. Evaluation includes synthetic LibriSpeech+DNS mixtures and AVA-Speech. No S4VAD-specific official code/license or Android benchmark was found.
- Full research notes R-031/R-032 were appended to `v14/V14_RESEARCH_LEDGER.md` on this branch. The practical follow-up is annotation-uncertainty-aware onset/offset evaluation and a lightweight optional semantic `TURN_STATE` experiment, separate from acoustic RAW EAR.

## Integration boundary and next steps

1. Boss/QA: review the exact provider-lease and revocation tests; verify all dedicated workflows trigger and pass on the new PR head. The strict safe-additive rejection remains visible for manual review.
2. Core: update the staged A5 consumer source pin to the exact RAW EAR V3 blob above; fix `audio_context_store.record()/view()` so it does not reacquire consent inside the lease; tombstone/delete derived AUDIO_ACOUSTIC_CONTEXT and clear process-local state on revocation; re-run combined producer→derived-context→C3 negative tests.
3. Perception/QA: after exact CI, compare RAW EAR, Silero and libfvad on the same licensed 16 kHz corpus with event-level latency and annotation-uncertainty reporting. Keep all audio paths source-bound.
4. Keep microphone capture, ASR, speech decoder/vocoder, full duplex, learning authority and model downloads OFF until separately implemented, measured and explicitly authorized.

No model, weights, dependency, permission, Age, updater setting or device data changed. This candidate is NOT_RELEASED. User action: none.

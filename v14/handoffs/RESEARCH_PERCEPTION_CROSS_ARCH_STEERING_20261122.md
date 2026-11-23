# Research & Perception handoff — cross-architecture activation transfer

Date: 2026-11-22  
Stack base: Boss integration branch `boss/v14-run11-current-evidence-sync-20261122` at `675666c695d5d1cad7126b384db4fb0ac31d3d17`  
Branch: `research-perception/v14-r091-cross-arch-steering-20261122-run7`  
Status: RESEARCH_ONLY / NOT_RELEASED / REDMI_UNVERIFIED

## Research finding (R-091)

Full paper read: Ayushi Agarwal, *Cross-Architecture Steering Transfer in Language Models: A Systematic Empirical Study*, arXiv:2608.05164, submitted 2026-05-26; preprint, not peer-reviewed in this review.

The study evaluates five English decoder-only models across two architecture lineages, uses residual-stream mean-pooling at roughly 50% depth, TopK SAEs, MNN feature matching and a 67M-parameter MLP bridge per directed model pair. It reports 47–49% cross-model feature-pair validation at ≥1.7B and 29.9–33.3% at 0.8B. Functional vector steering reports 71.0% win rate versus 68.0% native and 65.7% zero-projection; the 3 pp native comparison is not statistically conclusive (paired t(4)=1.85, p=0.14). The 1.7B boundary is only suggestive: one model per tier below 7B, and scale is confounded with positional encoding. QA and biomedical transfer are weak. All models share a corpus, and the paper defers T3 mechanistic activation-patching.

The released assets are not mobile candidates: approximately 52 A100-hours, 67M parameters per directed bridge, about 5 GB of bridge assets and a 1.3 GB global MLP. The paper declares code/selected artifacts Apache-2.0 and the derived corpus CC-BY-SA-4.0, with underlying model terms varying. The linked GitHub source could not be independently fetched via the connected GitHub API in this run (404), so no code reuse is approved. No weights or datasets were downloaded.

## Exact V14 distinction

The current `native_latent_receiver.py` path receives per-token final output embeddings from `LlamaRunner.tap`, feeds them into the receiver's input embedding boundary using `llama_batch.embd`, then compares output embeddings against zero/shuffle controls. It does not perform the paper's mid-layer residual injection and does not generate or score target task outputs. A measured `input_effect_rms` therefore proves numeric input sensitivity only. It must not be renamed semantic utility or learned B3 communication. The packet's `semantic_use_proven=false` and `production_route=false` remain correct.

## Next implementation sequence / ownership

1. **Core:** prove same-model token-prefill versus input-embedding parity on the exact pinned llama.cpp build; keep the native probe locally armed, one-shot and B3 OFF.
2. **Core + Perception:** add a separately gated target-generation path and an explicit utility receipt. Compare NO_MESSAGE, SOURCE_EXACT, same-model parity, projected input, zero, shuffled, row-shuffled and sign-reversed/bidirectional controls on identical source-disjoint prompts. Measure task correctness/evidence recovery, not just embedding RMS/cosine.
3. **Perception:** review source/model/position/layer provenance and ensure any mid-layer claim uses a real target-layer injection hook. Existing `native_layer_taps.cpp` is an extraction reference, not an injection proof.
4. **JEPA/Memory:** only after native target utility is proven, train a small pair-specific low-rank adapter and record actual gradients, parameter diffs, held-out/OOD gain, old-session retention, restart and rollback. No model-body weights or installed model are changed by this handoff.

## Evidence boundary

- LOCAL_LINUX: no full Aii checkout is mounted in this worker; no local repository tests or native model run were executed for R-091.
- CI: this research branch has no code tests; Boss integration CI remains authoritative for its own head.
- TERMUX/REDMI: no native model, Android receiver or phone test was performed. REDMI_UNVERIFIED.
- No device request, model download, permission change, weight edit or deployment occurred.

Next step: Core should implement same-model input parity and a separate target-generation utility gate before anyone claims native latent communication.


## R-092 — Adjacent RAW EAR signed ingress review — PR #2312 (2026-11-22)

The audio path is not the same as the MediaProjection UI adapter in #2375. The current Perception signed one-shot audio consumer is [PR #2312](https://github.com/RedMentos/Aii/pull/2312), exact code head `5221314d3c01ab6d874ecc0a8b8ff72c34e504a2`, stacked on QA PR #2286. It builds a one-second-or-less mono 44.1-kHz PCM16 request (88,200-byte cap / 117,600 Base64 chars), verifies the pinned P-256 companion receipt, request/nonce replay, source, Runtime generation, PCM digest, sample geometry, monotonic interval, Android RECORD_AUDIO status, local consent and FINAL provenance, then submits to the existing RAW EAR `audio_input.submit_audio_only` consumer. It persists replay metadata only. It does not open AudioRecord, request permission, run in the background, transcribe, identify speakers, update weights, grant T8 learning or authorize actions.

**Exact CI:** dedicated signed-consumer workflow `44992975596` SUCCESS. Staged/integrated workflow `44992975599` FAILURE: 238 passed / 10 skipped / 47 subtests, with two inherited two-checkout migration tests expecting `last_result=UPDATED` but observing `PARTIAL`. The worker path/profile checks passed. Treat this as a shared QA/Core updater migration blocker; do not weaken the assertions or project the dedicated consumer PASS onto staged acceptance.

**Superseded branch:** PR #2310 still carries a 16-kHz consumer and is not the correct branch to merge. PR #2312 is the 44.1-kHz successor; do not keep divergent copies of `audio_capture_consumer.py`. Deduplicate the identical `audio_input.py` dependency from #2304 when the parent chain is integrated.

**Platform research:** official Android AudioRecord documentation says 44.1 kHz is the only rate guaranteed across all devices; `getState()` and `getSampleRate()` must be checked. Android may resample hardware input to the requested client format, so the receipt must bind the actual client PCM. On API 29+, register `AudioRecordingCallback` before capture and reject capture silencing, device-route changes, preprocessing or stream-property changes. The Android sharing-audio-input guide explains that a competing higher-priority capture can cause an ordinary app to receive silence. Sources: [AudioRecord](https://developer.android.com/reference/android/media/AudioRecord), [AudioFormat](https://developer.android.com/reference/android/media/AudioFormat), [Sharing audio input](https://developer.android.com/media/platform/sharing-audio-input).

**Next owner actions:** Core/QA implement a visible, explicitly consented AudioRecord provider with RECORD_AUDIO, lifecycle/foreground handling, callback-before-start, exact sample count, route/silence/format-change rejection, release and buffer clearing. Perception rebases #2312 onto the current QA/Boss chain and deduplicates #2304. Then run the composed RAW EAR → A5 → A4 → C3 tests and only later an explicitly consented Redmi capture test.

Status: dedicated consumer CI PASS / staged migration FAIL / Android provider absent / REDMI_UNVERIFIED. No model, weight, permission, user data or device state changed.


**QA companion exact-source check:** current ref `qa/v14-companion-os-permission-contract-20261122` is at `7650ae0c19e93e4b6cbb778abb2f5123e49c364f`. `android-companion/app/src/main/AndroidManifest.xml` contains no `RECORD_AUDIO`; `CapabilityRegistry.java` marks `audio_capture` unavailable (“No one-shot visible AudioRecord provider; capture remains disabled”); `AudioCaptureDefaultOffTest.java` asserts the permission is absent. The provider is intentionally OFF. PR #2312 still names historical base `58666ddfc9945612a2117e1a844f812442d4ca64`; do not call it current-base until the QA/Boss parent stack is reconciled and the Perception branch is rebased.

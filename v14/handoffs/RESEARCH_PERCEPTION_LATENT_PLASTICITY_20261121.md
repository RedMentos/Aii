# Research/Perception handoff — cross-model latent ingress and online plasticity

Date: 2026-11-21
Lane: Research & Perception
Stack base: Boss integration PR #2258, readback 0ecbb1aac1f70c63cb39428a18811cfe4fd66d56
Status: research handoff only; NOT_RELEASED; REDMI_UNVERIFIED

## What changed in the evidence

- Research ledger entries R-047, R-048 and R-049 from the Perception source branch are synchronized onto the current integration stack.
- R-050 adds full-text reviews of XKV (arXiv:2608.20617) and HeteroFold (arXiv:2609.32259), a legal/OSS check of the HeteroFold repository, and an exact b10964 llama.cpp API inspection.
- R-051 adds a full-text review of Kong & Sutton's online growing/elastic network paper (arXiv:2608.01475).
- No production model, weight, permission or phone state changed.

## Current native latent facts

1. V13's existing LlamaRunner tap can obtain per-token final embeddings through the llama-server embedding mode. That is an output tap only.
2. Pinned llama.cpp b10964 (commit b29c606e28a01b1bc8c1351026a0fa6e616bf6c4, MIT) has llama_batch.embd for raw input token embeddings when token IDs are NULL, plus model input/output embedding dimension queries.
3. The b10964 llama-server HTTP surface exposes output embedding routes; no raw input-embedding injection endpoint was found.
4. llama_state_seq_get_data/set_data serializes one sequence in a context, but the API does not promise cross-model or cross-revision cache compatibility.
5. Therefore the first realistic activation bridge is a custom local libllama receiver wrapper. It must read the actual sender output and receiver input dimensions from loaded model metadata, validate positions and provenance, and remain OFF by default. This is not native K/V injection and is not XKV.

## Suggested implementation contract

Owner: Core & Harness. Research/Perception supplies the receiver contract and test design; JEPA supplies the later adapter-training/retention gate.

- Add a separate local native receiver executable/wrapper pinned to b10964. It accepts a bounded float embedding sequence and source/model revision metadata, then builds a llama_batch with token=NULL and embd set.
- Reject wrong receiver model revision, wrong embedding width, non-finite values, invalid sequence positions, excessive length and stale source generation. No remote shell or HTTP exposure.
- First test same-model parity by comparing ordinary token-ID prefill against input embeddings looked up from the same model. Require equivalent logits/next-token output within an explicit numerical tolerance.
- Negative controls: zero embeddings, shuffled embeddings, reversed positions, wrong dimensions, wrong model revision, empty input, NaN/Inf and overlong sequences. All must be rejected or measurably differ from baseline as appropriate.
- Only after parity and negative controls pass, train a small per-direction B1→B2 adapter while both bodies remain frozen. Record gradients, parameter diff, held-out utility, old-session retention, checkpoint/restart and rollback.
- Compare exact text, current symbolic path, latent path, no-message, zero, shuffled, reversed-position and OOD controls on identical tasks. Measure prefill, TTFT, RSS/PSS and adapter time separately.
- Later, if the receiver seam is stable, add native K/V tap/injection and test an XKV-style dual-cache, receiver-position translator. Do not use sequence-state serialization as an assumed cross-model cache format.

## Research caveats

- XKV: 45 settings, five split-evidence QA datasets, Qwen-0.6B/Gemma-1B/Llama-3B pairs, one A100 80GB/Ubuntu 22.04/CUDA 12.2 run. 5.8 ms is translator-only; both models still prefill. No official code/license found.
- HeteroFold: Llama-3.1-8B/Qwen3-4B/Ministral-3-14B in BF16; 10.7× result is a 32K-context comparison on a specific direction. Some task scores remain below text communication. Official repo pyproject declares MIT, but no root LICENSE file was present at the inspected main SHA; CUDA 12.8/PyTorch 2.9.1 stack and ~50 GB model weights make it unsuitable for Redmi reuse.
- AGN/AEN: online permuted MNIST/FashionMNIST, SGD 0.001, 10K/40K samples per task, dormancy estimated from 5% samples. Reported accuracy is online training accuracy, not retained old-session holdout. Use only as a small-head experiment after stable retention.

## Exact current code/test state

- PR #2256: head 63b5410769b872ddb64e002ab1c764e9e90966af. RAW EAR optional NumPy workflow 5 PASS; prosody-to-attention 173 PASS; consent-revocation 40 PASS; WebRTC comparison 117 PASS; staged/integrated 2148 PASS. Safe-additive validation is FAIL_BY_POLICY because an existing module is modified. No ARM64/Termux or Redmi measurement.
- PR #2255: head acca00e11192dafc20fa55de5fbf0752f7e4f7ba. A5 lease-focused workflow 59 PASS and privacy scan 319 PASS; staged/integrated workflow 2168 FAIL. It is not independently merged.
- Boss integration PR #2258: head at last readback 0ecbb1aac1f70c63cb39428a18811cfe4fd66d56; no workflow runs were returned for that newest head at readback. This handoff is stacked on that branch and requires exact-head CI after further integration commits.
- Local full repository tests: BLOCKED; no complete Aii checkout in the worker and github.com DNS failure on git ls-remote. No local Linux full-suite PASS is claimed.
- Redmi/native Android: REDMI_UNVERIFIED. No phone was reachable or exercised. No microphone, UI provider, native input-embedding receiver or B1/B2 K/V path was tested.

## Next action

Core builds the gated b10964 native receiver wrapper and proves same-model input-embedding parity. Perception reviews its model metadata, activation provenance, dimensions, position mapping and negative controls. JEPA then owns the small adapter's source-bound training, holdout utility and per-session retention. Production B3 remains symbolic/SHADOW until an actual receiver consumes the learned activations and passes all controls.



## Private device receipt

Private PIPELINE_STATUS request #435 remains open with zero authenticated comments; #431/#432/#403 also have none. V13OBS #115 was last updated 2026-11-18 and is only a historical five-turn snapshot, not a current device receipt. Therefore the installed SHA and updater status are UNKNOWN; REDMI_UNVERIFIED. No UPDATE_REQUEST, LOG_PAGE, shell command, model/weight change, permission change or phone mutation occurred.


---

## Boss integration correction — 2026-11-21 23:26 CET

The original handoff is preserved above. Its branch snapshots are historical; current exact state is:

- Boss #2258 branch head is moving; latest head at this correction is `646cdc32b5afd39c76bb0e83e2c54e8a23541a4f`, based on release-development `bdcad466ffea75a2b41f7d23be168f53c7197d20`. The code-bearing parent `0dc337e` passed its staged/integrated, A5 lease, audio/arithmetic, Lab-Age, owner-read, migration, deploy-integrity, offline and privacy CI. The current head has 14 queued checks and 2 additive-validator skips; no current-head PASS is claimed. #2258 remains DRAFT / NOT_RELEASED.
- Current Perception #2256 head `08fce3420ff2fc548276c421e99e79390d78e910` fails two Python 3.13/3.14 speaker-evidence tests because current-batch frames contaminate the pre-batch look-back. Keep the NumPy backend optional and default Python until fixed.
- Current Core native receiver #2266 head `3166858133844fc80201334f53ade450557d1191` contains the operator-only llama.cpp input-embedding probe; isolated wrapper/C++ selftests were reported PASS, but exact Python, pinned library build and Android ARM64 CI are queued. No model execution, semantic use, K/V injection, trained adapter or Redmi test.
- Current JEPA #2247 head `4ec92e89d3bb22fb6cf2792d01d02ae131feacff` has current-head A→B→A/staged/deploy workflows queued. Prior-head A2 updates are not current-head acceptance.
- Private owner-read request RedMentos/Aiiii #440 has no authenticated reply. Installed SHA and updater consent remain UNKNOWN. No update request or device mutation occurred.
- HeteroFold's repository declares MIT in pyproject metadata but has no root LICENSE file at the inspected main SHA; reuse is license-unverified. XKV and AGN/AEN are preprints and remain research-only. No model/code/weight import occurred.
- No local full Aii checkout or full local test was available; GitHub DNS resolution failed. GitHub CI is not Android proof.
- User action: none. REDMI_UNVERIFIED / NOT_RELEASED.



## RAW EAR speaker-change correction — 2026-11-21

### Current-base code slice

- Research/Perception owns the optional source-bound speaker evidence consumer and the batch-boundary correction. It is an additive path over caller-supplied PCM16; the default Runtime call still supplies no embeddings and loads no model.
- v13/code/v13/audio_speaker_evidence.py validates source/generation, model revision/checkpoint SHA, dimensions, frame timestamps and bounded look-back history. Embeddings remain process-local and are not persisted; output contains scalar cosine/change evidence only. No speaker label, identity, learning authority or action authority is emitted.
- v13/code/v13/audio_voice_cues.py optionally carries the evidence into A5 PerceptPacket, A4 salience/novelty and C3 summary. The optional NumPy pitch backend remains explicit; Python remains the default.
- Correctness fix: each batch now compares all its frames only with a snapshot of the stream history that existed before that batch. New frames are appended only after scoring. This prevents later same-batch frames from becoming their own look-back references and masking a speaker transition. The first batch is WARMUP; subsequent batches can produce measured evidence.
- Regression test_same_batch_tail_cannot_overwrite_cross_window_change_evidence compares 1-second and 2-second batches containing the same A→B transition. The old loop returned a false negative on the longer batch; the snapshot algorithm returns the same cross-window candidate for both.

### Exact test and environment boundary

- LOCAL_LINUX algorithm-level reproduction: PASS on CPython 3.13.5 x86_64. Old algorithm negative control reproduced the false-negative; corrected snapshot algorithm passed the 1-s/2-s invariance check.
- LOCAL_LINUX full Aii repository suite: BLOCKED — no complete checkout is mounted and GitHub DNS is unavailable in this worker. The repository test file and full staged/integrated suite have not been executed locally.
- The first PR-triggered runs 44957913408/44957913340 were superseded/cancelled during documentation-only pushes. Current code/test tree 880bfc has RAW EAR run 44958073016 (Python 3.13/3.14) and staged/integrated run 44958072992 QUEUED, not PASS; no integration candidate is accepted until exact result readback.
- REDMI/TERMUX: REDMI_UNVERIFIED. No phone, microphone, model weights, permissions, updater or device state was touched. No model download or swap.

### ReDimNet2 ONNX alternative

- Full arXiv HTML for ReDimNet2 (arXiv:2603.11841) and official PalabraAI repository/README were reviewed. The model family offers B0 1.1M/0.33 GMAC, B1 2.1M/0.56 GMAC, B2 3.6M/0.95 GMAC and B3 4.1M/2.70 GMAC; these are utterance-level speaker embeddings, not 80-ms causal streaming outputs.
- The MIT-licensed B3 ONNX conversion model card reports an 18,045,013-byte artifact, 192-D output and parity against PyTorch on 3-s/6-s examples. ONNX Runtime documents Android Java/C/C++ packages with CPU, NNAPI and XNNPACK options; device performance and Termux ABI remain unverified.
- This is a segment-level reference/enrollment candidate, not a drop-in replacement for FASTDIAR. No model was downloaded; experimental try and production swap remain separate explicit approvals.

### Coordination and next action

- The earlier #2272 branch was 16 commits behind the current Boss #2258 head and mergeable=false. A clean current-base Perception branch was created from Boss #2258 head 34eb645357d65bdd5ac69b9fb2c834d043086dac; it carries the optional backend, speaker consumer, regression and research update without copying stale board/user-next-action snapshots.
- Core/QA should run exact Python 3.13/3.14 speaker tests plus staged/integrated workflows on the replacement PR. The staged runtime had an independent source-pin failure in the older #2272 stack; do not attribute that to the speaker algorithm or call it a pass.
- Keep the speaker path and NumPy backend opt-in until real consented speech, ARM64/Termux cold-load/RSS/latency and Redmi false-positive measurements exist.



## Native latent receiver cross-review — 2026-11-21

- Verified the exact pinned llama.cpp header at b29c606e28a01b1bc8c1351026a0fa6e616bf6c4. Public input-embedding APIs are present: llama_batch.embd, llama_batch_init with a nonzero embedding dimension, llama_model_n_embd_inp/out, llama_decode, llama_get_embeddings_ith and llama_memory_clear. The Core probe is a genuine native input-embedding ingress mechanism.
- Core PR #2266 exact head 3166858133844fc80201334f53ade450557d1191: workflow 44955501021 PASS for Linux build against the pinned API, Python 3.13/3.14 runtime/contract tests, and Android arm64-v8a cross-compile.
- Boundary: CI did not load a real GGUF model. The native self-test exercises the compiled core; Python runtime tests use a fake executable and fixture model bytes. No native model-to-model semantic transfer, trained projector, B3 production route or Redmi execution is proven.
- The receiver rejects dimension mismatch rather than padding/truncating or using an untrained resize. Positive-vs-zero RMS and shuffle/repeat controls prove only that the supplied vectors affect native output, not that the representation is semantically aligned.
- Core's staged/integrated workflow 44955501004 FAILS separately: stale source pin for v13/contracts.py plus migration assertions returning PARTIAL instead of UPDATED (19 failed, 230 passed, 10 skipped, 2 errors). This does not invalidate the native receiver compile, but it blocks integrated acceptance.
- PR #2266 is based on the old release branch bdcad466ffea75a2b41f7d23be168f53c7197d20 rather than current Boss #2258. Perception posted exact API/CI findings on #2266; no Core code was changed.
- Next: Core rebase/stack #2266 on current #2258, repair the separate staged arithmetic source pin/migration failures, then run a real receiver only with an already-installed authorized model and explicit local consent. A learned, versioned projector plus held-out semantic/retention tests remains necessary for genuine cross-model latent coupling.

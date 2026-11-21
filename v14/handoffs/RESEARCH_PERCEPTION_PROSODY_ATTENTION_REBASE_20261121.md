# Research & Perception handoff — 2026-11-21 (rebased candidate)

## Queue ownership and current base

- Queue item: V14-006 — Research-to-code and active perception learning.
- Latest verified release-development base at this checkpoint: 569680bc10eabeb94ea5a1695d4bf77b8584e0a0 (14 commits ahead of the PR's original 04635a5522ab095f79544e23d9aa0330b0c9ff7a base; no overlapping code paths in the compared release commits).
- Current PR: #2177 — RAW EAR V3 prosody adapter on latest integration head, DRAFT / NOT_MERGED / NOT_RELEASED.
- Branch: research-perception/v14-prosody-attention-current-20261121.
- Current PR branch head before final base retarget: 32045d02eab5b5e555432f402ed6f829f5fa32ca. The tested code/test tree remains 1c4bb678025b421b98766cbce61570eec4683a52; subsequent commits only restore shared docs and extend the research ledger.
- Producer blob: v13/code/v13/audio_voice_cues.py = 0e328d14883840190937f0fef24a8e895ba7261c.
- Test blob: v13/code/tests/test_audio_ear_voice_cues_v14.py = 96b00b2e1b6340e2a61a8b6f230be8747889ab38.
- The earlier temporary rebase PR #2176 was closed after the release branch advanced; original #2161 remains the historical candidate and is not treated as integrated.

## Implemented A5 → A4 → C3 adapter

RAW EAR V3 extracts bounded pitch, voiced fraction/confidence, whole-window energy, voiced-frame 10th–90th percentile energy range, and a deterministic prosody-change score. Prosody is emitted only for voiced activity, preventing silence-padded onset/offset energy from being mistaken for prosodic change. The score is a relative salience heuristic, not a speech probability or calibrated confidence.

- A4 receives bounded novelty and interrupt contributions from voiced prosody; non-voiced noise/impulse remains a separate bounded activity signal.
- C3 admission receives the source-bound cue summary alongside F0 and energy ranges.
- The path accepts caller-supplied PCM16 only. No microphone is opened; raw PCM is not persisted; no ASR, VAD, speaker identification, speech learning, full-duplex or action authority is added.
- Core PR #2158 owns the staged normal-Runtime consumer and must update its exact producer pin to the V3 blob after review. This PR does not itself prove microphone ingestion, B1/B2 offers, C4 selection, C3 final output or phone behavior.

## Verification

### LOCAL_LINUX

- Exact local Aii checkout and repository pytest: BLOCKED because git ls-remote https://github.com/RedMentos/Aii.git cannot resolve github.com in this environment.
- Isolated Python 3.13 synthetic reproduction of the V3 algorithm: 13/13 PASS (voiced tone, pitch sweep, voiced energy burst, unvoiced-noise/silence/impulse negatives, 8/12/16/44.1/48 kHz, silence-padding rejection, and one-second input bound). This is not the exact repository suite.

### GitHub CI on exact code/test tree 1c4bb678025b421b98766cbce61570eec4683a52 (unchanged in current PR head 32045d02eab5b5e555432f402ed6f829f5fa32ca)

- Focused RAW EAR producer/consumer workflow 44880145343: Python 3.11 and 3.13 jobs both PASS; the file contains 12 test cases per version.
- Public privacy scan 44880145314: PASS.
- Staged-runtime/integrated-regression 44880145311: IN_PROGRESS at last readback.
- Generic safe-additive check 44880145319: FAIL because this candidate intentionally changes an existing producer and its test; do not bypass or weaken this policy. Independent Boss review is required.
- No merge, release, deployment or phone test is claimed.

## Research R-021 — causal transfer and middle-layer extraction

Full text of arXiv:2608.16347v2 (2026-11-09) reviewed: https://arxiv.org/html/2608.16347v2 . It finds 45–50% top-1 projected-state retrieval vs 5% chance for three decoder-only model pairs, but causal generation transfer passed its preregistered criterion for only Qwen2-0.5B→Phi-3-mini (23.3% vs 0% unrelated-state control, FDR p=.0469, n=30); two Mistral-targeted pairs were null. Retrieval success often did not yield a correct answer or shared meaning. Preprint, CC BY 4.0; code/data archive reported at Zenodo 10.5281/zenodo.24088479 (MIT code, CC BY 4.0 data/docs). Consequence: B3 needs real receiver injection plus held-out utility and negative controls, not CKA/retrieval alone.

OSS candidate gdonninelli/ggml-extractor main commit 0449f6335ce99f009c204e8c844a78eca6e9289d, MIT, C++17/CMake ≥3.20. It uses a context-creation cb_eval trampoline to capture selected l_out-* rows in the same context/KV cache; README verifies llama.cpp 5ecbe1ac1 (2026-08-18) and reports a CPU Gemma 3 1B Q8_0 benchmark. V13's pinned llama.cpp b29c606e28a01b1bc8c1351026a0fa6e616bf6c4 (2026-09-14) contains the documented cb_eval, llama_memory_*, llama_n_ctx_seq and Jinja source symbols, but no exact build/ABI/Android test was performed. Existing V13 native_layer_taps.cpp already extracts intermediate l_out-*; no dependency is vendored until exact pinned build and ARM checks justify it.

## Device / release status

- Private owner-read issue #115 was last updated 2026-11-18 and has no newer comment/receipt. Current installed SHA and updater consent are UNKNOWN; private read requests #368/#373 expired without a device response.
- REDMI_UNVERIFIED. No UPDATE_REQUEST, shell action, installer, model download/swap, permission change or phone/user-data mutation was performed.
- Core #2158 must update the V3 source pin and prove separate text/audio PerceptPacket modalities plus normal Runtime and B1/B2→C4→C3 consumption. The V3 adapter alone is not a release or whole-system acceptance.

## Research R-022 — audio continual learning and VAD

Full 24-page PACE paper reviewed: ICLR 2026, arXiv:2602.03355. It evaluates EAT (12-layer ViT, AudioSet-2M pretraining) on six class-incremental audio benchmarks; PACE reaches 90.95/94.05/69.08 average top-1 on TIMIT-2/TIMIT-3/VocalSet, versus RanPAC 85.63/89.92/62.82. Removing gradient projection drops VocalSet to 58.55; the no-projection session-1 heatmap reaches 7.9% after session 8. Single-GPU training-time overhead vs RanPAC is 1.22x/2.96x/3.13x on VocalSet/TIMIT-3/TIMIT-2. This is not mobile inference evidence. No official code/weight license or Android build was verified.

S4VAD arXiv:2609.11110 (2026-09-10) was checked at abstract level only; it motivates onset-delay metrics but has no verified implementation/license in this scan. libfvad is a BSD-3-Clause WebRTC-VAD C port with a separate Google patent grant; keep both notices. VoxRT's Android Silero wrapper is Apache-2.0 but its compiled runtime is proprietary, so it is not the default open-source path. No code, dependency or model was imported.

## Next executable step

Boss independently reviews PR #2177. Core updates the exact V3 source pin in #2158 only after review/merge and completes the staged consumer path. Research then compares existing native_layer_taps.cpp against ggml-extractor on exact pinned b10964, followed by pair-specific middle-layer receiver utility tests with no-message, shuffled, random, symbolic and exact-text controls. No model swap is proposed.


## Final exact-head CI readback — 2026-11-21 08:25 CET

- Exact RAW EAR workflow 44880145343: Python 3.11 PASS and Python 3.13 PASS, 12 tests per version.
- Privacy scan 44880145314: PASS.
- Staged/integrated workflow 44880145311: staged-runtime PASS (240 passed, 10 skipped, 47 subtests); integrated-regression PASS (415 passed, 3 skipped, 58 subtests).
- Safe-additive policy workflow 44880145319: FAIL because the existing producer is deliberately changed. This requires independent Boss review; no policy was weakened.
- Exact code/test blobs did not change after tested code head 1c4bb678025b421b98766cbce61570eec4683a52. Documentation commits were appended afterward.
- The current release branch is 569680bc10eabeb94ea5a1695d4bf77b8584e0a0. Stale shared edits to V14_LIVE_WORKPLAN.md, V14_WORK_BOARD.json and V14_USER_NEXT_ACTION.md were removed by restoring those files byte-for-byte to this release HEAD. R-021 was preserved and R-022 was appended to the research ledger. PR #2177 is now ready to be retargeted to the same release branch; Boss still owns final review and merge.
- Local exact repository suite remains BLOCKED by GitHub DNS. Local synthetic algorithm reproduction remains 13/13 PASS. Redmi remains REDMI_UNVERIFIED.


## Documentation and ownership cleanup — 2026-11-21

- Removed this candidate's stale edits to the shared workplan, board and user-next-action; each now reads back byte-identically to release HEAD `569680bc10eabeb94ea5a1695d4bf77b8584e0a0`.
- Preserved the existing R-021 activation-transfer note and added R-022 with full-text PACE review, S4VAD evidence boundary, libfvad BSD-3-Clause + patent notice and the proprietary VoxRT runtime caveat.
- No V14 master, historical V13 Canon, Runtime/stager/deployer, installed model, phone permission or user data changed.

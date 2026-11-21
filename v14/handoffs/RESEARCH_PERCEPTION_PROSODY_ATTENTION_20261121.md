# Research & Perception handoff — 2026-11-21

## Queue ownership

- Queue item: **V14-006 — Research-to-code and active perception learning**.
- Cross-lane finding: V14-003 native latent receiver feasibility; Core owns the actual receiver runtime.
- Latest release-branch base at retarget: `034a941694b9e8994d1bfe5cd781d27b943e1ed0` (includes merged #2165 model-lab candidate).
- Branch: `research-perception/v14-prosody-attention-20261121`.
- PR: [#2161 — RAW EAR prosodic dynamics → A4 attention](https://github.com/RedMentos/Aii/pull/2161), DRAFT / NOT_RELEASED.
- Latest handoff branch head before this file: `e9637f3de99c99330be3d7e0e1caa3418bf5b006`.
- Code/test tree tested by CI: `3cba5118e8b9641220ec411f859d20147218c6f9`.
- Code blob: `audio_voice_cues.py` = `ff88fd1e9a6898c6355592eb1d4349055b54939d`.
- Test blob: `test_audio_ear_voice_cues_v14.py` = `e8a10620a500ca5d9ba2d92092c108730e8f8362`.

## Implemented A5 → A4 → C3 change

The existing time-windowed RAW EAR adapter now emits a bounded `prosody_change_score` from either F0 excursion or within-window energy dynamics, only when periodic voiced activity is present. The score is deterministic and explicitly **not** a speech probability, trained VAD, ASR result, speaker identity, or calibrated confidence.

- `validate_voice_cues` enforces the V2 exact schema, finite [0,1] score and rejects a non-zero prosody score on non-voiced activity.
- A4 `Attention.modulate` receives a novelty contribution of `0.9 × prosody_change_score`; the bounded interrupt input receives `0.25 × prosody_change_score`. Unvoiced noise/impulsive activity uses a separate bounded activity contribution and cannot claim prosody.
- The source-bound C3 admission summary includes `prosody_change=` alongside F0 and energy range.
- Telemetry status is now `CALLER_SUPPLIED_PCM16_A5_A4_C3_ADMISSION`; the adapter does not label every caller buffer synthetic.
- No raw PCM is persisted. The existing consent receipt/source checks, finality rules, learning/action authority false, and no-speaker/no-ASR boundaries remain.

This improves the real A5 adapter's connection to A4 attention and the C3 admission candidate. Core PR #2158 remains the owner of the staged Runtime consumer that carries the packet to B1/B2/C3; this PR does not itself complete that Runtime integration.

## Verification evidence

### LOCAL_LINUX

- Container Python: **3.13.5**; pytest 9.0.2 available.
- `git ls-remote https://github.com/RedMentos/Aii.git` failed with `Could not resolve host: github.com`; exact full-repository local pytest/py_compile is therefore **BLOCKED**.
- Isolated local algorithm reproduction: **5/5 PASS** — flat-tone negative, pitch-sweep positive, amplitude-burst positive, unvoiced-noise negative, and monotonic A4 salience relation. This is not the exact repository test suite.

### GitHub CI

- Exact PR workflow: [run 44870157024](https://github.com/RedMentos/Aii/actions/runs/44870157024), on code/test commit `3cba5118e8b9641220ec411f859d20147218c6f9).
- Python 3.11: compile PASS; **11/11 tests PASS** in 1.79 s.
- Python 3.13: compile PASS; **11/11 tests PASS** in 3.93 s.
- The generic safe-additive workflow [run 44870156991](https://github.com/RedMentos/Aii/actions/runs/44870156991) failed its non-additive-path policy because this PR intentionally changes an existing adapter and its tests. No policy was weakened or bypassed; independent Boss review is required.
- Staged Runtime/integrated workflow [run 44870157033](https://github.com/RedMentos/Aii/actions/runs/44870157033): staged-runtime PASS; integrated-regression was still IN_PROGRESS at last readback. This is not a completed end-to-end pass.

### Core integration blocker

Core PR #2158's exact run [44866310899](https://github.com/RedMentos/Aii/actions/runs/44866310899) failed its consumer suite:
- arithmetic `7-12` returned no exact result;
- broker-failure regression returned ERROR instead of FINAL;
- staged source map mismatched `runtime.py`, `cognition.py`, and `audio_voice_cues.py` pins.
The exact findings and the new adapter blob were posted on #2158. Perception did not edit Core-owned runtime/stager/deployer files.

## Research findings

### R-007 full-text review

arXiv:2608.16347v2 (2026-11-09) was read in full. The study's middle-layer causal injection showed a modest positive effect only for Qwen2-0.5B → Phi-3-mini (23.3% vs 0% unrelated-state control, FDR p=0.0469); both pairs targeting Mistral were null. Successful output retrieval did not imply a correct answer or shared meaning. It supports pair-specific causal tests, not universal latent transfer.

### llama.cpp b10964 source audit

- V13 pins llama.cpp tag b10964 / source revision `b29c606e2`; upstream license is MIT.
- The pinned C API exposes final output embeddings and `llama_set_adapter_cvec`, but the pinned server has no per-request control-vector HTTP route. Its `llama_batch` input is token IDs or embedding rows, not mixed token/embedding rows.
- Current V13 tap is final output/RMSNorm, not the middle-layer tap used by the positive paper experiment.
- A genuine receiver path therefore needs a custom C-API runner or carefully serialized server extension and pair-specific causal generation tests. B3 remains OFF; no latent-injection success is claimed.

## Device, deployment and user effect

- **REDMI_UNVERIFIED:** no connected authorized phone, Android microphone receipt, native model run, ARM CPU/RSS/latency measurement, or private owner-read receipt was available.
- **NOT_RELEASED:** no update request or deployment occurred; updater/device state was not reverified in this run.
- No model/weight download or swap, permission change, installed data mutation, SQLite/chat-history change, or device action occurred.
- No user decision is required now. Keep speaker identity, ASR, full-duplex, native microphone, and real Android consent/revocation acceptance open.

## Next executable actions

1. Boss/QA independently review #2161's non-additive adapter change; do not merge solely because the focused CI is green.
2. Core updates its staged A5 source pin to the reviewed V2 blob and fixes its stale runtime/cognition pins and arithmetic regressions; rerun exact staged B1/B2/C3 integration.
3. Only after Core integration, obtain explicit Android microphone consent and measure actual Redmi/ARM CPU, PSS/RSS, latency, finality and revocation.
4. For V14-003, Core prototypes a per-request native receiver around the pinned C API; compare real injection against unrelated-vector, exact-message and no-message baselines before any B3 activation.


## Follow-up checkpoint — RAW EAR V3 pause-robust prosody (2026-11-21)

- The V2 salience formula had a reproduced false positive: a steady 500 ms tone with 250 ms leading and trailing silence scored 1.0 because the full-window RMS range was 102.31 dB.
- V3 keeps that full-window energy range as a separate observation, adds the 10th–90th percentile voiced-frame energy range, and derives prosody salience only from voiced-frame energy dynamics and F0 excursion. It is schema-versioned `RAW_EAR_AUTOCORR_V3`.
- The exact CI run 44871559784 passed the producer/real A4/C3 consumer tests on Python 3.11 (11/11) and 3.13 (11/11), with compile PASS. Local isolated algorithm reproduction across 8, 12, 16, 44.1 and 48 kHz passed; no exact local repository suite was possible because the checkout could not be obtained.
- Branch head `5e1e9c0ccdce48fd319c24903a6a92ab8a0f6432`; adapter blob `4324813f00eb86db2538ded63dfd1f711188d2cf`; test blob `d457b66cfd792e625f5588f900d876269e551aa9`.
- Core PR #2158 must update its adapter source pin from the old V2 blob to the V3 blob and rerun its staged B1/B2/C3 Runtime consumer. Core was notified in PR discussion. No Core files were edited.
- Research follow-up: PACE (ICLR 2026) argues audio PEFT needs session-wise representation-stability/retention tests; S4VAD (arXiv 2609.11110) is a possible separate low-latency VAD architecture but has no verified Android code/weights; Silero VAD is MIT/~2 MB ONNX candidate for a parallel speech-probability cue; VoiceCLAP-Small is CC-BY-4.0/~110M F32 with 30 s padding and is not a Redmi default.
- **REDMI_UNVERIFIED / NOT_RELEASED.** No microphone capture, native model, ARM PSS/RSS, phone TTFT, weight change, or deployment was performed.
- Next: Core updates the source pin and passes its exact staged/integrated consumer; QA only then arranges a separate explicit microphone-consent test on the actual Redmi. Perception proceeds to the V14-005 model-candidate lab without changing installed models.


## Follow-up checkpoint — single-frame edge correction and current-base retarget (2026-11-21 06:58 CET)

- Review defect: a 40 ms caller-supplied window can produce exactly one voiced frame; likewise a 100 ms window can contain one voiced frame among four. The 25% VOICED threshold was met, but V3 returned a null voiced-energy range and then failed its own validator.
- Fix: one voiced observation has range 0.0 (no within-window dynamics can be inferred). The validator verifies voiced_fraction/frame-count consistency, requires null energy range when no voiced frames exist, and rejects non-null F0 range, nonzero energy range or nonzero prosody score when only one voiced frame exists.
- Tests: new test covers both one-frame cases plus malformed energy and score negative controls. Module blob 0e328d14883840190937f0fef24a8e895ba7261c; test blob 96b00b2e1b6340e2a61a8b6f230be8747889ab38.
- LOCAL_LINUX: Python 3.13.5 isolated reproduction 2/2 PASS; both fixtures also pass the positive validator path and reject both negative mutations. Exact Aii checkout/pytest remains BLOCKED because git ls-remote cannot resolve github.com. No exact repository local suite PASS is claimed.
- Retarget: the PR branch is advanced by a no-force merge commit whose first parent is its prior head and second parent is current release base 034a941694b9e8994d1bfe5cd781d27b943e1ed0. Exact new-head CI is pending; previous pre-fix V3 CI does not verify this change.
- Core handoff: update the staged adapter pin to the new module blob above. Core #2158 still has independent QueryPacket audio_context, arithmetic-source and recovery-manifest failures. Perception changed no Core-owned runtime/stager/deployer files.
- Research: PACE full-text review confirms audio continual adaptation needs task/session-aware stability and selective subspace protection; it is not an Android RAW EAR implementation. libfvad is BSD-3-Clause plus a separate WebRTC patent grant and remains a no-weight VAD comparator only.
- Device: REDMI_UNVERIFIED / NOT_RELEASED. No microphone, phone, model, weight, permission, data or updater operation occurred. User action: none.


## Exact-head CI and B1/B2 native tap inventory — 2026-11-21 07:11 CET

- Current RAW EAR PR head e523f539febb659b6aa56710e9072738b75698cc: dedicated producer/consumer suite 12/12 on Python 3.11.18 and 3.13.18; staged Runtime and integrated regression PASS; privacy scan PASS. Safe-additive scope guard FAIL is expected because the existing producer/test are modified. No policy bypass; draft remains unmerged.
- Native tap inventory: b10964 / b29c606e2, --embedding --pooling none, per-token final RMSNorm output. TAP_SPECS: B1 LFM2 2048, B2 Qwen3.5 1024, C3 LFM2 1024. Exact model revisions/hashes and cross-tokenizer geometry are in R-023.
- Core defect: RunnerPool.get_tap binds qwen35.result_norm.final.v1 for B2/GIST, but LlamaRunner.tap hardcodes lfm2.result_norm.final.v1 in returned metrics. This breaks provenance/bridge keys for B2. Core owns the runner file; finding handed off on #2158. Fix is to propagate the bound tap ID and fail closed if missing.
- No native model taps, B3 receiver effect, Android hardware, microphone or installed-device measurements were run. REDMI_UNVERIFIED / NOT_RELEASED.

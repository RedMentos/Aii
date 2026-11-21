# Research & Perception handoff — 2026-11-21

## Queue ownership

- Queue item: **V14-006 — Research-to-code and active perception learning**.
- Cross-lane finding: V14-003 native latent receiver feasibility; Core owns the actual receiver runtime.
- Base release ancestor: `c0cedbde718ede6107f4df1f1bf9c784df4e00cf`.
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

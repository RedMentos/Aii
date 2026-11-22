# Research & Perception handoff — 2026-11-22

## Integration checkpoint

- Base: `boss/v14-recall-store-pin-rebind-20261122` at `d06c63794adc0ef802af9c7d91dc683d8a1057bf`
- Working branch: `research-perception/v14-raw-ear-rebase-d06c637-20261122`
- New commits: 15 ahead of base at PR creation (#2299); no merge, release or deployment claimed
- Scope: Perception-owned RAW EAR input API, speaker-change evidence and A4 voice-cue integration, rebased without overwriting the Boss-owned fair-budget Cognition overlay

## Code now on the rebased branch

- `v13/code/v13/audio_input.py`: caller-supplied mono PCM16 audio-window ingress, bounded sample rate/duration, source and consent provenance, provisional/final event path. This is an API adapter, not Android microphone capture.
- `v13/code/v13/audio_speaker_evidence.py`: source-bound speaker similarity evidence with caller-asserted, unverified thresholds with batch isolation, age checks and no speaker identity persistence.
- `v13/code/v13/audio_voice_cues.py`: preserves RAW EAR acoustic/prosody cues and sends `DEFER` for speaker decisions until a model-bound calibration artifact and pinned receipt are available; no transcript-only substitution.
- `v13/code/scripts/integrated_audio_context_candidate_20261121.py`: source pins for the exact voice-cue and speaker-evidence blobs; retained the current Boss `cognition = result.get(...)` overlay so audio composition does not erase the fair B1/B2 budget result.
- Recovery, stage and deployer hashes were rebound and read back as a complete chain.

## Exact pin verification

| Link | Verified value |
|---|---|
| Audio overlay Git blob | `bec483911d2b28d386240e6b7798edf85b3ee2ff` |
| Recovery AUDIO_BUILDER_BLOB_SHA1 | matches overlay blob |
| Recovery SHA-256 / stage BUILDER_SHA | `7d5c7c770049ca0c1f75f7c2802033d0773aa0a795085b18dc50b82094ef566b` |
| Stage SHA-256 / deployer STAGER_SHA256 | `26ff96fdf1ec93a7db9bba7ff5060d68bebef64fea3f939aa099ed6e343e1ab3` |
| Voice-cue / speaker-evidence source pins | match exact Git blob SHAs |

## Test and deployment state

- Base candidate `d06c637`: 14 successful, 2 skipped, 1 cancelled workflow run in its current PR-triggered matrix. This is base CI only.
- New rebased branch: exact-head CI pending/awaiting GitHub Actions dispatch after PR #2299 creation; do not inherit the old branch's 64-test pass as proof for this SHA. Do not inherit the old branch's 64-test pass as proof for this SHA.
- Local full-repository test suite: BLOCKED; no Aii checkout is mounted in the execution environment. No repository-local Python/native test was run.
- Native llama.cpp model execution: NOT RUN.
- Redmi/Termux: `REDMI_UNVERIFIED`; no live receipt or connected device proof in this run.
- Deployment/release: `NOT_RELEASED`; the Boss base remains a candidate, and a GitHub push is not a device deployment.

## User-visible function and Canon mapping

The rebased candidate adds a bounded audio-window ingress and diagnostic speaker-similarity evidence into the existing staged audio-context route. No speaker-change or continuity decision is emitted until a separately verified calibration artifact exists. It does not yet capture the Redmi microphone, decode speech, speak, barge in, learn speaker identity, or prove B1/B2/C3 semantic use. Canon paths: A0-A5 audio perception; STEP9/G10C/G10D VOICE_AUDIO remain OPEN; B1/B2/C3 delivery and B3 learned latent coupling remain unaccepted.

## Resource result and research next step

The new R-065 ledger entry reviews Draft-KV, FlyGCL, LatCom, StateBridge, NinaXander, Portable Semantics, cross-model negative results and the llama.cpp/gguf-py boundary. The highest-value latent experiment is a matched-versus-deranged receiver-utility test, starting with same-checkpoint B1/B2 StateBridge-style input-prefix alignment, then pair-specific adapters only if a native extraction path and receiver-side utility gate are available. Draft-KV requires a future native KV-side-memory hook; LatCom belongs after sender interfaces work. No model weights were downloaded or changed.

## Coordination request to Boss/Integrator

1. Review this branch against the exact Boss base and merge only after the new exact-head audio and staged/integrated workflows pass.
2. Update `v14/V14_WORK_BOARD.json`, `v14/V14_USER_NEXT_ACTION.md` and the shared coverage index after independent review; these shared coordination files were not edited here to avoid crossing Boss ownership.
3. After integration, obtain a fresh private device receipt before making any Redmi/Termux or microphone claim.


## Calibration gate correction — 2026-11-22

A code audit found that the registry explicitly labeled its threshold `CALLER_ASSERTED_UNVERIFIED` but still emitted boolean candidate/continuity fields, and A4 accepted those fields using only the caller's calibration label. That could produce false continuity/change claims and an A4 attention interrupt without a validated calibration dataset.

On the current branch, unverified thresholds now yield only raw cosine similarity/delta. Candidate and confidence booleans are `null`, peak decision is `null`, and A4/C3 state is `DEFER`. The C3 summary says `speaker_similarity_delta`, `spk_cal=UNVERIFIED`, and `spk_dec=DEFER`; no speaker-derived attention gain is applied. A future positive decision requires a model-bound verified calibration status and pinned receipt; no such artifact is available today.

LOCAL_LINUX isolated scratch logic: PASS for caller-asserted thresholds, no-threshold input, and a claimed calibrated status without a receipt all remaining DEFER while preserving raw similarity. Full Aii tests and exact-head CI are pending; no Redmi/microphone/model/weight proof.


## Latest code readback — 2026-11-22 04:00

- Branch: `research-perception/v14-raw-ear-rebase-d06c637-20261122`; latest branch commit at readback: `9fe259c94e755ce58304a6610437766d9e416f6d`.
- `audio_speaker_evidence.py` blob: `37aa9c392bbb68d60ccff9749c75b41b8783c539`; `audio_voice_cues.py` blob: `596d14487b9f2b28609eea79fb8b1b39f8da009c`; `test_audio_speaker_evidence.py` blob: `63221711d369651f9be157be2ee4da6cce7b502b`.
- Method label is now `COSINE_LOOKBACK_DIAGNOSTIC_V1`; no FastDiar model/code/weights are imported. Test fixtures use neutral fake model identifiers.
- LOCAL_LINUX scratch mirror: `py_compile` PASS and 4/4 unittest cases PASS (caller-asserted threshold, no threshold, missing receipt, and no speaker-derived attention interrupt).
- Full repository pytest: BLOCKED (no checkout mounted; GitHub DNS unavailable). Exact-head GitHub Actions readback returned no runs/statuses for the latest code commit; therefore CI is NOT_RUN/PENDING, not PASS.
- Boss base #2288 latest observed head `679f3667c5c98b867f85ae960824489da0d8fd3a`: runtime-deploy integrity, combined JEPA, Lab-Age, controller guard and A5 UI lease PASS; migration, owner-read/Python 3.14 startup, audio/arithmetic, staged/integrated regression and privacy were still in progress. No all-green base or release claim.


## Native latent-interface review — R-068 (2026-11-22)

Reviewed the exact pinned llama.cpp API used by Core #2300: commit `b29c606e28a01b1bc8c1351026a0fa6e616bf6c4` (2026-09-14, MIT). The header calls `llama_batch.embd` input token embeddings; `llama_get_embeddings_ith` returns output token embeddings, and its implementation indexes by `n_embd_out`. The decode input path uses `n_embd_inp` outside MTP/DFlash. Those dimensions can differ. Therefore #2300's sender-output → receiver-input probe is useful native ingress diagnostics, but a matching dimension does not establish a shared latent space or semantic alignment. The wrapper currently reports vector width/receiver input width without a distinct sender-output representation field.

Review note sent to Core: record sender-output and receiver-input dimensions/representation types separately, keep `alignment_status=UNTRAINED_UNKNOWN`, and do not promote B3 from nonzero input-effect RMS. The next real experiment needs held-out receiver-task utility against source-exact, zero, shuffled, random same-norm and OOD controls; only a trained pair-specific projector can test learned alignment.


### Additional regression added after scratch verification

The repository test `test_batch_similarity_diagnostic_does_not_trigger_a4_interrupt_or_c3_candidate` now compares the same audio with caller-supplied speaker embeddings against a no-embedding negative control and requires identical A4 external-interrupt gain. This exact repository integration test has **not** been run locally (full checkout unavailable) and has no exact-head CI result yet; only the isolated 4/4 scratch mirror passed. Do not report this new regression as PASS until CI or a full checkout executes it.


## PACT-Check paper review — R-069 (2026-11-22)

Read the full arXiv preprint `2611.06976v1` (2026-11-04) and official `zhenyi4/platour` repo (latest inspected commit `e6cdcb3e8a2ce3c7b6c646df745273ad9f2d31e8`, 2026-11-10). PLatour uses zero-initialized layer-wise projectors into the receiver residual stream and trains only those bridges while backpropagating through the frozen receiver. It is not directly the same as llama.cpp output-embedding-to-input-embedding injection.

The paper's PACT-Check controls are directly relevant to V14: Dummy Transfer, Irrelevant Transfer, Self-Communication and Trained Receiver. The results are task-dependent: PLatour's Qwen3-1.7B PACT-Score is +3.34 pp Chemistry, +0.23 GSM8K, -4.05 MATH500; neither Qwen3.5 PLatour system beats the receiver-trained control on math/coding domain averages. This is a strong reason not to call nonzero native input effect or a benchmark gain proof of useful sender information.

Official code is Apache-2.0, but its published stack is Linux x86_64/Python 3.11/CUDA with Torch 2.10.0, Transformers 5.17.0, vLLM 0.17.1, `fla-core`, `tilelang` and CUDA/CXX11-ABI dependencies. No direct Android/Termux reuse; model/data licenses are separate. Recommendation to Core: add PACT-Check-style controls to #2300 acceptance before any B3 semantic promotion.

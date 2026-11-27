# Research & Perception Run 54 — 2026-11-27

## Checkpoint

- Start: 2026-11-27 02:10:35 Europe/Berlin.
- Completion timestamp: UNKNOWN (not measured).
- Repository: `RedMentos/Aii`.
- Branch: `research-perception/v14-raw-ear-currentparent-20261126-run52`.
- PR: [#2540](https://github.com/RedMentos/Aii/pull/2540), draft / NOT_RELEASED.
- Exact code/test checkpoint: `58af4c96e09543bed3428c77e89c10c513838c25`.
- PR base: `research-perception/v14-kv-snapshot-consumer-20261126-run35` at `a47907c4a0603e602581c6462ecb845211eb0445`.
- Current release branch `gpt6/v13-private-remote-bridge-20261111`: `8d93236c753f0194224c19edc7411d8d7082b1d6` (2026-11-23). The PR is stacked work, not a release.

## Actual implementation

1. `consume_pcm16_voice_window` now validates the complete RAW EAR cue schema unconditionally before constructing/persisting the canonical A5 PerceptPacket. Previously validation only ran when the optional stateful VAD stream was enabled; malformed extractor output could therefore enter a packet and only be rejected later by the context consumer.
2. The source-bound audio context consumer now validates that A4's cue view exactly equals the validated acoustic cue object in the A5 packet. A valid-but-different A4 cue view is rejected before B1/B2/C3 context is created.
3. The positive A4→audio-context regression now exercises the real RAW EAR extractor rather than the abbreviated predictor-only `VOICED` fixture. Shared test fixtures now include the full cue contract.
4. Negative controls cover (a) malformed producer cues rejected before packet/A4 persistence and (b) a valid but mismatched A4 cue view rejected before B1/B2/C3 context creation.
5. The candidate builder's 15-entry `SOURCE_BLOBS` manifest was re-read against the live branch: 15/15 exact GitHub blob matches. Workflow source pins were updated to the new `audio_voice_cues.py` blob.

### Real consumer path and boundary

Caller-supplied PCM16 → timed A5 PerceptPacket → A4 RAW EAR/prosody/speaker cues and temporal prediction → source-bound optional audio context for B1_DETAIL, B2_GIST and C3. The context path does not persist raw PCM. Provisional cues are not promoted as final outcome evidence. This is a candidate/synthetic Runtime integration, not a normal installed phone turn or model inference.

## Exact test evidence

GitHub Actions on the exact code/test head `58af4c96e09543bed3428c77e89c10c513838c25`:

- RAW EAR fastpath: **155 passed** on Python 3.13 and **155 passed** on Python 3.14; the workflow also ran `py_compile` for the audio modules/tests and the generated-signal benchmark. The benchmark explicitly reported `device_benchmark=false`, `synthetic_benchmark=true`.
- A4/A5 feature-set probe: **15 tests passed** on Python 3.13 and **15 passed** on Python 3.14.
- WebRTC/libfvad comparator: Python 3.13 **PASS** (9 comparator tests and 166 source-bound audio tests); Python 3.14 was still IN_PROGRESS at the last poll.
- RuntimeDeploy offline integrity: Python 3.11 and Python 3.14 **PASS**.
- Public-content privacy scan: **PASS** on both RAW EAR fastpath jobs.
- Staged runtime: **FAIL** — 20 failed, 233 passed, 10 skipped, 2 errors, 41 subtests. The principal failure is the Core-owned recovery builder pin for `scripts/integrated_audio_context_candidate_20261121.py` (the base branch expects `831080bceec90711bd42e0fa4eba47c669975c98`; current Perception composer blob is `3b71ea51272a3bc1bc82cb12ebae3bd5e96f51e1`). Other inherited Core/QA failures include stale `v13/contracts.py` arithmetic and `v13/cognition.py` observer-fairness pins, plus two migration assertions returning `PARTIAL` instead of `UPDATED`.
- Integrated regression: **FAIL** — one failure at the same Core-owned audio-composer pin.
- These are GitHub Actions Linux results, not local-device or Redmi tests.

## Local / device / release status

- Full local Aii checkout and full local pytest: **BLOCKED / NOT RUN**. The container has no repository checkout; `git ls-remote https://github.com/RedMentos/Aii.git HEAD` failed because GitHub DNS could not resolve.
- Local native audio execution, Android/Termux tests and Redmi instrumentation: **NOT RUN / REDMI_UNVERIFIED**.
- No AudioRecord/microphone provider was exercised. No ASR, trainable decoder/vocoder, full duplex, real speech corpus or native model invocation was proven.
- No persistent B1/B2/C3 model-weight update, cross-organ gradient, trained latent coupling or production self-edit was performed.
- No model/weight download or swap, permission change, microphone enablement, UPDATE_REQUEST, CHAT_SEND, LOG_PAGE, shell command or device mutation was performed.
- GitHub push is not deployment. **NOT_RELEASED**.

## Cross-lane coordination

Core PR [#2544](https://github.com/RedMentos/Aii/pull/2544) was notified with the exact current composer blob `3b71ea51272a3bc1bc82cb12ebae3bd5e96f51e1`, the 15/15 source-manifest readback, and the A4↔A5 consistency gate. Core owns the recovery/stage/deployer pins and must rebase its stack onto #2540, refresh the composer pin and derived hashes bottom-up, and preserve fail-closed validation. QA owns the migration `PARTIAL` vs `UPDATED` assertions. Perception did not edit Core-owned files.

## Device receipt check

The last available consented private V13OBS #115 snapshot is historical (2026-11-24): installed SHA `8d93236c753f0194224c19edc7411d8d7082b1d6`, auto-update/dashboard/runtime reported enabled/up-to-date, but AI was `STOPPED_BY_USER`, model process `STOPPED`, autostart false; B1/B2 remained TIME_BUDGET with zero valid offers. New read-only owner requests #998 (HEALTH) and #999 (PIPELINE_STATUS) expired with no device comments: **NO_LIVE_RECEIPT**. Current updater/device state therefore remains unverified; no remote action was sent.

## Research note — MixMoMo

The full arXiv preprint [MixMoMo: Mixed-Precision Mixture-of-Experts Inference on Mobile GPUs and NPUs](https://arxiv.org/abs/2611.33981) (v1, 2026-11-25) was reviewed. It proposes per-expert quantization-impact profiles and activation-risk-based mixed precision; it reports 3.72× over uniform Q4_0 and 1.53× over its strongest baseline on 35B–80B models on OnePlus 13/15 Snapdragon 8 Elite Gen4/Gen5 devices with 24/16 GB RAM. The paper describes an approximately 8,000-line llama.cpp extension but no public implementation or extension license was found. Its hardware/model regime does not transfer to the Redmi Note 10 Pro 6-GB-class target. Record as a future sparse-MoE experiment hypothesis only; do not download, adopt or swap a model.

## Next executable action

1. Core/QA rebase the Core stack onto the current Perception parent #2540, refresh the recovery/stage/deployer source-pin chain, and repair the migration status assertions without weakening the guards.
2. Finish the Python 3.14 WebRTC/libfvad comparator and rerun exact-head staged/integrated CI after Core's rebase.
3. Keep AudioRecord/microphone OFF until the independently reviewed Android provider and consent/revocation path exist. Then validate a real permitted capture on the Redmi; do not infer it from Linux CI.
4. After the shared integration gate is unblocked, continue source-disjoint A4 attention/salience outcome tests and broader whole-Canon work.

**User action: none required.** No model change, device update or permission change is requested.

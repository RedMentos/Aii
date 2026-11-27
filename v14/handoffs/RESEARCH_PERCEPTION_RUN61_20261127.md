# Research & Perception — Run 61 (2026-11-27)

## Defect and hypothesis

The session-scoped A4 temporal predictor deliberately shares only numeric weights across sessions while keeping each session's temporal feature history ephemeral. A code audit found that `AudioTemporalPredictionRegistry._reset_state()` violated that separation: when one session hit `RESET_CHRONOLOGY` or `RESET_GAP`, it created a zero-initialized predictor and wrote it to the shared source/generation/consent checkpoint. A local temporal reset could therefore erase weights learned by another Store session.

## Implementation

- PR [#2553](https://github.com/RedMentos/Aii/pull/2553), DRAFT, child of [#2551](https://github.com/RedMentos/Aii/pull/2551).
- Branch: `research-perception/v14-a4-preserve-shared-weights-on-temporal-reset-20261127-run61`.
- Parent Perception head: `f268ff1326c78d9a5da99dcf5572788d53b0862b`.
- Predictor code commit: `7a24a5c309c687bd303dcafdc7a481a2deb9f198`; predictor blob: `2519e5cbbbfacc7bb252a4cd2c84148e4f641176`.
- Regression-test commit: `74afbe8078190f7b084d95cc61a7a151f6034139`; test blob: `abd5d2b53e6423ddebe73f52816e3431bea29b5d`.
- Exact composer-pin commit / branch head at PR creation: `5e37965f3eb3bc7051a1ee1bdf1473d54ef0b16b`; composer blob: `f1fd06c70f9d27148c22df869abe0ad66a4cf467`.

A valid shared checkpoint is now loaded into the reset session's new predictor. The session-local temporal baseline resets, but the persistent weights/update count and checkpoint version are left untouched. Missing, invalid or consent-rotated checkpoints still follow the existing initialization path. The integrated audio-context candidate's predictor blob pin was refreshed.

## Tests and evidence

- LOCAL_LINUX, CPython 3.13.5, SQLite 3.46.1: isolated reset-semantics reproduction **3/3 PASS**. It first reproduced the old zero-write defect, then verified preserved weights/version and a fresh temporal baseline, and verified consent rotation still resets. This is an isolated scratch harness, not the full repository suite.
- Full local Aii checkout/pytest: **BLOCKED / NOT_RUN**; no checkout is mounted and `git ls-remote https://github.com/RedMentos/Aii.git` fails because `github.com` DNS cannot resolve.
- Exact-head GitHub Actions for PR #2553: **PENDING** at this checkpoint.
- Parent #2551 exact head `f268ff1`: focused A4 temporal/source-isolation, A4 update-gate/retention, A4/A5 feature-set, RAW EAR NumPy and WebRTC/libfvad workflows all **PASS**. Its shared staged/integrated workflow **FAILS** on Core-owned Recovery/composer, arithmetic and observer source pins plus QA migration `PARTIAL` vs `UPDATED` assertions.
- No Android/Termux, microphone, native GGUF or Redmi test. **REDMI_UNVERIFIED / NOT_RELEASED**.

## Product and Canon impact

This protects the existing A4/RAW EAR temporal predictor's numeric checkpoint from being erased by another session's chronology or gap reset. It does not improve or prove predictor accuracy, enable a new learning policy, or establish a normal-turn microphone path. It does not fix P0 basic chat, B1/B2 valid-offer delivery, native B3 latent coupling or Android capture.

Relevant prior research remains R-175 (mistake-gated online updates; task-specific results and no Android evidence) and R-180 (co-observation is distinct from retention/plasticity). This run adds no new paper, OSS dependency, model or weight.

## Integration handoff

- Perception owns `audio_temporal_prediction.py`, its regression tests and the exact composer source pin.
- Core should rebase its Recovery → Stage → RuntimeDeploy chain onto #2553 and refresh only its own composer pin after this child is reviewed.
- QA retains the two-checkout migration assertions and must not have its ownership overwritten.
- No installed updater or device deployment was attempted; a GitHub PR is not a deployment.
- Next Perception step: once the shared source pins are current, add a two-Store/two-registry concurrency test for simultaneous writers and bounded conflict retry, then return to the still-unwired A5 visual-frame and signed audio Runtime consumers.

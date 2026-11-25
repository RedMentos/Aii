# Research & Perception — RAW EAR speaker-window chronology

Date: 2026-11-25
Branch: `research-perception/v14-audio-speaker-window-order-20261125-run27`
Base: PR #2472, `402b7aa5f09f04f6d11e7e14bd0b8d6e14adbfae` (current-release rebase at `8d93236c753f0194224c19edc7411d8d7082b1d6`).

## Defect and consumer

The A5 → A4 → C3 RAW EAR consumer calls `SpeakerChangeEvidenceRegistry.update()` from `audio_voice_cues.consume_pcm16_voice_window()`. The registry previously validated only the ordering of supplied embedding-frame end timestamps. It did not retain or validate the complete input window's `start_ms/end_ms`.

That allowed a later window to start before the preceding accepted window while its sparse supplied embedding-frame end timestamps still advanced. The separate `TemporalVoiceEvidence` smoother already rejected backwards window starts; the speaker-evidence branch did not apply the same interval invariant.

## Change

- Track last accepted window start/end separately from the speaker-reference frame clock.
- Reject backwards starts and non-advancing ends before any history/state publication.
- Preserve interval chronology when a model/calibration revision or a long voiced-history gap resets embedding history.
- Equal starts remain valid for cumulative/sliding windows when the end advances.
- No speaker identity is assigned; similarity remains diagnostic and caller thresholds remain uncalibrated. No PCM/vector persistence, model load, learning authority, or action authority is added.

## Tests added

1. Backwards start with advancing embedding-frame timestamps is rejected; previous state remains intact; equal-start cumulative continuation succeeds.
2. Window end regression is rejected even if supplied frame timestamps themselves advance.
3. Model-revision history reset does not reset the stream's interval clock.

## Verification boundary

- LOCAL_LINUX isolated interval-state reproduction: **3/3 PASS**. This is a minimal reproduction of the state transitions, not the repository module.
- LOCAL_LINUX full checkout/exact test: **BLOCKED / NOT_RUN**; no repository checkout is mounted and GitHub DNS cannot resolve.
- Exact repository CI: [RAW EAR fastpath run 45547732118](https://github.com/RedMentos/Aii/actions/runs/45547732118) **PASS 2/2** on Python 3.13 and 3.14. Each job ran **143 tests PASS**, py_compile, the deterministic synthetic benchmark (not a device benchmark), and privacy scan CLEAN.
- Exact staged/integrated CI: [run 45547732138](https://github.com/RedMentos/Aii/actions/runs/45547732138) **FAIL**. Staged-runtime: 18 failed / 235 passed / 10 skipped / 2 errors / 44 subtests. Integrated-regression also fails at the same strict source pin. The recovery builder expects controller-guard SHA-256 `86ad7838d15eb9a038fec629c340936edde78d65d921507e10cec29fed74b9d9`, but the current #2472 chain contains different bytes. Two-checkout migration returns PARTIAL rather than UPDATED because staging cannot compose. This is Core-owned; #2482/#2483 are the current pin-repair stack. No hash gate was weakened.
- Redmi/Termux: **REDMI_UNVERIFIED**. No fresh phone receipt, microphone capture, device action, update request, model/weight/permission change.
- Release: **NOT_RELEASED**. This branch is a child of #2472 and requires its full review/integration chain.

## Integration

Core/QA should retain the source-bound consent lease across the full A5/A4/B1/B2/C4/C3 turn as already required by #1904. This change only hardens the optional source-bound speaker-similarity history used inside the existing audio consumer. It does not resolve the basic-chat/B1/B2 P0, native microphone capture, calibrated diarization, or trained latent coupling.


## Research note — CI-JEPA counterfactual intervention selectivity

**Primary source reviewed:** Mintu Dutta, Ritesh Vyas and Mohendra Roy, *CI-JEPA: A Counterfactual Analysis of Latent Representations in Joint-Embedding Predictive Architectures for Self-Supervised Learning*, arXiv:2610.05043v1, submitted 2026-10-04. The full short paper's method, setup, tables, limitations and conclusion were read. The paper states acceptance at IS³A³ 2026; the proceedings/publication record was not independently verified. No official implementation or declared paper/code license was found in the checked source, so no reuse.

**Mechanism:** retain I-JEPA masked-target prediction and add an intervention-conditioned branch. It predicts `ΔZ = Z_CF − Z` from a learned intervention embedding and binary intervention mask, with SmoothL1 counterfactual loss added to the JEPA objective. This models the effect of an edit rather than forcing every edit to be invariant.

**Reported experiment:** Flowers102 (8,189 images; official train/validation/test split). Flower-center occlusion is treated as a candidate semantic intervention; background blur and tint as candidate nuisance interventions. Mean L2 representation changes are 4.42, 3.48 and 2.83 respectively; best validation linear-probe accuracy is 78.14% vs 77.55% for I-JEPA and pretrained ViT-B/16.

**Limits:** intervention effects are not reported for the baseline encoders, so improved selective sensitivity over the baselines is not established. The 0.59-point validation gain has no repeated-run uncertainty and is not a test-set result. Edit strength, edited area and artifacts may explain some ordering. The paper explicitly does not prove complete nuisance invariance or causal feature discovery.

**V14 testable adaptation:** extend the existing A3 source-disjoint counterfactual probe (#2470), not a parallel pipeline: pair controlled semantic-like and nuisance-like edits on the same source frames, match changed area/magnitude, compare the current A3 projector and simple feature baseline, report per-source SIR distributions and zero/shuffle/reversal controls. Keep it diagnostic-only; do not alter A4 gain or train weights until source-disjoint held-out utility, gradients/parameter diffs, retention, restart and rollback are demonstrated. This is a research proposal, not a result from this run.

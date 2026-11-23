# World-JEPA fixed-readout heldout-action ablation — prereg 2026-10-28

Owner: GPT-6; isolated new research files only on `assistant/v13-world-jepa-heldout-action-readout-20261028`, parent PR #826 head `0cc5e59fc1c91a71b0b232b42f70668c562d9d2b`. Do not modify original `world_jepa_incremental_probe.py`, `world_jepa_fair_baseline.py`, frozen `world_jepa.py`, model/seed registrations, Runtime or Canon.

## Hypothesis / control flaw
Prior wrong-action augmented controls use wrong action features for **both** training and heldout readout. A trainable ridge can relearn the wrong-action encoding; that comparison alone does not isolate whether the trained JEPA predictor uses the *correct heldout action*. New separate diagnostic fits the World-JEPA and outcome readout on original TRAIN actions only, then evaluates the **same frozen readout** on original heldout actions versus a heldout-only action-row shift and heldout-only action-column rotation. Holdout shift must preserve heldout action marginals, be split-isolated and change at least one row. No heldout outcome may enter model or ridge fitting.

## Fixed preregistration
- Input: existing `world_jepa_digital_shadow.make_dataset` closed digital outcome packets, including existing deterministic train/heldout split and source/split hashes.
- Seeds `(3,7)`, ensemble `3`, training steps `400` for the actual synthetic research diagnostic; `0` only for fast test.
- Direct baseline: existing fair train-only scaling and ridge lambda. Augmented readout: same train-only standardizer, same fitted ridge weights for all heldout arms.
- Report correct, row-mismatched and column-mismatched heldout MAE, per-seed differences, action-change fraction, negative gates and provenance hashes. **Do not claim a positive effect without measured improvement against direct and both mismatched controls**, and even then this remains synthetic/digital SHADOW, not real-world causal proof.
- Tests must catch retraining on mismatched actions, heldout leakage, bad shapes, no action mismatch, nonfinite scores, invalid step counts; preserve existing original probe untouched.
- Branch CI: pinned NumPy, isolated focused tests and actual synthetic 400-step diagnostic with closed raw logs, compile/privacy/diff checks, no model downloads or tool execution.

Negative gates: STEP2 UTILITY_FAIL, B3 L1 FAIL, Body-JEPA UNAVAILABLE, LP3 heldout FAIL, jepa_weight=0, Age0 RECORD_ONLY. This research has zero runtime authority. No private data or model weights in Git.

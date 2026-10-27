# Independent Z12c persistent World-JEPA SHADOW calibration review (2026-10-27)

Exact base: independent Z12c persistent branch `74bc1010826db437d3e1ef21fac9c8946986f89b` (child of Claude PR637). Ownership: `v13/code/v13/world_jepa_slots.py`, new `tests/test_world_jepa_slots_calibration_guard.py`, isolated CI/proofs. Do not overwrite source owner, change training data/hyperparameters/weights, alter registered cohorts, or merge into main. No native/Redmi/STEP2/B3/Body-JEPA promotion.

## Discovered functional integrity gap
`fit()` sets `op_err=zeros` without calibrating. `confidence()` nevertheless treats this as measured zero typical prediction error and may emit a confident `MODEL_SIMULATION` label. `save()` also accepts that uncalibrated model; a pinned digest/provenance protects bytes but does not establish the existence of calibration. A future runtime SHADOW consumer could mistake missing calibration for perfect calibration.

## Preregistered acceptance
1. A fitted but not calibrated model cannot return calibrated `confidence()` or persist an inference checkpoint; no invented zero-error authority.
2. `calibrate()` requires at least one actual observation of every action class (including UNTOUCHED), finite nonnegative slot errors, and positive finite support; missing-class calibration fails closed.
3. After valid calibration, `confidence()`, `save()`, `load()` and original prediction/confidence/slot-error byte-identical restart proof remain available.
4. Checkpoint metadata records `calibration_complete=true` and a new explicit revision `z12c-slot-world-jepa-inference-npz-v2`; old v1 artifacts fail closed and require intentional re-export from calibrated source (no silent migration).
5. A failed later calibration attempt must clear prior calibration authority. No claim that the caller-supplied calibration data is disjoint or semantically truthful; only structural calibration presence.
6. Original Z12c slot tests and persistent-checkpoint tests remain passing; no changes to registered train/holdout examples or model parameters.

Software/NumPy synthetic proof only. Preserve RED and GREEN originals, source SHA and negative gates. The parent full V13 suite is RED and cannot be promoted by this review.

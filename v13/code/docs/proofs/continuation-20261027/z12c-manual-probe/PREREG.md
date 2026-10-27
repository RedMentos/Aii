# Z12c manual World-JEPA SHADOW probe — preregistration 2026-10-27

Base: independent calibration review PR649 exact head `293ccf7dd8b24a9dd25e0ceffac1792e8e14cc53`, itself a child of the Z12c persistent slot World-JEPA branch/Claude PR637. New review-only child. Ownership: new `v13/code/v13/world_jepa_shadow_probe.py`, one `:world` operator dispatch in `v13/code/v13/operator.py`, new `tests/test_world_jepa_shadow_probe.py`, isolated workflow/proofs. Do not overwrite any concurrent owner, change registered cohorts/models/hyperparameters, activate automatic model use, or promote age/STEP2/B3/Body-JEPA.

## Missing functional capability
Z12c slot predictor can now fit, calibrate, save and load with exact provenance, but has no explicit human-facing read-only path to exercise the saved model after a restart. The user should be able to inspect and manually query a pinned inference-only SHADOW model from the existing persistent text UI without making it an answer authority.

## Acceptance (pre-source)
- `:world` with no args remains unchanged. `:world shadow status|load|predict|unload` is explicit local-operator only, no model-generated command, automatic hook or action execution.
- `load <basename.npz> <exact_sha256> <cohort_sha256> <source_sha256>` reads only regular non-symlink files from `<home>/checkpoints/world_jepa/`; it verifies v2 calibrated checkpoint and exact bytes/provenance **before** persisting a compact binding. No arbitrary path traversal.
- `predict <X-json> <A-json>` re-verifies the whole checkpoint every time, validates bounded finite aligned arrays and one-hot actions, and returns only typed latent prediction, spread, confidence and MODEL_SIMULATION/SIMULATION_UNCERTAIN labels. No user text or query payload persisted.
- A verified binding survives Runtime restart; corruption after binding, wrong provenance, missing file, malformed/nonfinite/oversized arrays, path traversal/symlink all fail closed. `unload` clears binding only, never deletes the file.
- Existing Z12c fit/calibration/checkpoint tests and operator/WorldState behavior remain passing. No native/Redmi/semantic truth or automatic learning claim. All negative gates remain unchanged.

Evidence: synthetic NumPy/Linux software-only; preregistered RED then GREEN with original raw ZIPs, SHA256, private backup. Full V13 suite remains RED; this manual probe is not whole-system integration.

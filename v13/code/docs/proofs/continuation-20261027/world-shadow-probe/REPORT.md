# World-JEPA v2 SHADOW probe — implementation and evidence (2026-10-27)

## Function and use
New `v13/world_jepa_shadow_probe.py` and `scripts/world_jepa_shadow_probe.py` provide a **read-only inference bridge** from an existing calibrated, digest- and provenance-bound v2 slot World-JEPA checkpoint to an explicit JSON observation and hypothetical action. It returns predicted next **target latents** per slot, ensemble spread, calibrated confidence/simulation label and optional per-slot prediction error. This does not execute the action, train the model, write facts, change Age, or grant runtime authority.

Inputs: JSON `before` = `slots × input_dim` finite numeric matrix, `actions` = `slots × op_dim` exactly one-hot rows (last operation is UNTOUCHED), optional `after` with the same shape as `before`. The supplied after-state is explicitly **unverified** (`after_supplied`, `after_verified=false`). Provenance JSON must exactly match the checkpoint's embedded provenance; `--sha256` must be its lowercase whole-file SHA256. Checkpoint revision v1 is deliberately incompatible; use calibrated v2 only.

From `v13/code`, after installing the repository's pinned compatible NumPy:
```sh
python scripts/world_jepa_shadow_probe.py --checkpoint /path/to/calibrated-v2.npz --sha256 <64-hex-sha> --provenance /path/to/expected-provenance.json --input /path/to/observation.json
# Optional: --output /path/to/new-result.json
```
No output path means JSON to stdout. An explicit output path is atomically replaced only **after** successful validation; it cannot alias the checkpoint, input, or provenance source path. Inputs and outputs are bounded; no implicit downloads or file actions. This is an isolated operator, **not integrated into the live V13 turn**.

## Prospective RED/GREEN and raw evidence
Base: PR #650 exact head `9c6cb2435d11bf58d3b18b0d830aeda261809d3e`, itself review-only child of PR #649. Prereg `b8b2b12e79e9b174bedd1cef0be3157217e4bbec`; tests `f3c494af0a180cd1cb753beabdb6a165ce344a09`; workflow `aad5151f3a4e956553ae6d97f4e57e7f32dbff2b` **before implementation**.
- RED Actions [40448003698](https://github.com/RedMentos/Aii/actions/runs/40448003698): 22 tests, 1 ERROR (module absent), compile exit 0, privacy CLEAN. Original ZIP artifact `12709495888`, SHA256 `3f0565c76913f7e744836b868e3a41cae280a2b7c9a4501869eab561cddc1ce4`.
- Initial GREEN Actions [40448047538](https://github.com/RedMentos/Aii/actions/runs/40448047538): 27/27 PASS, compile exit 0, privacy CLEAN, source `c2c42bc30c73ae5078ca5d7c1df3c31e477cfa1b`. Original ZIP `12709013179`, SHA256 `ed91e151ac9c46f92f0e7dec8d53899fc2af923fb3f71b582f862bcbaaa20fb6`.
- Review correction: distinguish caller-supplied after from verified outcome. Prospective amendment `ff7684e8f90ba5d837669a88308fd372b3abe073` identified destructive `--output` alias before test/source; RED test `6fac980b893fb2fc211efb678d1e8db5ceb324fc`. RED Actions [40448248219](https://github.com/RedMentos/Aii/actions/runs/40448248219): 28 tests, 2 FAIL 2 ERROR (checkpoint overwritten in synthetic temp fixture by aliased output), compile exit 0, privacy CLEAN. Original ZIP artifact `12709018650`, SHA256 `382b446986e9dbb9bbafddbdfb8c6f06d2b58c4728223ccfc49da53e745e791d`. This is an actual regression counterexample; preserve it.
- Alias fix `4e35ad559a4f2f55c24a61e98e0189f979530590`. Final GREEN Actions [40448278613](https://github.com/RedMentos/Aii/actions/runs/40448278613): **28/28 PASS**, compile exit 0, privacy CLEAN. Original ZIP artifact `12709635889`, SHA256 `0826f03c918f4fec8f11892e2f9c143cb63ca943e4ca9b2b7bc27d78e6fda98b`.
- An intermediate push `4265ff931160cb10d2e349dd5aeed748191f18a6` failed before matching test update; its workflow remains recorded. Other pending intermediate workflows were cancelled by GitHub's pending-run replacement; neither is a PASS.
- All four named original ZIPs checked for SHA256, CRC, HEAD and exit codes. Each privately uploaded to `/V13-Checkpoints/2026-10-27/Automation11-World-Shadow/`, re-materialized and independently byte-hash-verified. No rejected anyone-writable Drive destination used.

## Status and exact next work
Owner: independent follow-up, no overwrite of Claude's Z12c training sources. This is **software/synthetic NumPy evidence only**; no actual original Z12c seed 201/202/203 remeasurement, no real phone measurements, no native Body-JEPA, no live runtime integration. Parent full V13 suite remains historically RED (5 FAIL, 73 ERROR). STEP2 UTILITY_FAIL, B3 L1 FAIL, Body-JEPA UNAVAILABLE, `jepa_weight=0`, Age-0 gates and whole-system incomplete unchanged.

Next: a separately preregistered **unregistered** seed-211 real Linux file-world smoke (train=600, cf=12, attr=16, steps=50) to verify Z12c controls no longer crash, then an isolated source-bound train→calibrate→checkpoint→probe lifecycle with disjoint data and explicit Linux-vs-Redmi evidence separation. No frozen cohort replacement or automatic authority promotion.

Focused command:
```sh
cd v13/code && PYTHONPATH="$PWD:$PWD/scripts" python -m unittest -v tests.test_world_jepa_shadow_probe tests.test_z12c_control_calibration tests.test_world_jepa_slots_calibration_guard tests.test_world_jepa_slots_checkpoint tests.test_world_jepa_slots tests.test_world_jepa
```

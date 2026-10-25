# Run281 — executive no-B native harness binding (2026-10-25)

## Owner and base
- Base: verified Run280 PR280 checkpoint `08c0c5b0743452c61d0fc1dbcd0687b11f7e661d`; dependent review chain PR270→…→PR281, not old main.
- Owner: `v13/code/tests/integration_executive.py`, new Run281 test/workflow and this proof directory only. Existing production Runtime/AG0/C2/C3/JEF organs and Canon untouched.
- Canon blob `218464b12a2d27d92524c751922fa8e1c3fb0ea7`; global BUILD_STATE blob `fdf0827d7c4af5cdb85b69cbe651ed52784a07b5` unchanged.

## RED
- PR269 actual-weight native Linux run `40186761125`: executive `first_actual_c3=false`, while `second_actual_c3=true`. The executive test script removed B1/B2 installed entries but not AG0 committed slots, so an actual B1 runner could still answer the auto-routed first turn.
- New test commit `645f842cdbbe867ebe776d947371f9d4bd922353`, CI commit `f4f6ef54847dcbb82df3163e813c3506b5f1cdfe`.
- Exact-head Run281 RED CI `40192446574`: **24 tests, 2 FAIL / 22 PASS**. Actual synthetic-path RunnerPool mask control passed; executive harness lacked helper call and slot-absence gate.
- RED raw artifact `12598094026`, ZIP SHA256 `f91b455c9b0b2344b28aaa77ae18de3287bde7b054e5ab0bb87da483e05a4d19`.
- Raw: https://github.com/RedMentos/Aii/actions/runs/40192446574/artifacts/12598094026

## GREEN
- Production commit `ed3f5900dae23cfacc9c3f5c1c3c44f64c4ff29a`: disposable executive native harness calls Run280's tested `_mask_step1_bodies(r)`, and its original `body_not_required` check now additionally requires no committed B1/B2 slots. C3/C2 model paths remain accessible, native acceptance thresholds unchanged.
- Exact-head Linux-software CI `40192517271`: **24/24 PASS**, compileall PASS, official public privacy scan CLEAN. No actual native model execution in Run281.
- GREEN raw artifact `12597819634`, ZIP SHA256 `9aaac9c1628fb7a52e46e8fdd8dee508eea3ca9c4c6e39aa5adc5d56b9caf266`.
- Raw: https://github.com/RedMentos/Aii/actions/runs/40192517271/artifacts/12597819634
- Remote blob readback: `integration_executive.py` `0d71d97868cc3a0785846f1073afcc2784550b2c`, test `f5433b78e67583776cdcc8fb7fcb345a3605b83b`, CI `7259cfe40799067e5a84f716a7326e0c2ec2b937`.

## Registered native evidence and exact next step
- The registered public model manifest `v13/code/specs/models.json` is Git blob `7af05962af41d0bc3f7dd18ef01d4eba55eabf99` in both PR269 and current chain. `v13/code/v13/bootstrap.py` and `scripts/acceptance.py` are likewise byte-identical; no model/source pin changed.
- PR269 full native acceptance remains 20 stages attempted, 12 PASS / 8 FAIL, `IMPLEMENTED_PATHS_PARTIAL` (artifact `12597232047` SHA256 `eac321b4f8119f0ce10cbd65c050c87e56f11b94ec8d56322f450014f13054d0`). This patch does not promote any gate.
- STEP2 `UTILITY_FAIL`, B3 L1 `FAIL`, Body-JEPA `UNAVAILABLE`, `jepa_weight=0`, V13 `INCOMPLETE`. PR277 offline diagnostic CI still FAIL; Redmi NOT MEASURED.
- Next independent package: serial native exact-head **first four registered stages only** (JEF, experience, learning, executive) on a fresh Linux runner with pinned bootstrap and closed raw reports. Use the same native concurrency group as PR269; preserve `DIAGNOSTIC_INCOMPLETE` from `--stage-limit 4`, do not mislabel it full acceptance. Do not run STEP12/full native in parallel. Retain every failure and exact source/model hashes.

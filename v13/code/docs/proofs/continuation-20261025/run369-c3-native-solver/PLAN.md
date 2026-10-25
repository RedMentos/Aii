# Run369 — pinned C3 350M Linux-native solver smoke (preregistered)

Parent: `codex/ag12-embedded-holdout-20261025` @ `115c12bf00d04dd6cb461a317e29d14e66bf1091` (Run368 GREEN, stacked review chain, not main). Separate Run367 full-suite is RED for 63 classified historical errors; do not hide or retune it.

Owner: new `v13/code/scripts/run369_c3_native_solver_smoke.py`, `.github/workflows/run369-c3-pinned-native-solver.yml`, and this proof directory. Existing production `v13/runners.py`, `agi/solver.py`, model catalog and registered cohorts remain read-only.

## Immutable public artifacts (from existing `specs/models.json`)
- C3 `LiquidAI/LFM2.5-350M-GGUF` revision `657e078c94084481950a2d555a941481f715536b`, `LFM2.5-350M-QAD-Q4_0.gguf`, exact size `219312832`, SHA256 `3d10b6ab8fc91a919534b9558e266255aca0bbc7f6d015963599aa9e74e05b1d`; `LFM Open License 1.0` URL pinned in catalog. Do not redistribute model bytes in raw artifacts.
- `llama.cpp` runner tag `b10964`, pinned Linux x86-64 release tar size `16825086`, SHA256 `9abf88aea48a55d0f80edb1ee20220b186848cca0b4e919d71518cfd7ca67443`. Keep original source and runner hashes unchanged.
- Download directly from the catalog's HTTPS URLs into isolated GitHub runner temp; verify byte size, SHA256 and tar extraction confinement before execution. No paid provisioning, no phone access, no model download in local tests.

## Acceptance (Linux-native only)
1. `llama-server --version` starts from the hash-verified pinned release with local libraries.
2. Actual `v13.runners.LlamaRunner` loads pinned C3 on CPU, completes a bounded text generation and reports `FINAL`, finite timings, sampled resource measurements and `CAN_TRAIN_BODY=false`.
3. Actual `v13.agi.solver.BodySolver.ask` uses JSON grammar and native answer-token confidence, returns a nonempty answer and finite confidence in [0,1], with a recorded source; no correctness/AGI assertion.
4. Native process is unloaded/reaped, no background child, no age/approval/learning side effects. Record complete raw success/failure, host/dependencies, exact head, binary/model/source SHA, timings and privacy scan in closed artifact and private Library.
5. If upstream artifacts are unavailable or incompatible, preserve actual failure; do not substitute mocks or alter registered hashes. Continue independent packages.

Negative gates remain: no Redmi measurement, no B1/B2/JEPA training, no STEP2/B3/Body-JEPA/jepa_weight/whole-V13 promotion. This is a Linux-native C3 path probe, not a phone acceptance test.

# Core & Harness — native target-score receiver repair
Date: 2026-11-26

## Branch and lineage
- Branch: `core/v14-native-target-score-repair-20261126-run1`
- Base: `13cfe43a7a94d4b35d4a3be0249bd725b6f06c23` (Core PR #2515 head at discovery)
- Code checkpoint before this handoff: `5476ae6148e455fb30e06cc2b87c7eef93f6737c`
- Parent: Core PR #2515, `core/v14-native-target-score-20261125-run1`
- This is a stacked repair candidate, not a release.

## Defects repaired
1. **Pinned native build blocker:** `decode_embeddings()` called `llama_model_rope_type(model)` without receiving `model`. The function now takes `const llama_model *model`, rejects null context/model, and all six call sites pass the already-loaded receiver model.
2. **Hash chain:** refreshed the native C++ SHA-256 pin, native receiver builder Git-blob pin, recovery-builder SHA-256 pin, stage-builder SHA-256 pin, and RuntimeDeploy stage SHA-256 pin. No source-pin checks were weakened or bypassed.
3. **Staged Runtime test boundary:** `test_native_latent_receiver_runtime.py` is a staged-overlay test. It is already executed by `test_native_latent_receiver_stage.py` in a subprocess with the staged tree on `PYTHONPATH`; the workflow no longer also runs it directly against the unpatched source Runtime, which caused false failures.
4. **Synthetic task-score contract:** a single synthetic task group is correctly reported as `FIXTURE_ONLY` by the current parent evaluator; the test now expects that status while retaining the insufficient-holdout and zero-authority assertions. The later Perception helper refresh may change this ordering on its child branch.

## Exact evidence
- GitHub readback: all seven changed source/test/workflow files were written to this branch; exact blob hashes are recorded in the branch history.
- LOCAL_LINUX: `git ls-remote https://github.com/RedMentos/Aii.git HEAD` — BLOCKED because this environment cannot resolve `github.com`; no full checkout or full repository pytest was available.
- LOCAL_LINUX isolated source inspection: six `decode_embeddings(context.value, ...)` call sites were updated; the signature and null guard are present. This is not a full llama.cpp compile.
- Exact GitHub CI for this repair branch: PENDING until the PR is opened and checks finish.
- Pinned llama.cpp Linux build and Android arm64 cross-compile on the parent head: FAIL at the undeclared `model` reference. The repair is intended to address that exact compiler error; do not call it fixed until exact-head CI passes.
- Redmi / Termux: `REDMI_UNVERIFIED`. No phone receipt, native GGUF execution, installed update, model/weight/permission change, or device action occurred.
- Production B3 remains OFF. Native target-token likelihood is only a diagnostic proxy; it does not prove generated-answer correctness, semantic use, trained latent coupling, or learning.

## Next executable step
Run exact-head PR CI: Python 3.13/3.14 staged Runtime and regression tests, pinned llama.cpp Linux build/selftest, Android arm64 cross-compile, and privacy scan. Fix any new failures, then coordinate the Perception child (#2517/#2519) rebase against this repaired Core head. After the receiver builds, the remaining major gap is to execute the full source/session-bound eight-condition matrix against a pinned real GGUF and collect the required held-out cohort; no B3 promotion follows from compile success alone.

## User action
Keine Aktion nötig. No Termux command, UPDATE_REQUEST, restart, model download/swap, permission change, or device-data mutation is required.

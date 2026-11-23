# QA — native receiver descriptor handoff through staged Runtime

Date: 2026-11-23

## Branch and dependency

- QA branch: `qa/v14-native-receiver-fd-pin-chain-20261123-run1`
- Current code/test head: `7238eb8367828327fda67382391d57f50e2b7de4`
- Core dependency: PR #2400, descriptor-bound receiver code head `0a470ada486b848f3ab5762ba1074e7660803eee`
- QA base: `qa/v14-native-probe-model-hash-20261122` at `f64e9943998bba1ec69dcbe342fd865d1a64f990`
- This is a combined QA candidate, not a release or device deployment. Do not merge #2400 separately without reconciling the duplicate receiver stack.

## Reproduced defects on the earlier exact QA head

1. The stage composer expected Termux21 SHA-256 `76d728975151f884e85a0583721021bd0f4fd0ac10a738cae070c4d565c05ee4`, but the exact Termux21 file bytes on that head hashed to `029894297e4514cab3921e66b6680002aceb41323fb698ab8bc02f7e1d98f3ae`. This caused `ValueError: integrated builder hash mismatch` across staged Runtime, Lab-Age and migration checks.
2. After correcting that link, Lab-Age exposed a second stale leaf pin: the native receiver overlay expected `native_latent_receiver.py` SHA-256 `8b69dd4c99af35faa311bd7c2b9841d138006f6acd83ac8d13a16f56d8b2ee6b`, while the exact descriptor-bound source was `49526253037ad90c5b2001b87c0940ff6c074bd73a8d9556ea06d86e3a750e83`.

These were genuine source-composition defects, not reasons to weaken the staged gate.

## Corrected immutable chain — exact GitHub byte readback

All hashes below were recomputed from the exact current branch file contents and then read back from GitHub:

1. `integrated_native_latent_receiver_candidate_20261122.py` now pins the exact `native_latent_receiver.py` SHA-256: `49526253037ad90c5b2001b87c0940ff6c074bd73a8d9556ea06d86e3a750e83`.
2. Updated native receiver builder Git blob SHA-1: `0541038db8ec541b70c2e410083a0019deda72c0`.
3. `termux_runtime_recovery_candidate_20261121.py::NATIVE_RECEIVER_BLOB_SHA1`: `0541038db8ec541b70c2e410083a0019deda72c0`.
4. Exact Termux21 source SHA-256: `ae34b45f59bb5daba1cd0fc593e437dbc0478e53a2ea437d362bda4fdeed7530`.
5. `stage_integrated_candidate.py::BUILDER_SHA`: `ae34b45f59bb5daba1cd0fc593e437dbc0478e53a2ea437d362bda4fdeed7530`.
6. Exact stage-integrated source SHA-256: `9329647dbd17f6800b0335e65df6bab807b996cf4748942782ea8c538d72c4e0`.
7. `runtime_deploy.py::STAGER_SHA256`: `9329647dbd17f6800b0335e65df6bab807b996cf4748942782ea8c538d72c4e0`.

All six `BASE_PINS` and all four `NATIVE_FILES` in the native receiver composer were independently compared with the exact source bytes; they match at this readback. The chain predicate (native source → receiver builder blob → Termux21 → integrated stage → runtime deployer) is TRUE.

## Regression added

`v13/code/tests/test_native_latent_receiver_stage.py` now includes `test_native_receiver_source_pins_and_complete_stage_chain_are_current`. It asserts every base/native source pin, the Git blob identity of the native receiver builder, the Termux21 source SHA-256, the stage builder SHA-256 and the runtime deployer STAGER_SHA256. This should fail at the first stale link rather than only surfacing downstream during a full stage test.

## Verification boundary

- Exact GitHub source readback and independent hash-chain calculation: PASS.
- LOCAL_LINUX full Aii checkout / Python test execution: BLOCKED; no repository checkout is mounted and GitHub DNS/archive access is unavailable in this worker. No local repository test is claimed.
- Exact-head CI for code/test head `7238eb8367828327fda67382391d57f50e2b7de4`: no run was returned by the Actions API at last readback. Earlier failures on `fc54a52` are historical and are not reclassified as current-head results.
- Android ARM64 cross-compile: prior Core #2400 evidence only; no new build claim on this QA head.
- Native llama.cpp model execution: NOT RUN.
- Termux/Redmi: REDMI_UNVERIFIED. No device receipt, update request, model probe, model/weight change, permission change or user-data mutation.
- Production B3 remains OFF. Descriptor integrity and staged composition do not establish trained cross-model latent alignment, semantic utility, B1/B2 native consumption or production B3.

## Required gates and next action

1. Obtain exact-head CI for the current code/test head, including Python 3.13/3.14 native receiver tests, native staged Runtime, staged/integrated regression, runtime-deploy integrity, owner-read Python 3.14, Lab-Age and two-checkout migration.
2. Fix any new failure from its exact log and recompute the entire immutable chain bottom-up after every source edit.
3. Hand to Boss/Core only after the exact combined checks pass. Keep this candidate DRAFT / NOT_RELEASED until then.

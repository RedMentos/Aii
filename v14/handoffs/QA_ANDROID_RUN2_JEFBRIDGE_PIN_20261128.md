# QA & Android Run 2 — JEFBridge receipt source pin

Date: 2026-11-28  
Parent: Core PR #2576 (`core/v14-open-url-ci-repair-20261128-run3`)  
Parent exact head: `18e1c20d309b633f3a0e3a637000456480844130`  
QA branch: `qa/v14-controller-guard-jefbridge-pin-20261128-run1`

## Defect reproduced

Core's Android companion outcome bridge adds `JEFBridge.publish_android_action_outcome` for verified companion receipts. The code deliberately publishes only a source-bound `CONTROL_ONLY` symbolic message; it sets no device-observation, T8/world-learning, production-route, training or native-receiver authority.

The existing `record_only_controller_guard_20261116.py` rejected that exact new `v13/jefbridge.py` source. On Core head `18e1c20d309b633f3a0e3a637000456480844130`, workflow #46097873974 failed at `test_normal_runtime_composer_preserves_audio_and_ui_source_bindings` on both Python 3.13 and 3.14 with:
`controller guard source changed: v13/jefbridge.py actual=441ede97018c4490fceb15553230f949006424f6717b4fa4cf597f963575d812`.

## QA repair

- Added only SHA-256 `441ede97018c4490fceb15553230f949006424f6717b4fa4cf597f963575d812` to the existing `PINS["v13/jefbridge.py"]` set.
- Added a test that reads the exact JEFBridge source and checks the digest is allowlisted.
- Added a negative one-byte-tamper test. The altered digest must remain rejected.
- No RECORD_ONLY rule, learning policy, source transformation, Android permission, or model authority was weakened or enabled.

## Exact immutable chain

| Layer | Verified value |
|---|---|
| Guard source SHA-256 | `ece6a91d2b60dd86df73f41ef0e5310c815768c1acfe39354f2bc4ba1736a4d7` |
| Recovery-12 Git blob SHA-1 | `b59aa068c51150352ac656ee63585ffaf134061c1` |
| Recovery-21 SHA-256 | `122495c8059d9da4c66744715d252d9dc7fe3ff7a285fdbaadf3aa2da40421b8` |
| Stage builder SHA-256 | `8050684f165301fa8f133d6457ad77074acd2e213efc7087d590789f22517195` |
| RuntimeDeploy STAGER_SHA256 | same exact Stage builder SHA-256 |

The source chain was updated sequentially, not by bypassing any hash check.

## Independent failure left open

The same Core head also fails the two malformed-projector NPY header cases in workflows #46097874007 and #46097874016 on Python 3.13/3.14: 28 passed / 2 failed. The branch's old `vision_ui_frame_ingress.py` lacks the current Perception preflight, so a monkeypatched `np.load` is reached and the loader reports `PROJECTOR_LOAD_FAILED` instead of `PROJECTOR_TENSOR_HEADER_INVALID`.

The exact preflight already exists in Perception #2563 (workflow #46039137962, 31/31 on Python 3.13 and 3.14) and #2565 / Core #2570 (workflow #46057142216, 39/39 on each interpreter). Core should port/rebase the matching provider and test pair and regenerate the affected source pins. Do not delete or relax the allocation-bomb test.

## Environment and product boundary

- LOCAL_LINUX full checkout / pytest: NOT_RUN; checkout not mounted and GitHub DNS unavailable.
- GitHub CI: prior parent failures reproduced; QA branch exact CI still pending PR creation.
- Android ARM64: no new native build or device execution in this run.
- Redmi: REDMI_UNVERIFIED / NO_LIVE_RECEIPT. No fresh owner-verified HEALTH, PIPELINE_STATUS or DIAGNOSTICS response.
- No model or weight changes, downloads, device permissions, shell actions, update request or user-data writes.

## Next action

Open the stacked QA PR against Core #2576. Verify the exact new head's controller guard, RuntimeDeploy, staged/integrated regression, two-checkout migration and Python 3.14 startup. Then coordinate the separate NPY source-pair port with Core/Perception. Keep both PRs draft and NOT_RELEASED until exact staged integration is green.

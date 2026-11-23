# QA — native receiver descriptor handoff through staged Runtime

Date: 2026-11-23 04:xx Europe/Berlin

## Branch and dependency

- QA branch: `qa/v14-native-receiver-fd-pin-chain-20261123-run1`
- Source dependency: Core PR #2400, exact source head `0a470ada486b848f3ab5762ba1074e7660803eee`
- QA base: `qa/v14-native-probe-model-hash-20261122` at `f64e9943998bba1ec69dcbe342fd865d1a64f990`
- This branch is a combined QA candidate: it carries #2400's descriptor-bound native receiver implementation plus the missing QA-owned staged composer rebinding. It is not a release or device deployment.

## Reproduced integration defect

The focused descriptor-binding workflow and Android ARM64 cross-compile passed on #2400, but the exact staged Runtime refused to compose the changed receiver candidate:

- `termux_runtime_recovery_candidate_20261121.py` expected Git blob SHA-1 `452a0dfdd6bb8781d5640b09568a38606f873593`.
- The exact #2400 receiver builder file is Git blob `f9af2a09c237f5f57482fcacea4f5639f12de394`.
- The stale pin caused `ValueError: pinned audio composition input changed` before the descriptor-bound receiver could reach the staged Runtime.

## Rebound immutable chain

Read back after the QA commits:

1. `NATIVE_RECEIVER_BLOB_SHA1` in `termux_runtime_recovery_candidate_20261121.py` → `f9af2a09c237f5f57482fcacea4f5639f12de394`.
2. Exact Termux21 source SHA-256 → `76d728975151f884e85a0583721021bd0f4fd0ac10a738cae070c4d565c05ee4`.
3. `stage_integrated_candidate.py::BUILDER_SHA` → `76d728975151f884e85a0583721021bd0f4fd0ac10a738cae070c4d565c05ee4`.
4. Exact stage-integrated source SHA-256 → `04e0d16ad64439249167dc9643498a0f8c051c14de8228ccda8993bb91137aa1`.
5. `runtime_deploy.py::STAGER_SHA256` → `04e0d16ad64439249167dc9643498a0f8c051c14de8228ccda8993bb91137aa1`.

No release gate was disabled. No model, weights, user data, permission, launcher, or device state was changed.

## Verification boundary

- GitHub readback: PASS for all three edited source files and the complete pin chain.
- LOCAL_LINUX full Aii compile/tests: BLOCKED. No repository checkout is mounted; `git ls-remote https://github.com/RedMentos/Aii.git HEAD` fails DNS resolution in this worker. No local repository test is claimed.
- Exact GitHub CI: PENDING until this combined candidate PR is opened and the exact new head is read back.
- Native llama.cpp/model execution: NOT RUN in this worker.
- Termux/Redmi: `REDMI_UNVERIFIED`; no device receipt or private owner-read result was obtained.
- Production B3 remains OFF; this change only binds the exact diagnostic native receiver file to the child loader.

## Required exact-head gates

- Native receiver descriptor-binding workflow, Python 3.13 and 3.14.
- V13 staged context/integrated regression (must pass the nested composer, not only direct unit tests).
- V13 runtime deployment integrity and two-checkout migration workflows.
- Android ARM64 cross-compile remains separate from Redmi execution.

## Next action

Read exact-head workflow results, repair any remaining nested pins without relaxing the gate, then hand the green combined branch to Boss/Core for review and integration. Do not merge the old #2400 branch separately from this QA-composed candidate without reconciling the duplicate stack.

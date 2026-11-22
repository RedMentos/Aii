# Core handoff — staged native receiver and one-shot approval composition

Date: 2026-11-22  
Role: Core & Harness  
Branch: `core/v14-native-probe-operator-dispatch-20261122`  
PR: [#2381](https://github.com/RedMentos/Aii/pull/2381)  
Code checkpoint before this handoff: `1053c5e986d4709386a0d75cd2b2391f065042ee`  
Base: QA branch `qa/v14-native-probe-model-hash-20261122`, base SHA `42723cfd4c0629940b75c158283bdf5256568142`

## Product slice

This Core follow-up makes the native receiver diagnostic candidate executable as a *staged* Runtime without modifying the source Callosum bytes that QA's record-only guard and receiver overlay pin.

1. The staged test builds the existing recovery/stage candidate.
2. It applies `integrated_native_latent_receiver_candidate_20261122.py` to the staged Cognition/Callosum bytes, adding the diagnostic `Cognition.native_receive` consumer and Callosum probe report.
3. It refreshes the staged manifest's file hashes and records the receiver overlay as `SHADOW_REVIEW_ONLY`, with production routing and training/native-receiver authority at zero.
4. It then applies the existing `integrated_native_probe_approval_candidate_20261122.py` one-shot local approval overlay.
5. The staged subprocess runs the receiver, runtime, Callosum, approval and observer-budget regressions against that composed tree.

The Core source `v13/code/v13/callosum.py` was restored byte-for-byte from the QA base branch (Git blob `0dbe893a983a2739bb9e008e8a0c3fab5715aec3`). The duplicate direct-source operator test and separate Core workflow were removed; the existing staged receiver workflow is the single integration path. `v14/V14_USER_NEXT_ACTION.md` was restored from the QA base so this Core PR does not overwrite Boss-owned handoff content.

## Exact changes

- `.github/workflows/v14-native-latent-receiver.yml`: add the Core head to push filters and QA base to PR filters; direct test command runs native receiver unit tests and the staged integration test, not overlay-only approval tests against the unpatched source tree.
- `v13/code/tests/test_native_latent_receiver_stage.py`: compose receiver overlay before approval overlay; refresh stage manifest hashes after each stage; fix the manifest newline.
- Delete redundant `.github/workflows/v14-core-native-probe-operator.yml` and `test_native_latent_receiver_operator.py`.
- Preserve the QA-owned approval/guard files and source Callosum pins unchanged.

## Evidence and limitations

| Environment | Check | Result |
|---|---|---|
| LOCAL_LINUX | `git ls-remote https://github.com/RedMentos/Aii.git HEAD` | BLOCKED — `Could not resolve host: github.com`; no full Aii checkout is available |
| LOCAL_LINUX | Full Runtime/Operator/staged tests | NOT_RUN / BLOCKED by missing checkout |
| GitHub CI | New exact-head staged receiver workflow | NOT_TRIGGERED at this checkpoint; the base QA workflow does not yet include this PR's target branch in its trigger filters |
| GitHub readback | Core source Callosum blob | PASS — restored to the exact QA-base blob above |
| TERMUX/REDMI | Installed candidate, native probe, model process and actual B3 effect | REDMI_UNVERIFIED; no device action performed |

A coordination comment was posted on QA PR #2377 (comment 7086322481) asking QA to add `qa/v14-native-probe-model-hash-20261122` to `pull_request.branches` and `core/v14-native-probe-operator-dispatch-20261122` to `push.branches` in the QA-owned workflow. The branch-local filter change alone cannot cause GitHub to use a workflow version that is not present in the PR base.

## Safety and release boundary

- B3 remains OFF; this is not a trained latent channel or production routing.
- The probe remains diagnostic-only, one-shot, user-confirmed and SHADOW/staged.
- No model download/swap, weight edit, Android permission change, update request, remote shell, native probe or device mutation occurred.
- No Redmi-native result is claimed. No APK or installed Termux runtime was changed.

## Next executable action

1. QA adds the missing workflow trigger filters on its own branch.
2. Re-run exact Python 3.13/3.14 staged/integrated tests, pinned Linux native build and Android ARM64 cross-compile on the current #2381 head; fix any real failures.
3. Independent QA review checks path identity, source/model-byte binding, one-shot consumption, no redispatch, and all negative gates.
4. Boss integrates only after the full exact-head chain passes; the PR is not a release or deployment.

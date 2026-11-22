# Core handoff — staged native receiver and one-shot approval composition

Date: 2026-11-22  
Role: Core & Harness  
Branch: `core/v14-native-probe-operator-dispatch-20261122`  
PR: [#2381](https://github.com/RedMentos/Aii/pull/2381)  
Current code checkpoint: `b8287caa2d9025b195d1aa0ee7a43106b5a7a5d3`  
Base: QA branch `qa/v14-native-probe-model-hash-20261122`, base SHA `42723cfd4c0629940b75c158283bdf5256568142`

## Product slice

This Core follow-up composes the diagnostic native receiver and the one-shot local approval into the same isolated staged Runtime. It does not modify the source Callosum bytes protected by QA's record-only guard and receiver pins.

1. `stage_integrated_candidate.stage()` loads the pinned recovery wrapper.
2. That wrapper applies `integrated_native_latent_receiver_candidate_20261122.py` exactly once to the composed Cognition/Callosum/Operator sources and adds the diagnostic `Cognition.native_receive` consumer.
3. The stage test now verifies the resulting staged files, `replaced_files`, and the exact manifest SHA-256 values. It does **not** reapply the native receiver overlay; the overlay intentionally rejects double application.
4. The test then applies `integrated_native_probe_approval_candidate_20261122.py`, which adds the source/model-bound local `arm-probe`, one-shot `native-probe`, and `revoke-probe` commands.
5. The staged subprocess runs native receiver, runtime, Callosum, approval, and observer-budget regressions against that composed tree.

QA comment 7086445214 identified that the previous test applied the receiver overlay a second time after the recovery wrapper had already composed it. Commit `b8287caa` removes that duplicate application and asserts the single-pass stage output and hashes instead.

The Core source `v13/code/v13/callosum.py` remains byte-for-byte equal to the QA-base blob `0dbe893a983a2739bb9e008e8a0c3fab5715aec3`. The duplicate direct-source operator test and redundant Core workflow remain removed. The Boss-owned `v14/V14_USER_NEXT_ACTION.md` is not changed by this PR.

## Exact changes

- `.github/workflows/v14-native-latent-receiver.yml`: retain the exact staged receiver workflow and branch filters.
- `v13/code/tests/test_native_latent_receiver_stage.py`: assert the receiver is already present after the pinned stage builder; compare all seven receiver output files to the manifest hashes; then apply the approval overlay.
- Preserve QA-owned approval/guard files and source Callosum pins unchanged.
- Keep the approval consumer staged and diagnostic-only; no production B3 route or training authority is introduced.

## Evidence and limitations

| Environment | Check | Result |
|---|---|---|
| LOCAL_LINUX | `git ls-remote https://github.com/RedMentos/Aii.git HEAD` | BLOCKED — `Could not resolve host: github.com`; no full Aii checkout is available |
| LOCAL_LINUX | Full Runtime/Operator/staged pytest | NOT_RUN / BLOCKED by missing checkout |
| GitHub Actions | Exact-head native receiver staged workflow | QUEUED — run [45075518483](https://github.com/RedMentos/Aii/actions/runs/45075518483) |
| GitHub Actions | Exact-head private-bridge security workflow | QUEUED — run [45075518496](https://github.com/RedMentos/Aii/actions/runs/45075518496) |
| GitHub readback | Updated test blob | PASS — `69e876807dd40e6376102fbbb4576a5b0c47590d`; duplicate apply block absent |
| GitHub readback | Core source Callosum blob | PASS — exact QA-base blob retained |
| TERMUX/REDMI | Installed candidate, native probe, model process and actual B3 effect | REDMI_UNVERIFIED; no device action performed |

The QA base now includes the PR trigger filter, so the exact-head workflow has been queued. Do not treat queued CI as a pass.

QA's residual review also notes a path-to-loader TOCTOU window: the approval layer verifies the model file by descriptor, but the native loader still accepts a path. Keep the probe user-initiated and diagnostic-only; do not claim this is an OS sandbox or immutable model-file handoff. No local probe has been run.

## Safety and release boundary

- B3 remains OFF; this is not trained cross-model latent alignment, semantic utility, production routing, or learning.
- The probe remains staged, one-shot, source/model-bound, locally approved, and non-authoritative.
- No model download/swap, weight edit, Android permission change, update request, remote shell, native probe, or device mutation occurred.
- No Redmi-native result is claimed. No APK or installed Termux runtime was changed.
- The existing updater is not invoked by this PR; GitHub push is not deployment.

## Next executable action

1. Poll exact-head run 45075518483 and run 45075518496; fix only observed failures.
2. Obtain independent QA review of staged source/model binding, one-shot consumption, cancellation/timeout, no redispatch, and negative gates.
3. Boss integrates only after the complete exact-head chain passes and the dependency PR #2377 is accepted.
4. Any real native probe remains a separate explicit local TTY action after integration; no user chat approval or CI result silently authorizes it.

# Core handoff — staged native receiver and one-shot approval composition

Date: 2026-11-22  
Role: Core & Harness  
Branch: `core/v14-native-probe-operator-dispatch-20261122`  
PR: [#2381](https://github.com/RedMentos/Aii/pull/2381) — DRAFT / NOT_RELEASED  
Latest branch SHA: `c13157abdcd4745b2a9d238235eb0e264a09b1fe`  
Code checkpoint: `b8287caa2d9025b195d1aa0ee7a43106b5a7a5d3`  
QA base: `qa/v14-native-probe-model-hash-20261122`, current QA head `45f08a3c0da564f12cdddef89f99fde245657d61`

## Product slice

The Core follow-up composes the diagnostic native receiver and one-shot local approval into one isolated staged Runtime. It does not modify QA's source Callosum bytes or enable production B3.

1. `stage_integrated_candidate.stage()` loads the pinned recovery wrapper.
2. The wrapper applies `integrated_native_latent_receiver_candidate_20261122.py` exactly once to the composed Cognition/Callosum/Operator sources and adds the diagnostic `Cognition.native_receive` consumer.
3. The Core stage test verifies the resulting staged Cognition/Callosum/Operator/native files, `replaced_files`, and exact manifest SHA-256 values. It no longer applies the receiver overlay twice.
4. The test then applies `integrated_native_probe_approval_candidate_20261122.py` and runs the receiver/runtime/Callosum/approval/observer-budget regressions inside the staged subprocess.
5. The native receiver measures sender tap token/activation input and receiver-side input-consumption effect. This remains a diagnostic embedding-consumption check, not semantic alignment or trained B3.

QA comment 7086445214 identified duplicate receiver-overlay application in the earlier test; Core commit `b8287caa` removes it and asserts the composed stage output instead.

## Current exact-head CI failure — dependency defect

Core's exact-head staged workflow run [45075750380](https://github.com/RedMentos/Aii/actions/runs/45075750380) is **FAIL** on both Python 3.13 job `137372456751` and Python 3.14 job `137372456834`:

`test_native_latent_receiver_stage.py:53` asserts that the staged `v13/native_probe_approval.py` contains `os.O_NONBLOCK`. The current QA source module at `45f08a3` does contain the nonblocking FIFO defense, but QA's staged overlay candidate `v13/code/scripts/integrated_native_probe_approval_candidate_20261122.py` blob `787ac5f8b80c183de0920848d2fb6d6c2c7e3ff6` does not include `os.O_NONBLOCK` or `_verify_model_file`. The overlay replaces the safe source with its older copy.

Core posted this exact failure and requested that QA update the overlay/pins in PR #2377. The stage assertion is intentionally retained; weakening it would hide the safety regression. The same QA review also requires the canonical path and `(dev,inode,size,mtime_ns,ctime_ns)` identity to be persisted in the approval record at arm and compared at consume, including a negative where both manifest path and ModelManager route are redirected together to a byte-identical copy after arm. Core does not own the QA approval source/overlay files and will not overwrite them.

The private-bridge workflow passed on the prior exact Core head; the staged native receiver workflow is not accepted until the QA overlay is corrected and both Python versions pass.

## Exact changes

- `.github/workflows/v14-native-latent-receiver.yml`: trigger filters for the current QA base/Core branch.
- `v13/code/tests/test_native_latent_receiver_stage.py`: single-pass composed-stage assertions and exact manifest hash checks.
- No direct source edit to `v13/code/v13/callosum.py`; the QA record-only guard remains byte-identical.
- No modification to QA-owned `native_probe_approval.py`, approval overlay, or model-file verifier.
- `v14/handoffs/CORE_NATIVE_PROBE_OPERATOR_DISPATCH_20261122.md`: current dependency and evidence record.

## Evidence and limits

| Environment | Check | Result |
|---|---|---|
| LOCAL_LINUX | `git ls-remote https://github.com/RedMentos/Aii.git HEAD` | BLOCKED — DNS `Could not resolve host: github.com`; no full Aii checkout |
| LOCAL_LINUX | Full staged Runtime pytest | NOT_RUN / BLOCKED by missing checkout |
| GitHub Actions | Exact-head staged native receiver workflow | FAIL — [45075750380](https://github.com/RedMentos/Aii/actions/runs/45075750380), stale QA overlay omits O_NONBLOCK |
| GitHub Actions | Exact-head private-bridge security workflow | PASS on [45075518496](https://github.com/RedMentos/Aii/actions/runs/45075518496) |
| GitHub readback | Updated stage test | PASS — exact blob readback; duplicate receiver overlay application absent |
| GitHub readback | Core source Callosum | PASS — exact QA-base blob `0dbe893a983a2739bb9e008e8a0c3fab5715aec3` retained |
| TERMUX/REDMI | Installed candidate, native probe, model process and actual B3 effect | REDMI_UNVERIFIED; no device action performed |

## Safety and release boundary

- B3 remains OFF. This is not trained cross-model latent alignment, semantic utility, production routing or learning.
- The probe remains staged, one-shot, source/model-bound, locally approved, and non-authoritative.
- QA's documented path-to-loader TOCTOU remains a separate limitation; this is not an OS sandbox or immutable model-file handoff.
- No model download/swap, weight edit, Android permission change, update request, remote shell, native probe or device mutation occurred.
- No Redmi-native result is claimed. No APK or installed Termux runtime was changed.
- GitHub push is not deployment.

## Next executable action

1. QA updates the staged approval overlay to preserve `O_NONBLOCK` and persists exact canonical path/file identity in the approval record, with the byte-identical dual-route negative.
2. Poll the new QA and exact Core CI; do not remove the stage assertion.
3. Re-run exact staged/native receiver workflows and independently review the composed staged tree.
4. Boss integrates only after the dependency is accepted and the complete exact-head chain is green.
5. Any real native probe remains a separate explicit local TTY action after integration; no chat approval or CI result silently authorizes it.

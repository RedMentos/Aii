# Core Run 51 — Native receiver cancellation and CI checkpoint

Date: 2026-11-28
Owner: Core & Harness
Branch: `core/v14-native-receiver-kv-consumer-20261127-run1`
Checkpoint SHA: `baed8fd5ba3c043a1b0477222fb617860eb9830b`
Previous native-build SHA: `44a12c5edeb34fcbd73fdc9361ca683b9994fc09`
PR: #2572

## What changed

- The one-shot native receiver matrix Runtime now persists distinct `CANCELLED_AFTER_CONSUMPTION` and `TIMED_OUT_AFTER_CONSUMPTION` outcomes when the native bridge is interrupted or exceeds its bounded deadline. Other exceptions retain `FAILED_AFTER_CONSUMPTION` / `FAILED_REVOKED`.
- Cleanup closes the staged matrix and clears the Runtime's matrix, target-token, pair-record and staging-time references.
- The tests assert that the exact Runtime cancel event and a deadline no greater than 120 seconds reach the bridge. They also assert that the one-shot approval remains consumed and the staged state is cleaned up after cancellation/timeout.
- The recovery-builder pin chain was rebound to the exact current controller-guard file bytes. No controller guard logic or allowlist was changed by Core.
- The native receiver workflow's trigger/path coverage was extended for this Core Runtime branch.

## Exact verification

| Check | Result | Environment |
|---|---|---|
| `test_native_receiver_matrix_runtime.py` | **22 passed** | GitHub CI, Python 3.13 |
| `test_native_receiver_matrix_runtime.py` | **22 passed** | GitHub CI, Python 3.14 |
| Native receiver pinned Linux build | **PASS** | GitHub CI, SHA `44a12c5...` |
| Android ARM64 cross-compile | **PASS** | GitHub CI, SHA `44a12c5...` |
| Native artifact | Produced, review-only | `v14-native-latent-receiver-android-arm64` |
| Full staged Runtime / integrated regression | **FAIL / BLOCKED** | GitHub CI, Python 3.13/3.14 |
| Full local Aii checkout | **BLOCKED / NOT RUN** | Container cannot resolve `github.com` |
| Redmi installation or native execution | **REDMI_UNVERIFIED** | No fresh owner-verified device receipt |

The C++ native receiver sources did not change between the native-build SHA and the current Python-only cancellation checkpoint. The artifact was not installed, executed on Redmi, or promoted into production.

## Remaining blocker

The staged Runtime fails closed because `record_only_controller_guard_20261116.py` rejects the current `v13/callosum.py` source hash:

`f07fba55eac93af5f855a20c7ac136d15a2fa44315d0878d41b8090ddd905748`

The exact guard file in this branch hashes to `8c7a48af789cba4e734facdb63cf8aa84bcd8cf9d2ad3fd91e0ae212b7f5410f`; the recovery builder now pins those bytes. The remaining rejection is the guard's Callosum allowlist. Core did not modify this QA-owned boundary.

A different open Core branch (#2552) contains a guard version whose allowlist includes the rejected hash, but it also carries a different Callosum/Perception stack. Do not blindly cherry-pick that guard or rebase this PR without QA/Boss review. QA should either approve the exact hash or identify the compatible Callosum revision; Boss/Integrator should select the canonical base.

## Product truth

- The local probe is a bounded, source-bound diagnostic matrix, not production B3 routing.
- Native K/V effect evidence does not prove semantic use, learned cross-organ latent coupling, or JEPA training.
- Production B3 remains OFF; learning authority and model weights are unchanged.
- GitHub push is not deployment. No release SHA or verified updater installation exists from this run.
- No fresh private Redmi receipt was returned; report REDMI_UNVERIFIED.

## Next exact actions

1. QA reviews the Callosum hash and guard contract without weakening RECORD_ONLY or external capability boundaries.
2. Boss/Integrator reconciles the base branch and controller-guard version; preserve both original branches and do not force-push.
3. Re-run the exact staged Runtime, migration, and negative-control suites on the resulting head.
4. Only after an integrated release is installed and a fresh device receipt confirms the exact build should the user be asked separately whether to authorize one local native probe.
5. Continue independent Core P0 work on the normal B1/B2 → C4/JEF → C3 path and fastpath; no device proof should be inferred from CI.

## Research note

Keep the native receiver matrix diagnostic-only until it beats zero-vector, shuffled-token, rotated-vector, wrong-sender, wrong-receiver and text-only controls on a held-out task set. The next meaningful metric is a source-bound held-out receiver utility/log-probability delta, not merely a nonzero K/V snapshot.

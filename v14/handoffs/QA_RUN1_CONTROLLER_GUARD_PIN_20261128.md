# QA & Android — Run 1: controller-guard pin and staged integration
Date: 2026-11-28

## Scope and exact ancestry
- Core consumer PR: #2572
- Core branch/base used for this QA checkpoint: `core/v14-native-receiver-kv-consumer-20261127-run1`
- Exact Core base SHA: `50b6fc28fb3b5f7c6e2cd6d4c9340e81a93c6975`
- QA code/test head: `7109faadd3d65fa9026f9da6f1caee6c38b21a72`
- QA PR: #2580, stacked on #2572, DRAFT / NOT_RELEASED.

## Reproduced blocker and repair
The exact #2572 staged/integrated CI failed because the RECORD_ONLY controller guard rejected the Callosum source used by the new native receiver matrix consumer:
`v13/callosum.py SHA-256 f07fba55eac93af5f855a20c7ac136d15a2fa44315d0878d41b8090ddd905748`.

Reviewed the Callosum diff: it adds a diagnostic matrix-staging method and operator dispatch. Staging does not execute the matrix. Native execution remains behind local-TTY approval, exact source/event/generation/model binding, an exclusive Runtime probe lease, cancellation/deadline checks, managed-model unload and resource preflight. The matrix keeps production route false, semantic-use proof false, training authority zero and native-receiver authority zero.

QA changes:
- Added only that exact Callosum digest to the guard's existing explicit allowlist.
- Added exact-source and one-byte-tamper rejection tests.
- Rebound the complete immutable chain, without removing any hash check:
  - Guard SHA-256: `c8a67385527f781bd2b8f96020d31901c26aae73adf765f31c2bfa267272b007`
  - Recovery-12 Git blob SHA-1: `258bd73cf8288595a5c04b6f20eb5df238ab1ed9`
  - Recovery-21 SHA-256: `38bef4887930ad4438db665ab44e817e65b83d26ce0feb0312d68dc41de8bc1f`
  - Stage-builder SHA-256: `ade52e951fad0ec8da75feb14491bbc59e3f83fd3e317469f1d93103ba81026f`
  - RuntimeDeploy `STAGER_SHA256` pin: `ade52e951fad0ec8da75feb14491bbc59e3f83fd3e317469f1d93103ba81026f`
  - RuntimeDeploy source SHA-256: `fceedeaeca84dc72774f232fb87dd46527b800085c9e54ca329805921380d856`
- Added the QA branch to the existing native receiver matrix workflow's push filter so that its exact stage gate runs on this branch.

## Exact CI evidence
- Controller RECORD_ONLY guard workflow #46122041218: PASS.
- RuntimeDeploy offline workflow #46122041175: PASS on Python 3.11 and 3.14.
- Private bridge workflow #46121874840: PASS.
- Native receiver matrix focused tests: 22/22 PASS on Python 3.13 and 3.14.
- Native receiver ARM64 cross-compile: PASS (hosted Linux cross-compile only).
- Native receiver stage test: FAIL after the guard fix, now at the next independent source mismatch:
  `ValueError: audio source blob changed: v13/cognition.py`.
- Shared staged/integrated workflow #46122041291: FAIL at the same audio source pin; 16 failed, 239 passed, 10 skipped, 2 errors, 47 subtests in the integrated-regression job.
- Two-checkout migration #46122041209: FAIL with `PARTIAL` rather than `UPDATED` because the runtime stage is blocked. The assertion is not weakened; it is still the required release behavior.
- Lab Age and owner-read staged-runtime checks also stop at the same audio source mismatch. Their read-only owner-read portion passed.
- Privacy scan in the native receiver workflow: CLEAN.
- Full local Aii checkout/pytest: NOT_RUN; this execution container cannot resolve `github.com`.
- Redmi/Termux: REDMI_UNVERIFIED; no fresh private device receipt or hardware access.

## Cross-lane convergence blocker
The current #2572 ancestry carries the older audio composer blob `831080bceec90711bd42e0fa4eba47c669975c98`. Its `SOURCE_BLOBS` expects Cognition Git blob `06de0acf2c6d30d50301d5073f5569822edff813`, while the exact branch contains `deb8c274022e2a4419dd38adb11ca14481c4bd91`. All other eleven source pins in that old composer matched; the current mismatch is specifically Cognition.

The newer Perception chain #2578 → #2579 carries composer `f90f57599609eeab7bbe30805c709739c4ec475b`, which pins the current Cognition blob `deb8c274...` and includes additional RAW EAR/A4 source modules. Its focused A4, frame-ingress and RuntimeDeploy workflows have green evidence, but its own shared staged/integrated path has not been proven green. Therefore QA did not silently rewrite the older Perception composer or transplant a lone pin.

## Next owner action
Boss/Integrator must select the canonical convergence ancestry. Recommended: rebase/port Core #2572 onto the current #2579 Perception ancestry, reapply the reviewed Callosum matrix change, then regenerate the guard and Recovery → Stage → RuntimeDeploy pins against the resulting exact files. QA can then rerun the full staged/integrated, migration, owner-read and Python 3.14 gates. If the rebased Callosum bytes change, its allowlist hash must be reviewed again.

No production route, native learning authority, model/weight change, device permission or user-data action was enabled.


## Additional whole-system QA checks
- P0 issue #1904 remains OPEN. No new normal-turn 20-case CHAT_SEND/CHAT_RESULT acceptance set, correct-answer rate, B1/B2 valid-offer delivery, device TTFT/PSS/residency or installed-SHA receipt was obtained.
- Read-only private relay requests were created for HEALTH (#1046), PIPELINE_STATUS (#1047) and DIAGNOSTICS (#1048), each with a 600-second expiry. All were polled; none returned a `device_status` receipt. Result: `NO_LIVE_RECEIPT`. No LOG_PAGE request was made because log opt-in is not verified. Private V13OBS #115 has no fresh receipt; #1904's last cited snapshot remains the historical 2026-11-24 STOPPED_BY_USER state.
- Core normal-turn PR #2577 has a passing staged/integrated regression on its own #2568 ancestry, but its MediaProjection frame-ingress workflow fails 2/30 on both Python 3.13 and 3.14: malformed projector NPY shapes return `PROJECTOR_LOAD_FAILED` instead of `PROJECTOR_TENSOR_HEADER_INVALID`. The newer Perception #2565 branch contains the NPY header preflight; Core must port/rebase it rather than weakening the negative test.
- Speech-output PR #2479 is only an explicit `:voice speak --allow-network-unknown` Termux TTS fallback exercised with a fake CLI and real Runtime/SQLite. Automatic playback remains false, network/offline status UNKNOWN, audibility unverified, and stop/barge-in unsupported. It is not normal-turn speech or a trainable decoder/vocoder.
- These are independent blockers; none is evidence of Redmi hardware success. No private raw conversation/log data was copied to public GitHub.

# Core & Harness — V14 staged runtime pin-chain repair

**Date:** 2026-11-22  
**Owner:** Core & Harness  
**Base:** Boss integration branch `boss/v14-recall-store-pin-rebind-20261122` at `033c543b508da30cab2ad7b6c8a5c0caab0c31ed`  
**Branch:** `core/v14-stage-pin-chain-20261122-run1`  
**Status:** DRAFT / NOT_RELEASED / REDMI_UNVERIFIED

## Reproduced exact-head failures

On Boss head `033c543b508da30cab2ad7b6c8a5c0caab0c31ed`, the current CI logs showed three deterministic source-pin failures:

- `stage_integrated_candidate.py:48`: `integrated builder hash mismatch`.
- `runtime_deploy.py:491`: `Integrated stage builder changed`.
- `termux_runtime_recovery_candidate_20261112.py:223`: `Termux recovery builder source changed: scripts/record_only_controller_guard_20261116.py`.

These failures prevented the composed stage from reaching the existing staged Runtime / Lab-Age / phone-offer tests. The two-checkout migration returned PARTIAL downstream of staging and is not independent evidence of a Git migration defect.

## Code repair

The changes restore the exact source-hash chain without weakening any validation:

1. Updated the base recovery composer’s pinned Record-Only controller-guard SHA to the exact current guard bytes.
2. Updated the outer recovery builder’s Git blob SHA-1 pin to the new base-composer blob.
3. Updated the integrated stager’s BUILDER_SHA to the exact outer recovery-builder SHA-256.
4. Updated runtime_deploy.STAGER_SHA256 to the exact integrated-stager SHA-256.

## Exact GitHub readback

| Object | Verified value |
| --- | --- |
| Record-Only guard SHA-256 | `77be1b41933940eb427fb86cc30c9d6a8ecb89f4f3914c7d28652eefa17825be` |
| Base recovery composer Git blob SHA-1 | `a142f51814a521183416619b763b3a6202fe6d67` |
| Outer recovery builder SHA-256 | `bb70dc50030f35eafedb75bc03ee163aa90ed319f98e8c8e8667b2c83363f7b9` |
| Integrated stager SHA-256 | `2299f74d514116b9eec9f7f1a4a85a0cff77a2af5d0f3ead3941ea38a2787986` |
| runtime_deploy.STAGER_SHA256 | Exact match to the integrated stager above |

All four modified source files were fetched again from the working branch after their writes; the returned blob identities and recomputed SHA-256 values matched the intended content. This is a GitHub byte/readback check, not a runtime test.

## Tests and evidence boundary

- **LOCAL_LINUX repository tests:** BLOCKED. No Aii checkout is mounted; `git ls-remote https://github.com/RedMentos/Aii.git` failed because this runner cannot resolve github.com.
- **GitHub Actions exact-head tests:** PENDING on the new Core branch/PR.
- **SYNTHETIC / CI:** no new PASS claimed yet.
- **TERMUX / REDMI:** REDMI_UNVERIFIED. No connected authorized phone receipt, installed SHA, model process, native GGUF generation or PSS/TTFT measurement was available.
- No model, weight, Age, permission, updater, SQLite/chat data or installed-device state was changed.

## Next executable step

Run the exact staged/integrated, audio/arithmetic, Lab-Age, controller guard, owner-read/startup, two-checkout migration, C4→C3 consumer, and runtime-deploy workflows on this exact branch head. Fix any new failure from its observed source boundary; do not promote the candidate to release or device status from hash readback alone.

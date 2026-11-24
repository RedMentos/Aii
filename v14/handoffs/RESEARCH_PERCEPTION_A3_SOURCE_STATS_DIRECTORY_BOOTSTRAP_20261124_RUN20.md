# Research & Perception — A3 source-stat directory bootstrap

**Date:** 2026-11-24  
**Run:** 20  
**Follow-up branch:** research-perception/v14-a3-source-stats-dirfd-create-20261124-run20  
**Parent:** PR #2477 at dd7e841a4047072dd9bc7dc33d7ad34bb94bf867 (itself stacked on Core PR #2465)  
**Release:** NOT_RELEASED

## Reproduced defect

The exact #2477 Python 3.13 and 3.14 vision/source-lineage workflow failed four tests. vision.train() / train_tiles() call build_source_statistics() before Projector.save(). On a fresh Store, data/vision has not yet been created. The source-stat writer opened data and vision but did not create them, so its documented OSError fallback returned an empty stats list / UNAVAILABLE_STORAGE. The later projector save created the directory, leaving a working projector without the exact deletion statistics needed by the new forget path.

Affected exact-head regressions included fresh global/tile rebuild, fresh-fit parameter equivalence, and corrupt-stat fallback setup. This was a real integration bug in the new A3 path, not a reason to weaken the forget or hash gates.

## Code change

v13/code/v13/vision_projector_stats.py now opens or creates each missing directory level relative to an already-open parent directory descriptor:

- mkdirat semantics through os.mkdir(..., dir_fd=...), mode 0700;
- immediate O_NOFOLLOW | O_DIRECTORY open after creation (including the concurrent-creator case);
- fstat directory-type verification;
- existing owner-only 0600 statistics files and fsync/atomic rename retained;
- symlinked or non-directory paths still fail closed.

test_vision_projector_stats.py adds a fresh-root regression that verifies both directory modes, four persisted per-source artifacts, and 0600 file modes. Existing symlink/tamper/source-cap and full A3 Runtime forget tests remain in the exact workflow.

## Local reproduction

- **LOCAL_LINUX, CPython 3.13.5:** reproduced the old implementation's FileNotFoundError: data on a fresh root.
- **LOCAL_LINUX isolated dir-fd harness:** PASS — new implementation created data/ and data/vision as 0700, wrote an artifact as 0600, fsynced the file and directory, and rejected a symlinked vision directory with NotADirectoryError.
- This harness exercises the exact directory-creation algorithm, not the complete Aii package or Runtime. Full local repository pytest remains BLOCKED / NOT_RUN because no checkout is mounted and the prior local GitHub DNS lookup failed.

## Acceptance and integration boundary

The branch and PR are pushed. The available PR-triggered workflow-run readback returned no runs for the exact head after the pull_request path filter was extended; no CI PASS is claimed. Required checks: source-stat helper + full test_vision.py + source-lineage on Python 3.13 and 3.14; staged/integrated and Core source-lifecycle workflows. The existing #2477 failures are not reclassified as passes.

Core/QA still owns the materialized source-lifecycle composer. It must include vision_projector_stats.py with its exact SHA and rebind the changed vision.py source pin before the staged consumer can pass. Do not relax source hashes.

No Android/Termux/Redmi, microphone, native model, model/weight update, user-data mutation, permission change, or deployment was performed. **REDMI_UNVERIFIED / NOT_RELEASED.** No user action is required.


## Exact PR trigger coverage

The existing vision/source-lineage workflow's push path filter already included the helper and helper tests, but its pull_request path filter omitted both. PR #2484 therefore extends that filter and the compile step so the exact fresh-root regression runs as a required PR-triggered check, not merely on branch push. The Python 3.13/3.14 workflow remains the same bounded test environment.


## Research review added to the shared ledger

- **R-141, QSS (NeurIPS 2026):** full paper read. Schema/content split gives exact deletion for content points in QSS-E and label-only deletion in QSS-L; retained-schema deletion still rebuilds. The paper reports 4–483x expected latency gains on low-class-count tasks, not a general mobile result. The linked GitHub repository has no LICENSE file and qss.py carries a Meta 'Confidential and proprietary' header; no code reuse.
- **R-142, ridge-statistics probing (arXiv 2609.04475, 2026-09-03):** full preprint read. Repeated high-precision full-head broadcasts can expose deleted sufficient statistics under an active-client/quiet-interval threat model. V14's local A3 statistics therefore remain local-only. A Runtime negative-control test was added so status exposes counts/mode but not source-stat paths, hashes or matrices.
- **R-143, memory-efficient CNNs (IJCV 2026-01-29, CC BY 4.0):** full article read. The 63 KB/42 KB peak-activation results are STM32H7 results, with a 3.34M-parameter ImageNet model; useful as a future streaming feature-extraction idea, not a Redmi or LFM replacement. No code repository was located.


## Final exact-head and private-device readback

- #2477 exact head dd7e841: 4 failed / 45 passed on Python 3.13 and the same 4 / 45 on Python 3.14. The four failing Runtime tests all traced to empty source_stats on a fresh Store before data/vision existed.
- #2484 exact head 3ef4471603831103717631bf2b12a24b96307cac: the available PR-triggered workflow-run readback returned no runs after the pull_request path filter was extended. No CI PASS is claimed; an owner-triggered Actions run is still required.
- Latest private device metadata snapshot (2026-11-24 09:28:11Z): 5 turns, zero valid B1/B2 offers, two failed native attempts for each role, no semantic-use proof and no native latent exchange; two later C3 prefill phases were 33–37 seconds. No transcript or device identifier copied.
- Last authenticated updater receipt (2026-11-23 14:24Z) reports auto-update enabled and runtime/dashboard UP_TO_DATE at fb563d771fe2d493c4ec25abe94280981d24ef5c. Current development HEAD 8d93236c753f0194224c19edc7411d8d7082b1d6 is newer and is not verified installed. New read-only requests expired without device_status: NO_LIVE_RECEIPT.
- No UPDATE_REQUEST, shell, LOG_PAGE, CHAT_SEND, model/weight/permission change, user-data mutation or deployment.


## Run 21 follow-up — 2026-11-25

- **Code/test commit:** `8d0861188a61290366cd2aa377edcfac0c625610` on this branch; PR #2484 remains DRAFT/NOT_RELEASED.
- **Hardening:** the helper now checks directory ownership and uses descriptor-relative `fchmod(0700)` for both existing and newly created `data/` and `data/vision/`; this addresses permissive legacy directories without following symlinks. Added a production-builder regression starting from 0755 directories.
- **LOCAL_LINUX CPython 3.13.5 isolated harness:** PASS 4/4 for fresh creation, 0755→0700 hardening, `data` symlink rejection and `vision` symlink rejection. This is not full package pytest. Full local checkout tests remain NOT_RUN.
- **Exact GitHub head:** 8d0861188a61290366cd2aa377edcfac0c625610. Workflow runs 45506945163 (vision source-lineage), 45506945574 (staged/integrated), 45506945185 (runtime deployment integrity), 45506945923 (MediaProjection ingress) were IN_PROGRESS at readback; no CI PASS claimed.
- **Research:** R-144 (Si & Qin, arXiv:2608.16141) supports tracking representation drift alongside retention/new learning instead of treating all drift as failure; the reproduction repository has no LICENSE. R-145 (Yan et al., arXiv:2609.25146) documents hierarchical sparse expert routing plus multi-timescale integration; official FlyGCL code is MIT, but its full visual/VLA stacks use ViT/CLIP/DiT and multiple heavyweight packages, so no direct Android port or code reuse.
- **Device:** REDMI_UNVERIFIED. No device receipt, microphone capture, model/weight/permission change, update request or deployment.
- **Next:** read back all four exact-head workflows; if source-lineage passes, Core/QA must integrate the helper into the materialized source closure and rebind pins, then rerun staged/integrated/consumer/migration tests. Do not merge/release before that.
- **User action:** none.


## Research & Perception — run 22 exact-head readback (2026-11-25)

**Current code/test head:** `177f72364440519f6d38cecdb7dca7629ae2304b` on PR [#2484](https://github.com/RedMentos/Aii/pull/2484), still OPEN/DRAFT/NOT_RELEASED.

- The source-stat helper hardens both fresh and pre-existing `data/` + `data/vision/` directories: owner check, descriptor-relative `fchmod(0700)`, post-change mode verification; artifacts remain 0600. The added regression starts with 0755 directories and verifies 0700 after the production builder.
- **LOCAL_LINUX CPython 3.13.5 isolated helper harness:** PASS 4/4 (fresh creation, legacy 0755 hardening, `data` symlink rejection, `vision` symlink rejection). Full local Aii checkout pytest/py_compile was NOT_RUN because this worker has no repository checkout.
- **CI exact head:** source-lineage + A3 forget suite PASS 51/51 on Python 3.13 and 51/51 on Python 3.14; exact compile step passed. RAW EYE frame-ingress PASS on 3.13 and 3.14. Runtime deployment-integrity offline checks PASS on 3.11 and 3.14.
- **Integration remains blocked:** staged-runtime FAIL: 19 failed / 234 passed / 10 skipped / 2 errors / 41 subtests; integrated-regression FAIL: 1 failed. Both stop at `scripts/source_lifecycle_lock_integration_candidate.py:179` with `unsupported lifecycle source: vision.py`. Core PR #2465 currently pins `vision.py` to `350573e65eb445b8b83f5517e3bfe07ece04e036055c55fc3e23c79d5b0cc728` and does not include `vision_projector_stats.py`; the exact #2484 source workflow reports `vision.py` SHA-256 `329bdacc068bf7059c87ef74425fbbfc9538ad85d494264c3f73cc89bb0c793d` and helper SHA-256 `5db10a4fefa0e5d40d67b242ba18858972b499283e1e00f6d13d3e5d2760032f`. Core/Integrator was given this exact evidence in a comment on #2465. No hash check was weakened.
- **Runtime consumer:** A3 `vision.train()` / `train_tiles()` → source-stat builder → local secure storage; explicit source forget rebuilds only exact full-fit ridge heads. It does not unlearn the image feature extractor, teacher or other organs.
- **Device/release:** REDMI_UNVERIFIED; no phone receipt, Termux test, model/weight/permission change, UPDATE_REQUEST or deployment. Last available private updater receipt is older than the current release-development HEAD, so current installation remains unverified.
- **Research:** R-144 full preprint review (replay can preserve function while representations drift; don't make zero drift a universal objective; no code reuse due absent license). R-145 full FlyGCL preprint and MIT OSS audit (hierarchical expert specialization + temporal integration; full visual/VLA stacks are heavyweight; no port or code/weights imported).
- **User action:** none. No manual Termux command or model download/swap.
- **Next internal step:** Core/Integrator updates the strict source-lifecycle composer to include the helper and pin exact current bytes, then reruns staged/integrated/consumer/migration. Perception should not edit Core-owned composer files.



## Run 23 — private device and updater status (2026-11-25)

- The latest private metadata snapshot (2026-11-24 09:28:11Z) reports the existing base release `8d93236c753f0194224c19edc7411d8d7082b1d6` as runtime/dashboard UP_TO_DATE, auto-update enabled, and no updater error.
- This does **not** deploy #2484. The AI service is running, but the model process is STOPPED / STOPPED_BY_USER, autostart is false, and native-residency telemetry is unavailable.
- Latest recorded turn: C3 7 tokens, 358-token admitted prompt, TTFT 2.046 s, total 6.295 s. B1/B2 each had 2 failed native attempts (TIME_BUDGET, 53.2 s / 54.2 s) and zero valid offers. No semantic-use or native latent-exchange proof.
- New owner-read HEALTH/PIPELINE_STATUS/DIAGNOSTICS requests have no device_status receipt yet: NO_LIVE_RECEIPT. No raw text/logs, LOG_PAGE, CHAT_SEND, UPDATE_REQUEST, shell, or device action.
- #2484 remains DRAFT and staged/integrated CI is blocked by the Core source composer. The base updater is healthy/up-to-date, but the PR-specific device path remains REDMI_UNVERIFIED. No user action.

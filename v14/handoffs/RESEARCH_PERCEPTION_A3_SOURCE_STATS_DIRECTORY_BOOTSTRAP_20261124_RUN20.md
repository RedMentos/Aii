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

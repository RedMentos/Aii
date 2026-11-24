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

Exact GitHub Actions for this follow-up are pending until the branch is pushed. Required checks: source-stat helper + full test_vision.py + source-lineage on Python 3.13 and 3.14; staged/integrated and Core source-lifecycle workflows. The existing #2477 failures are not reclassified as passes.

Core/QA still owns the materialized source-lifecycle composer. It must include vision_projector_stats.py with its exact SHA and rebind the changed vision.py source pin before the staged consumer can pass. Do not relax source hashes.

No Android/Termux/Redmi, microphone, native model, model/weight update, user-data mutation, permission change, or deployment was performed. **REDMI_UNVERIFIED / NOT_RELEASED.** No user action is required.


## Exact PR trigger coverage

The existing vision/source-lineage workflow's push path filter already included the helper and helper tests, but its pull_request path filter omitted both. PR #2484 therefore extends that filter and the compile step so the exact fresh-root regression runs as a required PR-triggered check, not merely on branch push. The Python 3.13/3.14 workflow remains the same bounded test environment.

# Research & Perception — run 24 handoff (2026-11-25)

## Scope and ownership

- Lane: Research & Perception.
- Whole-system epic: [#1984](https://github.com/RedMentos/Aii/issues/1984).
- Active candidate: [PR #2484](https://github.com/RedMentos/Aii/pull/2484), stacked on Perception #2477 and Core #2465.
- No edits to Core-owned source-lifecycle composer, shared board, active master, historical V13 appendix, release branch, models, weights, permissions or user data.

## New code/test checkpoint

- Branch: `research-perception/v14-a3-source-stats-dirfd-create-20261124-run20`.
- New test commit: `6b637fcf2179e69fdd61159610e0a4666676c63a`.
- Research-ledger commit: `3a46ec69f152524396db79e12648a122cf3f4f6c`.
- Current PR head must be read from GitHub before further work; do not infer it from this handoff.
- Added two tests to `v13/code/tests/test_vision_projector_stats.py`:
  1. Eight concurrent first-use builders create 32 unique source-stat artifacts while converging on owner-only 0700 `data/` and `data/vision/` directories and 0600 files.
  2. A controlled interleaving creates a symlink after the initial ENOENT but before descriptor-relative mkdir returns. The no-follow reopen must reject it, the public builder must report `UNAVAILABLE_STORAGE`, and the outside directory must remain untouched.
- The test file was read back from GitHub at blob `dbc2e8985c9a81f5703890348d5ac215e1ae1648`; both new test names are present.

## Local verification

Environment: LOCAL_LINUX, CPython 3.13.5, NumPy 2.3.5 and pytest 9.0.2 available; no full Aii checkout is mounted and GitHub DNS is unavailable to the local container.

- Exact `_open_or_create_dir` helper copied from PR #2484, 8-thread first-use interleaving × 4 files per worker: **PASS, 32/32 unique files**, one directory inode, 0700 directory and 0600 files.
- Exact helper with a symlink winning the create race through `os.symlink(..., dir_fd=...)`: **PASS, fail-closed**; outside directory remained empty.
- These are isolated helper-level reproductions, not the repository pytest suite and not Android evidence.
- Full local `pytest` / `py_compile`: **BLOCKED / NOT_RUN** (no checkout).
- Exact-head GitHub Actions after test commit: vision source-lineage/forget **PASS**, RAW EYE frame ingress **PASS**, runtime deployment integrity **PASS**; staged context/integrated regression was **IN_PROGRESS** at the last read. Re-poll the exact current PR head before any PASS claim.

## Runtime and integration boundary

- The #2484 parent runtime change creates missing A3 source-stat directories using descriptor-relative mkdir/open, verifies owner/type, hardens directory modes to 0700, and keeps statistics artifacts at 0600.
- Actual consumer: `vision.train()` / `train_tiles()` → `build_source_statistics()` → `_vision_dir_fd()`.
- #2484 remains DRAFT / NOT_RELEASED. Core #2465 still owns the strict staged source-lifecycle composer; its exact `vision.py` pin rejects the current Perception source/helper closure. Required fix is to include `vision_projector_stats.py` and rebind exact source pins bottom-up; do not weaken hash checks.
- Redmi: **REDMI_UNVERIFIED**. No fresh authenticated device receipt was available in this run. Last recorded private metadata in PR #2484 says base release `8d93236c753f0194224c19edc7411d8d7082b1d6`, auto-update enabled, Runtime/Dashboard UP_TO_DATE for that base, model process STOPPED_BY_USER/autostart false, B1/B2 two TIME_BUDGET failures each and zero valid offers. That does not install or validate #2484.
- Deployment: **NOT_RELEASED**; no UPDATE_REQUEST sent, no manual Termux command, no model/weight/permission change.

## Research

- Added R-149 to `v14/V14_RESEARCH_LEDGER.md`: He et al., *Efficient Conversational Multi-Talker ASR with Predicted Speaker-Agnostic Activity Streams*, arXiv:2611.26796v1 (submitted 2026-11-19), full HTML paper reviewed, CC BY 4.0. The two-stream HEAT method offers a possible future cap of two ASR passes but assumes at most two concurrent speakers; the H-Dir predictor uses WavLM-Large and Whisper-large-v3-turbo and is not a Redmi candidate. No code/weights imported.
- Research record is a hypothesis and design reference, not a new runtime function or a claim that RAW EAR now performs multi-talker ASR.

## Next executable action

1. Poll exact current #2484 head CI; inspect any staged/integrated failure logs.
2. Coordinate with Core owner on #2465's exact source-lifecycle materialization closure and source pins; Perception must not edit Core-owned composer files.
3. Once composed, re-run A3 source-forget + staged/integrated + consumer/migration checks on one exact SHA.
4. Continue a separate high-value Canon path after this integration blocker, preferably the signed Android RAW EAR provider/consumer boundary; keep microphone capture OFF until QA's companion verifier, revocation and zeroization chain is integrated.


## Follow-up checkpoint — crash-durable directory metadata (2026-11-25)

- Runtime commit: `7f15b9e674f25beca02ffb646ab0e399aaeec9ad`.
- Test commit: `5d1983a11dabdea2147016d98386f3123679793c`.
- `_open_or_create_dir()` now fsyncs the parent directory after a new child is created or a concurrent creator wins the mkdir race, and fsyncs the opened directory after changing legacy permissions to 0700. This closes the gap where the directory entry or privacy mode was visible in memory but not yet made durable before A3 returned its source-stat records. Existing 0600 artifact writes and atomic rename/fsync remain unchanged.
- Added tests that observe the actual directory inodes passed to fsync for fresh creation and for 0755→0700 hardening.
- LOCAL_LINUX CPython 3.13.5 exact-helper harness: new parent-entry fsync PASS; existing-directory permission-metadata fsync PASS; prior 32-file concurrency and symlink-race probes remain PASS.
- These are isolated helper reproductions, not the full Aii test module. The exact GitHub Actions run for the new head must provide repository-level results.
- No Android filesystem/fsync behavior has been measured. If the target filesystem rejects directory fsync, the existing caller fails closed to `UNAVAILABLE_STORAGE` rather than claiming durable exact-deletion state.

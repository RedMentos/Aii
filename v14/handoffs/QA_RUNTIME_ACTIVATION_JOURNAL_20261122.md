# QA: crash-consistent runtime activation journal — 2026-11-22

**Branch:** `qa/v14-activation-journal-20261122`  
**Base:** Boss integration candidate `f0d3c848dfb1d65e282f065233adbe3c9205e439` (`boss/v14-recall-store-pin-rebind-20261122`)  
**Status:** DRAFT / CI PENDING / NOT_RELEASED / REDMI_UNVERIFIED.

## Reproduced defect

The current deployment and rollback paths atomically replace the launcher and `runtime-active.json` separately. A process death between those replacements can leave a mismatched pair. The previous exception handler only runs for Python exceptions, not SIGKILL/process death or power loss. It also did not restore a marker if the marker replacement had already completed before a later failure.

## Implementation candidate

- Added a durable owner-only `.runtime-activation.json` transaction journal with explicit PREPARED, LAUNCHER_SWITCHED and COMMITTED states.
- Every atomic replacement now fsyncs the file and parent directory.
- Deploy and rollback use the same pair-switch transaction. A restart either recognizes a fully committed pair or restores the exact previous launcher/marker pair.
- Recovery validates journal schema, ownership, mode, link count, backup names, hashes and current pair before writing. Unknown/tampered launcher or marker states fail closed; the journal is retained for diagnosis.
- Added CLI `--rollback` using the same journal. No model, SQLite/chat, permissions, Age, updater setting or device data are changed.
- Added eight process-death, rollback, tamper and directory-fsync regression tests; runtime-deploy CI runs them on Python 3.11 and 3.14.

## Verification boundary

- GitHub source readback: implementation, tests and workflow paths are present on this branch.
- LOCAL_LINUX full Aii checkout: BLOCKED; no repository checkout is mounted in this worker.
- Exact-head CI: pending. No test is marked PASS before its run completes.
- Android/Redmi: REDMI_UNVERIFIED. No live device receipt, deploy, rollback or native measurement was available.
- This does not fix the separate Boss source-pin composition failure at `termux_runtime_recovery_candidate_20261112.py:313`; #2288 remains blocked until its exact-head CI is green.
- Pipeline UI rollback action is not yet wired to the new `rollback()` API; the current candidate exposes the safe runtime rollback function/CLI. Rebase/compose the UI path only after Boss integrates the transaction helper.

## Next

Run exact-head Python 3.11/3.14 runtime-deploy integrity tests, inspect every process-death result, then rebase the rollback UI/worker consumer and rerun the full staged/integrated release gates. No Redmi release or user action is requested.

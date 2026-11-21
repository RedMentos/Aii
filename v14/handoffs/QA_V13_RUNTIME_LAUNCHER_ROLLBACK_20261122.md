# QA handoff — V13 runtime launcher rollback

**Date:** 2026-11-22  
**Owner:** QA & Android  
**Integration base:** Boss branch `boss/v14-core-perception-store-audio-integration-20261121` at `9922cf86ecf8801d30a46a1e98817e5c6c1db092`  
**Branch:** `qa/v14-runtime-launcher-rollback-currentbase-20261122`  
**Status:** CURRENT-BASE CANDIDATE / CI PENDING / NOT_RELEASED / REDMI_UNVERIFIED

## Functional defect addressed

The supported `v13-update rollback` path previously refused to restore the installed launcher. Restoring only a Git tree was insufficient, and the runtime marker also had to be restored consistently.

## Current-base implementation

- Retains the Boss branch's current stage/UI builder SHA pins and its complete-runtime CLI description.
- Saves owner-only, SHA-bound launcher and prior-marker backups; validates backup ownership, mode, path containment, hashes, stage manifest and marker/launcher relationship before mutation.
- Restores the previous launcher and marker, or removes the marker on first-install rollback. Models, SQLite, dashboard source and permissions are not modified.
- Routes the lower-level `runtime_deploy --rollback` option through the same pipeline transaction as `v13-update rollback`, so it cannot bypass the update lock, auto-update disable or managed-chat stop/resume path.
- Fsyncs the containing directory after atomic file replacement and after first-install marker removal.
- If the prior chat's RESTORE resume request fails after the runtime rollback succeeded, the result now remains `ROLLED_BACK_RUNTIME_ONLY` and separately reports `resume=FAILED` / `resume_error=STATE`; it no longer misreports the entire rollback as failed.

## Negative controls

- First install vs second deploy; exact launcher and marker bytes restored.
- Tampered backup, active runtime, unsafe path/symlink and stage mismatch refuse before switching.
- Busy pipeline lock refuses without disabling existing auto-update consent.
- Models and SQLite sentinel bytes remain unchanged.
- Atomic file replacement requests parent-directory fsync.
- Lower-level rollback CLI delegates to the locked pipeline path.
- Resume-marker failure is distinct from successful launcher restoration.

## Evidence boundary

The parent Boss branch exact CI at `9922cf86` completed its staged audio/arithmetic (Python 3.13/3.14), staged Runtime (251 passed / 10 skipped / 47 subtests), integrated regression (424 passed / 3 skipped / 58 subtests), runtime deployment, Lab-Age, owner-read and migration checks successfully. The earlier rollback-only branch exact head `314d39b06e9d5acac99b15196180de921feb9ff8` passed its runtime deployment, staged Runtime, integrated regression, Python 3.14 staged startup, owner-read, Lab-Age and migration workflows; the strict safe-additive validator correctly failed by policy because this changes existing runtime code.

This current-base branch's new exact-head CI is pending. No full local Aii checkout was available. No Android SDK/Gradle build, Redmi/Termux action, phone receipt, model inference, weight change, permission change or user-data mutation occurred. **REDMI_UNVERIFIED / NOT_RELEASED.**

## Remaining rollback scope

- This is runtime-launcher rollback only. Dashboard Git source remains `UNCHANGED`; a WebView rollback button and complete dashboard rollback are still open.
- The two-file launcher/marker switch is individually atomic but is not yet a journaled multi-file crash-recovery protocol. Do not claim power-loss recovery between the two replacements.
- The RESTORE marker is a request only. WebView consumption and actual chat restart require a real device receipt.

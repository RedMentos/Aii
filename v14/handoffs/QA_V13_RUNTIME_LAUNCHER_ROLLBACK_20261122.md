# QA handoff — V13 runtime launcher rollback

**Date:** 2026-11-22  
**Owner:** QA & Android  
**Integration base:** Boss branch `boss/v14-core-perception-store-audio-integration-20261121` at `9922cf86ecf8801d30a46a1e98817e5c6c1db092`  
**Code-bearing QA SHA:** `93bdae7a3d90415968d5531b59804d987e3d238a`  
**Branch:** `qa/v14-runtime-launcher-rollback-currentbase-20261122`  
**PR:** [#2276](https://github.com/RedMentos/Aii/pull/2276)  
**Status:** EXACT CODE-HEAD CI GREEN / DRAFT / NOT_RELEASED / REDMI_UNVERIFIED

## Functional defect addressed

The supported `v13-update rollback` path previously refused to restore the installed launcher. Restoring only a Git tree was insufficient, and the runtime marker also had to be restored consistently.

## Current-base implementation

- Retains the Boss branch's current stage/UI builder SHA pins and complete-runtime CLI description.
- Saves owner-only, SHA-bound launcher and prior-marker backups; validates backup ownership, mode, path containment, hashes, stage manifest and marker/launcher relationship before mutation.
- Restores the previous launcher and marker, or removes the marker on first-install rollback. Models, SQLite, dashboard source and permissions are not modified.
- Routes the lower-level `runtime_deploy --rollback` option through the same pipeline transaction as `v13-update rollback`, so it cannot bypass the update lock, auto-update disable or managed-chat stop/resume path. It refuses unmanaged alternate homes.
- Fsyncs the containing directory after atomic file replacement and after first-install marker removal.
- If the prior chat's RESTORE resume request fails after the runtime rollback succeeds, the result remains `ROLLED_BACK_RUNTIME_ONLY` and separately reports `resume=FAILED` / `resume_error=STATE`; it no longer misreports the entire rollback as failed.

## Exact tests — GitHub CI on code-bearing SHA `93bdae7a3d90415968d5531b59804d987e3d238a`

- **V13 runtime deployment integrity**, run `44960976027`: PASS. Offline suite compiled `runtime_deploy.py`, `pipeline_agent.py` and test files; rollback regressions included:
  - `test_atomic_file_fsyncs_parent_directory`
  - `test_runtime_deploy_rollback_cli_uses_pipeline_transaction`
  - `test_runtime_deploy_rollback_cli_refuses_unmanaged_home`
  - `test_first_install_rollback_restores_original_launcher_and_removes_marker`
  - `test_second_deploy_rollback_restores_previous_launcher_and_marker`
  - `test_tampered_backup_launcher_fails_closed_without_switch`
  - `test_runtime_rollback_reports_resume_failure_without_masking_restored_runtime`
  - pipeline suite: **37 tests PASS**
- **V13 staged context and integrated regression**, run `44960976004`: PASS — staged Runtime **252 passed / 10 skipped / 47 subtests**; integrated regression **424 passed / 3 skipped / 58 subtests**; staged arithmetic/broker **39 passed / 17 subtests**.
- **Python 3.14 staged startup and SQLite source refs + owner-read**, run `44960976013`: PASS; chat-session/Store-lock tests **11 passed**.
- **Two-checkout migration**, run `44960976012`: PASS.
- **Lab-Age control/WebView truth**, run `44960976014`: PASS.
- Parent Boss branch exact CI at `9922cf86ecf8801d30a46a1e98817e5c6c1db092`: 12 SUCCESS, 5 SKIPPED, 3 CANCELLED, 0 failures.
- The earlier rollback-only branch `314d39b06e9d5acac99b15196180de921feb9ff8` also had exact functional CI green. Its additive-only validator failure was by policy because existing runtime files changed. This current stacked PR did not trigger that additive-only workflow; no gate was bypassed or weakened.

## Evidence boundary

No full local Aii checkout was available. No Android SDK/Gradle build, Redmi/Termux action, phone receipt, model inference, weight change, permission change or user-data mutation occurred. **REDMI_UNVERIFIED / NOT_RELEASED.**

## Remaining rollback scope

- Runtime-launcher rollback only. Dashboard Git source remains `UNCHANGED`; a WebView rollback button and complete dashboard rollback are still open.
- The two-file launcher/marker switch is individually atomic but is not yet a journaled multi-file crash-recovery protocol. Do not claim power-loss recovery between the two replacements.
- The RESTORE marker is a request only. WebView consumption and actual chat restart require a real device receipt.

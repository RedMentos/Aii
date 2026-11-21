# QA handoff — V13 runtime launcher rollback

**Date:** 2026-11-21  
**Owner:** QA & Android  
**Base:** `gpt6/v13-private-remote-bridge-20261111` at `bdcad466ffea75a2b41f7d23be168f53c7197d20`  
**Branch:** `qa/v14-runtime-launcher-rollback-20261121`  
**Status:** DRAFT / CI_PENDING / NOT_RELEASED / REDMI_UNVERIFIED

## Finding

The existing `v13-update rollback` CLI path explicitly returned REFUSED because the legacy behavior restored only a Git tree and did not restore the installed `~/v13/bin/v13` launcher. `runtime_deploy.deploy()` saved the previous launcher but did not save the previous `runtime-active.json` marker, so a launcher-only restore would leave the installed runtime receipt inconsistent.

This is a direct gap in V14-002 (verified update, backup, non-destructive rollback and restart).

## QA implementation

- Each new runtime deployment saves the previous launcher SHA and, when present, an owner-only backup of the previous runtime marker with its SHA.
- `runtime_deploy.rollback()` validates the current launcher/marker/stage, validates private backup paths and hashes, verifies the previous immutable code snapshot, then restores the previous launcher and marker. First-install rollback restores the original launcher and removes the current marker as a clearly labeled legacy rollback.
- Rollback refuses active runtimes, symlinks, path escapes, tampered backups, malformed markers and stage-integrity mismatches.
- The pipeline CLI's explicit `rollback` action disables future automatic activation, takes the pipeline lock, gracefully stops only a managed V13 chat, restores the runtime launcher, and resumes the prior chat. It reports `ROLLED_BACK_RUNTIME_ONLY`; the dashboard Git checkout is deliberately reported `UNCHANGED`, not falsely rolled back.
- Dashboard source rollback and a WebView rollback button remain open; full V14-002 is not complete.

## Tests

- New runtime-deploy tests: two-deploy rollback restores the exact prior launcher and marker; first-install rollback restores the original launcher; tampered launcher backup and active-runtime controls fail closed; models and SQLite fixture bytes remain unchanged.
- New pipeline tests: auto-update is disabled, managed chat stop/resume is used, a busy update lock refuses without changing consent, and the CLI no longer returns the legacy stub refusal.
- LOCAL_LINUX test run: pending; no repository checkout/network is available in this worker. Exact GitHub CI is the executable proof gate.
- Android/Redmi: **UNVERIFIED**; no APK, Termux service, model, SQLite or user data was touched.

## Next acceptance

Run the exact Python 3.11 runtime-deploy and pipeline tests plus the staged integrated regression on the exact PR SHA. Then test the actual WebView/Termux rollback route on an authorized Redmi, including managed chat stop/restart and proof that the prior marker/launcher are restored. Add dashboard source rollback before claiming the full V14-002 acceptance.

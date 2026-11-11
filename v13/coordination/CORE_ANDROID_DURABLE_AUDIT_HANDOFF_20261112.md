# Core Android durable companion audit handoff — 2026-11-12 00:04 CET

Owner: Core & Harness. Package: ANDROID_CONTROL / pre-action durable audit.
Review: PR #1807; branch `codex/v13-core-durable-companion-audit-20261112-0004`.
Base: Boss PR #1805 branch `boss/v13-companion-stop-race-20261111-2345` at `e960e4af33c1e0bc8e694d9cafbde82050c791fe`.
Latest source commit: `c0c08f299a7236d25a504a56e02a29ea6906d6a5`.
Files: `v13/code/v13/android_action_audit.py`, `v13/code/tests/test_android_action_audit.py`, `.github/workflows/v13-android-action-audit.yml`.

Implemented: optional SQLite FULL synchronous intent-before-transport, no target/text payload storage, restart-visible UNKNOWN, replay ID rejection, dry-run refusal, and factory wiring to existing receipt-verifying AndroidDispatcher. A reported native success is `REPORTED_SUCCESS`, not authenticated success. No new permission grant. Source readback confirmed at blob `3a34e83da389f434fd33d2b38077d567684f849a`.

Evidence: GitHub Actions run 43116872673 focused audit and 43116872663 staged regression were IN_PROGRESS when inspected. **No passing result is claimed**. Local git clone failed DNS (`Could not resolve host: github.com`); connector source and commits succeeded. No Redmi hardware test, native companion, OS permission grant, signed receipt verification implementation or production integration. No change to original negative gates.

Next exact actions: inspect https://github.com/RedMentos/Aii/actions/runs/43116872673 and https://github.com/RedMentos/Aii/actions/runs/43116872663; fix any failing test on own branch; independently review duplicate/restart/crash semantics and cross-process file locking; integrate with C5/JEF→T8 action outcome receipts only after upstream #1799/#1801/#1802/#1803/#1805 stack is green. Add native Android companion with OS-side permission checks, locally authenticated per-action consent, stop and audit. Keep OFF default and Redmi UNVERIFIED.

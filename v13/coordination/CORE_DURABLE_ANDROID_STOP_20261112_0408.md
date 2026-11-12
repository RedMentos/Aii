# Core Android durable stop — 2026-11-12 04:08 Europe/Berlin

Owner: Core & Harness. Review branch: `core/v13-android-durable-stop-20261112-0408`; stacked on #1818 (itself on Boss #1816). PR #1820. No other owner's source edited.

## Executable edge
`android_local_console` now creates a durable stop latch next to its audit SQLite database. A local `:android stop` first cancels in-flight registry requests, then fsyncs a stop marker. Reopening the console with a new, enabled `CapabilityRegistry` sees that marker and immediately stops the registry. Existing/malformed stop markers are fail-closed. No reset API; native Android permission and companion authorization remain separate.

## Evidence and limitations
- GitHub source commit and PR saved; synthetic tests added for restart and malformed marker.
- CI workflow `.github/workflows/v13-core-durable-android-stop.yml` added; exact-head result **PENDING/UNVERIFIED** at this checkpoint.
- Direct git clone/test unavailable in this runtime: `Could not resolve host: github.com`; connector source readback is available. Local `py_compile` of standalone stop-latch prototype succeeded, **not** a full repository test.
- This is same-UID Termux state, not tamper-proof. External processes can remove/alter files. No Android native companion, OS permission, Redmi measurement, voice, full JEPA, or AGI proof.
- No production promotion; original negative gates, SourceHandoff freeze and `canonical_architecture_complete=false` remain unchanged.

## Next exact commands
On exact PR head: `PYTHONPATH=v13/code python -m pytest -q v13/code/tests/test_android_local_console.py v13/code/tests/test_android_operator_audited_session.py v13/code/tests/test_android_operator_validation.py`. Check workflow, repair any red, review stop marker write failure and symlink cases, then integrate the Android action outcome into authenticated C5/JEF→T8 without granting C3 text direct execution. For real native Android, independent companion OS grant/approval/receipt verifier and device tests are still required.

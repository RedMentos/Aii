# Core Android-device-control candidate — 2026-11-11 08:00 Europe/Berlin

Owner: Core & Harness. PR #1749, branch `codex/v13-android-control-contract-20261111-hour08`, based on integrated PR #1716 SHA `706b75bb85be3b851975eea8cfd151c80c56a395`. No shared frozen Runtime, JEPA, QA or A5 files changed.

## Actual runnable surface

`PYTHONPATH=v13/code python -m v13.android_control_cli --db "$HOME/.v13/android-control-audit.sqlite"` is a **Termux interactive dry-run** operator. The SQLite broker validates an action schema, requires a fresh explicit typed YES per action, logs proposal/approval/dry-run, rejects reused or expired approvals, has an operator stop switch and denies non-interactive CLI input. This is local proposal handling, **not Android control**. No Android OS permission, app UI automation, screen capture or trusted companion transport is implemented. A Python caller could spoof `confirmed_by_local_ui=True`; this is not a security boundary until an authenticated companion owns confirmation and the broker is isolated from model/tool code. Do not connect arbitrary model calls to `start`/`approve`.

Supported candidate schema: launch_app(package), observe_ui(), tap(x,y), swipe(x1,y1,x2,y2,duration_ms), type_text(text), back(). These are dry-run envelopes only. No shell/network/control bypass, no implicit grant, no active device authority. Do not interpret Android coordinates until a native companion validates current display bounds, target app, foreground state, protected fields and gesture semantics.

## Validation and next exact commands

CI workflow `.github/workflows/v13-android-control-broker.yml` runs `PYTHONPATH=v13/code python -m pytest -q v13/code/tests/test_android_control.py v13/code/tests/test_android_control_cli.py`. Initial broker-only CI on commit `b5b7987b0846f79c37d6a81ba532926dfb9b0108`: GitHub Actions run 42976731806 SUCCESS. Expanded CLI CI on latest commit: check exact HEAD Actions before claiming success. Local clone was attempted and failed DNS `Could not resolve host: github.com`; no local native tests claimed. GitHub readback confirmed source blob hashes.

Next owner package: native Android companion with explicit user-controlled AccessibilityService permission and independent MediaProjection consent; authenticated same-device IPC with action nonce/digest binding and stop; protected-app/field restrictions, per-action audit and observed outcome; permission-revocation and process-restart tests. Then bridge approved Android outcomes into trusted PerceptPacket/T8 lineage without granting World/JEPA/model any approval authority. QA owns security instrumentation, Perception owns UI observation contract. Real Redmi Note 10 Pro proof remains UNVERIFIED. No STEP2/B3/Body/AGI gate changes; no production promotion.

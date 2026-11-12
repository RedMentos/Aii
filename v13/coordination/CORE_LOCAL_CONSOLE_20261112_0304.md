# Core Android local operator console — 2026-11-12 03:04 Europe/Berlin

Owner: Core & Harness. Branch: `core/v13-android-local-console-20261112-0304`; base Boss #1816 SHA `cc1bf89bc72a626362e3b7da6bef19b288be535a`; PR #1818. Scope: only new `android_local_console.py`, `test_android_local_console.py`, CI and this handoff. Boss owns `android_operator_audited_session.py` and prior audit; do not overwrite.

User-facing synthetic path: explicit operator command → local confirmation callback → existing capability registry → audited dispatcher → injected companion transport/verifier → persisted SQLite journal. New `:android status` reports redacted counters; `:android stop` closes the session's action capability. Neither supplies native Android authentication. Natural language does not implicitly invoke tools.

Evidence: exact GitHub source commits `3fcb0300716822923cb9ba9ece765cf40b7e5a99`, `8582f9a516490699dcb2c1745557ba013d65d67f`, workflow `6b6786e2647784ef834a0c2ef3cf08ddac47a1be`. CI pending at handoff; no local full pytest because github.com DNS resolution failed. All native Android/Redmi, real voice, GGUF learning, full system gates remain OPEN/UNVERIFIED. Draft PR is not production integration.

Next exact command on checked-out PR head: `cd v13/code && PYTHONPATH=. python -m pytest -q tests/test_android_local_console.py tests/test_android_operator_audited_session.py tests/test_android_operator_validation.py`. Check PR #1818 workflow run and fix failures on own branch. Then integrate with trusted native Android companion and actual local permission UX, not a Python-origin flag; validate Android 13 on Redmi. Other high-priority Core work: B1/B2↔JEF/C3 real training/retention and C3 speech renderer.

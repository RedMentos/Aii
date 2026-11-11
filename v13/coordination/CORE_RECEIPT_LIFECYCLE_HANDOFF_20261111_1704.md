# Core receipt lifecycle checkpoint — 2026-11-11 17:04 CET

Owner: Core & Harness. Review PR #1786, base Core #1783 at 88207021e329970c6f57662c116c36ffb7362d81. Head source 1e5e9df1730057621f1639e343196005deedc153.

Issue: dry-run receipt remained accepted after stop/restart/start, and a simulated dispatch failure could be followed by an accepted success. The broker now binds receipt acceptance to the durable audit stop epoch and enforces exactly one terminal result (success or dispatch failure). No native Android operation, grant or user confirmation was performed.

Changed: v13/code/v13/android_control.py and tests/test_android_operator_loop.py. Two regression tests cover stop/close/restart/start and terminal dispatch failure. Tests are committed but CI status at initial query returned no statuses; **not verified PASS**. Exact test command: `PYTHONPATH=v13/code python -m pytest -q v13/code/tests/test_android_control.py v13/code/tests/test_android_operator_loop.py`.

Next: check exact-head Actions; fix failures, review concurrency/SQLite crash consistency, and coordinate copy into Boss #1785 without editing its branch. Then build independently OS-enforced Android native companion/consent boundary and B1/B2 active adapter reload; no desktop dependency. Native Redmi, OS permission, speech and permanent master-weight training remain UNVERIFIED/OFF. STEP2 and B3 negative gates unchanged. No secrets or third-party sources added.

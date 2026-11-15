# Perception handoff — 2026-11-15 11:00 CET

Parent: `gpt6/v13-private-remote-bridge-20261111`. Shared P0: #1904.
Scope: strict A5 input validation for `v13/code/v13/percept_admission.py`; adversarial tests `v13/code/tests/test_percept_admission_strict_types_20261115.py`.

Hypothesis: truthy string consent/finality and bool timestamps can cross an observation-only admission contract, creating unsafe source inclusion or inconsistent ordering. Patch rejects non-boolean consent/finality, non-int timing/priority, and malformed source/summary before sorting or budget selection. Real False remains omitted. This does not verify live consent revocation; caller must check authorization at final use.

Test command: `cd v13/code && PYTHONPATH=. python -m unittest discover -s tests -p 'test_percept_admission*.py'`.
**Execution status: NOT RUN** — development container GitHub DNS failed; exact-head CI and phone validation unavailable. Tests are source-committed, not claimed passed.

Low risk: stdlib-only stricter validation + offline tests, no new permissions, no model writes. Compatibility risk: callers previously sending truthy strings now receive ValueError; review producers and use explicit bool normalization only at trusted input boundary. Boss/Core must review, run exact-head CI, integrate into release and measure on Redmi. NOT_RELEASED / REDMI_UNVERIFIED. No A3 training or audio microphone proof; A3 native gate remains unavailable.
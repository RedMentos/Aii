# Run79 prereg — Context OS measured cache-cost integrity

2026-10-24. Base Run78 PR111 `aa471a307b5ea19b7ebc0a110df973a0fe4e394c`.
Owner: `v13/code/v13/context_os.py`, `v13/code/tests/test_context_os.py`, and Run79 evidence only. No other owners' files or native jobs.

Problem: `ContextOS.observe` currently accepts negative integers and booleans for `cache_n/prompt_n` because Python `bool` subclasses `int`. An invalid metric may create a negative or >1 reuse ratio, pollute accumulated cost telemetry and emit an invalid neuromodulator cost_error for an ACTIVE plan. These are runner measurements, not human feedback.

Test-first RED cases: cached=-5/prompt=10, cached=5/prompt=-1 and cached=True/prompt=9 must all produce reuse_ratio=None, no cache accumulator update and no cost signal. Valid cached=3/prompt=7 remains .3; zero/zero remains unavailable. Do not change the mode/authority, source, learning or native measurement protocol.

Fix: accept only exact nonnegative integers with positive sum, preserving otherwise current cost and warm behavior. Run actual Linux focused CI (including 363 Run78 tests) and official privacy scan; preserve RED/GREEN raw logs. No model inference or Redmi claim. Gates unchanged: STEP2 UTILITY_FAIL, B3 L1 FAIL, Body-JEPA UNAVAILABLE, jepa_weight=0, V13 INCOMPLETE.

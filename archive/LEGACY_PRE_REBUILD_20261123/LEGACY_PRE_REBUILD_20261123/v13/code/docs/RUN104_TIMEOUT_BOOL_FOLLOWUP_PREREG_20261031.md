# Run104 timeout Boolean guard follow-up — prereg before remote code, 2026-10-31

During isolated local preflight of the preregistered 21-case Run104 smoke, an additional adversarial `run_bounded(True, 'run104_c3_c5_exit')` case revealed that the existing `isinstance(True,int)` accepts a Boolean as a one-second timeout, launches the worker, and returned 124 after killing it. Local initial test `test_install_selftest_run104_20261031.py` **RED**: 4 tests, 1 failure, raw log preserved in the run's local scratch (not a native result). This was found **before any remote Run104 implementation commit**.

Narrow follow-up: replace only `isinstance(seconds,int)` with exact `type(seconds) is int` in `scripts/install_selftest.py`. Keep 1..120 integer semantics, default 120, worker process-group kill, and all original registered cohorts unchanged. Re-run original installer contract, original Run102 cohort contract, new Run104 4-case contract and extracted 21-case worker. No runtime/model/age/learning authority change.

Local candidate with exact type guard passed 4/4 Run104 contract and 21/21 actual bounded worker; this is exploratory local software preflight, **not** a substitute for independently captured GitHub Actions evidence. Preserve the original RED and no gate promotion.

# Run354 prereg — current exact-head complete Python source suite (2026-10-25)

Base: verified Run353 PR349 checkpoint `cdc10ed21aaff8a65db26f0b3ceca6de11fb53de` (review chain Run351→Run352→Run353, not main). Owner: only new workflow `.github/workflows/run354-fullsuite-current.yml` and this proof folder. No production source, registered model/seed, frozen tests, learning/age/approval or Canon edits.

## Problem and frozen acceptance
- Historical Run338 full suite reported 3009 tests, 2 failures and 39 errors (15 skips); substantial Run339–Run353 changes have landed on the review chain. A fresh exact-head complete test inventory is needed before choosing the next real failure, not just repeated focused PASS.
- Reuse Run338's verified isolated CPU-only dependency set and serialized CI group, pinned exact PR head checkout, immutable Canon SHA check, compileall, `python -m unittest discover -s tests -p 'test_*.py' -v` with 900-second timeout, raw stdout/stderr, source SHA, host, dependency versions, privacy scan and closed SHA manifest.
- Preserve every failed test and its traceback. Nonzero suite exit is an **observed failure**, not a reason to change or bypass gates. Do not claim whole-system readiness if this suite passes; no native/Redmi/thermal/energy/model quality evidence here.
- Before implementing a fix, identify the highest-priority reproducible current failure and preregister its negative controls. Do not silently remove frozen tests or retune the historical source/model/seed.
- No paid provisioning or concurrent heavy native/model execution. The existing serialized CI concurrency group is retained. If CI cannot provision pinned deps, record exact blocker and continue other independent work.

Next command on GitHub Actions: exact-head Run354 workflow triggered by its new review PR; artifact `RUN354_FULL_SUITE_RAW.log` plus `RUN354_SHA256SUMS.txt`.
# Run62 — §94.4 Sleep C trace decay idempotence

Base: Run61 prereg commit `7849f756fbf5da3f3bc7e279fd01c163c3f1a505`; independent branch. Owner does not edit Run61 history files or any registered LP3/native cohort.

**Reproduced production-code bug:** old `sleep_c` decays the same historical time interval on every call. With 10 elapsed days at 0.98/day, expected 0.8170728068875467 after two same-time ticks, but old code returns 0.6676079717550941. Original RED and reproducer are preserved.

**Patch:** new pure `sleep_trace_decay.py` validates and stages the whole batch, stores `trace_decay_at` in the existing per-item schedule, and applies only newly elapsed time. Repeated ticks at unchanged wall time are idempotent. Legacy records get a first watermark; previously over-decayed state is not silently repaired. A replay `last` timestamp supersedes older watermark; backwards clock never rewinds it. Priority floor never increases a trace. The production `SleepCycle.sleep_c` callsite now imports the helper. No facts, model weights, user permissions, age rights or original gates changed.

**Evidence:** 13/13 focused Python tests PASS; 13/13 Python -O PASS; 2000/2000 randomized algebraic checks PASS (fixed seed); compileall PASS. The first randomized review failed because it compared two slightly different floating-point timestamps as exactly equal; original RED retained, corrected review checks the exact stored watermark. Exact raw logs and executable scripts are in this directory.

**Not yet proved:** actual `SleepCycle` integration tests were authored but NOT RUN because this host cannot clone the complete repo (GitHub DNS resolution failure). Full suite, official privacy scanner, real native model, Redmi and sustained resource tests NOT RUN. The patch is a production-bound software candidate, not proof of learning utility or full V13 acceptance.

**Reproduce:** `cd v13/code && python -m unittest -v tests.test_sleep_trace_decay && python -O -m unittest -q tests.test_sleep_trace_decay && python -m unittest -v tests.test_sleep_trace_decay_integration`. The last command requires complete checkout. Independent review: `PYTHONPATH=. python docs/proofs/continuation-20261024/sleep-decay-run62/independent_review.py`.

**Exact next step:** independent full-checkout review of this production callsite and Store restart semantics; run official privacy scan and full suite. Then continue independent canonical packages, not native LP3 if cgroup delegation unavailable.

**Original gates unchanged:** STEP2 UTILITY_FAIL; B3 L1 FAIL; Body-JEPA UNAVAILABLE; `jepa_weight=0`; full V13 INCOMPLETE.

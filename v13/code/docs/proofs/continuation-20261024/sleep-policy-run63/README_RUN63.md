# Run63 — §94 Sleep replay policy finite validation and overflow-safe quotas

Base PR95 Run62 `845863efac747e87593a1dc663ac5b40f4746f6b`. Minimal existing `sleep.py` validation and sample-quota changes plus two new pure/helper and regression modules. No change to registered model/seed cohorts, Age rights, learning or facts.

**Original RED:** `validate_policy` accepted `mix.recent=NaN` because NaN comparisons never satisfy `v<0` or `sum<=0`; `ReplayQueue.sample` then failed in `int(NaN)`. The operator `set_policy` parses float strings, so this is reachable via `:sleep mix.recent nan`. Original failure and reproducer retained.

**Independent review RED:** even finite `mix.recent=1e308` passed validation, but `int(n*weight/total)` overflowed before division. Fixed by computing `n*(weight/total)`, preserving valid ratios without premature multiplication overflow. Non-finite entries, total overflow, malformed mappings and boolean quiet hours now fail closed. Existing valid defaults/ratios remain unchanged.

**Evidence:** 10 initial focused software tests PASS; 2 new review tests added; 12/12 focused tests PASS and 12/12 Python -O PASS, compileall PASS. Two actual `v13.sleep` integration tests authored but NOT RUN (complete checkout inaccessible). All original RED and test raw logs saved. Remote source/test Git blobs independently compared with locally tested originals.

**Not proved:** actual Store/SleepRuntime, complete repo tests, official privacy scan, native model, Redmi and long-run response utility NOT RUN. The patch is production-bound software code on a review branch, not merged or activated on the user's phone.

**Reproduce:** `cd v13/code && python -m unittest -v tests.test_sleep_policy_finite && python -O -m unittest -q tests.test_sleep_policy_finite && python -m unittest -v tests.test_sleep_policy_finite_integration`. The last command requires a complete checkout.

**Next:** independent full checkout test, official privacy scan and real Store policy setter/restart check. Continue canonical functionality while LP3 cgroup/Redmi blocked.

Gates unchanged: STEP2 UTILITY_FAIL, B3 L1 FAIL, Body-JEPA UNAVAILABLE, `jepa_weight=0`, full V13 INCOMPLETE.

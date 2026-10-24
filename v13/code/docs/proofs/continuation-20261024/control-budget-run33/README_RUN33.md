# V13 Run33 — WP-T14 Thin-Control-Fabric budget integrity review

Base PR68 `9677fd7c5f43dcddb62e8d75b0dc2d605e0fa18a`. Independent isolated candidate for JEF/C2 shared budget, no production edits. Original `control_budget.py` source reviewed from GitHub. Reproduced 6 adversarial RED (5 FAIL + 1 ERROR): arbitrary outside-home checkpoint file sizes counted, symlink escape counted, nonfinite/reordered stage marks treated as data, malformed metadata crashed, and NaN limit accepted. These are software controls, not observed real-world exploit.

Candidate confines checkpoint size inventory to non-symlink regular files under resolved `home/checkpoints`, counts each once, and explicitly states this is NOT cryptographic hash verification (existing registry must prove authenticity). Stage marks require finite, nonnegative, monotonic times in declared STAGES order; malformed metadata skipped. Budget caps must be finite and nonnegative; 0 remains unset. No new limits invented or benchmark gates promoted.

8/8 adversarial software tests PASS, compileall PASS. Original upstream test cases were inspected for API compatibility, but the original full suite and native Redmi control-budget measurements were not executed. Existing WP-T14 NO_LIMITS remains report-only until measured hardware caps.

Next: integrate on full checkout, run original `test_control_budget.py` and full suite, measure actual C2/JEF overhead and checkpoint resident memory on Redmi, register caps and thermal/energy proof. Preserve all original V13 acceptance criteria.

STEP2 UTILITY_FAIL, B3 L1 FAIL, Body-JEPA UNAVAILABLE, jepa_weight=0, full V13 INCOMPLETE. Rejected Drive destination unused.

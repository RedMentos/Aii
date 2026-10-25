# Run137 — selective Widget quote integration review

2026-10-25 UTC. Base Run136 PR167 `b97ea8d9ad519f32c0bbec70bba6660ad5c0c926`. Run127 upstream PR158 `088f08d6dcdb0c7ec8dcc4c1e28e78c11c7a380f`. Exact source precondition: latest installer blob `73c43485f929a81add056e0b0d0c8a3a0136cab0` equals Run127's original Run125 base. Imported verified Run127 installer blob `744ef9cbf20bb096eb8222c010d2bd28f8fe7ab2` and original test blob `fccc0f240fb521211baf35bb2774d2c7d74caf5c` without rewriting; independent remote fetch confirmed.

Local Linux shell RED: `HOME=... V13_HOME=".../it' s; echo INJECTED" bash KNOEPFE_EINRICHTEN.sh` returned installer 0 but generated `tasks/V13 Stillstand` had `bash -n` exit 2 (syntax error near `(`); did not create intended control file. After byte-exact Run127 fix, `bash -n` PASS and running the generated button created the literal requested `control/STILLSTAND` with permissions 0600. The injected-looking semicolon remained path data, not an executed command. Local 23/23 combined tests PASS (phone_halt + AGE0d + HX2 + Run136 fixtures). Initial attempt at 24 tests had 1 ERROR because `test_phone_startup_notice_run125` is absent from older Run130 source ZIP, not because of a test assertion; retained as failure.

CI separately checks official privacy, frozen Runtime blob `a691d27bd0772a4fa1f03d57ec90663237bf6825`, exact upstream file/test hashes and real Run127 Widget tests on current chain. No Android/Redmi hardware proof. No native model job; Run136 owns separate heavy C3 job.

Gates: STEP2 UTILITY_FAIL, B3 L1 FAIL, Body-JEPA UNAVAILABLE, jepa_weight=0, DS2 H2 FAIL, V13 INCOMPLETE. No full-system claim.

Next: build a fresh exact-head Termux source ZIP from Run137 after CI, extract independently and re-run stop-path tests; ask user for Redmi execution only when genuinely necessary. Do not use rejected Drive destination.

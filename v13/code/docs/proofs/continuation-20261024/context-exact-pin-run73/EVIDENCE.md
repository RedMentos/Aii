# Run73 closed real Linux Context OS evidence

Base Run72 PR105 `1ddcb357358d94632e806a2e303fa58f82a1544b`. Canon §§8.3–8.5 exact_recent_pin. Before fix, budget loop compressed and POINTERed exact-pinned RAW turns, yet applied ACTIVE plan. Real full-checkout GitHub Linux CI **52 tests, 4 expected FAIL** (run 40129458948/job 120977867215); raw log preserved. Four failures: pinned forms POINTER, impossible-budget ACTIVE incorrectly applied, single pinned oversize, numeric/code case.

Fix: budget compression/pointer restricted to unpinned turns; impossible planned char budget records `budget_unmet_fallback` and `exact_pin_budget_unmet`, returns legacy rather than applying Context OS plan, and does not seed an unapplied append transcript.

Independent existing-test review run 40129529920/job 120978139487: **69 tests, 1 FAIL** because the old ACTIVE operator-permission test used an impossible exact-pin budget. Its fixture was given a generous 8192-token context without weakening the authority assertion. Failure log preserved.

Final real full-checkout public Linux CI run **40129653728**, job **120978456310**: **70/70 PASS**, compileall PASS; official added-lines privacy scan `privacy scan 1ddcb3573..HEAD: CLEAN`. Raw RED/review/GREEN job logs committed as exact text. Test suites include Run68-73, Run64/65 and existing `tests.test_context_os`.

Evidence tier: actual Linux software/SQLite integration tests, not native model utility, Redmi, full suite or exact tokenizer proof. Open follow-up: SHADOW hypothetical transcript can be reused after switching to ACTIVE without actual prompt provenance; handle in Run74.

Gates unchanged: STEP2 UTILITY_FAIL; B3 L1 FAIL; Body-JEPA UNAVAILABLE; jepa_weight=0; V13 INCOMPLETE.

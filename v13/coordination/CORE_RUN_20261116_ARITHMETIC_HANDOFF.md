# Core work handoff — 2026-11-16 07:08 UTC

Owner: Core & Harness. Package: CORE-P0-EXACT-ARITH-20261116.
Review branch: `gpt6/core-exact-arithmetic-20261116`; PR #1998; parent release SHA `d9ffe1f3fb1646a3e7b7aa4e8e30f46e05267614`.
Touched: `v13/code/v13/exact_arithmetic.py`, `v13/code/v13/runtime.py`, `v13/code/tests/test_exact_arithmetic.py`. No competing owner edits on this branch.

Hypothesis: native C3's measured wrong answer for 2+2 can be avoided only for unambiguous two-operand arithmetic by an exact bounded local computation, while all other turns keep the B1/B2/C4/C3 architecture. Code routes through the existing Runtime turn action, output transaction, persistence, and source reference. It does not solve body offer delivery or learned native latent coupling.

Evidence: isolated Python arithmetic checks 11 inputs passed on Linux development container. This is NOT an integrated Runtime test, full repo CI, or Redmi test. Tests committed but CI status UNKNOWN. Negative B1/B2 TIME_BUDGET, STEP2/B3 FAIL and all Age gates unchanged.

Integration owner: Boss. Do not mark RELEASED or phone success until independent review, exact-head CI and actual installed Redmi receipt. No raw private transcript in this PR.

Next exact commands after checkout: `cd v13/code && PYTHONPATH=. python -m unittest tests.test_exact_arithmetic -v`; `python -m compileall -q v13`; run targeted Runtime SQLite end-to-end tests; inspect action lineage for exact arithmetic, plus deep query that still wakes B1/B2; run public_repo_privacy_scan.py against parent. If green, Boss integrates into release branch and obtains consented private phone proof. P0 #1904 remains open; whole Canon #1984 remains open.

Other unblocked work: native observer budget/prefill profiling, B1/B2 offer delivery, C4 synthesis, C3 correctness, real Android 20-turn gate; A/audio/vision, JEPA, weight updates, memory, self, sleep, permissioned Android control remain incomplete or unverified. Memorilla #1983 is separate additive draft.

Follow-up commit `e0da625804ca63c861261ef64d633de006f191d8`: adds Runtime/SQLite asynchronous submit-to-final regression (not yet executed; requires exact branch checkout/CI). Readback confirmed source and test blobs on GitHub. This does not change Android evidence or release state.

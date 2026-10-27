# WP-N7 current-event cache-cost at-most-once credit — 2026-10-27

**Review-only child of PR #721** (exact base `6150b2551a6cd4aefe9d2f499563985482a09c10`), not old `main`. Owner: `codex/automation11-n7-cache-observe-once-20261027`. Builds on PR #720's native cache-metric validation and PR #721's source-invalidation guards.

## Defect and fix

`ContextOS.observe` previously incremented aggregate cache-token counts and emitted an ACTIVE N10 cost signal every time the same valid metrics were submitted. It also credited a stale event after a newer plan for the same role, and a `CANCELLED` result. This creates nonphysical cost-learning evidence even with perfectly shaped native metrics.

The patch credits **only a valid FINAL observation matching the role's current plan**, and records `cache_recorded=True` atomically with the aggregate in the existing CAS state mutation. A duplicate, stale event or non-FINAL result gets no aggregate or modulator credit. Malformed metrics remain rejected as in PR #720; a malformed/non-FINAL attempt does not consume the receipt, so a later valid FINAL can still count. No unbounded new event ledger was added; older delayed observations fail closed. This is at-most-once aggregate credit, not a crash-atomic external modulator outbox guarantee.

## Tests and evidence

- New RED counterexamples: valid duplicate submitted twice (must remain one aggregate and one modulator signal), valid stale event after newer plan (must not count), and `CANCELLED` valid timings (must not count, later FINAL accepted).
- Test-only commit `92bd873dab359e711fbd4198c2efa5ed2f784a45`, Actions `40518457190` pending at checkpoint. Independent RED witness branch `codex/automation11-n7-cache-once-red-witness-20261027` at `172ea86e25251fdf4bd23d12c270018e22cb0005` is available if the original run is cancelled by GitHub's pending-job concurrency.
- Fix commit `cc6e7332591d6abe90cbef42d91f000b72d74e91`, Actions `40518505881` pending at checkpoint.
- Focused workflow `.github/workflows/n7-cache-observe-once.yml` runs `cd v13/code && PYTHONPATH=. python -m unittest -v tests.test_context_os`, compile, privacy scan, diff check. No models downloaded.
- **Do not claim RED/GREEN results until exact SHA CI logs are inspected.** Retain cancelled/failed attempts as observed.

## Verified RED / GREEN

- Independent RED witness Actions `40518545104`, exact source `172ea86e25251fdf4bd23d12c270018e22cb0005`: **26 tests, 3 expected FAIL**. Original code returned reuse ratios 0.3 for duplicate, 0.8 for stale event and 0.9 for CANCELLED; each failed the fail-closed assertion. Failed attempt preserved.
- GREEN Actions `40518505881`, exact source `cc6e7332591d6abe90cbef42d91f000b72d74e91`: **26/26 focused PASS**, compile PASS, privacy CLEAN, diff check PASS. No native model was loaded.
- Combined integration PR #724 / Actions `40518877350` remains a separate review gate. Parent N7 full suite `40518088127` was RED due to historical optional `/root/native/restore` PermissionError; do not misstate it as a green baseline.

## Limits / next step

Software-only cost-signal integrity; no native KV/cache benefit, no proof of global exactly-once across process crash between CAS and external modulator signal, no Redmi. `STEP2=UTILITY_FAIL`, `B3 L1=FAIL`, `BJ1=NO_SIGNAL`, registered `jepa_weight=0`, Age authority 0, whole V13 incomplete.

**Next:** verify RED/GREEN logs, independent review of state mutation and modulator behavior, then run broader software suite on this child if needed. Parent PR #721 broad suite Actions `40518088127` is independent and must be inspected before claiming broad regression success.

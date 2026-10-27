# Module lifecycle CAS — preregistered synthetic RED (2026-10-27)

Base: exact five-parent review integration PR #672, `9eae3cc175512382038cc5f55887e7a8dbc9797f` (tree `9ff3f1e7cbe6fe3508ccb38e2265c614e0a8463a`). This is **not** main, and not a frozen SourceHandoff cohort.

## Hypothesis / planned regression before source change

A concurrent user revoke, module disable, or Notaus arriving after the first state check can be lost during a later unconditional `StateBox.mutate`, or after a corpus snapshot was taken. Test with controlled SQLite callbacks; no real network, model or device. Success means:
- `propose` cannot record after a mid-call disable.
- `check` cannot revive a revoked quarantined module.
- `activate` cannot revive revoked/disabled modules or proceed under newly activated Notaus.
- `corpus` returns no stale module rows if revoke occurs during its file read.
- `export_dataset` does not write stale JSONL when revoke occurs immediately after corpus materialization.
- Existing happy-path, mid-fetch, export-ban and operator tests still pass.

Do not change frozen cohorts or runtime source pins; only adjacent `modules_gate.py`, `module_learn.py`, tests and scoped proof. Explicit residual: a cross-table Notaus/revoke in the tiny interval after the final validation but before filesystem `os.replace` cannot be made atomic with current StateBox/SQLite API; a stronger filesystem+policy transaction remains open.

## Original RED, preserved

Commit `b7706a33c67481cd91858876dbc7f270773f92bf` (test-only plus CI workflow), Actions `40465079891` (2026-10-27). **48 tests, 7 FAIL**: all seven newly preregistered race counterexamples; 41 existing tests PASS. CI exit1. Original raw artifact `12716372213`, ZIP SHA256 from Actions upload `c5e856ec4ef3d98552db7917fc67b041c5d55886b50ea97458db2dd9fa1f3a8c`. Source hashes and compile/privacy exits are captured inside artifact, not yet independently byte-audited. Do not rewrite this failure as success.

Next exact command (on candidate branch): `cd v13/code && PYTHONPATH="$PWD:$PWD/scripts" python -m unittest -v tests.test_module_lifecycle_cas tests.test_modules_gate tests.test_review666_module_halt_race tests.test_review666_bp11b_export_gate`.

Gates unchanged: STEP2 UTILITY_FAIL; B3 L1_FAIL; Body-JEPA UNAVAILABLE; `jepa_weight=0`; Redmi unmeasured; complete blueprint false. No module training gain or real module fetch claimed.

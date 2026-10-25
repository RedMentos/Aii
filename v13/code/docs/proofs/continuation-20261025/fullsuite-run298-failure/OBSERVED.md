# Full-suite failure observed on verified Run298 checkpoint (do not promote)

Observed UTC 2026-10-25 after Run300 scoped checkpoint. The existing `V13 Run255 current-chain full suite after source/Age/LP3 packages` workflow ran against Run298 head `3523fecea8d0b4c0bcacbd51fd70e9eebd2934f9`. Run ID `40202886433`, full-suite job `121198609390`, raw artifact `12602378950` (`V13-Run255-FullSuite-Raw-3523fecea8d0b4c0bcacbd51fd70e9eebd2934f9`). **2833 tests, 2 failures, 36 errors, 14 skipped; exit 1**. Privacy job succeeded. The failure is retained, not hidden by Run298 focused GREEN.

Observed primary clusters in raw job log:
- 36 errors, predominantly native firing candidate/merged smoke tests: `scripts/native_firing_runtime_candidate.py:sources()` raises `ValueError: Live sources differ from complete baseline/candidate`. The pinned candidate expects exact live source hashes and rejects current chain.
- `test_cancel_resident_cleanup_run284` fails: fake pool still lists PIDs `[284001,284002]` after cancellation, expected `[]`.
- `test_run177_native_chain_reconcile_20261025` fails: `v13/store.py` live SHA256 `4846be970c290629e395bfc8d1751d6b3deb7c1bb23aef06d58fc38293f561a5` differs from expected `fe66f92533b20738b5ec384e9d7c0b5ac8b4b4f658c6c1ad23792d813ff29980`.

These are **observed**, not yet proven pre-existing relative to Run298. None is a failing Run298-specific WorldModel test; focused Run298 test and related workflows passed. Do not alter frozen native candidate source or relax hashes to make the suite green. Root cause requires separate owner/registered cohort reconciliation; cancellation resident cleanup needs an independent operational proof and may require frozen Runtime changes. No STEP2, B3, native or whole-system gate promotion.

Next: independent owner should compare these failures against the previous registered full-suite baseline and either (a) fix real cancellation cleanup without overriding active owners or (b) re-register the native source chain explicitly with hash-checked candidate provenance, preserving the old negative artifact. Meanwhile continue unrelated canonical implementation.

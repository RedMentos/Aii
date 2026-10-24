# Run49 preregistration — closed offline cross-package integration runner for Runs42–48

Parent Run48 `0d055b96eeaa4fd9359749b130723227b0491b0f`; ownership exclusively `v13/code/docs/proofs/continuation-20261024/integration-run49/`. No modifications to frozen production runtime, canonical blueprint, existing PR packages, Age rights, native cohorts or acceptance gates.

Implement an offline, no-network integration runner that reconstructs Run42–48 from their persisted exact source/archive files, verifies pinned SHA256/Git blobs before executing, serializes all CPU/torch tests, and produces one closed JSON ledger with per-package exit code, test count, raw stdout/stderr log hashes, source identity, original negative gates and exact next command. Never invoke native model jobs or any paid service. Stop on integrity failure; on test failure preserve logs and continue only unrelated packages.

Predeclared checks: Run42 14 tests; Run43 14; Run44 8 plus negative synthetic cohort (must report FAIL_SYNTHETIC, not turn PASS); Run45 14; Run46 7 plus positive toy cohort (SYNTHETIC_ONLY); Run47 17; Run48 9 plus shadow/no-commit/revocation scenario. Exact counts are historical references and should be rechecked. Source artifacts and SHA256s must match known run checkpoints. The runner must reject archive path traversal and not write outside its isolated scratch directory. Test an intentionally corrupted archive as negative control and preserve raw error.

Full V13 status remains INCOMPLETE, STEP2 UTILITY_FAIL, B3 L1 FAIL, Body-JEPA UNAVAILABLE, jepa_weight=0. No claim of native/Redmi utility or actual full repo suite.

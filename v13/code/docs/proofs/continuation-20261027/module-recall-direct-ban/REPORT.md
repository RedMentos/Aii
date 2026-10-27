# Independent BP11b review: direct `:modul frage` must honor typed `module_recall` ban

**Base:** PR #675 exact checkpoint `99c6d4dd82a35d4df54e080e41586ee120353e25`, itself review-only child of PR #672 five-parent integration. No main merge, frozen cohort or Age/learning authority change.

**Confirmed bypass:** the ToolRegistry path for `module_recall` checks a typed `:verbot werkzeug module_recall`, but direct `module_learn.recall` and the `:modul frage` operator command used `M.corpus()` and skipped the tool-specific READ_LOCAL prohibition. A ban inserted during corpus file I/O could also leak the already-read result. A broad READ_LOCAL ban was bypassed as well. No network or model required.

**Preregistered RED:** test commit `683182da2e4a5d0adcfa2ab6c38b3d74cc0ced60`, workflow commit `5bda873ce2e17c82ae8e7d2beb9db957f16f8ea9`. Actions `40466019062`: **51 tests, 4 FAIL** (all four new bypass cases), 47 existing PASS, compile0, privacy CLEAN. Raw artifact `12716174443`, ZIP SHA256 `a09b3697b0f1c2c0dd127f5776e193301d2a4bc67983d2ccaa9340ef83b6730f`, CRC/HEAD/exits checked, private Library byte-identical.

**Fix:** `3fb6958ce4c4de4344a3662077fef86028736bc7`, `module_learn.py` only: fixed typed `module_recall`/READ_LOCAL gate before and after reading the corpus and before emitting hits. Empty hits on prohibition, no new tool rights. Actions `40466133397`: **51/51 PASS**, compile0, privacy CLEAN. Raw artifact `12715743761`, ZIP SHA256 `b482c8ad07deaeb4d4684f4d5278dc8d884f4de5ef32491f3feb099dd8803a70`, CRC/HEAD/exits checked, private backup byte-identical. Source SHA256: `module_learn.py` `a287571fec5661a0e09f28a6530e04daca466955df1ebe9b0ff7c296e75ed439`, `test_module_recall_direct_ban.py` `2a2b5d4c0f30c9dc4579f2cfe3136b37cca2c2db061ae405c9fa7355dafe48f7`.

**Residual:** no guarantee of strict cross-table linearizability if a ban is added after the final gate check; direct readers cannot roll back information already emitted. No semantic gain, module training, real fetch, native or Redmi proof. STEP2 UTILITY_FAIL, B3 L1 FAIL, Body-JEPA UNAVAILABLE, `jepa_weight=0`, complete V13 false.

**Next command:** `cd v13/code && PYTHONPATH="$PWD:$PWD/scripts" python -m unittest -v tests.test_module_recall_direct_ban tests.test_module_lifecycle_cas tests.test_modules_gate tests.test_review666_bp11b_export_gate`. Independently review source, compare broad suite after parent PR #675 differential, and run source-only phone package on combined head before production consideration. Original raw ZIPs: private `/V13-Checkpoints/2026-10-27/Module-Lifecycle-CAS/`.

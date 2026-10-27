# WP-BP2b independent adapter artifact integrity review · 2026-10-27

Owner: independent GPT-6 reviewer, review branch `assistant/v13-bp2b-adapter-integrity-20261027`, exact parent `4d6e468f3a8ca30668063e85d6d8c06eb8f24f7a` (native runner branch, **not** production main). File ownership: only `scripts/bp2b_native_runner.py`, `tests/test_bp2b_native_runner.py`, this proof folder, and a new branch-specific CI workflow. Do not edit the active owner branch.

## Counterexample and proposed guard

The source-bound native runner currently trusts `tr.fit()`'s returned `artifact` string and `hash` without independently opening the GGUF. A missing file, wrong digest, symlink, or artifact outside this attempt can yield `COMPLETED` with an unverified adapter digest. That weakens a model-learning evidence receipt, even if source and master preflight pass.

Before `predict`, verify the exact adapter bytes by streaming SHA256 and compare with returned 64-hex lowercase digest. Refuse nonregular/symlinked files and artifacts outside this attempt's trainer directory, including symlinked parents. Keep failed attempt receipt and no age promotion. The fake trainer used in tests must now create an actual tiny fake artifact, explicitly `SOFTWARE_FAKE_TEST`, to exercise the same boundary.

## Verification and negative controls

First commit counterexample tests (missing artifact, wrong digest, symlink and outside path) and record expected RED. Then implement minimal guard and record GREEN. Run the existing `tests.test_bp2b_native_runner` and `tests.test_bp2b_transfer_score` under branch-scoped Actions, compileall, and public-repo privacy scan against parent. Preserve original RED raw evidence; never describe fake tests as native. Verify remote commit SHA after each checkpoint.

No native model run or model download is authorized by this package. Existing seed/model/source hashes and the negative STEP2, B3, BJ1, jepa_weight, Redmi and full-scope gates remain unchanged. Next: independently review source/tokenizer TOCTOU and real Linux FP32 lifecycle only after checking heavy owner.

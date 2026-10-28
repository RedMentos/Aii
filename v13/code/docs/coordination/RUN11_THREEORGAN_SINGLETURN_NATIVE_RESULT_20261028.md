# Run11 current-catalog three-organ serial Linux native — verified checkpoint 2026-10-28

Owner: Codex; review-only PR #842 child of #841. Prereg `da4577b511e3210841285251f91a886b65d56998`, original script change `5fc63831f8f170ee24e46e91e3b8d5f5531e934d`; exact fixed protocol seed27, tokens4, context512, threads2, prompt `Hello.`, `--single-turn`, 1MiB bounded per-stream raw. Frozen current catalog/model manager/runner pins unchanged.

**Software:** 20/20 focused synthetic tests PASS, compile/privacy/diff0 on workflow `40631283470` at `87c9e7f1927130ffb3dd4e2491d8b3ee462d355c`; artifact 12791448383 ZIP SHA256 `19cdc05771514d1c19f5eee4728741f51bccf7c6b5d2aaac51bd3bde2ee3dd41`, CRC and 10/10 internal hashes verified. Prior RED CI failures retained (syntax, fixture shebang, prereg whitespace), fixed without changing frozen model/seed.

**Actual pinned three-role Linux native:** GitHub Actions `40631633470` at source `3cb42fb85797a401d716a5bdcd63d5ce12b0e2af`, SUCCESS. Artifact `12791324333` ZIP SHA256 `731401473b0f9c5bbbcf663ebcefc59b46cc875d7d0bdc18fd3389e6f80e7a92`, CRC valid, **34/34 internal SHA256SUMS verified**. All guards, native probe, report check, privacy, diff exit0. Three exact current-catalog models installed and SHA verified, runner source and binary tar verified. No model/binary uploaded.

- B1_DETAIL exact LFM2.5-1.2B SHA256 `bb741ebb106d543e9de114b843a3d3d73d51c74b5801e69da2abde821a0cb3e1`: native exit0, 1.119s native elapsed, stdout1051 bytes SHA256 `f2a06749b9d7da3b4c49e22a5f498cdc93331eab13379b99b308b625ee79fce9`, stderr0, generation marker true, no cap/timeout.
- B2_GIST distinct Qwen3.5-0.8B SHA256 `57d1997790d1744fba5b40a7317df71ea5e2acee28c47e78f0cce39c0703f8cf`: native exit0, 1.720s, stdout1074 bytes SHA256 `460222441b12b6fd4c6fef6de4127a4148c60d8d2fd3cb1f371962c73e10fe9c`, stderr0, generation marker true, no cap/timeout.
- C3_LANGUAGE LFM2.5-350M SHA256 `3d10b6ab8fc91a919534b9558e266255aca0bbc7f6d015963599aa9e74e05b1d`: native exit0, 0.517s, stdout1040 bytes SHA256 `fa627a5e390cdc2e74aac1868f196f055324a1d1d335bf250b5523dc508d6be9`, stderr0, generation marker true, no cap/timeout.
- Actual pinned llama-cli SHA256 `3acf625ff44f1dc28799e7e036519207b5564191d6243371bfae086b3911ed71`; `SMOKE_REPORT.json` `native_linux_load_decode=true`, `step2_gate_promoted=false`, `jepa_weight=0`, `redmi_proof=false`. cgroup_memory_limit_bytes=null (no explicit cgroup cap evidence); no RSS/thermal/energy claim.

**Full software suite inherited from parent source `ca1fbeaeb75597ded2ef71ec96977651513df173`: 2208 tests PASS, 1 skipped, artifact SHA256 `b2990af020faa1ed2e9e4cf587936e754bebc6143d2fe4314b7de6f8fa5d35d6`. The 3-role change itself has focused and native checks; a fresh full suite on the changed child source remains open.

## Next work

1. After this heavy job completes, run distinct pinned C2 Needle3 native control-call candidate PR #843 (separate source, no overlap); source/model/binary/schema exact pins, raw proof, no JEF authority.
2. Advance beyond load/decode to genuine JEF/C2 + B1/B2/C3 routing and STEP2 registered four-arm causal utility only with explicit source/fixture/seed/model/runner closure and exclusive owner. Existing STEP2 UTILITY_FAIL must not be promoted by these smokes.
3. Redmi Note 10 Pro native thermal/RSS/energy and long-term JEPA retention remain unmeasured.

Negative gates unchanged: STEP2 UTILITY_FAIL, B3 L1 FAIL, Body-JEPA UNAVAILABLE, LP3 heldout FAIL, jepa_weight=0, Age0 RECORD_ONLY; canonical_architecture_complete=false, user_full_scope_complete=false. No AGI claim. Remaining platform budget UNKNOWN.

Next focused command: `cd v13/code && PYTHONPATH=.:tests python3 -m unittest -v tests.test_step2_current_catalog_native_smoke_20261028 tests.test_native_smoke_io_20261028`.

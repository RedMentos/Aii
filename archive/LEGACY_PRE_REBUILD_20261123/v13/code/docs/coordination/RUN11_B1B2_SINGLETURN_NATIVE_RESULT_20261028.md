# Distinct B1/B2 current-catalog serial native Linux — verified checkpoint 2026-10-28

Owner: Codex; review-only PR #841 based on #840 `7b3347103e65e5f491a91aba8a84e1bc78818242`; prereg `e7f3ef2e7e0501e3b966b5ab207194fa8ef2baec` preceded native execution. Original #839 B1/B2 pin prereg remains unchanged. Neither parent owner branch nor main overwritten.

**Actual GitHub Actions Linux native** run `40630688094`, source `15565b34a8a24b5b9f6c7e6d1775f5eac50a1a4e`, SUCCESS. Artifact `12790857881` ZIP SHA256 `dcdf98d54b35f4300c6c1e8ffa0df3d06e8fcb6f5be27ab03683f463ce965d0b`, CRC valid and **19/19 internal SHA256SUMS verified**. Guards, native, report binding, privacy, diff all exit0. No GGUF/binary uploaded.

**B1_DETAIL:** exact LFM2.5-1.2B QAD GGUF 695755488 bytes, SHA256 `bb741ebb106d543e9de114b843a3d3d73d51c74b5801e69da2abde821a0cb3e1`, LFM Open License 1.0; actual Linux native exit0, 0.967s native elapsed excluding downloads, stdout 1022 bytes SHA256 `75d6a661c1681c63a77b82e2dbcbc7e0ae0acefed3e1951c0b80b209fda89d20`, stderr0, generation marker true, no timeout/cap, single-turn exits. Fixed prompt `Hello.`, 12 output tokens.

**B2_GIST:** byte-distinct Qwen3.5-0.8B GGUF 563036064 bytes, SHA256 `57d1997790d1744fba5b40a7317df71ea5e2acee28c47e78f0cce39c0703f8cf`, Apache-2.0; actual Linux native exit0, 1.418s excluding downloads, stdout 1058 bytes SHA256 `9e29f1c55ec1328b751f5beefd3b9feb09888bd86f80520f8ef4d021b85d8fdd`, stderr0, generation marker true, no timeout/cap. **B2's 12-token response was an unfinished thinking preamble, not a useful answer.** No semantic utility claim.

Shared official llama.cpp b10964 tar SHA256 `9abf88aea48a55d0f80edb1ee20220b186848cca0b4e919d71518cfd7ca67443`, extracted llama-cli SHA256 `3acf625ff44f1dc28799e7e036519207b5564191d6243371bfae086b3911ed71`; catalog Git blob `7af05962af41d0bc3f7dd18ef01d4eba55eabf99`, manager blob `bd035cf8029850cce00b179edf533e53bf24358a`. `serial_execution=true`, `models_distinct=true`, `native_all_pass=true` **only for Linux model-load/one-turn generation smoke**. C3 native prior run `40630449102` separately GREEN, not part of this B1/B2 job.

## Open next work

1. Run full Linux software regression at this exact review branch source; do not mistake 13 focused tests for whole-suite proof.
2. Independently review native output semantic limits and move to preregistered STEP2 four-arm native collector only after installing exact three current models and runner, source/fixture/seed closure, exclusive owner and resource preflight. Do not recycle historical frozen STEP2 cohort.
3. Address legacy `step2_current_catalog_native_smoke.py` default-interactive/unbounded capture path separately; this candidate does not silently modify it.
4. Redmi native device/thermal/RSS evidence still requires operator.

**Negative gates unchanged:** STEP2 UTILITY_FAIL, B3 L1 FAIL, Body-JEPA UNAVAILABLE, LP3 heldout FAIL, jepa_weight=0, Age0 RECORD_ONLY; canonical_architecture_complete=false, user_full_scope_complete=false. No JEF/C2, learning, causal complementarity or whole-system proof. Platform remaining budget UNKNOWN.

Next focused command: `cd v13/code && PYTHONPATH=.:tests python3 -m unittest -v tests.test_native_smoke_io_20261028 tests.test_current_b1b2_native_linux_smoke_20261028 tests.test_current_c3_native_linux_smoke_20261028`. Full: `cd v13/code && PYTHONPATH=.:tests python3 -m unittest discover -s tests -p 'test_*.py' -q`.

# Current catalog three-organ Linux native serial smoke — prereg 2026-10-28

Owner: Codex isolated review child of #841 at `ca1fbeaeb75597ded2ef71ec96977651513df173`. File ownership: `scripts/step2_current_catalog_native_smoke.py`, `tests/test_step2_current_catalog_native_smoke_20261028.py`, new CI and handoff. No edits to #840/#841 owner branches, main, frozen catalog, models, runner, or source hashes. The already pinned current-catalog model artifact/runner proofs remain authoritative; no model substitution.

## Problem and evidence

The legacy `step2_current_catalog_native_smoke.py` runs three current models B1_DETAIL, B2_GIST, C3_LANGUAGE serially but invokes pinned `llama-cli` without `--single-turn` and captures stdout/stderr with unbounded `subprocess.PIPE`. Exact C3 run #838 proved this default mode loops after answering: native exit124 and 962086943 stdout bytes (raw ZIP artifact 12790289704). Separate fixed one-turn C3 and distinct B1/B2 Linux native runs already verified GREEN on #840/#841, with hashes/CRC and private Library backup. This prereg extends the proven fix to the older three-role catalog smoke, not the STEP2 causal harness.

## Frozen protocol and acceptance

Preserve `ROLES=('B1_DETAIL','B2_GIST','C3_LANGUAGE')`, `SEED=27`, `TOKENS=4`, `CONTEXT=512`, `THREADS=2`, `PROMPT='Hello.'`, current catalog Git blob `7af05962af41d0bc3f7dd18ef01d4eba55eabf99`, runner b10964 tar SHA256 `9abf88aea48a55d0f80edb1ee20220b186848cca0b4e919d71518cfd7ca67443`, B1 `bb741ebb106d543e9de114b843a3d3d73d51c74b5801e69da2abde821a0cb3e1`, B2 `57d1997790d1744fba5b40a7317df71ea5e2acee28c47e78f0cce39c0703f8cf`, C3 `3d10b6ab8fc91a919534b9558e266255aca0bbc7f6d015963599aa9e74e05b1d`. Use `--single-turn` and shared bounded file-backed Linux native helper (1MiB per stream). Preserve legacy `<role>.stdout/.stderr/.json` evidence files, record cap and timeout, generation witness, raw bytes hashes, actual model and runner SHA; fail on any partial/timeout/cap/no generation. Version probe remains bounded by 30s, no heavy model.
 
Software focused tests and full-suite evidence precede native execution; no overlapping heavy native owner. Then isolated Linux runner with pinned public downloads and fresh scratch, B1->B2->C3 strictly serial; closed raw metadata/log artifact, CRC and internal SHA verification. Never upload GGUF or runner binary. Any native failure remains RED, no retry with changed protocol without new prereg.

This is **Linux-native three-model serial load/decode smoke only**. Not STEP2 four-arm utility, JEF/C2, JEPA learning, B3, Redmi, thermal/RSS or whole-system proof. STEP2 UTILITY_FAIL, B3 L1 FAIL, Body-JEPA UNAVAILABLE, LP3 heldout FAIL, jepa_weight=0, Age0 RECORD_ONLY remain unchanged. Remaining platform budget UNKNOWN.

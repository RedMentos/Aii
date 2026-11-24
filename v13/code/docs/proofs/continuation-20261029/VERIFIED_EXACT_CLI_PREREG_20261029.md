# V13 F1/F5 deterministic exact-source standalone CLI — preregistration (2026-10-29)

Parent review-only source: PR #1142, commit `4824f0c82e012959c5e16dfcc802079b1503f921`. Canon blob `218464b12a2d27d92524c751922fa8e1c3fb0ea7` unchanged. No production merge.

## Problem and intended contract

`scripts/ask_verified_budget.py` exposes `exact_source()` for the local TTY operator `:verified exact`, but its own `main()` only exposes preflight READY and explicitly opted-in native C3 generation. A user invoking the standalone script cannot request its deterministic source-exact answer. Implement explicit `--exact` CLI mode without making it default, without any native C3 call, without granting new learning/tool/age authority.

## Pre-registered software checks

1. On an existing Age-0 home with one live F1/F5 source `Project Elyra budget = 615 Euro`, `--exact` returns `FINAL_SOURCE_EXACT`, exactly `Project Elyra: 615 Euro.`, `native_calls=0`, `learned=false`, exit 0, and never invokes `RunnerPool.get`.
2. With no source or revoked source, `--exact` returns CLARIFY, never a factual answer, exit 0.
3. Existing CLI invocation without `--exact` stays READY only; no answer.
4. `--exact --native` is rejected by argparse as mutually exclusive before opening a home.
5. An invalid or nonexistent home is still rejected. Existing Stage-0, RECORD_ONLY, no-latents, jepa_weight0 and idle/paused checks are reused through `_preflight`.

Tests are committed before candidate source. A RED on parent is expected for missing `--exact` argument. Focused Python unittest on Linux is SOFTWARE evidence only. New mode is not native C3, not a learned German capability, not Redmi, not STEP2/B3/Body-JEPA/LP3 promotion. All negative gates remain unchanged.

## Evidence handling

Retain failed test output and exact source/test Git blobs in Actions artifact with SHA256SUMS, source head, compile/privacy/diff results. Verify remote bytes after write. Follow-up independent review must inspect actual output and not infer PASS from workflow existence.

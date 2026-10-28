# Run11 independent current-catalog GGUF + llama.cpp runner prerequisite byte audit — 2026-10-28

Review-only audit of existing parent PR #826 Actions, **not a new native run**. No model bytes or user data redistributed. The current parent model catalog Git blob is `7af05962af41d0bc3f7dd18ef01d4eba55eabf99`, model manager blob `bd035cf8029850cce00b179edf533e53bf24358a`.

## Existing actual byte evidence independently checked

GitHub Actions `40623200362` at `ac77c3ee9ddb1102e4dd8c046e256a88210c10f1` (artifact `12787808759`): downloaded pinned public GGUF files into ephemeral Linux scratch; all three SHA256 and GGUF magic checks true, exit 0. Raw ZIP SHA256 `597e33f6b13590b91862c6d70c5ec847b2cfcb3988a182f62434a4ff08a625e6`, CRC and all internal SHA256 verified.

- B1/body: `LiquidAI/LFM2.5-1.2B-Instruct-GGUF`, revision `6767265158422fb8a19c62ceb45f16f05363615b`, 695,755,488 bytes, SHA256 `bb741ebb106d543e9de114b843a3d3d73d51c74b5801e69da2abde821a0cb3e1`, declared license LFM Open License 1.0.
- B2/gist: `ggml-org/Qwen3.5-0.8B-GGUF`, revision `8fea620810c4afa23dd6443f999a48574c1611a3`, 563,036,064 bytes, SHA256 `57d1997790d1744fba5b40a7317df71ea5e2acee28c47e78f0cce39c0703f8cf`, declared license Apache-2.0.
- C3/language: `LiquidAI/LFM2.5-350M-GGUF`, revision `657e078c94084481950a2d555a941481f715536b`, 219,312,832 bytes, SHA256 `3d10b6ab8fc91a919534b9558e266255aca0bbc7f6d015963599aa9e74e05b1d`, declared license LFM Open License 1.0.
- Total verified GGUF bytes: **1,478,104,384**. This current catalog is distinct from older Age0 phone measurements; no cohort is silently substituted.

GitHub Actions `40623461284` at `28f425e210770d919bfc618552dc1921b4690a11` (artifact `12787868989`): pinned `llama.cpp` runner tag `b10964`, source revision `b29c606e2`; source archive 37,420,323 bytes SHA256 `4c96d72c40cefdacf621457d8a12fe5673b8de5b640ff7fe6d342ea1c579a9fe`; Linux binary archive 16,825,086 bytes SHA256 `9abf88aea48a55d0f80edb1ee20220b186848cca0b4e919d71518cfd7ca67443`; archive structures validated, exit 0. Raw ZIP SHA256 `9a9dd00d93dac13c0374af71ad4038962925476a54a7b609c4c5118436ef4092`, CRC/internal SHA256 verified. `executable_hash_verified=false` in this archive-only proof: no native executable or inference proof.

Private persistent Library backup (re-materialized byte-identical):
`/V13-Checkpoints/2026-10-28/Run11-STEP2-Native-Prereq-Independent-Audit/GGUF-BYTES-40623200362.zip`
and
`/V13-Checkpoints/2026-10-28/Run11-STEP2-Native-Prereq-Independent-Audit/RUNNER-ARCHIVES-40623461284.zip`.

## Next exact owner-dependent action and gates

The parent PR #826 has a **manual-only** workflow `.github/workflows/step2-current-catalog-linux-native-smoke-20261028.yml`, which pins the catalog and model-manager blobs, downloads the same artifacts, verifies runner, and serially calls `llama-cli` for B1/B2/C3 with bounded tokens/context. It was **not dispatched here**, and the archive proofs must not be called native inference. Run only with explicit workflow dispatch after owner/resource review; verify full raw output and report `LINUX_NATIVE_SMOKE_ONLY`. Then pursue separate preregistered four-arm semantic utility; the current smoke does not satisfy STEP2.

Remaining: Redmi hardware/thermal/energy and RSS/KV evidence, native 12-run four-arm source/runner closure, JEF/C3/B1/B2 learning utility, JEPA/B3 gates. STEP2 UTILITY_FAIL, B3 L1 FAIL, Body-JEPA UNAVAILABLE, jepa_weight=0, Age0 RECORD_ONLY. Do not promote gates from these byte checks.

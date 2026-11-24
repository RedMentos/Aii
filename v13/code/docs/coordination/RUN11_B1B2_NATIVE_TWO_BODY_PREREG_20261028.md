# Current-catalog distinct B1/B2 native Linux smoke — prereg 2026-10-28

Review-only child of #838 source `c0260321fb7a26c3c7e6cd867a1879fe7ce164a0`; prereg before implementation/model downloads. **Do not start heavy B1/B2 native run until C3 #838 native job completes**, to serialize heavy model jobs. No main merge or owner overwrite.

## Exact frozen public artifacts (catalog Git blob `7af05962af41d0bc3f7dd18ef01d4eba55eabf99`)
- B1_DETAIL: `LiquidAI/LFM2.5-1.2B-Instruct-GGUF`, upstream revision `6767265158422fb8a19c62ceb45f16f05363615b`, `LFM2.5-1.2B-Instruct-QAD-Q4_0.gguf`, **695755488 bytes**, SHA256 `bb741ebb106d543e9de114b843a3d3d73d51c74b5801e69da2abde821a0cb3e1`, LFM Open License 1.0.
- B2_GIST: `ggml-org/Qwen3.5-0.8B-GGUF`, upstream revision `8fea620810c4afa23dd6443f999a48574c1611a3`, `Qwen3.5-0.8B-Q4_0.gguf`, **563036064 bytes**, SHA256 `57d1997790d1744fba5b40a7317df71ea5e2acee28c47e78f0cce39c0703f8cf`, Apache-2.0.
- Runner: official llama.cpp b10964 Linux x86_64 release binary tar, **16825086 bytes**, SHA256 `9abf88aea48a55d0f80edb1ee20220b186848cca0b4e919d71518cfd7ca67443`; source tar pinned separately `4c96d72c40cefdacf621457d8a12fe5673b8de5b640ff7fe6d342ea1c579a9fe` (not downloaded here).
- B1/B2 must be byte-distinct and separately invoked; no same-model/shared-weight substitution.

## Native experiment and evidence
After #838 C3 job completes, isolated Ubuntu24.04 runner downloads exact B1, B2 and binary tar with existing verified downloader, safe-extracts official llama-cli, **runs B1 then B2 serially** on the same fixed public `Hello.` prompt, deterministic sampling, 12 output tokens, context <=256, 2 CPU threads, each <=180s. Verify exact bytes before and after, actual binary SHA, process exit, raw stdout/stderr, elapsed and role-specific result; archive **metadata/logs only**, never GGUF/binary. If either fails, record RED and do not promote.

This is distinct two-body **Linux native smoke**, not a 70-row STEP2 causal four-arm, not C2/JEF, B3, Body-JEPA, Redmi, semantic complementarity, trained weights, latency budget or whole-system acceptance. Negative gates unchanged: STEP2 UTILITY_FAIL, B3 L1 FAIL, Body-JEPA UNAVAILABLE, LP3 heldout FAIL, jepa_weight=0, Age0 RECORD_ONLY. Full four-arm experiment requires fresh prereg, exclusive owner, source/model/seed binding and native resource measurement.

# Run326 preregistration — isolate Run325 FP32 master byte mismatch (source unchanged)

UTC 2026-10-25. Independent owner: **only** new `.github/workflows/run326-fp32-master-parity.yml`, `v13/code/scripts/audit_fp32_master_parity_run326.py`, `v13/code/tests/test_fp32_master_parity_run326.py`, and this proof directory. Parent Run325 `9d893ab9d741c8ccbf913912b4992b8819d84ac7` / PR322. Do not edit the active Run320/325 workflow/evaluator, C++ trainer, runtime, Canon, registration, thresholds or any model source.

## Observed RED and falsifiable hypothesis

Run325 GitHub Actions run `40213614735`, job `121229918266` (2026-10-25T16:54:49Z) stopped **before optimizer**: official b10964 converter produced a 1.42 GB GGUF, but the Run325 full-byte SHA assertion against independently verified Run324 master `5d200c19f13483e66b39d9feb3353032581882f3eb10cc8752f027d4688d6e6f` failed. The later native/audit steps were skipped (reported successful as wrapper steps only); zero optimizer epochs, zero native evaluation. Original raw artifact `12607105983` and failed run must remain unchanged. The likely source of byte drift is that Run324 converted from `run324hf` while Run325 converted from `run325hf`, with a different tokenizer snapshot allowlist; GGUF metadata may embed local path/name. This is a **hypothesis**, not yet established.

## Frozen A/B diagnostic

Use the same public pinned HF `LiquidAI/LFM2.5-350M@9e6c6ccf47cd318696e137d381a7ded8fe4df09f`, original `model.safetensors` SHA256 `1c9c77a4471a7f590f85240f74ed1fc26df7fbde88c3006724e2f93ca993ea4e`, official `ggml-org/llama.cpp` b10964 source tar SHA256 `4c96d72c40cefdacf621457d8a12fe5673b8de5b640ff7fe6d342ea1c579a9fe`, unmodified converter SHA256 `e9a1da876330bbce9687541ab31736542a01b4ac43c6686126514a50f122fb7f`, and exact Run324 isolated Python versions. In a single serialized CI job, download snapshot once with **Run324's exact allow_patterns** and verify all original source bytes. Make a second directory with identical files (not symlinks). Convert both with identical official command, same `--outtype f32`, only snapshot directory name `run324hf` vs `run325hf` differing. The primary arm must reproduce original Run324 exact full-file SHA `5d200c...`; otherwise RED and no explanation. Compare full per-tensor payload SHA256, tensor names/shapes/types and GGUF metadata fields; classify only `METADATA_ONLY_DRIFT`, `TENSOR_DRIFT`, `NO_DRIFT` or `BASELINE_NOT_REPRODUCED`. Preserve actual hashes, original raw failures, dependency freeze and privacy, **no GGUF or weights in artifacts**.

A path-only A/B does not by itself prove the *additional* Run325 allowlist difference irrelevant; the exact Run325 recipe remains separately RED until its full conversion is repeated and verified. No optimizer or model activation in Run326. All original STEP2 UTILITY_FAIL, B3 L1 FAIL, Body-JEPA UNAVAILABLE, jepa_weight=0, Redmi MISSING, V13 INCOMPLETE remain. A successful diagnostic permits a separately reviewed exact-recipe correction; never silently change the frozen Run320 cohort, source/model/seed or selection criteria.

## Next command

Run `python -m unittest -v tests.test_fp32_master_parity_run326` from `v13/code`, then the new serialized CI. Independently inspect raw artifact and hashes before choosing the next authorized package.

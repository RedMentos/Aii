# Current-catalog C3 native Linux smoke — exact prereg 2026-10-28

Review-only independent native package based on #837 source `9da8df36dfe7a5bb79fadd252d344b979576da6d`. This prereg precedes implementation and download. No main merge, no Redmi or Age promotion.

## Frozen public artifacts
- Catalog `v13/code/specs/models.json` Git blob `7af05962af41d0bc3f7dd18ef01d4eba55eabf99`.
- Current C3 `LiquidAI/LFM2.5-350M-GGUF`, exact upstream revision `657e078c94084481950a2d555a941481f715536b`, `LFM2.5-350M-QAD-Q4_0.gguf`, **219312832 bytes**, SHA256 `3d10b6ab8fc91a919534b9558e266255aca0bbc7f6d015963599aa9e74e05b1d`, license **LFM Open License 1.0**.
- Official llama.cpp release `b10964` Linux x86_64 binary tar `llama-b10964-bin-ubuntu-x64.tar.gz`, **16825086 bytes**, SHA256 `9abf88aea48a55d0f80edb1ee20220b186848cca0b4e919d71518cfd7ca67443`. Source tar reference `b10964` SHA256 `4c96d72c40cefdacf621457d8a12fe5673b8de5b640ff7fe6d342ea1c579a9fe` (source bytes not downloaded by this minimal run).
- Official URLs only from pinned catalog; no arbitrary mirrors or changed cohorts.

## Native experiment
On one isolated Ubuntu 24.04 runner, **serially** download C3 and runner tar using existing `ModelManager.download_file` exact size/SHA checks; safe-extract release binary to scratch; hash actual `llama-cli`, run a fixed public prompt `Hello.` with 12 generated tokens, deterministic sampling, <=256 context, 2 CPU threads, bounded 180s timeout. Preserve full raw stdout/stderr, exit code, model/runner hashes, runtime architecture, binary SHA and source blob, metadata and report. Never upload model/binary weights. Refuse source drift, unsafe tar paths/symlinks, missing executable, wrong hash or nonzero native exit. Preserve failed attempt as RED rather than claiming native proof.

This is **current-catalog Linux native C3 smoke only**: not C2+C3 JEF, B1/B2 two-body, STEP2, Body-JEPA, Redmi, semantic quality, latency budget or whole-system acceptance. No model swap in production. Negative gates unchanged: STEP2 UTILITY_FAIL, B3 L1 FAIL, Body-JEPA UNAVAILABLE, LP3 heldout FAIL, jepa_weight=0, Age0 RECORD_ONLY. After this probe, separate preregistration and exclusive owner needed for full native four-arm experiment.

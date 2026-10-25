# Run160 bounded pinned GGUF prefix audit verified (not full model)

GitHub Actions run 40162947978, job 121078133532, exact head `99de3b9d8b9acfe8a75070fa5c098a849a2e8bb8`, 2026-10-25: **8/8 software tests PASS**, compileall PASS, official privacy `c282a8812..HEAD: CLEAN`. After preserved 8 MiB failure, follow-up 32 MiB prefix HTTP Range 206 succeeded for both pinned revisions.

B1 body (LiquidAI LFM2.5-1.2B, registered full size 695755488): **148 tensor descriptors** — 55 F32, 92 Q4_0, 1 Q6_K. B2 gist (ggml-org Qwen3.5-0.8B, registered full size 563036064): **320 descriptors** — 133 F32, 186 Q4_0, 1 Q8_0. Both prefix responses `bytes 0-33554431/<registered size>`. Closed raw JSON reports: artifact ID 12586903696, ZIP SHA-256 `ce0195eb59022d13a3a847f57bab34c929f218edba4fdba9c2036547365713e6`. Source/test Git blobs `c321c58864303f5d44afc1a542d27a65d0d15854` and `5d14e3a41a36cb2c107ad8b4ea14da41b8f5fa32`.

**Critical:** These are 32 MiB prefixes, not full model hashes or train masters. Tensor metadata suggests possible FP32 inference slices but does **not** prove native gradients, separate master, EMA, requantization, weight roundtrip, retention or runtime utility. Training authority 0; Body-JEPA UNAVAILABLE, jepa_weight 0 and all other original gates unchanged.

Workflow: https://github.com/RedMentos/Aii/actions/runs/40162947978

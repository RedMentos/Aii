# Distinct current B1/B2 pinned Linux native serial smoke — execution prereg 2026-10-28

Owner: Codex independent review child of #840, source `7b3347103e65e5f491a91aba8a84e1bc78818242`, no changes to #839 or #840 owners, no main merge. Prior B1/B2 exact pin prereg `a05e0e31258585b5e11205783b84c35dc9ab5b55` and script candidate remain intact. Prior C3 native heavy job 40630449102 completed SUCCESS, verified ZIP SHA256 `064425a7cf1184c145a83e0248c5b42fdcccf5cccc67b8716376d9338b8b8573`; no heavy native jobs were active at prereg.

## Frozen artifacts, no substitutions

B1_DETAIL LiquidAI/LFM2.5-1.2B-Instruct-GGUF revision `6767265158422fb8a19c62ceb45f16f05363615b`, 695755488 bytes SHA256 `bb741ebb106d543e9de114b843a3d3d73d51c74b5801e69da2abde821a0cb3e1`, LFM Open License 1.0. B2_GIST ggml-org/Qwen3.5-0.8B-GGUF revision `8fea620810c4afa23dd6443f999a48574c1611a3`, 563036064 bytes SHA256 `57d1997790d1744fba5b40a7317df71ea5e2acee28c47e78f0cce39c0703f8cf`, Apache-2.0. Official llama.cpp b10964 Linux-x86_64 tar 16825086 bytes SHA256 `9abf88aea48a55d0f80edb1ee20220b186848cca0b4e919d71518cfd7ca67443`. Catalog Git blob `7af05962af41d0bc3f7dd18ef01d4eba55eabf99`, model manager Git blob `bd035cf8029850cce00b179edf533e53bf24358a`. Never publish weights/binary.

## Procedure and falsifiers

Use fresh Ubuntu24.04 runner scratch >=3GiB free. Focused source/pin/bounded-I/O tests first. Download exact two GGUF and runner with existing pinned verified downloader; verify bytes and GGUF magic. Execute B1 then B2 strictly serial, each fixed `Hello.`, 12 output tokens, temp0, context256, 2 CPU threads, `--single-turn`, 180s process timeout, per-stream raw RLIMIT_FSIZE 1MiB. Close stdout/stderr raw and hashes, exit, timing, model identity for each; report `models_distinct=true`, `serial_execution=true`, `native_all_pass=true` only if both native subprocesses exit0 with real generation marker and no cap/timeout. Record RED with raw if any check fails; no partial success promoted. GitHub artifact contains metadata and fixed public prompt logs only. Use exact raw checksum/CRC and CI SHA256SUMS verification.

This is only **Linux-native distinct B1/B2 one-turn smoke**. No C2/JEF, C3 within this run, semantic complementarity, STEP2 70-row/four-arm, JEPA training, B3, Redmi, energy/thermal or whole-system gate. Negative gates remain STEP2 UTILITY_FAIL, B3 L1 FAIL, Body-JEPA UNAVAILABLE, LP3 heldout FAIL, jepa_weight=0, Age0 RECORD_ONLY.

## Next exact command

`PYTHONPATH=v13/code python3 v13/code/scripts/current_b1b2_native_linux_smoke_20261028.py --scratch-home <fresh-path> --evidence-dir <fresh-path>`

Before starting heavy job, check active owners; serialize. Remaining platform budget UNKNOWN.

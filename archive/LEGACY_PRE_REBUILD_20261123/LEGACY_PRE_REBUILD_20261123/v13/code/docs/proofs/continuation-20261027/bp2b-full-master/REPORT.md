# WP-BP2b exact official public full-master preflight — VERIFIED, 2026-10-27

**Scope:** source/provenance only, not a model-learning run. Review branch `assistant/v13-bp2b-full-master-preflight-20261027`, exact parent PR #710 `ac3a6294c316e58ba0e5f8ea1f1f1f5b1fc82b22`. Owner: GPT-6 independent reviewer. No runtime source, registered cohort, seed, optimizer, master hash or Age gate changed.

## Actual public bytes and independent verification

GitHub Actions `40505391672` ran at exact source commit `1baf024286fa1caaaead24e853b329543cf4e1fb`. Standard Ubuntu 24.04 runner downloaded from **official** `LiquidAI/LFM2.5-1.2B-Instruct` at exact Hugging Face revision `8c1348a4aac046a3a5d7698e7fcaaa8a3b7d9cdf`, license `LFM Open License 1.0`:

- `model.safetensors`: **2,340,697,936 bytes**, actual streamed SHA256 `1ba63d9adb03ae43581db0e136e4416febe0441aff7296397bd455fb6017f73a`, matching pinned model digest.
- Seven exact metadata/tokenizer/config/license files: all size/SHA256 checks match `v13/code/specs/bp2b_master_metadata.json`. Total isolated source directory **2,345,537,719 bytes**.
- `bp2b_master_preflight.py` returned **`FULL_FILE_HASH_PASS`**, `master_sha256_verified_locally=true`, `model_loaded=false`, `training_performed=false`, `learning_authority=0`.
- Download, verify, compile and privacy exits **0/0/0/0**, privacy scan CLEAN. No native model inference, training, adapter creation, Q4 or Redmi measurement.

## Raw evidence integrity and backup

Original raw GitHub Actions ZIP artifact ID `12734881225` (run `40505391672`), ZIP SHA256 **`2025a4b4d2f9794bff71e9f15f557d125586cb38a9f3c7b969a79f278aff8c30`**, independently rehashed after download; CRC PASS. It contains original download/preflight stdout/stderr, exact HEAD, pin/runner blob hashes, exit statuses and `PREFLIGHT.json`; **does not contain model weights or any private data**. Private backup: ChatGPT Library `/V13-Checkpoints/2026-10-27/BP2b-Full-Master-Preflight/bp2b-full-master-evidence-40505391672.zip`; re-materialized and byte-compared to original ZIP, PASS. Anyone-writable Drive was not used.

## Gate and next step

This establishes that the pinned public master and tokenizer bytes are reachable and verifiable on standard Linux CI. **It does not establish that the model loads, that FP32 training fits the memory/thermal budget, or that BP2b transfers/learns.** Model bytes remained ephemeral on that CI runner, not a durable cache for subsequent native jobs.

Next command in an isolated heavy owner-cleared Linux job after re-downloading exact bytes: `cd v13/code && PYTHONPATH=. python scripts/bp2b_native_runner.py --seed 41 --arm legacy --out <isolated-output> --master-dir <verified-master-dir> --attempt <unique-id> --execute-native`. First independently pin compatible Torch/Transformers/PEFT/GGUF versions and enforce a single CPU-heavy owner; do not run concurrent native arms. After a valid native arm, compare all 4 preregistered arms × 3 seeds, then separate Q4 and Redmi tests.

Negative gates remain `STEP2 UTILITY_FAIL`, `B3 L1 FAIL`, `BJ1_NO_SIGNAL`, `jepa_weight=0`, Redmi unmeasured, canonical and full V13 incomplete. No age, learning, route or tool authority promoted.

# WP-BP2b FP32 model/tokenizer provenance preflight prereg · 2026-10-27

Owner: automation11 BP2b master metadata, isolated review child of PR #707 exact `96973e070d91f5dfb456e0ae8166dfedc4ad6f15`. **Metadata only**: no model weights download, no native training, no quantization, no activation.

Public primary source: LiquidAI/LFM2.5-1.2B-Instruct (LFM Open License 1.0), pinned HF commit `8c1348a4aac046a3a5d7698e7fcaaa8a3b7d9cdf`. Official model.safetensors Xet SHA256 `1ba63d9adb03ae43581db0e136e4416febe0441aff7296397bd455fb6017f73a` matches earlier BP2a native master evidence, but tokenizer/config exact bytes have not been compared to Claude's historical directory; do not assert compatibility yet.

Prospective metadata-only files: `config.json`, `generation_config.json`, `tokenizer.json`, `tokenizer_config.json`, `special_tokens_map.json`, `chat_template.jinja`, `LICENSE`, all from the same exact pinned revision. Network download bounded to <16 MiB total, HTTP failure/empty file fails; record each SHA256, bytes, source URL, revision, license, runner commit, full raw stdout/stderr and privacy scan. A missing file or unreachable HF is a transient prereq, not a reason to stop independent blueprint work. Never download the 2.34GB master weights in this metadata job.

Acceptance: 7/7 pinned small artifacts downloaded, hashes/byte sizes durably recorded and independently checked, privacy CLEAN, no model weights fetched. Afterward freeze hashes in an explicit follow-up proof before running the 4-arm native BP2b experiment. Original cohorts, source/model/seed hashes and all negative gates unchanged. Exact next command after workflow: inspect the original GitHub Actions artifact, verify hashes, then write a source-bound metadata lock.

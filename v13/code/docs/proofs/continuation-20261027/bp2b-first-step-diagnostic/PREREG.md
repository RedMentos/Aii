# BP2b NEW first-step diagnostic preregistration — 2026-10-27

**New independent diagnostic cohort**, not an amendment to the original 12-arm × 3-seed BP2b transfer experiment or the failed seed41 legacy attempt. Parent review integration exact `5323f65e2b37144c81820a9a250e87c6add8fbc7`; script initial blob `1a1087a04ac5a81855f4255992fcb910e169acd4`. Owner `codex/automation11-bp2b-first-step-diagnostic-20261027`.

## Frozen reference and deliberate diagnostic change
- Reference: original `bp2b_native_runner.plan(41,'legacy')`, original selected source facts, anchor list, rank 8, alpha 16, learning rate 5e-4, 4 threads, anchor_weight 1, locality_swaps 2, `jepa_weight=0`, Age authority 0.
- Model: official `LiquidAI/LFM2.5-1.2B-Instruct` revision `8c1348a4aac046a3a5d7698e7fcaaa8a3b7d9cdf`, LFM Open License 1.0; FP32 `model.safetensors` SHA256 `1ba63d9adb03ae43581db0e136e4416febe0441aff7296397bd455fb6017f73a`, exact seven metadata hashes in `specs/bp2b_master_metadata.json`.
- **Only this new diagnostic** changes `max_steps=30,min_steps=30` to `max_steps=1,min_steps=1` and opts into `checkpoint_resume=True`. It stops deliberately immediately after the first completed optimizer+EMA checkpoint has been fsynced and hash-bound; no predictions, scoring, retention, adapter export or Age promotion.
- Source binding: exact full-master local preflight and immutable checkpoint source fingerprint include full model SHA, items, config, anchors and generation `bp2b-first-step-diagnostic`. The diagnostic cannot resume the original frozen arm's checkpoint directory.
- Measurement: time from `fit` invocation to first committed checkpoint **including model load, anchor generation and forward/backward**, sampled process RSS, source/env hashes, exit status and failure class. It does **not** separately time the optimizer kernel; no claimed 30-step throughput.

## Execution/stop gates
- Isolated Linux GitHub-hosted runner, one CPU-heavy owner at a time. Before execution verify no other native owner in progress. Require >=12GiB available and cgroup limit, pinned compatible CPU Torch/Transformers/PEFT, exact public source hash. No paid provisioning.
- Cap one diagnostic at 20 minutes and job at 35 minutes. Timeout or missing first-step pointer is **INCOMPLETE**, never a native PASS. Preserve original logs and failed attempts.
- Public artifact includes only `STARTED.json`, `RESULT.json` or `FAILED.json`, sampled RSS JSONL, environment/source logs and hashes. **Never upload optimizer tensors, model weights, adapter, full training state or private data.** Retain raw failed logs.
- Success is only `FIRST_STEP_COMMITTED` with a verified fsynced SHA pointer and bounded RSS/elapsed report. This is a diagnostic of feasibility, not a learning utility result. The old 35-minute attempt `40506115941` exited 124 and stays failed.

**Negative gates:** STEP2 UTILITY_FAIL, B3 L1 FAIL, BJ1 NO_SIGNAL, registered jepa_weight=0, Age authority 0, Redmi unmeasured, V13 incomplete.

**First prerequisite:** exact-head software tests and independent source review. Do not launch native before that gate; next command `cd v13/code && PYTHONPATH=. python -m unittest -v tests.test_bp2b_first_step_diagnostic`.

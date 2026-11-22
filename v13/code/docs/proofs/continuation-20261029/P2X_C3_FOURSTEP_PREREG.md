# P2X C3 QAD FP32 16-example × 4-step bounded receiver LoRA pilot — prereg (2026-10-29)

Owner GPT-6, independent default-off native-learning experiment, exact parent `39e104e409c86fcdec7fbb8076858fa85e9ad90a` (cross-organ review PR #1087). New experimental seed **2026102924**; not a replacement for frozen P2X/P0X model/source/seed registrations. No production AG6 activation.

## Frozen sources, license, and disjointness

Reuse exactly the public official LiquidAI QAD FP32 master files and SHA256 from `v13/code/scripts/p2x_c3_lora_pilot.py::MASTER_SHA`, the frozen P2X disjoint trainset export `FIXTURE_SHA=cd3edfdb464c6f99650b1ea32b5b09854268f0b53faa79df22ddcd135f21985a`, train SHA256 `af191c087d872a42924f2d2d465a3f26f6c323bf48c5c0682b30094b9d666cf1`, validation and answer hashes unchanged. No P0X or validation/calibration rows in fitting. Preserve official license/provenance, original negative native 360-call evidence and QAD inference GGUF baseline.

## Prospective exact bounded experiment

Select 16 source-disjoint training records, four each target A/B/NONE/UNKNOWN, with unique project IDs across targets; A/B/NONE require both exact B1+B2, UNKNOWN requires one missing or shuffled source. Deterministic sort by id/arm, no heldout inspection. Train only rank-2 `v_proj,out_proj` LoRA on frozen QAD FP32 master for exactly **4 optimizer steps**, each a full pass over all 16 records (64 forward/backward example visits); alpha4, lr0.0003, seed2026102924, threads2, max_tokens512, jepa_weight0, anchor_weight0, no weight merge, no live activation. Record per-step CE, base immutability, adapter GGUF/safetensors hashes, token lengths, RSS, wall time, source/model/seed binding. No synthetic/fake native proof.

## Prior feasibility and limits

Original independent one-step 8-example native [40853624892](https://github.com/RedMentos/Aii/actions/runs/40853624892) used ~33.86 s training, peak RSS 2280 MB, trainable 83,968 parameters, 44 GGUF adapter tensors, master recall .25. Original run's token-admission length counts were invalid; corrected tokenizer-only proof on PR #1075 must be reused. Extrapolating runtime is only a budget estimate, not evidence. Serialize this model job behind any active native owner and enforce resource admission ≥5GB free RAM/disk; preserve RED and stop safely on deadline.

## Acceptance

Prospective source-only tests before native; exact pinned workflow; 16 selected IDs and targets verified; actual token counts ≤512 and equal trainer encoding; four completed steps with finite CE and adapter hash/44 tensors; no base weight drift; all raw stages/CRC/SHA256SUMS/Privacy pass; independent replay audit and private byte-verified backup. Any failure remains RED; no retry with changed cohort/source/seed without a new prereg. **Even a GREEN four-step fit does not establish heldout source-use utility, deployed QAD GGUF adapter parity, JEPA learning, STEP2, B3, AG6, Redmi or V13 completion.** Those remain negative.

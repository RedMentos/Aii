# BP1 QAD V2 native LoRA default-scale binding — prospective fix (2026-10-27)

Owner: GPT-6 automation11. Independent child of PR #694 head `d6ccb20dde4d2bf5d87b8cbc31c91bec09fe425d`. Preregister before code/test edits. Frozen training `v13/code/v13/lora_trainer.py` blob `49a752879ae5d19391963742a0f042e740edb2cc`, 25-row train SHA `9f356917911983e887f80aaadd8b58365fe43ecbf6632bb5e9e0a1aa8628ff86`, 22 heldout SHA `7238a0220255cbccbcf1f9ccfad8dc03febfc37f7bc1d9d0aa645618f006508c`, QAD FP32/Q4, b10964 runner, seed13, 2-step rank2/alpha4, 1024 tokens, jepa_weight0 all unchanged.

## Original RED, closed before this patch

Native Actions `40488120145` exact head `6205378d9834ce3843db33e5145049f71014db91` FAILED. Original raw ZIP artifact `12728650326`, SHA256 `053ab766af541e3859950eb5ce0e7d59f67c61747f3e775c412bccd2ba38b7fa`; independently downloaded, CRC/HEAD/exits audited. TRAIN0, V2_MODEL0, V2_HELDOUT0, V2_ADAPTER_LOCATOR0; V2_EXIT1; `V2_BINDING_RAW.log` confirms strict source/proof binding; zero prediction rows. `V2_COLLECT_RAW.log`: `RuntimeError: QAD native LoRA adapter ID/path/default-scale mismatch` during GET /lora-adapters after server successfully loads real adapter. Original raw ZIP privately stored in Library `/V13-Checkpoints/2026-10-27/BP1-QAD-V2-Retry-40488120145/ORIGINAL-NATIVE-RED.zip`, re-materialized byte-exact SHA identical. Do not reclassify this RED as pass.

## Pinned primary-source hypothesis

llama.cpp pinned b10964 commit `b29c606e28a01b1bc8c1351026a0fa6e616bf6c4` (MIT): `common/arg.cpp` `--lora` registers scale `1.0`, while `--lora-scaled FNAME:SCALE` registers explicit scale; `common/common.cpp` `--lora-init-without-apply` skips initial application but does not mutate the declared scale; `tools/server/server-task.cpp` GET /lora-adapters reports that declared scale. Therefore the V2 collector's `--lora ... --lora-init-without-apply` plus strict GET default-scale==0 likely fails because GET returns 1.0. **Not yet independently observed HTTP JSON**; record as causal hypothesis, not verified root cause.

## Authorized minimal change and acceptance

Change only `scripts/bp1_qad_lora_eval.py` launch argument from `--lora <adapter>` to `--lora-scaled <adapter>:0`, preserving `--lora-init-without-apply` and strict GET ID/path/scale==0. Add adversarial tests that inspect actual argv and ensure default 1.0, wrong ID/path and malformed responses are still rejected. Software CI first, with raw exit and privacy evidence; preserve existing V2 tests. Separate explicit ACTIVATE_SCALE0 trigger on own review branch, only after no other heavy owner. Native result must show genuine 44 complete responses, independently audited raw, source/proof hashes and scoring before any utility claim. Preserve all failed runs and negative gates.

No production merge, adapter upload, STEP2/B3/Body-JEPA/Redmi/full V13 promotion. If native still fails, close and back up RED, then pursue other canonical work.

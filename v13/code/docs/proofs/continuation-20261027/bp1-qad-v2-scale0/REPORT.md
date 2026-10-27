# BP1 QAD V2 default-scale retry — pre-native checkpoint (2026-10-27)

Owner GPT-6 automation11, review PR #697, child of PR #694. Source before native activation: `5feca55f8cfb5519b741d7073b62cfdc2e8c2521`. Prereg `9816351005eae8998fc72e01d34fd8f01be6ae23` before source/test edits. All original 25 train rows, 22 heldout rows, QAD FP32/Q4, pinned b10964 runner, seed13, rank2/alpha4/2steps/1024, frozen trainer blob `49a752879ae5d19391963742a0f042e740edb2cc`, `jepa_weight=0` unchanged.

## Original RED preserved

Original native retry Actions [40488120145](https://github.com/RedMentos/Aii/actions/runs/40488120145) at `6205378d9834ce3843db33e5145049f71014db91` **FAILURE**. Original artifact `12728650326`, ZIP SHA256 `053ab766af541e3859950eb5ce0e7d59f67c61747f3e775c412bccd2ba38b7fa`, CRC PASS, 36 files, HEAD and exits independently audited. Train0, model0, heldout0, adapter-locator0, binding0; V2_EXIT1, 0 predictions. Native server loaded original trained LoRA but strict GET /lora-adapters ID/path/default-scale check failed. Raw GET JSON was not captured; upstream b10964 source supports the declared-scale=1 hypothesis, not yet verified as sole cause. Original ZIP privately backed up to Library `/V13-Checkpoints/2026-10-27/BP1-QAD-V2-Retry-40488120145/ORIGINAL-NATIVE-RED.zip`, re-materialized byte-identical.

## Fix and software evidence

`scripts/bp1_qad_lora_eval.py`: pass `--lora-scaled <adapter>:0` instead of `--lora <adapter>`, retain `--lora-init-without-apply`, strict ID/path/default-scale==0 and type checks. No source, frozen train, heldout, model, runner or permission changes. Tests reject boolean/wrong ID, wrong path, scale1, bool/string/missing scale. CI [40490183517](https://github.com/RedMentos/Aii/actions/runs/40490183517) at `940ae6d250a2e9a1b2040bdfcec5d5e3ef7ec959`: **42/42 software PASS**, compile0, privacy CLEAN, frozen trainer blob unchanged. Original ZIP artifact `12728746126` SHA256 `584336a064e51475602b9f06b86502ed55a39b94025e9bba46cfdd63669f72b5`, CRC/HEAD/exits audited; privately backed up and re-materialized byte-identical `/V13-Checkpoints/2026-10-27/BP1-QAD-V2-Scale0/ORIGINAL-GREEN-SOFTWARE-40490183517.zip`.

## Activation and next

Fresh branch-scoped `.github/workflows/bp1-qad-train-plus-v2-samejob.yml` has **only** `ACTIVATE_SCALE0.txt` as trigger and uses the unchanged global heavy serial group. GitHub Actions no in_progress/queued jobs at preactivation check. Next: create `v13/code/docs/proofs/continuation-20261027/bp1-qad-train-v2-samejob/ACTIVATE_SCALE0.txt` on this branch, run fresh native train+44-row paired heldout; audit original raw ZIP independently, preserve any failure, and score only if 44 unique source-bound responses complete. Native status currently NOT_ACTIVATED. No adapter weights to public artifacts. If RED, record and continue independent packages.

STEP2 UTILITY_FAIL, B3 L1_FAIL, Body-JEPA UNAVAILABLE, `jepa_weight=0`, Redmi unmeasured, whole V13 incomplete; production main unchanged.

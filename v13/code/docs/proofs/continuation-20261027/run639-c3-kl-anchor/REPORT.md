# Run639 — prospective KL-anchored selected C3 LoRA (review-only)

**Owner:** GPT-6, isolated Run639 training/evaluator/tests/workflows/proof files. Parent Run638 PR634 head `920c37d0436b536f4ed7c96570fc0dc6e3a14528`. Draft PR635; not integrated into main.

## Original verified negative and new hypothesis

Run638 actual 32-step FP32 selected C3 master LoRA achieved CE 0.00019 and master recall 2/2, but **selected deployed QAD-Q4 heldout 0/2, Cedar leakage 2/2, KL-to-base 5.8776**, bounded synthetic utility FAIL. Original Run637 2-step heldout 1/2, Cedar leak 0/2 but train 0/2. Run638 original native ZIP SHA256 `d295a534aee3bb541b31fdfe760df1ec0b355ec0dd5642abbb949b198707b65c`, CRC and 31/31 inner hashes PASS, private byte-verified backup; unanchored GGUF SHA256 `bd5fb8e523ba5444602401911d7fc8e0b2a571980cc95bf1a42f15c2bfb1cb83`.

Run639 prereg `a2e6edc75f4880694512951b8f1c723d26693e80` and cohort `ccec34634714b760b6cba6ce626536928f229ed3` **precede code/tests/native**. Treatment: same selected licensed model/deployed QAD-Q4, seed13, rank2/alpha4/v_proj/out_proj/lr .001, two Alder train facts, 2 heldout, 2 Cedar near misses, 32 steps, jepa_weight0. **Only new intervention:** existing `LoraTrainer` KL-to-base anchor_weight 1.0 on four disjoint arithmetic/farewell/Birch prompts, never frozen evaluation rows. Acceptance train >=1/2, heldout >=1/2, Cedar leakage 0/2, HF/native token, scale0 and original baseline parity, numeric LoRA effect; even PASS is bounded synthetic only.

## Source evidence, RED retained

First Run639 source Actions 40431632975 RED: 44 tests, 19 FAIL + 1 ERROR because source accidentally checked an old schema literal. First native Actions 40431676966 RED: source exit1, optimizer/native **not attempted**; raw preserved. Prospective technical amendment `fa61ac7a1cb848b40027dd6a1bb4662d86c5f700` was committed **before** the schema-only repair; frozen treatment/cohort/model/seed/acceptance untouched. RED source ZIP SHA256 `de57259880ce396732b44bfe4f50d2beb1512d6bf38ccd58a69e1c1212b23b2b`, CRC PASS; RED native ZIP SHA256 `ac7e5fa6090d9c16a475ac7100bee5ebe507c381f04c2b915c4e6aefaa199d65`, CRC and 23/23 inner SHA PASS. Both private Library byte-identical roundtrips under `/V13-Checkpoints/2026-10-27/Run639/`.

Repaired source Actions **40431786509 GREEN** on `7499c9b1ca9133b3de3a01cd9a39c12ed0254439`: **44/44** tests, Python compile, privacy CLEAN; ZIP SHA256 `093656bb999e66635b159da7817bf25a40eaa68fac8e0399d0be44186b0f0cc2`, CRC and 9/9 inner SHA PASS, private byte-identical Library backup.

## Native result and gates

**New native Actions 40431900872** on `3e69b7af4bb8f1bb20b38fa1eb303c3ca3686549`: in progress when this report was written. **No anchored learning or utility result claimed yet.** Exact selected model/license/Jinja/server and Run638 baseline artifacts must be re-fetched and hash-verified before any optimizer. Raw artifact, actual CE/KL/RSS/answer text, baseline reproducibility, CRC and private byte roundtrip remain pending.

Negative gates remain: STEP2 `UTILITY_FAIL`, B3 L1 `FAIL`, Body-JEPA `UNAVAILABLE`, `jepa_weight=0`, Redmi `UNMEASURED`, V13 `INCOMPLETE`; production_weight_authority=0, age/approval unchanged. No model activation.

**Next exact command:** inspect native Actions 40431900872, download complete raw ZIP, SHA256/CRC/inner manifest and original Run638 adapter/proof, measure anchored train/heldout/Cedar results; preserve RED if failed, private backup with byte roundtrip, update scoped BUILD_STATE/PR, then next independent canonical package. No post-result anchor-weight/prompt tuning in Run639.

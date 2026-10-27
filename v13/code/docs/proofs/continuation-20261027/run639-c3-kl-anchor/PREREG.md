# Run639 — prospective anchored selected C3 32-step LoRA, shadow-only (2026-10-27 UTC)

## Frozen motivation before new training
Run638 native Actions 40431064922 proved an actual 32-step FP32 master LoRA with CE 0.00019 and master recall 2/2, but selected deployed QAD-Q4 **heldout 0/2, Cedar near-miss leakage 2/2**, KL-to-base 5.8776; bounded utility FAIL. Original Run637 2-step LoRA: train 0/2, heldout 1/2, near-miss 0/2. The 32-step adapter, proof and original raw are immutable: Run638 ZIP SHA256 `d295a534aee3bb541b31fdfe760df1ec0b355ec0dd5642abbb949b198707b65c`, adapter GGUF SHA256 `bd5fb8e523ba5444602401911d7fc8e0b2a571980cc95bf1a42f15c2bfb1cb83`, native proof SHA256 `82b9073b9b955286c705b9ab506e49622c68745465b0a52b11213fdc9f72fd10`, training proof SHA256 `f49ea0206e717c85b1018ea62204bdc8e876519e9c4f404f4ca21e9bb16b6d2e`. Preserve these negative outcomes; do not edit Run638's registered cohort, source, model, or original artifacts.

## Independent prospective treatment
This new Run639 cohort is frozen *before* any Run639 implementation/tests/native job. Keep selected licensed LFM2.5-350M master revision `b6248156b66a93e5c4581d82953a9df630c582ef` SHA256 `1c9c77a4471a7f590f85240f74ed1fc26df7fbde88c3006724e2f93ca993ea4e`; deployed QAD-Q4 revision `657e078c94084481950a2d555a941481f715536b` SHA256 `3d10b6ab8fc91a919534b9558e266255aca0bbc7f6d015963599aa9e74e05b1d`; Jinja SHA256 `013eed60546434b6967e3483153d8c5c37abcb1d667f8b1f914683f2a9411531`; LFM Open License v1.0. Preserve original 2 Alder train facts, 2 heldout and 2 Cedar near-miss cases, seed13, rank2, alpha4, v_proj/out_proj, lr0.001, exactly 32 optimizer steps, jepa_weight0, locality_swaps0, all other Run638 settings.

Only new intervention: use existing canonical `LoraTrainer` **KL-to-base anchor_weight=1.0** (its unmodified default) on exactly four **distinct disjoint anchor prompts**, base-generated continuations, not target labels:
1. `What is three plus three?`
2. `Write a short farewell.`
3. `In the fictional Birch protocol, what is the marker color?`
4. `In the fictional Birch protocol, what is the gate number?`

These four are **not** any train, heldout or Cedar evaluation prompt. Never anchor on the frozen 2+2/greeting or Cedar evaluation rows. `anchors_per_step` retains trainer default 8, so all four are used per step. The Run638 comparison used anchor_weight=0, no anchors; no other hyperparameter change. This is one registered test of canonical KL anchoring, not adaptive search.

## Exact acceptance
1. Verify new cohort Git blob, original Run638/Run637 frozen sources and all selected master/model/seed/license hashes before optimizer. Source-only negative controls, privacy scan, no age/approval/production activation.
2. Exactly 32 native CPU steps on licensed FP32 master; record CE, anchor KL, heldout KL, LoRA-B nonzero, RSS/time and GGUF/PEFT hashes. No training on deployed Q4.
3. Same pinned llama.cpp b10964 selected QAD-Q4, official Jinja, HF/native token parity, base==scale0, original Run638 32-step text reproducibility, native LoRA effect; six frozen cases. Paired comparison **unanchored Run638 32-step vs anchored Run639 32-step**, plus original Run637 2-step historical acceptance floor.
4. Bounded synthetic anchored utility requires anchored **train >=1/2**, **heldout >=1/2** (original 2-step retention floor), **Cedar near-miss 0/2** (original 2-step nonleak floor), exact tokenizer/scale0/baseline reproducibility and numeric LoRA effect. Report all failures and original negative. This does not establish general semantic utility, B3, STEP2, Body-JEPA or Redmi.
5. No tuning/retries with altered anchor prompts or weight after results. A technical infrastructure repair needs a prospective amendment preserving the original RED raw.

## Operational constraints
Heavy native serialized via existing `v13-run628-single-native-c3` concurrency. Source and evidence artifacts closed with SHA256 manifest and original raw; private Library backup with byte roundtrip. No personal data, no paid provisioning. Negative gates immutable: STEP2 UTILITY_FAIL, B3 L1 FAIL, Body-JEPA UNAVAILABLE, jepa_weight0, Redmi unmeasured, V13 incomplete, production_weight_authority=0. Other organs remain required.

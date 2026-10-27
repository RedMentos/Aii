# Run638 — selected C3 32-step LoRA dose-response (review-only)

**Owner:** GPT-6, isolated files `run638_c3_dose_response.py`, `run638_c3_native_compare.py`, their tests/workflows and this scoped proof folder. Parent Run637 PR632 head `60077686e5dcadade6e7a1a08934b55aca3cd665`. Draft PR634; not main-integrated.

## Evidence and reason

Run635 2-step licensed FP32 master LoRA produced a real GGUF with nonzero LoRA-B and CE reduction but **0 learned master recall**. Run637 exact selected deployed QAD-Q4 native six-case test (Actions 40429819193) established HF/native tokenizer parity, exact base/scale0, nonzero scale1 logprob effects, **0/2 train hits, NO_ANSWER_UTILITY**. Original ZIP SHA256 `940ae9372309ee828869e40e8d416f1bea54b4426c5420d5a925bf50ef329ce0`; ZIP CRC PASS, 22/22 inner SHA PASS, privately saved with byte-identical roundtrip under `/V13-Checkpoints/2026-10-27/Run637/`. Original failure 40429549368 remains preserved; later repaired job does not erase it.

## Prospective new package

Prereg commit `b23b6162` and independent cohort commit `89523d4e` precede source code/tests/workflows. Cohort blob `94c8558de44069b4e3baa351b6ca74e5e9f4ec9c`. The **only training treatment difference** from original Run632 V2 is exactly 32 instead of 2 optimizer steps. Identical two Alder train facts, two heldout facts, two Cedar near misses, selected master/deployed model SHA, seed13, rank2, alpha4, v_proj/out_proj, lr 0.001, no JEPA or anchors. No original source/model/seed/cohort/adapter hash is modified.

New source candidate checks cohort/license/master/deployed identities before any optimizer, requires 32 actual steps, finite CE/KL/RSS/time and nonzero LoRA-B, exports GGUF/PEFT and negative-gate-bound proof. Paired native evaluator re-fetches original Run635 adapter and Run637 native proof by immutable artifact ZIP/SHA, loads exact original llama.cpp b10964 and QAD-Q4, compares base/original-2step/new-32step on the same six official-Jinja prompts, including HF/native token IDs, base/scale0 equality, baseline text reproducibility, train/heldout/near-miss and numeric effects. A bounded synthetic gain requires train > original with retention/locality and parity. Even that would **not** establish general semantic utility, Body-JEPA or STEP2.

**Source-only Actions 40430961589 GREEN** (exact source `6bed39909d9ee1d16277ade4e3f79938b1f9ca63`): 43/43 tests, Python compile, public-repo privacy CLEAN; original ZIP SHA256 `0d778b62e9571c3b9f9708a3fb148dbdc9ecab2cf9cc68cb7f70edf6a497e2f5`, CRC PASS, 9/9 internal SHA PASS, private Library backup `/V13-Checkpoints/2026-10-27/Run638/`. Earlier 25/25 source pass separately retained.

**Native Actions 40431064922 completed GREEN as execution, but NEGATIVE for bounded utility** on exact head `d6d97601d75ccaee05da96278549651edd3bb43d`. Artifact `12702091198`, original ZIP SHA256 `d295a534aee3bb541b31fdfe760df1ec0b355ec0dd5642abbb949b198707b65c`, CRC PASS, 31/31 inner SHA PASS, private Library byte-identical backup. 43/43 source tests and privacy CLEAN. Train proof SHA256 `f49ea0206e717c85b1018ea62204bdc8e876519e9c4f404f4ca21e9bb16b6d2e`; deployed native proof SHA256 `82b9073b9b955286c705b9ab506e49622c68745465b0a52b11213fdc9f72fd10`; new LoRA GGUF SHA256 `bd5fb8e523ba5444602401911d7fc8e0b2a571980cc95bf1a42f15c2bfb1cb83`.

**Actual observed:** 32 CPU steps, CE 0.00019, FP32 master learned recall 1.0 (2/2), heldout KL-to-base **5.8776**, 30.85 seconds and 2420.8 MB peak RSS. On exact selected QAD-Q4, original 2-step vs new 32-step: **train 0/2 → 2/2** (Alder answers `violet`, `83`), **heldout 1/2 → 0/2** (2+2 answered `83`; greeting `violet83`), **Cedar near-miss leakage 0/2 → 2/2** (both learned Alder answers copied to Cedar). Original baseline reproduced exactly, tokenizer/scale0 parity PASS, numeric LoRA effect PASS. **Bounded synthetic utility FAIL** due retention and locality. This is concrete catastrophic overfitting, not successful usable learning; the original 2-step and new 32-step failures remain intact.

## Gates and handoff

STEP2 `UTILITY_FAIL`; B3 L1 `FAIL`; Body-JEPA `UNAVAILABLE`; `jepa_weight=0`; Redmi `UNMEASURED`; V13 `INCOMPLETE`; production weight authority 0. Age, user approvals and other organs unchanged. No main merge or model activation.

**Next exact command:** preregister an independent anchored/locality-controlled C3 learning cohort, using disjoint KL-to-base anchor prompts (not frozen heldout or Cedar near-miss evaluation rows) and existing canonical LoraTrainer regularization; preserve Run638's negative utility as a fixed comparator. Continue with source-only tests, exact native QAD-Q4 utility, raw SHA/CRC and private backup. No retroactive Run638 hyperparameter tuning.

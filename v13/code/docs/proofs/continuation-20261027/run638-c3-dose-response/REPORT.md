# Run638 — selected C3 32-step LoRA dose-response (review-only)

**Owner:** GPT-6, isolated files `run638_c3_dose_response.py`, `run638_c3_native_compare.py`, their tests/workflows and this scoped proof folder. Parent Run637 PR632 head `60077686e5dcadade6e7a1a08934b55aca3cd665`. Draft PR634; not main-integrated.

## Evidence and reason

Run635 2-step licensed FP32 master LoRA produced a real GGUF with nonzero LoRA-B and CE reduction but **0 learned master recall**. Run637 exact selected deployed QAD-Q4 native six-case test (Actions 40429819193) established HF/native tokenizer parity, exact base/scale0, nonzero scale1 logprob effects, **0/2 train hits, NO_ANSWER_UTILITY**. Original ZIP SHA256 `940ae9372309ee828869e40e8d416f1bea54b4426c5420d5a925bf50ef329ce0`; ZIP CRC PASS, 22/22 inner SHA PASS, privately saved with byte-identical roundtrip under `/V13-Checkpoints/2026-10-27/Run637/`. Original failure 40429549368 remains preserved; later repaired job does not erase it.

## Prospective new package

Prereg commit `b23b6162` and independent cohort commit `89523d4e` precede source code/tests/workflows. Cohort blob `94c8558de44069b4e3baa351b6ca74e5e9f4ec9c`. The **only training treatment difference** from original Run632 V2 is exactly 32 instead of 2 optimizer steps. Identical two Alder train facts, two heldout facts, two Cedar near misses, selected master/deployed model SHA, seed13, rank2, alpha4, v_proj/out_proj, lr 0.001, no JEPA or anchors. No original source/model/seed/cohort/adapter hash is modified.

New source candidate checks cohort/license/master/deployed identities before any optimizer, requires 32 actual steps, finite CE/KL/RSS/time and nonzero LoRA-B, exports GGUF/PEFT and negative-gate-bound proof. Paired native evaluator re-fetches original Run635 adapter and Run637 native proof by immutable artifact ZIP/SHA, loads exact original llama.cpp b10964 and QAD-Q4, compares base/original-2step/new-32step on the same six official-Jinja prompts, including HF/native token IDs, base/scale0 equality, baseline text reproducibility, train/heldout/near-miss and numeric effects. A bounded synthetic gain requires train > original with retention/locality and parity. Even that would **not** establish general semantic utility, Body-JEPA or STEP2.

**Source-only Actions 40430961589 GREEN** (exact source `6bed39909d9ee1d16277ade4e3f79938b1f9ca63`): 43/43 tests, Python compile, public-repo privacy CLEAN; original ZIP SHA256 `0d778b62e9571c3b9f9708a3fb148dbdc9ecab2cf9cc68cb7f70edf6a497e2f5`, CRC PASS, 9/9 internal SHA PASS, private Library backup `/V13-Checkpoints/2026-10-27/Run638/`. Earlier 25/25 source pass separately retained.

**Native Actions 40431064922**: in progress when this report was written. **No 32-step learning/utility outcome is claimed yet.** Inspect raw and update report only after verifying the exact run.

## Gates and handoff

STEP2 `UTILITY_FAIL`; B3 L1 `FAIL`; Body-JEPA `UNAVAILABLE`; `jepa_weight=0`; Redmi `UNMEASURED`; V13 `INCOMPLETE`; production weight authority 0. Age, user approvals and other organs unchanged. No main merge or model activation.

**Next exact command:** inspect Actions run 40431064922 and artifact, SHA/CRC/inner manifest, check pinned master/Jinja/license/model/server/original adapter, compare native metrics, back up raw privately with byte roundtrip, update scoped BUILD_STATE/REPORT/PR, then immediately continue the next independent canonical package. No new unregistered hyperparameter search.

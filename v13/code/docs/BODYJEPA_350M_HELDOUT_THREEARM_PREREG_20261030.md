# Body-JEPA 350M three-arm held-out utility/retention ablation prereg — 2026-10-30

Review-only branch `assistant/v13-bodyjepa-350m-heldout-threearm-20261030`, child of #1223 at `be26f5176a55180be0f9086868a9c4a1c2a5889c`. This prereg is committed **before** the new synthetic cohort or ablation code. Do not modify historical Body-JEPA gradient source `bodyjepa_real_master_gradient_20261030.py`, prior seed73, models, objectives, Canon, source hashes or negative gates.

## Motivation / prior evidence
Original Actions `40978418273`, verified 350M FP32 real-master LoRA/EMA/predictor one-step mechanism, master SHA256 `1c9c77a4471a7f590f85240f74ed1fc26df7fbde88c3006724e2f93ca993ea4e`, revision `120bf032c36dd1273de754669da040dba7ad4982`, model `LiquidAI/LFM2.5-350M`, license LFM Open License 1.0. That run proves **gradient flow only**, not heldout benefit or retention. Its original RED attempts remain preserved.

## Frozen new study
- Seed **101**, exactly **8 invented train facts** with distinct source IDs, eight disjoint *paraphrase* evaluation questions referring to the same facts (never trained), eight near-miss entity prompts (never trained) and eight generic retention anchors. Source text and target answers fixed in a JSON fixture committed before any training script.
- Three arms on the **same pinned FP32 master**, sequentially isolated and same LoRA architecture (rank2, alpha4, dropout0, target modules w1/w2/w3), same initialized adapter/predictor seed101, same SGD learning rate **0.001**, same **4 full-batch update steps** and exactly eight training facts per step:
  1. `CE_ONLY`: answer-only cross-entropy.
  2. `CE_EMA_JEPA`: same CE plus JEPA cosine loss, weight **0.2**, with EMA adapter targets, stop-gradient and momentum **0.9**.
  3. `CE_SHUFFLED_JEPA`: same CE plus weight0.2 JEPA with a fixed cyclic derangement of target rows, same EMA mechanism. Shuffled is a negative control, never a positive learning label.
- All arms measure: exact token-level heldout paraphrase CE, train CE, near-miss and retention KL(base||candidate), trainable adapter delta, frozen parameter SHA256 before/after, gradient/EMA integrity, source/target alignment, finite loss, actual native process and memory. No adapter is exported/activated or used by llama.cpp. No live user data.
- **Candidate utility signal only** iff all arms complete, frozen base hash identical, each LoRA delta >0, all metrics finite, CE_EMA_JEPA heldout CE at least **0.02 lower** than CE_ONLY and at least **0.02 lower** than CE_SHUFFLED_JEPA, and both near-miss and retention KL of CE_EMA_JEPA are <=0.05. Otherwise `HELDOUT_BENEFIT_NOT_PROVEN` or `PILOT_PARTIAL_RED`. Report exact values, not only pass/fail. This tiny author-visible invented cohort is not statistically powered, independently blinded or sufficient for B1/B2 1.2B, Android or whole-system claims.
- Frozen Torch/Transformers/PEFT versions, master/source/license/fixture hashes and raw artifact closure required before native launch. Never change thresholds, fixture, seed or training steps after seeing results. If native dependencies/model are unavailable, resolve pinned public artifacts in isolated env rather than treating a fresh scratch directory as a final blocker.
- Run native heavy work only in `v13-step2-budget-paired-native-20261030` concurrency group, serialize with other owners, preserve all original failures, no paid provisioning or live training permission.

Age0 RECORD_ONLY; STEP2 UTILITY_FAIL; B3 NO_PROMOTION; Body-JEPA UNAVAILABLE; runtime jepa_weight=0; Redmi UNMEASURED; whole V13 INCOMPLETE. Next: freeze cohort JSON, implement isolated scorer and synthetic gradient tests, source-only preflight, then one explicitly marked native run. Platform remaining budget UNKNOWN.

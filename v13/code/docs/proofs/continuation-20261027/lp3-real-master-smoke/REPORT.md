# WP-LP3 real C3 HF master compatibility smoke — 2026-10-27

**New preregistered diagnostic**, review-only child of PR #727 exact `158e2546e9de93a117ca43a50b94d3adf670c07b`. Preregistration committed first at `35687ffe3c838962ad3f5a0cd6e85c6a140151d1`, clarified **before execution** at `ed0478b5eb7cd29525198bd7b6bef3d285fb4cd9`. No changes to LP1/LP2/BP2b registered experiments.

`scripts/lp3_real_master_smoke.py` verifies official pinned `LiquidAI/LFM2.5-350M` HF master revision `120bf032c36dd1273de754669da040dba7ad4982`, `model.safetensors` SHA256 `1c9c77a4471a7f590f85240f74ed1fc26df7fbde88c3006724e2f93ca993ea4e` (matches LP2 source). License LFM Open License 1.0. Isolated Linux CPU runner downloads pinned public source, checks full SHA, freezes model, extracts prompt-only features, checks own/shift/zero soft-prefix logits and target-free next-token effects, performs one predictor/projector AdamW step on first-answer-token CE, checks frozen-base sample and generates 2 target-free tokens. All data are synthetic. Raw logs/exit receipts are preserved without model/optimizer bytes.

New `tests/test_lp3_real_master_smoke.py` has three no-model source preflight/CLI tests. Workflow `.github/workflows/lp3-real-master-smoke.yml` runs those plus 12 inherited synthetic mechanism tests, then one real HF master compatibility smoke, with explicit timeout failure. **At report creation native CI is queued; no real-model PASS claimed.** A successful one-step gradient and logits test is not evidence of useful memory learning, LP2 heldout gain, B1/B2 transfer, JEPA or Redmi performance.

**Next:** inspect exact Actions run and raw artifact, independently audit model SHA/receipt, repair any genuine compatibility failure on an isolated child while retaining original failure; only then preregister a matched CE/own/shift LP3 heldout utility cohort. No overlapping heavy native jobs.

Unchanged: LP1 NO_ATTRIBUTABLE_GAIN; LP2 ALIGNS_NO_GAIN; BJ1 NO_SIGNAL; STEP2 UTILITY_FAIL; B3 L1 FAIL; `jepa_weight=0`, Age authority 0, Redmi unmeasured, V13 incomplete.

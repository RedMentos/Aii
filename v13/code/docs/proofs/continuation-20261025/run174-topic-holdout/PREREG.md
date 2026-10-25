# Run174 prospective prereg — larger B1 temporal shadow, topic-disjoint test

Created 2026-10-25 before any Run174 native execution. Base Run173 PR203 head `9b5608f0f7c027e8755b8a0988ec084b2337cc53`. Owner only new Run174 script/test/workflow/proof. No Runtime/Canon/registered model/old cohort edits. Age 0 remains RECORD_ONLY, this candidate is external SHADOW only.

**Reason for new experiment:** Run171 completed 86 real B1 t→t+2 pairs but predictor was worse than copy and shuffled controls (`predictive_ablation_pass=False`, `commit_eligible=False`). Do not tune or rerun on its exposed four heldout source groups. The I-JEPA primary paper (Assran et al., arXiv:2301.08243) emphasizes informative context and substantial targets; Run171's small 65-pair training split is a limitation, not proof of a JEPA gain. Run174 independently pre-registers more source groups and a **second fixed-target evaluation**, without changing the existing predictor worker.

## Locked cohort and scoring

- B1 frozen registered `LiquidAI/LFM2.5-1.2B-Instruct-GGUF` revision `6767265158422fb8a19c62ceb45f16f05363615b`, size 695755488, SHA-256 `bb741ebb106d543e9de114b843a3d3d73d51c74b5801e69da2abde821a0cb3e1`; pinned llama.cpp b10964 archive SHA-256 `9abf88aea48a55d0f80edb1ee20220b186848cca0b4e919d71518cfd7ca67443`.
- 20 fixed synthetic English **topics**, six distinct text variants each, total 120 texts, ordered topic-major. Canonical `json.dumps(TEXTS,separators=(',',':'),ensure_ascii=False)` SHA-256 `e8f65406ed05090581f0a23471e9403c569b246621517f85988533e521078e43`. Native B1 read-only `lfm2.result_norm.final.v1` 2048D tap, max 64 tokens, token positions `i=3,6,9,...<n-2`, predict `i+2`. One runner, sequential.
- Source-group unit is **topic**, not near-duplicate text. First 17 topics train+dev; frozen `v13.predictor_worker.train` uses its existing last-quarter heldout split: first 13 train, next four development. **Final topics 17,18,19 are untouched by fitting or selection**. No hyperparameter search or seed cherry-picking.
- Existing predictor config: `seed=17425`, defaults from `KNOBS[k][0]` for predictor_lr/ema_decay/max_update_norm/retention_max_delta/predictor_steps, regularizer EMA. Trainable external projector/predictor, frozen B1, slow EMA target. No body parameter update.
- Independent final test: score prediction against **frozen initial target/anchor**, not only moving EMA target. Precommitted threshold `prediction_fixed_target_mse < 0.98 * min(copy_fixed_target_mse, shuffled_fixed_target_mse)` **and** existing worker `commit_eligible=True`. Report all individual metrics, fail any unmet gate. Even if these shadow metrics pass, **no Body-JEPA/answer-utility promotion**.

## Test/claims

Local repository-layout Python 3.13 NumPy: 4/4 synthetic tests PASS; raw log SHA-256 `303a201291373a52a57cdb459c25daab80804b79d10f04bb08ae1c9252a55bb4`. Source Git blob `1d3035aa0029f94e1e86e2f0aa6111e46ef8523e`, test Git blob `534948bb920f0c58061b20194826a0bc0c1c4cf8`. Synthetic tests cannot establish real native or answer-level utility.

Output only metadata, token counts/hashes, aggregate train/dev/test metrics. Delete private taps, model, native binary and candidate weights; no public model redistribution. Serialized native concurrency group; official privacy scanner. Never retry rejected anyone-writable Drive destination.

Gates stay `STEP2=UTILITY_FAIL`, `B3_L1=FAIL`, `Body_JEPA=UNAVAILABLE`, `jepa_weight=0`, `DS2_H2=FAIL`, `V13=INCOMPLETE`. Exact next after native result: independently assess fixed-target test and control, preserve FAIL if unmet; pursue a real B1/B2 train-master ObjectiveAdapter with source-bound gradient/credit, retention and answer-level utility.

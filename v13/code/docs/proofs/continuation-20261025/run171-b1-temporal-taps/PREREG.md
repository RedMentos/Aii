# Run171 prospective registration — real pinned B1 temporal taps to frozen external predictor

Created 2026-10-25 before any Run171 native inference. Exact base Run170 PR200 head `79df0f7e9c1cf0f3a17f08aac4b31ecf01f51911` (Run169 PR199 head `9b42893de8aa0655729cdd1b990c61cd8f8ca367`). Owner: **only new Run171 script/test/workflow/proof files**. Frozen Runtime/Canon, registered model files and existing cohorts unchanged. No active model swap, no body weight writes, no learning approval.

## Precommitted inputs and cohort

Use exact registered B1 `LiquidAI/LFM2.5-1.2B-Instruct-GGUF` revision `6767265158422fb8a19c62ceb45f16f05363615b`, full size `695755488`, SHA-256 `bb741ebb106d543e9de114b843a3d3d73d51c74b5801e69da2abde821a0cb3e1`; pinned llama.cpp b10964 Linux archive SHA-256 `9abf88aea48a55d0f80edb1ee20220b186848cca0b4e919d71518cfd7ca67443`. No alternate source or runner.

Sixteen **public synthetic English texts**, fixed order and exact `json.dumps(TEXTS,separators=(',',':'),ensure_ascii=False)` SHA-256 `76c0276ed2501a017a10c10c0cbfbc30e97268bee95e910df3388ceccfaa1302`, are defined in `scripts/run171_b1_future_states.py`. B1 read-only `LlamaRunner(...,purpose='tap')` with `max_tokens=64`, one native model at a time, `lfm2.result_norm.final.v1`, 2048D, no latent injection/body training. Per text temporal pairs use native token indices `i=3,6,9,...<n-2` and target `i+2`, source-group `run171-text-XX`; all pairs from one text remain together. First 12 source groups train; last four holdout via unchanged `v13.predictor_worker.train`. No posthoc text or split changes.

Predictor config: `seed=17125`, existing `KNOBS[k][0]` for `predictor_lr`, `ema_decay`, `max_update_norm`, `retention_max_delta`, `predictor_steps`; regularizer `ema`. One candidate external projector/predictor/slow EMA target, native B1 weights **frozen**. Compare heldout prediction MSE against same-worker copy and shuffled-target baselines; retain finite-difference gradient, noncollapse, retention, deterministic repeat, checkpoint reload. No threshold tuning on holdout; report failure if any.

## Claim limits / privacy / ownership

This is a **real native tap + external shadow predictor** if CI completes, not B1 Body-JEPA weight training, JEPA answer utility or Redmi evidence. Report only token counts/digests and aggregate metrics, no latent vectors, GGUF, checkpoint weights or native binaries. Run with shared `v13-native-c3-run131-serialized` concurrency group and bounded Linux memory/disk. Delete private temp files and unload/reap runner even on failure. No parallel native jobs. All gates stay `STEP2=UTILITY_FAIL`, `B3_L1=FAIL`, `Body_JEPA=UNAVAILABLE`, `jepa_weight=0`, `DS2_H2=FAIL`, `V13=INCOMPLETE`.

Next: inspect actual CI metrics and counterexamples; if no attributable gain, preserve FAIL. Then plan a source-bound **trainable Body weight** objective with actual predictive targets and downstream heldout answer utility/retention before any authority promotion.

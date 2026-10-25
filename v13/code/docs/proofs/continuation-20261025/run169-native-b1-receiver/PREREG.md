# Run169 prereg — private native B1 GGUF receiver comparison (NOT JEPA utility)

Date 2026-10-25. Base Run168 `b630f68d2536aa5aefff2775c476cc7682ab42a1`. Owner new native receiver script/tests/workflow/proof only. Frozen Runtime/Canon, registered models/cohorts, Run160–168 unchanged. No active installation or permission promotion.

## Exact registered assets
B1 GGUF `LiquidAI/LFM2.5-1.2B-Instruct-GGUF`, revision `6767265158422fb8a19c62ceb45f16f05363615b`, 695755488 bytes, SHA256 `bb741ebb106d543e9de114b843a3d3d73d51c74b5801e69da2abde821a0cb3e1`. Linux llama.cpp b10964 binary archive from existing `specs/models.json`, SHA256 `9abf88aea48a55d0f80edb1ee20220b186848cca0b4e919d71518cfd7ca67443`. Verify both before native execution.

## Exact probe and gates
Use Run162 sorted first four eligible F32[2048] norm vectors; Run163 exact source audit; Run166 synthetic quadratic Torch micro; Run168 private F32-only patch/rollback with all GGUF tensor spans validated. Materialize the same audited **private** patched GGUF bytes after Run168 rollback; require its SHA equals Run168's pre-rollback patched SHA. Load **baseline and patched sequentially**, never concurrently, via existing `v13.runners.LlamaRunner` with pinned llama-server and B1 role. Context 1024, threads 2, max output 32, deterministic seeds 16900–16902. Prompts (fixed order):
1. `Say hello in one short sentence.`
2. `What is 2 plus 2? Answer with one number.`
3. `Repeat exactly: blue river.`
JSON canonical list SHA256 `f744b15218f8448879ae4339cf158e463e114b2026e6967fa9e3e7197f3ac64f`. No posthoc prompt substitution.

Require each native response completes (nonempty, bounded), record response SHA/length and paired equality only. **Do not label changes as improvements**. Always unload/reap native runner and restore the private patched GGUF to original SHA, even on failure; original model SHA unchanged. No active model swap, no training utility claim.

## Evidence and safety
Linux native model receiver evidence only; Run166 objective is synthetic quadratic, **NOT JEPA**, no real predictive latent training, no retention/ablation utility, no Redmi. Serialized with `v13-native-c3-run131-serialized`, private temporary model/runner/patch files deleted after CI, metadata-only report and closed raw failure logs, official privacy. `STEP2=UTILITY_FAIL`, `B3_L1=FAIL`, `Body_JEPA=UNAVAILABLE`, `jepa_weight=0`, `DS2_H2=FAIL`, `V13=INCOMPLETE`.

Next: actual predictive JEPA objective with teacher/target latents and retention/answer utility; don't promote based on load/format or small output differences.

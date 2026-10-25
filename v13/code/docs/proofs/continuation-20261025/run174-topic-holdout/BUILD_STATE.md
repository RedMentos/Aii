# Run174 BUILD_STATE — preregistered, native NOT RUN yet (2026-10-25)

Owner new Run174 source/test/workflow/proof only, branch `codex/run174-b1-topic-disjoint-shadow-20261025` based on PR203 `9b5608f0f7c027e8755b8a0988ec084b2337cc53`. No frozen runtime, Canon, registered cohort, model or age-gate modifications.

Implemented 20 topic-group × 6 public text variants = 120 source-bound B1 read-only native tap inputs; t→t+2 temporal pair builder, group-disjoint train/dev/final-test, unchanged external EMA predictor worker, and independent **fixed initial target** final-test MSE vs copy/shuffle controls. No body weight training or active predictor use.

Local Python 3.13 + NumPy, repository layout: **4/4 synthetic tests PASS**, compileall PASS. Raw log SHA-256 `303a201291373a52a57cdb459c25daab80804b79d10f04bb08ae1c9252a55bb4`. Source Git blob `1d3035aa0029f94e1e86e2f0aa6111e46ef8523e`; test Git blob `534948bb920f0c58061b20194826a0bc0c1c4cf8`. Public text cohort SHA-256 `e8f65406ed05090581f0a23471e9403c569b246621517f85988533e521078e43`.

**Prior negative native result preserved:** Run171 86 pairs, external predictor after MSE 1.05325 > copy 1.03237 and shuffle 1.00692; `commit_eligible=False`. New Run174 final topics are not Run171 holdout; no parameter search/cherry-picking. Run173 full-suite may still FAIL due orphan descendant.

Current evidence class SOFTWARE/SYNTHETIC only. CI native result **NOT RUN** until PR starts. Shared serialized native group; no simultaneous native jobs. No private vectors, model, weights or raw output published.

Unchanged gates: `STEP2=UTILITY_FAIL`, `B3_L1=FAIL`, `Body_JEPA=UNAVAILABLE`, `jepa_weight=0`, `DS2_H2=FAIL`, `V13=INCOMPLETE`.

Exact next step: finish/check Run173 full suite and raw failures; then open Run174 PR, verify Linux CI model hashes, final fixed-target heldout and all controls. If gain fails, preserve FAIL. Even if shadow gains, require real Body weight gradient/credit, downstream answer utility/retention, and Redmi evidence before any gate promotion. Rejected Drive destination remains prohibited.

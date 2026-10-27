# LP3 gradient-path diagnostic after failed heldout pilot — 2026-10-27

**Owner:** `codex/automation11e-lp3-gradient-diagnostic-20261027`, review-only child of failed native pilot PR #734 exact `afbc0818b1080c11ac78cca3df5eeb6cd7b081b4`. Independent prereg `fd3354f59fd84def242a222e4639a6501ff170df` remotely verified before runner/workflow. Original failure Actions `40527420680` native exit 1 and private byte-verified raw ZIP SHA256 `3fc467c37f92b2fe442b440c60904e626fc1ef513b92345b6c3a3d8768581004` retained unchanged.

## Implementation and claim limit

`scripts/lp3_gradient_diagnostic.py`: pinned official full FP32 LFM2.5-350M master SHA preflight, seed109, prefix2; **zero optimizer updates**. Measures per-prompt full-answer and first-token CE/predictor/projector gradients plus own/zero next-logit delta on all six original train questions, two original real-master compatibility questions as single rows, and their original two-row first-token batch. Frozen base sample hash and no-grad guard. No weights/optimizer bytes, no heldout training, no utility or Age claim. `tests/test_lp3_gradient_diagnostic.py` verifies fixed comparators, explicit opt-in and zero-gradient recording.

## Native checkpoint

Actions **40528733559** launched on exact workflow/source commit `8b11cfde8670838ead5f8ed2773b178070521771` and is **IN_PROGRESS** at checkpoint. Full pinned master, isolated dependencies, bounded 15m native step, closed raw logs/exit and privacy/diff checks; preserve failures. **No gradient result claimed before raw artifact audit.**

## Negative gates and next

Original LP3 heldout pilot remains **FAIL_MISSING_PREDICTOR_OR_PROJECTOR_GRADIENT**, not an attributable utility result. LP1 NO_ATTRIBUTABLE_GAIN; LP2 ALIGNS_NO_GAIN; BJ1 NO_SIGNAL; STEP2 UTILITY_FAIL; B3 L1 FAIL; jepa_weight=0, Age authority=0, Redmi unmeasured, V13 incomplete.

Next: read Actions `40528733559`, download/hash/independently audit raw artifact, distinguish single-vs-batch, full-vs-first and prompt-dependent gradients. Preserve original failed pilot, preregister any future utility retry separately. Continue independent scheduler/Context OS work meanwhile.

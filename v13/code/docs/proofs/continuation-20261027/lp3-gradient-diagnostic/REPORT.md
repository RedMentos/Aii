# LP3 gradient-path diagnostic after failed heldout pilot — 2026-10-27

**Owner:** `codex/automation11e-lp3-gradient-diagnostic-20261027`, review-only child of failed native pilot PR #734 exact `afbc0818b1080c11ac78cca3df5eeb6cd7b081b4`. Independent prereg `fd3354f59fd84def242a222e4639a6501ff170df` remotely verified before runner/workflow. Original failure Actions `40527420680` native exit 1 and private byte-verified raw ZIP SHA256 `3fc467c37f92b2fe442b440c60904e626fc1ef513b92345b6c3a3d8768581004` retained unchanged.

## Implementation and claim limit

`scripts/lp3_gradient_diagnostic.py`: pinned official full FP32 LFM2.5-350M master SHA preflight, seed109, prefix2; **zero optimizer updates**. Measures per-prompt full-answer and first-token CE/predictor/projector gradients plus own/zero next-logit delta on all six original train questions, two original real-master compatibility questions as single rows, and their original two-row first-token batch. Frozen base sample hash and no-grad guard. No weights/optimizer bytes, no heldout training, no utility or Age claim. `tests/test_lp3_gradient_diagnostic.py` verifies fixed comparators, explicit opt-in and zero-gradient recording.

## Native checkpoint

Actions **40528733559** exact source `8b11cfde8670838ead5f8ed2773b178070521771`: **LINUX_NATIVE_DIAGNOSTIC_PASS** (not utility). Full official FP32 master SHA preflight PASS; native exit 0, privacy 0, diff 0; 0 optimizer updates. All **six** original training prompts had positive finite full-answer predictor gradients **3051–15289** and projector gradients **4026–21528**; first-token gradients also positive. Two original compatibility prompts had positive single-row gradients, and the original two-row batch had predictor **5783.98**, projector **8694.68**. Next-token own-vs-zero deltas on six training prompts were **0.354–0.738**. This excludes a simple initial single-row/target-length disconnection; the original heldout run still failed, plausibly after optimizer steps or due evaluation-state interactions, **not yet diagnosed**. Artifact `12744098893`, ZIP SHA256 `cb8aed75ae34809e06581557ca9cfce2dda088158f156077831f643b7d8114ed`, RESULT.json SHA256 `0114f75f6f26c39299a8c9d1180a71073eb9835de99919b2caaaa94eac737944`, raw log SHA256 `140984e3810cec1f551004ab88e42d0ccffe07d3225269d618e6e308b14812db`. ZIP privately backed up and byte-verified at `/V13-Checkpoints/2026-10-27/LP3-Gradient-Diagnostic/lp3-gradient-diagnostic-40528733559.zip`. No model/optimizer bytes or gate promotion.

## Negative gates and next

Original LP3 heldout pilot remains **FAIL_MISSING_PREDICTOR_OR_PROJECTOR_GRADIENT**, not an attributable utility result. LP1 NO_ATTRIBUTABLE_GAIN; LP2 ALIGNS_NO_GAIN; BJ1 NO_SIGNAL; STEP2 UTILITY_FAIL; B3 L1 FAIL; jepa_weight=0, Age authority=0, Redmi unmeasured, V13 incomplete.

Next: separately preregister stepwise gradient/optimizer-state telemetry for the original fixed 24-step sequence (or a controlled low-LR arm) to locate the later vanishing point. Preserve the original failed utility cohort and its raw artifact. Continue scheduler/Context OS work; no utility or Age claim.

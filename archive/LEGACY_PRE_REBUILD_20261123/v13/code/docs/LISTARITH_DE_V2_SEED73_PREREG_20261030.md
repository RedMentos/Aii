# Seed73 German list_arith v2 SHADOW candidate prereg — 2026-10-30

Owner `assistant/v13-listarith-de-v2-candidate-seed73-20261030`, review-only child of PR #1218 at `55c3628929ad2d9059736d761d58e1fe810b817f`.

**Observed development signal (not heldout):** frozen seed71 original detector scored 25/36 with four unsupported false-positive operations (negation and metalinguistic sum) and seven supported false negatives. The original seed67 narrow holdout scored 24/24; both cohorts, original detector and labels remain immutable.

## Locked experiment before implementation
Create and commit **36 new seed73 synthetic German prompts** (12 total, 12 max-min difference, 12 unsupported) before candidate code. They use different paraphrases and negative intents from seed71, no real private text. Freeze fixture Git blob before source/evaluator. Do not change labels after observing predictions.

Implement a **separate opt-in-unwired SHADOW candidate**, not a replacement for the seed67 detector or production ToolStep. Improve fail-closed negation/metalinguistic refusal, broaden ordinary German sum and max-min phrasings, preserve specific-pair/count/mean rejection, and reject conflicting operations. No numeric extraction, no tools, no model weights, no learning, no authority.

One-shot source-pinned comparison: exact old seed67 detector versus candidate on frozen seed73; preserve all 36 raw paired predictions and original labels. Compute exact correct counts, NONE false positives, supported recall, confusion and macro-F1. `V2_SHADOW_CANDIDATE_SUPPORTED` requires candidate correct >=30/36, >=6 net exact wins over original, zero NONE false positives, and >=9/12 correct in both supported classes. Otherwise `V2_SHADOW_CANDIDATE_NOT_SUPPORTED`. **Neither outcome is an age, STEP2, B3, Body-JEPA, C5, Redmi or live-tool gate.** The threshold is exploratory synthetic evidence, not general German robustness. Original source must remain byte-identical.

Add adversarial tests: negation, meta-questions, specific A/B, conflicting operations, empty/oversized/nonstring input, no live consumers, unchanged English registrar, frozen original seed67 tests, and no score/type coercion. Save original RED attempts and source/fixture hashes. If a candidate fails, do not retune seed73; a future fresh cohort is required.

Exact next command: after fixture commit, implement candidate + evaluator + tests; run source-pinned software CI, download original raw ZIP, verify CRC/inner hashes/negative gates and preserve full report. Continue native C3 German typed-value research separately.

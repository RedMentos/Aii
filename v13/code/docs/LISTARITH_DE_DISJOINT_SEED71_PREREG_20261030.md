# Seed71 disjoint German list_arith SHADOW generalization prereg — 2026-10-30

Owner: `assistant/v13-listarith-de-disjoint-stress-seed71-20261030`, review-only child of PR #1217 at `4915b0b20f72df7957bd688975518dd4e1a6a8a6`.

## Frozen before evaluator
Create **36 newly written** German questions, 12 each for expected `total`, `difference_max_min`, `None`. Unlike seed67, include paraphrases absent from seed67's narrow template family, explicit negations, questions about stated totals rather than requests to calculate, natural German maximum/minimum synonyms, and unsupported pairwise/count/average questions. Each prompt has two or more named numeric items in the source section and one final question. No external/private data; no model inference.

This is a **new disjoint synthetic stress cohort**, not seed67 holdout or a retuning set. Fixture rows are to be committed and Git-blob-pinned **before** evaluator/test implementation. Do not modify `v13/agi/listarith_de_shadow.py`, original seed67 fixtures, scorer or any production path.

## Measurements and locked interpretation
- Run the exact current `listarith_de_shadow.propose` on all 36 frozen questions; store each original prediction/reason, expected label, row id, and source blob.
- Compute confusion matrix, overall exact accuracy, per-class precision/recall, macro-F1, `None` false-positive count, and separate negation-only failure count. No rescore or cherry-picking.
- `SHADOW_GENERALIZATION_PASS` requires **at least 30/36 correct**, **0/12 false-positive operations on unsupported `None`**, and **at least 8/12 recall in each supported class**. Otherwise `SHADOW_GENERALIZATION_RED`. This threshold is exploratory and **never** a live-tool or age gate.
- Check original seed67 source blob and fixtures unchanged. If RED, preserve failure and propose a separate future candidate, not retroactively change seed71 labels or seed67 detector.
- Standard-library evaluator and tests only, no downloads, no native jobs, no user action, no tool/approval/learning authority.

Age0 RECORD_ONLY, STEP2 UTILITY_FAIL, B3 NO_PROMOTION, Body-JEPA UNAVAILABLE, jepa_weight=0, Redmi unmeasured, whole system incomplete. Next command after prereg+fixtures: run source-pinned evaluator in CI and audit raw report; then pursue native C3 typed extraction on a new approved evidence path.

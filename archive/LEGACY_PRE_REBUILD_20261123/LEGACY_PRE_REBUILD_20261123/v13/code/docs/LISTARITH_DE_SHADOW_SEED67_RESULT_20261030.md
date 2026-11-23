# German `list_arith` seed67 SHADOW result — 2026-10-30

**Status: `SHADOW_DE_SUPPORTED` on a narrow synthetic software-only cohort. NOT a live tool or native-model result.** This branch is a review-only child of #1215; no original `v13/agi/listarith.py`, ToolStep, C5, age/approval policy, model, runtime or user-facing answer path changed.

## Frozen before evaluation

- Immutable prereg `v13/code/docs/LISTARITH_GERMAN_SHADOW_SEED67_PREREG_20261030.md` committed at `3286ddd680fcc46b6f89950269000482edd326ca`, fixture file committed at `45506ebab8595cea59cba85b2c773a6c0f44d438`, both **before** detector/evaluator code.
- 48 synthetic German prompts, 24 dev/24 heldout, eight per label in each split (`total`, `difference_max_min`, `none`), canonical SHA256 `468b231fd196f28e773fba1d541f4ed7c7436d180d78b835e0ad3eb3f85a3d05`. All holdout labels and raw rows preserved.
- New `v13/agi/listarith_de_shadow.py` is **non-authoritative**, question-scoped, rejects specific A/B comparisons, counts, averages, ambiguous/conflicting operations, nonstrings and long input; returns only typed `proposal`, `reason`, `authority=SHADOW_ONLY`. `live_consumers=0`.

## Verified evidence

- Exact-source dev CI `41008481290` at `ee91cc4b136ef22f8dd92d8796c481491e0b7376`: **GREEN**, 6/6 tests including all 24 dev labels, eight original English `listarith.operation` regressions, adversarial no-authority tests, pinned canonical/original module, privacy/diff PASS. Original ZIP artifact `12956477979`, SHA256 `41b11aca7a2f1edbf6dcd0af6a02f2946656ce2558d9d1bd87df20bae731a6fa`, CRC clean, 14/14 inner hashes, all 6 stage exits zero.
- **One-shot frozen holdout** Actions `41008645454` at `32810da640642af24fa8bc57b124f670adb68421`: **GREEN integrity**; original artifact `12956302340`, ZIP SHA256 `d1f1a2f9d6317c077a5a12fa8ba58b1b6c60f299bbba4bf4801c1837c8c05168`, CRC clean, 18/18 inner SHA256SUMS, all 7 stage exits zero. Original `report.json`: **24/24** heldout labels exact, **0/8** false-positive proposals on `none`, **8/8** English regression examples unchanged; `SHADOW_DE_SUPPORTED`. All 24 original heldout raw rows independently checked, no mismatches. This result is only the preregistered small synthetic task family; dev/holdout share template structure, so it does not prove general German language robustness.
- Both original CI ZIPs privately backed under `/V13-Checkpoints/2026-10-30/Run12-Listarith-GermanShadow-Seed67/` and re-materialized SHA256 byte-identical. No anyone-writable Drive upload.

## Next substantive steps

1. Independent, **new** disjoint German paraphrase/negation/count/ambiguous-question holdout with source text from different templates; do not retune or rescore seed67. Add code-switching/typos and real source data only with permission and privacy checks.
2. Native C3 typed value extraction on German questions and actual ToolStep→C5→TOOL_RESULT answer quality with strict source binding; current seed67 only proposes an operation, **does not read values or calculate**.
3. After new native utility and false-positive evidence, evaluate a guarded **SHADOW** consumer; live tool enablement still requires explicit user approval and the age/transaction gates. No model, JEPA or Redmi claims.

**Gates:** Age0 RECORD_ONLY, STEP2 UTILITY_FAIL, B3 NO_PROMOTION, Body-JEPA UNAVAILABLE, jepa_weight=0, Redmi UNMEASURED, whole V13 incomplete. Remaining platform budget UNKNOWN.

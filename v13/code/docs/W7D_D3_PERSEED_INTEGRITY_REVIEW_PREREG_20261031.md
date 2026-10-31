# W7D independent preregistered D3 per-seed integrity review (2026-10-31)

Owner: GPT-6 scheduled continuation. Parent PR #1419 exact HEAD `2033b2f716dff6c7e792e4c2f86c17b1680644a6`; this document is to be remotely committed and read back before code/test edits. No native run has been claimed.

## Preexisting contract and observed discrepancy

The existing frozen W7D preregistration `WORLD_JEPA_DELTA_INVERSE_PREREG_20261031.md` requires D3 **mean per-seed W4 Spearman rho change <= -0.05 and every seed delta <= +0.05**. The current `scripts/w7d_world_jepa_delta_inverse_real.py` instead checks only a pooled rho difference and returns `D3_per_seed_rho_unmeasured=True`; the pooled result may be true despite an unmeasured per-seed requirement. This is an exploratory diagnostic integrity issue, not evidence of learned utility.

## Bounded correction

Keep original collector, evaluator, frozen model, W1-W7, original W7S failure, seeds 701/702/703, training/CF/attribution sizes, steps, source/model hashes and SHADOW authority unchanged. In the W7D runner only, compute each arm's per-seed W4 rho from the already retained `_conf_err` covered-confidence/error pairs **before** their historical redaction. Use the original frozen `z12b_world_jepa.spearman` algorithm for comparability, require at least two finite pairs per seed, require finite computed rho, and reject invalid data rather than interpreting missing values as success. Record three paired rho deltas, mean delta, pooled delta as a separately labelled diagnostic, and D3 true only if mean <= -0.05 and every paired delta <= +0.05. Preserve original W1-W7 gates as the only W7D candidate-status determinants; D1-D3 are exploratory only. Retain raw per-seed RESULT files; no posthoc replacement of any failed run.

## Independent tests and acceptance

1. Counterexample: pooled rho improvement alone must not pass D3 when any per-seed rho regresses by > +0.05.
2. Positive finite three-seed fixture meeting mean/per-seed D3; swapped seeds, insufficient covered pairs, nonfinite/invalid raw, missing keys must fail closed.
3. D1/D2 outputs and original W7 candidate status remain unchanged; D3 is never a promotion gate.
4. New isolated workflow on this review branch: frozen Git-blob pin verification, exact unit tests and relevant existing W7D regressions, py_compile, privacy diff scan, diff --check, retained raw exit receipts + SHA256SUMS. No heavy/native job or Redmi claim.
5. Remote-read-back of source/tests/status and CI before declaring software PASS. Preserve failed workflow evidence.

This review is independent of PR #1419, remains draft/review-only, and must not merge or modify production. All Age0 RECORD_ONLY, STEP2 UTILITY_FAIL, B3 NO_PROMOTION, Body-JEPA UNAVAILABLE, jepa_weight=0 and World-JEPA SHADOW gates remain negative.

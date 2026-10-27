# WP-BJ1 Body-JEPA training sample-weight preflight preregistration

Date 2026-10-27 UTC. Owner GPT-6 continuation. Review-only child of PR #746 World-JEPA branch at exact parent `45616b669cbf56eabc29e5ff55979c223476d601`. Ownership: `v13/code/v13/body_jepa.py`, `v13/code/tests/test_body_jepa.py`, isolated workflow and this proof directory. No frozen runtime/model/source cohort, no trainer activation, no training authority.

## Problem and counterexample

`BodyJepaTrainer.fit` currently extracts per-item weights only **after** loading the base model and allocating LoRA/EMA/optimizer. The JEPA objective validates its own weights only when `jepa_weight>0`; the CE-only baseline with `jepa_weight=0` divides by an unchecked weight sum. Negative, boolean, NaN, Inf, zero-sum or overflowed weights can cause invalid CE/optimizer updates, wasted native resources and untrustworthy training evidence.

RED software test: invalid weights must raise ValueError **before** importing/loading any model; a spy on `_load` must never be called. Valid missing/default weights, positive values and mixed positive/zero values must preserve exact numeric weights. Reject all-zero and nonfinite sums. GREEN candidate: one shared validated list used for CE and JEPA, no change to legitimate training loss, optimizer, seeds, cohort or source master. Preserve the original failed tests, run focused Body-JEPA torch unit tests and full suite; no real master download or native training.

Proof requires prereg commit before test/source, source-bound RED/GREEN raw artifacts, compile, privacy/diff, independent review and private backup. LP1 NO_ATTRIBUTABLE_GAIN; LP2 ALIGNS_NO_GAIN; BJ1 NO_SIGNAL; STEP2 UTILITY_FAIL; B3 L1 FAIL; jepa_weight=0 in registered cohort; Age authority=0; Redmi unmeasured; whole V13 incomplete.
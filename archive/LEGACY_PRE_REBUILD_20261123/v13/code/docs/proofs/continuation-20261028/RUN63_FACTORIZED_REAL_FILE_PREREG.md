# Run63 — fairer factorized global and slot-aware local ridge comparators (2026-10-28)

Owner GPT-6 continuation; independent review-only child of Run60 #968 **exact independently audited push head** `a94e27cbe0c100af2d88c994ea4f89bfd89bf433` (Actions `40762607763`, original ZIP SHA256 `ef76f76d65627776d906e141571e0cfafe595ec65f76173dee14727ed9957ca7`, CRC clean, 20/20 SHA256SUMS, 14 focused/2596 full OK, privacy CLEAN). No edits to original Run60, original Z12b, frozen WorldJEPA, registered seeds/cohorts/models, Runtime/Store or main.

## Problem and preregistered hypothesis

Run60 supervised isolated Linux file-action study observed heldout overall MSE persistence 0.0532817190410003, global exact-full-action ridge 0.06248578875059215, shared slot-local ridge 0.016492981896166048 (seeds 211/223/227). But its global ridge uses 31D **exact operation×slot action one-hot** and cannot estimate coefficients for unseen combinations. Its lower score does not prove that locality, rather than *factorized action encoding*, caused improvement.

Fresh, disjoint deterministic seeds **233, 239, 241**; for each seed choose four heldout non-noop operation×slot combinations by `random.Random(seed).sample(Run60.NON_NOOP,4)`. Use exact unchanged Run60 `_rows(seed, held, 240, test=False)` and `_rows(seed, held, 60, test=True)` to execute actual isolated Linux temporary-file actions. Train/test walks separate, no heldout combos in training. No user files or network. **Fixed lambda 0.01**, intercept unpenalized, no hyperparameter selection, no posthoc thresholds, no metric-based retries. Record actual action success and source/row digests.

Five preregistered supervised comparators, all fit train rows only:
1. persistence, unchanged x;
2. original Run60 global full-action onehot ridge, unchanged;
3. original Run60 shared slot-local operation-conditioned ridge, unchanged;
4. **factorized global delta ridge**: input [bias, full x60, operation onehot5, slot onehot6], fit full delta `x2-x`, predict `x + delta_hat`. No exact operation×slot onehot;
5. **slot-aware local ridge**: input [bias, local x10, operation onehot5, slot onehot6], fit only target-slot `x2_slot`, copy other slots unchanged. No exact operation×slot onehot.

Primary metric: heldout overall MSE for all five; secondary target-slot MSE, per-seed and aggregate, train/test action/success counts, SHA256 row digests. Explicitly compare factorized global and slot-aware local against shared local; no thresholds or claims of causal/JEPA/Redmi/Body utility regardless of outcome. A better factorized comparator weakens uniqueness of locality; a worse comparator motivates **new** independently registered architecture tests, not a retroactive Run60 gate. All five models see the same real observed test outcomes only during scoring.

Tests: exact fresh seeds, split exclusion, reproducible data, all 5 finite metrics, no holdout target in fitting, factorized features invariant to exact action index representation beyond op/slot, frozen Run60/original source pins, negative gates, no unauthorized actions. Pinned Linux software-only push and PR CI, focused/full suite, raw ZIP SHA256SUMS, privacy/diff. No external model or training authority.

Age0 RECORD_ONLY; STEP2 UTILITY_FAIL; B3 L1 FAIL; Body-JEPA UNAVAILABLE; LP3 FAIL; jepa_weight=0; Redmi UNMEASURED; full V13 incomplete. Run62 cross-chain integration remains a separate conditional review branch, not production.

# Run60 — compositional slot-local baseline on real file-action outcomes (2026-10-28)

Owner GPT-6 continuation. Independent review-only source-only package from Run56 verified head `e37fe520b924786001e3fa707ee5e9c0a17054ec`; disjoint from Run58 B2 and Run59 synthetic latent readout. No main merge, no edits to frozen `world_jepa.py`, `z12b_world_jepa.py`, models, seeds or original registered Z12b cohorts.

## Canon question and original negative evidence

Canon §7.2.1 requires action-conditioned, outcome-grounded prediction and controlled baselines. Original WP-Z12b real file-action World-JEPA preregistered three-seed experiment FAILED its criterion (77% covered action retrieval vs required 80%; held-out operation/slot combinations only 27%; attribution false positives). Do not reinterpret or modify those failed original runs. Hypothesis: **sharing a learned per-slot operation transition across all six slots** is a simpler compositional inductive bias than a single global predictor, and may improve novel operation×slot combinations. This package is a fresh, separately preregistered diagnostic baseline, not a JEPA replacement or posthoc Z12b pass.

## Fresh experiment fixed before implementation

Use only original public deterministic file-action helpers `scripts.z12b_world_jepa` (`features`, `do`, `ACTIONS`, `OPS`, `SLOTS`) in isolated temporary directories. No real user files, Runtime/Store, external tools or model downloads. Three seeds **211, 223, 227**. For each seed choose four held-out (op,slot) combinations deterministically from 30 non-noop actions. Train 240 real file transitions using the remaining combinations, with separate seeded state walks and independent test state walks. Evaluate 60 heldout-combination real file transitions per seed. Each transition copies a state folder, performs exactly one candidate action in the copy, observes `features(x2)`, and deletes the copy. Record actual operation success/failure; never synthesize next-state labels. Fixed `lambda=0.01`, no hyperparameter selection or retry-on-metric.

Three predeclared comparators:
1. **Persistence** `x2_hat=x` (no action).
2. **Global ridge**: predict full 60D `x2` from [bias, full 60D x, 31D exact action onehot], fit train only; unseen combination coefficients absent.
3. **Slot-local ridge**: for each non-noop train transition, fit one shared 10D next-slot predictor from [bias, local 10D pre-slot, 5D operation onehot]; inference copies full x and replaces only the target slot with the predicted 10D local next-state. Noop is exact persistence. No heldout outcome enters fitting. This is supervised ridge on real observed file effects, **not** JEPA learning.

Primary outcome: mean per-feature heldout MSE for the three comparators, with per-seed values and aggregate. Secondary: heldout target-slot MSE and exact operation success counts. No threshold, no causal/AGI/JEPA utility claim; a worse slot-local result must be preserved. Report only aggregates, seeds, split/action digests and source hashes, no raw text or file content. Tests check deterministic fixture/split, real changed bytes, no heldout combination in training, no caller data or installed-home access, finite metrics, negative gates. CI source-only pinned NumPy, focused/full suite, privacy/diff, raw hashes. Never change the original Z12b three-seed evidence.

## Scope

Linux real filesystem actions are not native Body/LLM inference or Redmi measurements. No runtime consumer, online plasticity, approvals, external actions or source-to-user authority. Age0 RECORD_ONLY; STEP2 UTILITY_FAIL; B3 L1 FAIL; Body-JEPA UNAVAILABLE; LP3 FAIL; jepa_weight=0; Redmi UNMEASURED; V13 incomplete. Follow-up only if measured benefit: separately preregister action-conditioned JEPA predictor adaptation and test against both original controls and slot-local ridge on disjoint real action states.

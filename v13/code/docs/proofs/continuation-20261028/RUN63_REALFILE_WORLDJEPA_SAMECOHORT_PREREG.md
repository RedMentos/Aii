# Run63 — same-cohort real file-action World-JEPA vs compositional slot-local ridge (2026-10-28)

Owner GPT-6 continuation; independent review-only child of Run60 PR #968 exact source `a94e27cbe0c100af2d88c994ea4f89bfd89bf433`. Run60 independently GREEN Actions 40762607763 original ZIP SHA256 `ef76f76d65627776d906e141571e0cfafe595ec65f76173dee14727ed9957ca7`, 20/20 inner hashes, 14 focused/2596 full OK, privacy CLEAN. Original WP-Z12b three-seed FAIL remains frozen. No main merge, Runtime, Store, model/seed/cohort rewrites.

## New preregistered question and design

Run60's slot-local ridge improves heldout per-feature MSE over persistence/global ridge on fresh real isolated file actions, but the original World-JEPA was measured on a different cohort and with different retrieval metrics. **Never compare those absolute numbers as if same-cohort.** New preregistered seeds **233, 239, 241**, each with **240 train** and **60 heldout** real file-action transitions generated from frozen Run60 `_rows` and original `z12b_world_jepa` helpers, four op×slot combinations held out by `random.Random(seed).sample(range(NOOP),4)`. All source states in isolated temporary folders, actual file effects observed in copied folders. No human data or independent world process. Fresh holdout outcomes remain unseen until scoring; no tuning on them.

Three WorldJEPA arms with identical `WorldJEPA(seed=seed,ensemble=2)`, **40 steps**, same train rows and fixed model/source:
- OBSERVED: fit on true op+slot onehot action, evaluate with true heldout action.
- ZERO_ACTION: fit and evaluate on zero action vectors, identical architecture/steps.
- SHUFFLED_TRAIN_ACTION: fit on deterministic `np.random.default_rng(seed).permutation(n_train)` action pairing (fallback cyclic if identity), evaluate with true heldout action.
For each arm, fit one **train-only supervised ridge decoder** `lambda=0.01` from predicted train latent to observed train next-state 60D features; score the frozen decoder on heldout predicted latents vs **actual** heldout next-state features. No heldout label enters fit, no counterfactual outcome fabricated. Same-cohort comparators: Run60's slot-local ridge, global exact-action ridge and persistence (all fitted only on same train rows). Report per-feature and target-slot heldout MSE per seed and pooled, source/split/permutation hashes, actual changed-action counts, and negative gates. No threshold, no posthoc seed/step/architecture selection. The observed JEPA arm may lose; preserve that result.

Tests: exact new seeds and sizes, disjoint held combinations, real file effects, deterministic report, input/source guards, no model weights publication, no authority; frozen original source hashes. Dedicated pinned Linux software-only CI focused/full, privacy/diff, original raw artifact SHA256SUMS. No native/Redmi evidence.

## Interpretation

This is **supervised JEPA-latent readout**, not JEPA-only utility or proof of causal planning. Same-cohort comparison can inform a later isolated slot-equivariant JEPA predictor, but cannot promote original WP-Z12b W1–W6, STEP2, B3, Body-JEPA, LP3, age or jepa_weight. Age0 RECORD_ONLY, STEP2 UTILITY_FAIL, B3 L1 FAIL, Body-JEPA UNAVAILABLE, LP3 FAIL, jepa_weight=0, Redmi UNMEASURED, V13 incomplete.

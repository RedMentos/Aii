# WP-T8 World-model held-out coverage leakage — preregistered review

Date: 2026-10-27 UTC. Owner: GPT-6 continuation. Review-only child of PR #739 exact `fa76ea437b26a161a2e21c17dee575811cc0eda0`. World-model source blob `8579d4938624137749e7eb793f5016294c36401f`; test source blob `db2103dbd21d6494030e0d37873539bf993e0350`. Preserve full SSOT and all frozen cohorts.

## Observed code defect and expected RED

`world_model.fit` uses `_split(n)` for train/held-out metrics, but builds `st['states']` from **all** transitions, including held-out rows. `coverage` and `counterfactual` then use this leaked support, potentially assigning a held-out-only action a nonzero coverage count and zero OOD distance (its own observation). This is data leakage into the simulation confidence/claim boundary even if forward MAE remains held out. Preregister a synthetic 48-row sequence where only one held-out row has action `both`; assert its training support count and `coverage.samples` are zero and label `SIMULATION_UNCERTAIN`. Existing code should fail this assertion.

## Proposed GREEN

Build `st['states']` from `tr` only. Retain existing `st['counts']` as clearly labelled total observed action counts for historical report compatibility; add `support_counts` from training-only support to prevent future misinterpretation. `coverage` continues using training states only. Preserve split, model/seed/optimizer, forward/inverse targets, held-out metrics and all negative gates. No model training on Redmi or new native proof.

## Evidence and acceptance

Focused `cd v13/code && PYTHONPATH=. python -m unittest -v tests.test_world_model`, compile, privacy and diff checks, exact source/head raw logs, expected RED then GREEN. Full software suite after GREEN, original failed attempt retained. All output is software/synthetic only, not World-JEPA causal or Age proof. No main merge without independent review.

## Preregistered persistence amendment (before source fix)

Existing persisted `T8_WORLD_MODEL` states with revision `t8-world-model-v1` already contain leaked all-transition support. A code-only fix must not continue trusting those bytes after restart. Bump `REVISION` to `t8-world-model-v2`; `load()` must fail closed for legacy v1 states until a new `fit()` is performed. Add a regression that replaces a fresh fit with the old revision and confirms `load()` returns None and `counterfactual()` returns `NO_WORLD_MODEL`. Do not rewrite or erase the old persisted state silently; refitting is explicit and produces a new v2 state. This amendment predates the source fix and is independent of the expected RED heldout-only action test.

## Independent review amendment: explicit legacy state and bounded support metadata

A caller may pass `st=` directly to `counterfactual`, bypassing `load` revision validation. Add a regression for explicit old v1 state and reject it with `NO_WORLD_MODEL` in the public counterfactual boundary. Also `states` retains at most 256 per action; report `support_counts` as actually retained training support (bounded), with separate `train_counts` for all training rows. A 400-row single-action regression must show support count=256 and train count equals the split. These checks are additive; they do not change the preregistered split or learning parameters. This amendment precedes the additional source patch.

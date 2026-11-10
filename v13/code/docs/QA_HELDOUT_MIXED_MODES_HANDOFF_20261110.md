# QA heldout mixed-mode fix — 2026-11-10

## Finding
Severity: MEDIUM — retention diagnostic correctness / runtime state preservation.
`heldout_retention_kl()` used `was_training=bool(model.training)` then `model.eval()`, and restored with `model.train(was_training)`. In PyTorch, `Module.train(...)` recursively sets all children to the same state, so a model with mixed modes (e.g. frozen base in eval and trainable adapter in train) is mutated by an otherwise read-only retention probe. This can change later training/dropout behavior and make retention comparisons unreliable.

## Fix
`v13/code/v13/body_jepa.py`: snapshot `model.modules()` flags, perform baseline/adapted KL in eval, restore root and each child flag in `finally`. Does not change weights, optimizer, adapter permission or age gates.

## Proof / limits
`v13/code/tests/test_heldout_mixed_modes.py`: four tests for successful probe, failed forward, invalid later probe and repeated deterministic KL with mixed child flags. Tests committed but full repository CI not yet verified. GitHub Actions query for latest head 73a5772c returned no runs at this checkpoint. Git clone unavailable in this execution environment (github.com DNS resolution failed), so no claim of full test pass or Android proof.

## Coordination
Stacked draft PR #1680 on QA branch `qa/v13-streamed-anchor-dropout-20261110` (PR #1676), not on main; avoid rewriting concurrent Body-JEPA PRs #1672/#1676/#1670/#1669. Owner: QA/Android. Integration owner should reconcile Body-JEPA changes in a single tested branch before merging. Next: verify CI and regressions, then test native Termux and checkpoint/rollback paths.

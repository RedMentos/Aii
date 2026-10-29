# WP-Z12b closed-store fixed-readout action ablation — preregistration

Date UTC: 2026-10-29. Review-only child of #1130 at exact parent `e15f46a5212dceeeac4361a68ba982bcb00419a4`. Existing canon blob `218464b12a2d27d92524c751922fa8e1c3fb0ea7` and all registered source/model/seed/cohort hashes stay unchanged.

## Problem / required utility path

The existing `world_jepa_heldout_action_readout_20261028.run_rows` implements a frozen supervised outcome readout and two heldout wrong-action controls, but its CLI only accepts a synthetic smoke. The existing closed-Store CLI evaluates other metrics and cannot invoke this particular fixed-readout ablation on an operator's actual closed SQLite transitions. Add an explicit, private, read-only operator bridge from closed Store to the existing action-ablation kernel. This is an operational proof path, **not** a claim that learned JEPA beats direct ridge or that counterfactuals are causal.

## Controls / acceptance (software first)

1. Explicit `--ack-closed-store` and `--ack-shadow-fit` both required before reading/training. No default live Runtime access; no SQLite writes; refuse WAL/SHM/journal, final symlink, invalid schema, small dataset and invalid steps. No silent permission escalation.
2. Exact `world_model.transitions` from `ReadOnlyStore` fed to existing `run_rows`; train/heldout partition, train-only fitting, frozen readout, correct-action vs row/column heldout mismatch and direct ridge baseline remain the existing implementation unchanged. No synthetic-only path masquerading as real.
3. Output only aggregate source/train/heldout hashes, counts, MAE/deltas and explicit nonpromotion flags. Never print paths, action/event IDs, raw states, raw latents or personal text. Source hash is a digest of canonical parsed transitions, not independently verified DB file bytes.
4. Software integration test uses an isolated synthetic SQLite fixture with real SELECT, fit and readout; assert byte-identical DB, no sidecars, no private identifiers, no persisted model weights, Age0/STEP2/B3/Body-JEPA/LP3/jepa_weight unchanged. A mock-only full-path test is insufficient.
5. Independent negative test for missing acknowledgment, invalid path, nonfinite report, and unchanged action-control semantics. Focused tests, compile, privacy and diff checks source-pinned; preserve original RED if found. Full suite may retain inherited Run34/Run37 preflight RED.

## Ownership / claim limit

Own only `v13/code/scripts/world_jepa_closedstore_heldout_action_probe_20261029.py`, `v13/code/tests/test_world_jepa_closedstore_heldout_action_probe_20261029.py`, new CI workflows and dedicated BUILD_STATE. Do not modify `world_jepa_heldout_action_readout_20261028.py`, `world_jepa_readonly_store.py`, any live Runtime, model pins, prior evidence, frozen cohorts or parent branches. Use small separate checkpoints. Linux software synthetic SQLite test != real user DB, native model or Redmi proof. Positive MAE gain is only a diagnostic; all gates stay negative.

## Exact next

Commit prereg before code/test. Implement explicit offline CLI and integration test; run source-pinned focused GitHub Actions and independently verify ZIP SHA256, CRC, inner SHA256SUMS, privacy, diff. Preserve private artifact and update review BUILD_STATE. Continue independent canonical packages.
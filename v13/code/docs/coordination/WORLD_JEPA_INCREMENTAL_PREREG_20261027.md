# World-JEPA incremental observed-outcome readout — preregistration (2026-10-27)

## Scope / ownership
- Independent review-only sibling of #758 from exact WP-Z12d PR #754 head `3a14e9bc62e19a58d6fa4bad1fcddbb3e9c179b2`, NOT main and NOT a replacement for #754 or its negative result.
- Frozen source blobs: `v13/code/v13/world_jepa.py` = `5ffd56097e66a37e2922e39d1dc0ba86cb28a760`; `scripts/world_jepa_digital_shadow.py` = `4ab37e11d8238d376e568567f901c85c12d09da8`. Neither file, registered cohort, thresholds, weights, seeds or SSOT may be edited.
- Own new files only: `scripts/world_jepa_incremental_probe.py`, `tests/test_world_jepa_incremental_probe.py`, dedicated CI and this note.

## Research question
The preregistered #754 synthetic outcome readout had **no incremental utility** against direct ridge (pooled JEPA MAE 0.203321 / 0.192621 vs direct 0.152555). Does the action-conditioned *predicted latent* add heldout information **beyond** the direct observed-state/action ridge features, rather than merely replacing a stronger baseline?

## Frozen synthetic experiment
- Reuse `bridge.synthetic_fixture(n=64,seed=20261027)`, original deterministic train/heldout `bridge.make_dataset` partition (47/17), no genuine/private rows.
- Seeds `(3,7)`, `steps=400`, ensemble3, existing model constants untouched. Original direct ridge `lambda=0.01` and 9D `[1,state4,action4]`.
- New 25D augmented ridge `[direct9,predicted-latent16]` with `lambda=0.01`; predicted latent standardized with TRAIN mean/std only. Fit readout on train targets only, heldout outcomes consumed exclusively by scoring.
- Matched controls: (a) same-dimensional seeded random linear projection of direct features (no new information), (b) wrong-action predicted latent with cyclic action shift, each standardized on its own TRAIN features and trained on train targets. Keep train-only ridge and no heldout feature/target fitting.
- Primary descriptive metric: pooled heldout MAE direct vs augmented; secondary wrong-action/random-projection controls and three outcome MAEs. **No new promotion threshold**. Improvement alone is not a causal or genuine utility proof. Report full numeric results including failures, no cherry-picking.
- Smoke tests with `steps=0` only for software contracts, then exact 400-step synthetic Actions measurement. Do not relabel steps0 as real training.

## Required software tests
- Exact train-only JEPA fit and ridge targets, no heldout target leakage.
- Fixed output fields, finite metrics, original negative gates and no runtime/weight/age authority.
- Malformed input fail closed, no raw action IDs/text in aggregate.
- CI raw exits, HEAD and frozen source hashes, privacy CLEAN; original failure and all negative gates preserved.

## Evidence and next step
Synthetic software only. No private store, genuine observed evaluation, Linux-native model/Redmi measurements or whole-system utility. `LP1_NO_ATTRIBUTABLE_GAIN`, `LP2_ALIGNS_NO_GAIN`, `BJ1_NO_SIGNAL`, `STEP2_UTILITY_FAIL`, `B3_L1_FAIL`, `jepa_weight=0`, Age authority0, whole V13 incomplete. Independent review and future real observed-store evaluation needed; no auto-merge.

# U5/AG6 training boundary — numeric anchor error must veto trainer.fit

**Date:** 2026-10-29. **Exact parent:** review PR #1095 head `3f4f0f46bed1b30ca1ad19f6e0d40e54f571e0dc`. Ownership: `v13/code/v13/agi/weights.py`, narrow `v13/code/v13/anchor.py` exception type, new regression tests, this note and isolated CI. No registered model, cohort, seed, source hash or approval gate changed.

## Independent integration finding before code
The parent U5 numeric guard rejects invalid `anchor_weight` at `anchor.for_batch`, but `WeightConsolidation.train` catches **every** exception from `for_batch`, logs an anchor error and still calls `trainer.fit` with the original trainer config. If the config contains NaN/Inf/negative weight, validation at `for_batch` is not an actual training boundary. This can reach a trainer despite an invalid coefficient. Parent PR #1095 remains a partial helper until this integration is verified.

## Precommitted RED-first behavior
- Invalid numeric novelty/stability or anchor weight produces a dedicated `AnchorAdmissionError` (a ValueError subclass), distinct from unrelated anchor-availability exceptions.
- `WeightConsolidation.train` catches this specific admission error **before** its generic fallback, persists `ANCHOR_INVALID` batch status and error class, returns without calling `trainer.fit`, without modifying the trainer config and without creating an artifact.
- For a valid finite anchor, existing SHADOW/ACTIVE training behavior remains unchanged. For an unrelated anchor calculation exception, the original generic fallback behavior remains unchanged (do not silently change legacy availability semantics).
- A staged batch cannot retry `train` from `ANCHOR_INVALID` without a new staging action. No promotion or approval is granted.
- Test on an isolated real Store/WeightConsolidation with a spy trainer and invalid coefficient; run focused existing U5/AG6 tests and the new integration regression, compile/privacy/diff; archive raw RED and GREEN. No native model or real weight training.

## Claim limits
Software training-boundary containment only. Does not prove AG6 retention, native learning, STEP2 utility, B3, JEPA or complete V13. Age0 RECORD_ONLY, jepa_weight=0 and all original negative gates remain unchanged.

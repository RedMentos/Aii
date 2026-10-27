# Z12c slot-wise World-JEPA persistent SHADOW checkpoint preregistration — 2026-10-27

Base: Claude PR637 head `7471a7fb61d453b2aa6c9500b896cfb564010a90`. Independent review-only child, not integrated into Codex/Termux runtime. File ownership: `v13/code/v13/world_jepa_slots.py`, new `tests/test_world_jepa_slots_checkpoint.py`, scoped CI/proof. Do not modify Z12c training, cohorts, hyperparameters, registered data, weights, source hashes or original negative gates.

## Functional missing capability
`SlotWorldJEPA.fit` trains real NumPy online encoder, EMA target and per-slot predictors, but the trained state is RAM-only; after process exit it cannot be used. This blocks actual persistent learned World-JEPA shadow utility and future runtime wiring.

## Acceptance
Provide a bounded, pickle-free, atomic inference-only NPZ checkpoint with explicit exact provenance binding. Trained model's `predict`, `confidence` and `slot_errors` must be **array-byte-identical** after restart. Wrong provenance, corrupted bytes, untrained save, missing expected provenance and interrupted atomic write fail closed, preserving the previous file. No permission to write facts, change ages, execute tools, promote `jepa_weight`, or claim native/Redmi/real-world learning. Run existing Z12c slot tests and new checkpoint tests with synthetic transitions, record RED then GREEN and original raw SHA256.

This is inference persistence only; optimizer/EMA training-resume state is not yet supported and must not be claimed. The saved checkpoint is a shadow model and does not automatically become a runtime predictor.

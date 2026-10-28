# Closed observed-store → fitted World-JEPA → private checkpoint → operator probe (prereg 2026-10-28)

Review-only child of three-child integration #835 at exact `41c05a078533677a2a7cd889fc28448a6fc96590`. This prereg precedes new code/tests; no main merge or owner branch changes.

## Purpose
Make the existing World-JEPA SHADOW path actually usable offline on a **closed** V13 SQLite store: SELECT-only `ReadOnlyStore` → existing `world_model.transitions` → strict `world_jepa_digital_shadow.make_dataset` → **train split only** WorldJEPA fit (seed 3, ensemble 2, bounded steps) → fresh private mode-0600 inference-only NPZ `world_jepa_shadow_checkpoint.save` → exact external SHA-pinned `world_jepa_shadow_operator_probe.infer` on heldout observations/actions. Emit only aggregate heldout confidence/OOD/label counts, source/NPZ digests and nonpromotion flags, **no raw IDs, inputs, latent vectors or paths**.

Require explicit `--ack-closed-store`, reject SQLite WAL/journal sidecars, symlinks, invalid/incomplete transitions, existing checkpoint, invalid steps. Preserve failed attempts; never overwrite. No Runtime wiring, tool action, optimizer persistence/resume, native inference, model downloads, external communication or age authority. Source digest is of canonical observed transition rows, **not independently authenticated DB bytes**.

## Evidence
Use an actual temporary SQLite fixture (64 synthetic actions), verify DB bytes unchanged, no WAL, training fit receives only registered training partition, checkpoint can reload and match operator probe, source/NPZ hashes correct, output omits synthetic action/event IDs and private paths. Negative tests for no acknowledgement, live WAL sidecar, existing checkpoint and insufficient rows. Pinned NumPy Linux software CI, raw exits, compile/privacy/diff; independent review and full suite before integration.

This is observed **digital outcome** SHADOW, not physical future-world prediction, proof of utility, Redmi or AGI. STEP2 UTILITY_FAIL, B3 L1 FAIL, Body-JEPA UNAVAILABLE, LP3 heldout FAIL, jepa_weight=0, Age0 RECORD_ONLY. Other Canon requirements remain open.

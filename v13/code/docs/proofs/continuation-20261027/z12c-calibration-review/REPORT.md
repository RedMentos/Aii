# Independent Z12c persistent World-JEPA calibration review — 2026-10-27

Review-only child of Z12c persistent SHADOW head `74bc1010826db437d3e1ef21fac9c8946986f89b` (itself based on Claude PR637). The NumPy slot model previously set `op_err` to **zeros** in `fit()` and allowed `confidence()` and inference-only `save()` before any measured operation error. This could label a model simulation confident merely because no calibration had happened. Source/ZIP digests could not correct that missing semantic precondition.

The candidate now invalidates calibration on fit/recalibration, requires a nonempty aligned one-hot calibration set with every operation class observed and finite nonnegative slot errors, and blocks confidence/checkpointing until successful calibration. `load()` accepts only an explicitly calibrated v2 inference checkpoint; old v1 archives are deliberately incompatible and need a reviewed re-export. This **does not prove** calibration examples are held out or representative; that remains an external evidence requirement.

## Preregistered RED and GREEN

Prereg `f8dbec37c9d1b3dbf3e166b54f9d36133c5ec549`, tests `073fbc30107ca3124ba58db9e2f8cc09b2f6256d` before source. Actions `40444019062` at `e908bdcc5f2416d4f7dd858c8d001c49bfa21540`: **16 tests, 6 FAIL** including uncalibrated confidence/save, missing-class and failed-recalibration authority, v1 acceptance and missing v2 metadata. Raw ZIP artifact 12706829139 SHA256 `7637df1e09d88b1920558b76f2ab773ec968f2a6bbfde4c4c2845d641f0b534e`.

Source `a88e2aa868a1939e5ecd837cad48cdde24265f77`, Actions `40444186901`: **16/16 PASS**, compile PASS, privacy CLEAN; original slot prediction/byte-identical checkpoint and world tests still PASS. Raw ZIP artifact 12707368107 SHA256 `2fd966a19f0f81a7b5703b86638b4a756b419d9bee536d3d94988bcde4c27557`. Both original ZIPs CRC/source/exit checked and saved byte-identically to private Library `/V13-Checkpoints/2026-10-27/Z12c-Calibration-Review/`.

## Claims / remaining work

Only synthetic NumPy SHADOW evidence. This does not activate World-JEPA in the live runtime, resume optimizer state, establish Body-JEPA, native weight updates, general semantic utility or Redmi performance. Deliberate v1→v2 incompatibility requires owner review; do not merge automatically. STEP2 UTILITY_FAIL, B3 L1 FAIL, Body-JEPA UNAVAILABLE, `jepa_weight=0`, Redmi UNMEASURED, V13 INCOMPLETE remain. Full-suite historical RED remains unchanged. Next: integrate only after independent review and build a source-bound runtime SHADOW observer or resume native C3 utility research with frozen evidence.

# Manual SHADOW probe amendment 1 — symlinked parent directory (2026-10-27)

Original prereg RED Actions 40444553695: 35 tests, 4 FAIL + 3 ERROR. First implementation `426b1d59c9b2d8f4330cb3dfa9e278ad5098cf15` GREEN Actions 40444625415: 35/35 PASS, compile/privacy CLEAN; original raw artifacts retained.

Independent review found an uncovered path-containment gap before release: `_path()` rejected a symlinked checkpoint file and a symlinked `world_jepa` leaf, but not a symlinked parent `<home>/checkpoints`. If that parent points outside the home, the file can still pass `path.resolve().parent == root.resolve()` and be read (even though exact digest/provenance still protect model identity). This violates the preregistered dedicated in-home path restriction.

Prospective adversarial control: copy the valid pinned NPZ into an external directory, replace only `<home>/checkpoints` with a directory symlink to it, and require `:world shadow load` to raise ValueError without persisting binding. Narrow fix: reject any symlink at `<home>/checkpoints` and require resolved root to remain under resolved home. Keep all original tests and original GREEN proof; new RED and repaired GREEN must be separate, with original raw bytes saved. No age/permission/model change.

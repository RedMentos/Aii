# Run263 — pinned public artifacts and actual Linux native Age-0 probe (prereg 2026-10-25)

Base: PR259 exact head `28a9ebcbe51661adb716ae5bdd9ca999dbf2af3c`. Exclusive ownership: new CI workflow and this proof directory. No production, historical tests, Canon, model registry, source/seed hash, native cohort, STEP2/B3/JEPA gates or user permission changes.

Goal: replace "missing from fresh scratch" with a real prerequisite recheck and, when permitted, download exact registered public models and pinned native runner to a fresh **isolated GitHub Linux** temp home. Existing `v13.bootstrap` validates all registered size/SHA256 values. Use only pinned URLs from `specs/models.json`, no model swaps, no silent hash substitutions, no user data. The LFM Open License remains recorded; this job does not assert operator license acceptance.

Serialize with existing `v13-native-c3-run131-serialized` group, no overlapping heavy jobs. Before downloads record current Linux CPU/RAM/disk/cgroup/compiler and exact Runtime+model manifest Git blobs. Isolated CPU Python `numpy==2.3.5`, `prompt_toolkit==3.0.52`. Run `python -m v13.bootstrap --home TEMP` bounded 1800s, then independently deep-verify all model SHA256 and run `python -m v13 --home TEMP probe` bounded 480s. Preserve raw stdout/stderr, exit codes, build log, native probe JSON and privacy result, including failed downloads/builds. Enforce actual exit codes after uploading evidence.

Claims: a PASS is Linux-native inference with exact registered weights on this GitHub host only; not Redmi, not Body-JEPA training, not STEP2 utility, not B3 L1, not jepa_weight activation, not 6-GB sustained RAM/thermal evidence, and not complete V13. A FAIL remains FAIL; investigate exact error and continue other independent work.

Exact next step: inspect Run263 CI, verify closed artifact digest and model hash report; compare native probe with existing frozen Linux evidence. Then separately run real two-body utility/second-attempt cohort under registered seeds and mobile validation when device is available.

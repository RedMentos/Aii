# World-JEPA persistent SHADOW inference interface — prospective registration 2026-10-27

Base: verified PR #650 exact SHA `9c6cb2435d11bf58d3b18b0d830aeda261809d3e` (descends from independent Z12c calibration PR #649 and Claude Z12c). Branch is review-only, not production. File ownership: new `v13/world_jepa_shadow_probe.py`, new `scripts/world_jepa_shadow_probe.py`, new `tests/test_world_jepa_shadow_probe.py`, scoped workflow/docs; do not edit frozen training sources, cohorts, existing optimizer or active runtime.

## Functional gap
The calibrated v2 slot World-JEPA can persist and load a digest-bound inference checkpoint, but no standalone operator can feed a current observation plus hypothetical per-slot action to that checkpoint and receive a bounded read-only SHADOW prediction and, if observed, per-slot error after restart. The current Z12c benchmark is a training/evaluation harness, not an inference interface.

## Acceptance (tests before implementation)
1. Load an existing v2 inference checkpoint only with exact SHA256 and exact expected provenance. Never silently train, fetch models, run file actions, activate tools, change Age, modify source facts, or give decisions authority.
2. Typed finite `before` (S x input_dim), exactly one-hot `actions` (S x op_dim), and optional `after` (S x input_dim) must match checkpoint dimensions. Reject bools, strings, nonfinite values, malformed rows, and invalid action vectors without partial output.
3. Return deterministic machine-readable `V13_Z12C_SHADOW_PROBE_V1` with checkpoint/input SHA, per-slot predicted target latent and ensemble spread, calibrated confidence/label, and optional actual per-slot error. All outputs finite, bounded, and marked `SHADOW_ONLY`, `action_executed=false`, `learning_performed=false`, `authority=0`. Never present a simulation as an observed fact.
4. Restart with the same checkpoint and observation yields byte-identical JSON. Wrong digest/provenance fails closed. Optional explicit output uses atomic file replacement; no output file is created on validation failure. CLI prints JSON to stdout by default, no implicit filesystem side effects beyond reading requested inputs.
5. Tests include a real small NumPy fit/calibrate/save/load on a synthetic slot world, tampered input, no-after, with-after, wrong checkpoint, no output on failure and JSON CLI invocation. Run a separate **unregistered** real-file-world Z12c smoke seed 211 (train=600, cf=12, attr=16, steps=50), preserving any failure, without reusing original preregistered 201/202/203 cohorts or claiming C1–C7 promotion.
6. Linux CI must close original raw logs/exit/source hashes and privacy scan; preserve RED/GREEN and any smoke failure, branch-scoped BUILD_STATE, private backup when permitted. No full-suite PASS claim without full suite; negative gates STEP2 UTILITY_FAIL, B3 L1 FAIL, Body-JEPA UNAVAILABLE, jepa_weight=0, Redmi UNMEASURED remain.

No new model dependency: reuse NumPy, existing SlotWorldJEPA v2 and stdlib only. This is an **inference utility bridge**, not a live Runtime hook or semantic/causal validity proof.

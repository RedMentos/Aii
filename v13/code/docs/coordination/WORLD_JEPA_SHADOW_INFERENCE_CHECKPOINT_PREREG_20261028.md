# World-JEPA SHADOW inference-only state checkpoint prereg — 2026-10-28

Review-only independent candidate on `assistant/v13-world-jepa-shadow-inference-checkpoint-20261028`, parent PR #826 `0cc5e59fc1c91a71b0b232b42f70668c562d9d2b`. Owner GPT-6. No edits to frozen `v13/world_jepa.py`, runtime, learning authority, model weights or registered cohorts. No real model checkpoints in Git.

## Goal
The current `WorldJEPA.fit` produces a fitted NumPy encoder/EMA target/ensemble but lacks a safe inference-state export/import. Add an **isolated SHADOW-only, inference-only** checkpoint module to save/reload its fitted latent predictor, action support and OOD calibration without refitting. It must reproduce `latent`, `predict`, `ood`, `confidence` and labels exactly across a process boundary. It does **not** resume Adam/EMA training or grant runtime/age authority; continual-learning optimizer persistence is a separate future package.

## Fixed design / tests
- Strict versioned NumPy NPZ with `allow_pickle=False`, canonical JSON metadata, explicit shapes and names, no arbitrary object loading.
- Exact external 64-hex source SHA256 pin required; file SHA256 returned and required on load. Reject wrong source/file hash, missing/duplicate/unexpected arrays, nonfinite weights/calibration, malformed shapes, invalid action support and oversized archive members. No path traversal/symlink.
- Save via fresh temporary file + fsync + exclusive hard link to a never-existing target, fsync directory, no overwrite. On error do not mutate existing checkpoint.
- Test deterministic small synthetic fitted model (fixed seed and steps) roundtrip equality; changed model/source/hash/metadata fail closed; no runtime or gate promotion.
- CI only pinned NumPy, focused tests + original `test_world_jepa` where feasible, compile/privacy/diff and closed raw ZIP. No model download, no private data or weights in CI artifact.

Negative gates: STEP2 UTILITY_FAIL, B3 L1 FAIL, Body-JEPA UNAVAILABLE, LP3 heldout FAIL, jepa_weight=0, Age0 RECORD_ONLY. This is a storage candidate, not evidence of learning utility.

# Run76 — isolated Claude Z12c slot-wise World-JEPA compatibility candidate (2026-10-28)

Owner GPT-6 scheduled continuation; review-only independent sibling of Run74, based on independently GREEN Run72 docs-head `2e294299ec79145a3fcffd8cf0a0c90f6fbc3b5c`, Actions 40778787735, original ZIP SHA256 `6d25e1ad8b714b50827482f3eb9bfb2dd4e0360805443ff4aa358582707612eb`, CRC clean, 35/35 SHA256SUMS, 112 focused/2648 full OK, privacy CLEAN, private backup byte-verified. Do not modify frozen `v13/code/v13/world_jepa.py` (Git blob `b95cd3fd9172ddef0fb88f0a7d70e2921c43e777`) or any registered Run64/67/69/71 source, seed, cohort or test.

## Reason and source provenance

Claude PR #637 `7471a7fb61d453b2aa6c9500b896cfb564010a90` reports Z12C_SLOT_WORLD_JEPA_PASS on synthetic-content file world with given slots, no runtime/Redmi integration. Independent review found its slot-wise module calls dynamic `_init/_init_pred/_init_inv` and `loss_grads` with latent dimension 8; frozen Run72 WorldJEPA has fixed latent dimension 16 and incompatible init signatures. Direct import would fail or alter frozen registered experiments.

## Fixed candidate before implementation

- Import exact Claude `world_jepa.py` Git blob `470377f999ccd250be284e674e4b8f165942889b` under **new isolated namespace** `v13/code/v13/world_jepa_slots_kernels.py` (same bytes, new path; source provenance explicit). Do not replace or monkeypatch `v13.world_jepa`.
- Copy Claude `world_jepa_slots.py` source blob `95de5e4b0c18f75a987b8602626a90257cde730d` to **new** `v13/code/v13/world_jepa_slots_isolated.py`, changing only the import from `v13.world_jepa` to `v13.world_jepa_slots_kernels` and the revision string to an isolated label. Record exact diff. Do not claim exact-byte identity for this intentionally adapted file.
- Copy Claude slotwise unit tests `f326460707ebf54696f684b2592f7c186eff46af` to new test path, changing only import to isolated module, plus explicit frozen-kernel immutability and no-monkeypatch tests. No new model weights, user data, native or phone inference. No training in Runtime, no authority.
- CI: pinned Git hashes for new files and frozen WorldJEPA, focused isolated slotwise + original frozen WorldJEPA tests, full software suite, privacy, closed original raw SHA256SUMS. Preserve RED. A unit-test PASS proves software compatibility only, not reproduction of Claude 201-203 benchmark, semantic action understanding, B2↔JEPA utility or whole-system completion.
- Research/claim limits: Claude prereg 205a0c4 preceded result 4e2a938; six aggregate criteria C1-C4,C6,C7 recompute from published per-seed JSON, but C5 Spearman cannot independently recompute because per-query confidence/error pairs are stripped. No fresh cohort chosen; any future quantitative comparison requires new preregistered source-disjoint data and negative controls.

All Age0 RECORD_ONLY, STEP2 UTILITY_FAIL, B3 L1 FAIL, Body-JEPA UNAVAILABLE, LP3 FAIL, jepa_weight=0, Redmi UNMEASURED and whole-system incomplete remain.
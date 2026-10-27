# World-JEPA frozen training-budget ablation — verified 2026-10-27

**Owner:** `codex/automation11-world-training-budget-20261027`, review-only child of PR #661 at `3e98b05663233913b9721d437f20d814999a31a1`. Original checkpoint and registered Z12c cohorts unchanged.

## Frozen input and fixed arms

Preregistered steps **10, 50, 200, 800** before training. Original real Linux file-world Actions `40453512115` ZIP SHA256 `f3f5eef1d0257c60438d80bf79508494a802f98d94e965f96fac4cf92c909be8`, source `bff9efa8995b82152c2de853581572991e1bfb8852af792cb02544f584f4b770`, training cohort `484ba3e1175800eeb1a21bbbb8e308721368b3391dc2e27811bd288e29d363dd`, seed212, first 192 train rows, last 48 clean calibration rows. Heldout seeds313/314/315, each 160 rows, all previously observed. No data re-collection or tuning.

Existing original 10-step checkpoint SHA256 `955ee6efd0eaf2f85803297773ad016d54a33c7c707cd0406b3ceb23739d5e51` remains untouched. **The 10-step arm reproduces all frozen original weights/calibration exactly: max absolute difference 0.0**. All four newly trained SHADOW candidates were saved with step-specific provenance, SHA verified and reloaded; independent restart recomputed heldout metrics. No runtime model replacement.

## Evidence

- Initial workflow attempts `40454483814`, `40454492464` failed from CI setup errors (inherited ZIP extraction path, wrong test module), preserved in Actions. `40454548553` exposed strict float comparison sensitivity under a different BLAS/OMP environment; original raw failed ZIP SHA256 `fc00724e3236ea065e3f68696ef055608cef02cd9f8f2605a1d743fdc69f4a3b` privately backed up. Restoring original single-thread BLAS/OMP environment fixed exact restart verification **without altering original auditor code or frozen evidence**.
- GREEN Actions `40454957085` at `7de8f8706e30d12eefdcb84f8837847c48b1564a`: **6/6 tests PASS**, all 4 arms restart-verified, independent verify exit0, compile0, privacy CLEAN. Original raw ZIP SHA256 `0c9ada699da8900038f97c4daca3107d16f331955ed7cc4f7d5e2d941c039f2f`, CRC clean, 20 files including every candidate checkpoint and raw per-arm JSON. Source SHA256 `e081fd252c0e715954092bc26f83b09c3d0408a58c06dd2f05518b404c6a9b10`; test SHA256 `77e73c8a3563241831140c99f307eb484fbd381890488d4f946cb37496bd2d5b`.
- Private persistent evidence: `/V13-Checkpoints/2026-10-27/World-Holdout-Utility/world-budget-40454957085.zip` (plus failed attempt and original frozen ZIP).

## Result (exploratory, previously seen heldouts)

All values below are **weighted per-arm action-minus-identity normalized target-latent MSE** across three heldout seeds; negative means action-conditioned prediction beats the same arm's identity/no-change target baseline. Because each training budget changes target encoder and latent normalization, raw MSE across arms is not an independent apples-to-apples model ranking.

| Training steps | Action − identity MSE | Action vs identity, seeds | Mean uncertainty |
| ---: | ---: | --- | --- |
| 10 | **+0.04284334** | Worse in 3/3 | 479/480 uncertain |
| 50 | **−0.05852516** | Better in 3/3 | 479/480 uncertain |
| 200 | **−0.17949107** | Better in 3/3 | 479/480 uncertain |
| 800 | **−0.18684503** | Better in 3/3 | 479/480 uncertain |

Checkpoint SHA256 by arm: 10=`4ce89511097d95a2d841d9f83a95bbb040cbc3c7a495134e1a1f309aaeed9661`; 50=`a95e6dd57b90989ecbc1b4bb0cb3050d3a64e9fd6e4168a8f44a79d061929f77`; 200=`d0bb49b0a1b002c42a1c5b3864356cdb99f9ac61c5de7c2a78bbffa9a5476834`; 800=`e8797fdf9814e27daf68750d7f9ee95069f9f7949aafe548c6558cc6e6e80f6c`.

**Interpretation:** The earlier 10-step identity deficit was strongly affected by undertraining on this toy file-world. Increasing the budget gives positive *within-arm* action-vs-identity results, but the heldout seeds were already inspected, confidence remains almost universally uncertain, and this is synthetic-content Linux only. It is **not** a fresh blinded generalization proof, causal utility proof, Redmi sustained proof, or STEP2/B3/Body-JEPA PASS.

## Next exact step

Freeze these candidate checkpoint hashes. Before new measurements, preregister **fresh unseen** independent real Linux file-world seeds (e.g. 316/317/318) and evaluate the fixed 10/50/200/800 candidates without any training/calibration or model selection on the new cohorts. Preserve original process logs, row timestamps, SHA and identity/rotated controls. Require a new independent restart verifier and compare against a target-encoder identity baseline within each arm. Even positive fresh results do not promote runtime authority without original registered gates and Redmi/native evidence.

STEP2 UTILITY_FAIL, B3 L1_FAIL, Body-JEPA UNAVAILABLE, `jepa_weight=0`, Age-0 approval and whole-system completion remain unchanged.

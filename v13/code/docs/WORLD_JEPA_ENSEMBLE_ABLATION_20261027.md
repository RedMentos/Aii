# Frozen World-JEPA ensemble-mean ablation — verified 2026-10-27

**Owner:** `codex/automation11-world-ensemble-ablation-20261027`, child of PR #660 at `85a88ffd48c59d618c5fdb04022813580418e9d0`. This is review-only; no main/AG5/Claude merge.

## Question and locked inputs

The v2 SlotWorldJEPA inference interface currently returns the **first** trained predictor, while ensemble spread is used only for uncertainty. Test whether arithmetic mean of the exact two saved predictors improves prediction on the **same original closed** heldout cohorts. Pre-registered before analysis in `docs/proofs/continuation-20261027/world-ensemble-mean/PREREG.md`.

Frozen original: Actions `40453512115`, ZIP SHA256 `f3f5eef1d0257c60438d80bf79508494a802f98d94e965f96fac4cf92c909be8`; checkpoint SHA256 `955ee6efd0eaf2f85803297773ad016d54a33c7c707cd0406b3ceb23739d5e51`, source SHA256 `bff9efa8995b82152c2de853581572991e1bfb8852af792cb02544f584f4b770`, training seed212, 240 rows, **only 10 training steps**. Heldout seeds313/314/315, 160 rows each. No new collection, fitting, calibration, coefficient tuning, authority or source/model/seed change.

## Implemented and tested

- New `scripts/world_jepa_ensemble_ablation.py`: exact frozen manifest/cohort/checkpoint hashes; independent NumPy weight-path encoder and predictor reconstruction, checked against existing V13 first-predictor output to 1e-12; read-only restart verification of original timing receipts; 16-row inference chunks; explicit negative gates.
- New `tests/test_world_jepa_ensemble_ablation.py`: five tests for exact scores, no writes, forged manifest, swapped seed, and modified checkpoint rejection.
- CI Actions `40454073831` initially failed only because the ZIP path guard incorrectly rejected legitimate top-level proof files; failure/log preserved. Corrected Actions `40454140942` at `f1ae6fa4ed96271518bc1ae02064c70a5db4316b`: **5/5 PASS**, ablation exit0, compile0, privacy CLEAN. Original raw ZIP SHA256 `a396e90409c7e5d36c4ca038635faa5c540e6df662eff376930ca1394e636309`, CRC/HEAD/exit verified. Source SHA256 `40505d3bb3600213198a73965b7b38e28137f9cff1b398b7981ca2ac7a90705b`; test SHA256 `a9b2ea5252632c332b31ed43b9590beaedbe77dc2ecb109d66185a145e39c7e2`.
- Completely independent local NumPy reference (does not import V13 modules): source SHA256 `9a28e2ca730bf0fa88285693f32e7cc7dbc09199a84f2ed8a95773025e2c98c1`, result JSON SHA256 `d4837acb616f03381648144d52096305c6c9a97925762e61dca1fbeb2bc23e45`; every weighted MSE matches GitHub CI to <1e-12.
- Original proof ZIP, reference source and JSON privately saved at `/V13-Checkpoints/2026-10-27/World-Holdout-Utility/` and re-materialized byte-exact. The rejected anyone-writable Drive location was not used.

## Result: negative for ensemble averaging

On the exact 480 heldout rows, normalized target-latent MSE:

| Arm | MSE (lower is better) |
| --- | ---: |
| Identity/no-change target encoder | **0.27064647** |
| Existing first predictor | 0.31348981 |
| Arithmetic mean of first + second | 0.34496149 |
| Second predictor alone | 0.38991495 |

Ensemble mean is **worse** than first in all three heldout seeds, and worse than identity in all three. The mean improves on the first predictor for almost no individual rows. Therefore **do not change** the current first-predictor default based on this result. It does not prove the entire architecture cannot work: this exact exploratory checkpoint was trained for only 10 steps on a small synthetic-content file world.

All STEP2 UTILITY_FAIL, B3 L1_FAIL, Body-JEPA UNAVAILABLE, `jepa_weight=0`, Age/approval and full-scope negative gates remain intact. No native/Redmi/semantic/causal utility proof.

## Next exact package

Keep original registered Z12c and the frozen 10-step checkpoint untouched. Pre-register a **fixed training-budget** ablation on the same closed training rows and separate original heldouts, with fixed steps and no posthoc tuning, to determine whether undertraining rather than ensemble aggregation explains the identity deficit. Preserve each failed arm and exact checkpoint/source hashes. Independently review before any runtime/default change. Existing AG5/World conflict integration remains a separate owner-controlled path.

Next verification: `cd v13/code && V13_FROZEN_WORLD_ROOT=/path/to/extracted-original/closed PYTHONPATH="$PWD:$PWD/scripts" python3 -m unittest -v tests.test_world_jepa_ensemble_ablation`.

# Preregistered fresh-seed replication of Z12c with strict v2 calibration — 2026-10-27

Base: PR #653 exact `3d39a7e0663ffbf72b804e5926822f2c9ab2ec7f`, itself independent review chain from PR #649. This branch is **evidence only**, not production, and makes **no changes** to training sources, original cohorts, seeds, hyperparameters or thresholds. Owner: independent V13 automation research, no concurrent native/model heavy job owner. The original Claude Z12c result for frozen seeds 201/202/203 was PASS and remains untouched.

## Exact frozen source blobs
- `scripts/z12b_world_jepa.py`: `2fd1366dc1b6d8c02803ee3254020f70e5bf3eb4`
- `scripts/z12c_slot_world_jepa.py`: `340b568a1270c82559901196f7cd8fcc04e14e0f` (PR #650 ablation control fix)
- `v13/world_jepa_slots.py`: `65636468f10ed22b1b743aba14a1144f55e9708f` (PR #649 strict calibration v2)
- `v13/world_jepa.py`: `470377f999ccd250be284e674e4b8f165942889b`
- `v13/common.py`: `8efd950c7bc221fbdae3fca200610cb383286001`

## New cohorts and fixed protocol
Fresh seeds **214, 215, 216**, no overlap with original 201/202/203, tiny smoke 211 or lifecycle 212. For each seed: 4,000 actual temporary Linux file-world training transitions, 10% held-out clean validation, 150 counterfactual states × 6 actually executed candidate actions, 300 attribution intervals, 3,000 optimizer steps, same model and controls. Use existing `scripts/z12c_slot_world_jepa.py` without modification:
```sh
cd v13/code
PYTHONPATH="$PWD:$PWD/scripts" OPENBLAS_NUM_THREADS=1 python scripts/z12c_slot_world_jepa.py /tmp/z12c-v2-fresh.json --seeds 214,215,216 --train 4000 --cf 150 --attr 300 --steps 3000
```
CI serializes all three seeds in one Linux runner, NumPy 2.3.5, prompt-toolkit 3.0.52, no native LLM/model downloads, no live user files. Preserve stdout/stderr/exit, result JSON, source SHA256, host metadata, privacy scan and all failures as original raw ZIP.

## Acceptance and interpretation (no posthoc tuning)
Reuse exact original C1–C7 from inherited `z12c-slot-world-jepa/PREREG.md`: covered retrieval ≥0.80 pooled and ≥0.70 each; held-out op-slot ≥0.70 and better control +0.30; no-action/shuffled covered ≤0.40 and model gap ≥0.30; no collapse rank≥3 and min std≥0.05; Spearman confidence/error ≤−0.30; attribution own-only SELF≥0.90, world-only WORLD≥0.90, none SELF≥0.80; action-free balanced at least 0.20 worse. PASS only if every original criterion passes, otherwise FAIL and retain raw. This is a **new replication** after strict v2 calibration, not a rewrite or reclassification of historical original PASS.

No B3/STEP2/Body-JEPA/native/Redmi/AGI promotion, no jepa_weight change, no age/approval changes. A passing result is evidence for a narrow given-slot synthetic-content file world, not general semantic world modeling. A failing result is preserved, not tuned away.

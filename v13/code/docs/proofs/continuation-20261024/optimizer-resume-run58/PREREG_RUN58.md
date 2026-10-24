# Run58 — exact shadow optimizer restart with source-bound checkpoint

2026-10-24. Base PR91 `1a8823d7eb5baaa11ddd20681f741baf73c9f3bd`. Own only `v13/code/docs/proofs/continuation-20261024/optimizer-resume-run58/*`; no production edits, no overlap with active owners.

Goal: make Run57's actual synthetic gradient training recoverable after a process restart while retaining original SourceRef/age gates and Run56 durable shadow receipt. Checkpoint must bind source dataset SHA256, SourceRefs, frozen base SHA256, step count, weights, Adam step/exp_avg/exp_avg_sq; no pickle. Manifest-last publication and fsync. A partial/crashed checkpoint is not a valid training authority.

Preregistered fixed cohort from Run57: 64 source-grounded train /64 heldout, seed 20261024, weight seed 1337, Adam lr .10, 120 steps, same batch sequence; compare uninterrupted 120 vs 60+save+fresh-model-restore+60 bitwise for model and all optimizer moments; heldout accuracy identical. Tests: source revoked after save prevents resume; wrong dataset hash, tampered NPZ/manifest, wrong step, missing manifest and generation change fail closed; resumed delta can publish only as SHADOW receipt with valid sources. At least one fresh-process save/restart test. Preserve failures, do not alter thresholds or seeds.

Evidence: Linux synthetic SQLite/PyTorch/NumPy, not actual Store/Runtime, native C3/Bodies, Redmi, general JEPA or full V13. Original STEP2 UTILITY_FAIL, B3 L1 FAIL, Body-JEPA UNAVAILABLE, jepa_weight=0, V13 INCOMPLETE.

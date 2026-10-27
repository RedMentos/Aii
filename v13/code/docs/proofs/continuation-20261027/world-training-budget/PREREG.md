# Frozen World-JEPA training-budget ablation — prereg 2026-10-27

Parent: `codex/automation11-world-ensemble-ablation-20261027` at `3e98b05663233913b9721d437f20d814999a31a1`. No AG5/Claude/main integration.

## Frozen data and controls

Use ONLY original real Linux file-world training cohort from Actions `40453512115`, ZIP SHA256 `f3f5eef1d0257c60438d80bf79508494a802f98d94e965f96fac4cf92c909be8`, cohort SHA256 `484ba3e1175800eeb1a21bbbb8e308721368b3391dc2e27811bd288e29d363dd`, source SHA256 `bff9efa8995b82152c2de853581572991e1bfb8852af792cb02544f584f4b770`, training seed212. Original 240 rows, first 192 for fit and final 48 clean for calibration (exclude any world-overlapping calibration rows exactly as original lifecycle). Preserve original 10-step checkpoint SHA256 `955ee6efd0eaf2f85803297773ad016d54a33c7c707cd0406b3ceb23739d5e51` unchanged.

Frozen heldout evaluation: original independently collected seeds313/314/315, 160 rows each, exact pinned manifest/cohort hashes from PR #660. Never fit, calibrate or tune using any heldout rows. No new file-world collection, no source/model/seed change to registered cohorts.

## Predeclared arms and measurements

From scratch using the exact existing `SlotWorldJEPA` implementation, same seed212, ensemble=2, same train/calibration split, same architecture/optimizer, fit for **10, 50, 200, 800 steps** (fixed in advance). The 10-step arm is a deterministic reproduction control; require weights/predictions to match the original frozen checkpoint to numeric tolerance before interpreting other arms. The other three are new SHADOW candidate checkpoints, never runtime replacements. Each candidate must be saved with explicit step-specific provenance, reloaded from exact SHA256, and evaluated without further learning.

For each arm and each heldout seed, compute the same target-normalized action-conditioned MSE, target-encoder identity/no-change MSE, one-row-rotated-action MSE, action-minus-identity and action-minus-rotated deltas, mean confidence, and uncertain count. **Within-arm delta vs identity is primary** because target encoder and normalization evolve with training; raw MSE across different target encoders is not a direct apples-to-apples comparison. Record wall time and peak RSS as Linux-only diagnostics, not Redmi performance. Do not select a winner or tune hyperparameters based on these already observed heldouts; the result is exploratory.

## Required evidence and negative gates

Exact original ZIP SHA/CRC and closed raw input hashes; explicit training/calibration cohort indices, each candidate checkpoint SHA, independent save/load prediction equality, all per-seed scores including negative arms, raw stderr/logs, source/test SHA, privacy scan and meaningful tests. No overwrite of original checkpoint, registered Z12c C1/C2/C3 failures or original artifacts. Keep STEP2 UTILITY_FAIL, B3 L1_FAIL, Body-JEPA UNAVAILABLE, `jepa_weight=0`, Age/approval and full-scope negative gates. No native/Redmi/semantic/causal utility claim.

If an arm fails or is too expensive, preserve its failure and continue remaining fixed arms if possible; never fabricate results. No live model promotion. A future *fresh, blinded* cohort and native/Redmi proof would be required before any runtime change.

# WP-Z12b registered heldout World-JEPA ensemble/causal-signal ablation

2026-10-27 UTC. Review-only child of PR #748 exact parent `50c0a73c22d53eeb708a491f7c6b26cddd492d8d`, inherited World-JEPA blob `5ffd56097e66a37e2922e39d1dc0ba86cb28a760`. This preregistration precedes evaluator source, test and workflow. Owner scope: new `scripts/world_jepa_heldout_ablation.py`, new `tests/test_world_jepa_heldout_ablation.py`, dedicated workflow, this proof folder. Do not edit model code, original cohort, master pins or runtime.

## Frozen cohort and experiment
New synthetic 4-bit world: each one-hot action flips its selected bit; four irrelevant integer-grid noise slots independently change. Raw source rows are generated with Python `random.Random(seed)` in the exact order: four bits randrange(2), four noise integers randrange(-2000,2001), one action randrange(4), four independent next-noise integers randrange(-2000,2001). Canonical raw-row JSON `sort_keys=True,separators=(',',':')` is hashed with SHA256 before floating conversion. No model-facing targets from heldout are used during fit.

- Training: 1000 rows, seed `20261027`, SHA256 `317410989c41a3e75032dfd02692da7d126596ab2ff350996e7b1b383a055822`, action counts [249,266,246,239].
- Heldout: 240 disjoint rows, seed `20261107`, SHA256 `011f122f4290f5b14cae8699841ae477cfcc0837958a0bc30c95e3e1af06b20b`, action counts [64,68,61,47].
- Three fixed model seeds [3,7,11], 1000 fit steps each, ensemble=3, original constants and optimizer unchanged. No adaptive retuning after looking at scores.
- Compare on exactly the same heldout observations and each trained model: (a) all-member mean, (b) first member, (c) wrong action `(action+1)%4` passed to mean, (d) persistence baseline `latent(X, target=False)`. Score target-latent standardized MSE using **train-only** `zsd`; report each seed and pooled means.
- Primary ensemble criterion: pooled mean MSE <= 0.95 × first-member MSE **and** >=2 of 3 seeds individually improve.
- Separate action-signal criterion: pooled mean MSE <= 0.90 × wrong-action mean MSE **and** <= 0.90 × persistence MSE. This is a synthetic action-grounding signal, not causal competence or real-world utility.
- Confidence sanity: all heldout confidence with `counts=None` finite within [0,1], labels only `MODEL_SIMULATION`/`SIMULATION_UNCERTAIN`; no `REAL` claim.
- If any input/hash/shape fails, no score; record FAIL. Do not rewrite failed attempts, alter seeds, tune thresholds or silently replace the cohort.

## Evidence and limits
Dedicated GitHub Actions job: pinned NumPy, no model download, no native model/Redmi, raw exits and artifact. Unit tests prove generator SHA, scorer separation and tamper refusal. Preserve original failures. The evaluator reports both PASS and FAIL for criteria and never promotes LP1/LP2/BJ1/STEP2/B3, `jepa_weight=0`, Age authority 0 or whole-system completion. Next after measurement: independent review, new harder heldout tasks if justified, eventual real model/Redmi measurements.

# WP-Z12b registered heldout World-JEPA ensemble/action controls — measured result

2026-10-27 UTC. Draft PR #749, review-only child of PR #748 original `50c0a73c22d53eeb708a491f7c6b26cddd492d8d`. Prereg `e64eb87867f2efa9ee10b69f0fd613bb11d18d8c` was committed and verified before evaluator, tests or workflow. Original `world_jepa.py` unchanged, blob `5ffd56097e66a37e2922e39d1dc0ba86cb28a760`.

## Exact source and measurement

GitHub Actions **40550853611 SUCCESS**, exact source/workflow `255a93e2bce328551c78cd4bbaa3d03aef4f7a61`, harness Git blob `6982e857573f0420cc83ae83ed8529da977c78bb`. Frozen synthetic train 1000 seed 20261027 SHA256 `317410989c41a3e75032dfd02692da7d126596ab2ff350996e7b1b383a055822`; disjoint heldout 240 seed 20261107 SHA256 `011f122f4290f5b14cae8699841ae477cfcc0837958a0bc30c95e3e1af06b20b`. Model seeds 3/7/11, 1000 steps each, ensemble 3, NumPy 2.2.6. Original training constants/optimizer unchanged. All source hashes verified before fit. **14/14 software tests PASS**. INSTALL/UNIT/MEASURE/COMPILE/PRIVACY/DIFF raw exits all 0. Raw artifact `12753484971`, ZIP SHA256 `11cd8474537c59446fa1306e6f36cdea84636a1ca35046c3717b54c77e399a65`, CRC PASS.

### Heldout target-latent standardized MSE (lower is better)

| Seed | Ensemble mean | First member | Wrong action | Persistence |
|---|---:|---:|---:|---:|
| 3 | 0.383743 | 0.404044 | 1.678466 | 1.323779 |
| 7 | 0.404008 | 0.450039 | 1.646767 | 1.361920 |
| 11 | 0.382600 | 0.415205 | 1.671301 | 1.359778 |
| **Pooled** | **0.390117** | **0.423096** | **1.665511** | **1.348492** |

Independent raw-receipt arithmetic rechecked pooled means exactly (float rounding only) and both frozen gate formulas. Ensemble mean improves MSE **7.79%** vs first member and all three seeds individually improve; prereg ensemble >=5% criterion **PASS**. Correct-action ensemble MSE is **76.58% lower** than wrong-action control and **71.07% lower** than persistence; prereg synthetic action-signal criterion **PASS**. This is a *synthetic heldout latent prediction* result, not real-world causal utility. The score target is the model's own EMA latent, not a separately validated external-world target.

Mean model confidence on heldout was ~0.659–0.681, and 0–0.4% rows labeled uncertain; **this is not calibration evidence**. Calibration and action-state conditional coverage remain open. Source/control hashes and evaluation were not tuned after seeing the result.

**Private persistent backup:** original Actions raw ZIP uploaded to native private Library `/V13-Checkpoints/2026-10-27/Automation11S-World-JEPA-Heldout/`, then re-materialized SHA256 byte-identical. Rejected anyone-writable Drive destination not used. Public GitHub contains only synthetic code/metrics, no private raw user data.

## Claim limits / next

World-JEPA remains experimental SHADOW and not runtime-wired; no native LLM, B1/B2, Redmi or actual environment trial. LP1 NO_ATTRIBUTABLE_GAIN, LP2 ALIGNS_NO_GAIN, BJ1 NO_SIGNAL, STEP2 UTILITY_FAIL, B3 L1 FAIL, `jepa_weight=0`, Age authority 0, V13 incomplete. No main merge. Independent review required. Next substantive work: harder state-action OOD/novel-action heldout controls with separate preregistration, or resume blocked LP3 native utility diagnostics after owner/resource check. Do not infer learned general intelligence from this synthetic result.

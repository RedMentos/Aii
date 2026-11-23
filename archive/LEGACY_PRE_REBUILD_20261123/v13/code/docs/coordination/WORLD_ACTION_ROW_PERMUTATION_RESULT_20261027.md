# World-JEPA split-isolated action-row control — closed synthetic result (2026-10-27)

**Scope:** review-only child of PR #771 exact parent `c84b95142e30dabd834e0cb5e495b3b8511a0a0e`; not `main`. Prereg `00f1dd2fa737fe5cb3a9ea074e437c51233aa040` predates new script, tests and workflows. Owner: GPT automation11 World-JEPA review. Frozen model, bridge, probe, closed-store wrapper and fair-baseline blobs unchanged. No native LLM, Redmi, private observed DB, production wiring, or learning/age promotion.

## Verified raw evidence

- **Focused software Actions 40584035458 SUCCESS:** 17/17 tests PASS, FROZEN/PREREG/INSTALL/UNIT/COMPILE/PRIVACY/DIFF exits 0, privacy CLEAN. Original ZIP artifact `12771385044`, SHA256 `dbabefeb21df8c07ef40bc0f4198b4b4cdcea6b94d49ab64bfabae43e0223e9f`, CRC PASS, HEAD `b55160560f00f422f155a594ebf1491521cc6b40`.
- **400-step synthetic SQLite Actions 40584122246 SUCCESS:** FROZEN/PREREG/INSTALL/SYNTHETIC/COMPILE/PRIVACY/DIFF exits 0, privacy CLEAN. Original ZIP artifact `12771185604`, SHA256 `a4b8e69843e8bd197992c3b4a48f0aa04b3154f70db8b0ed1bb10166df48be5b`, CRC PASS, HEAD `543b21941a8289723600204ce95c9ab6edd8eca3`. Read-only SQLite file bytes unchanged, no journal sidecars. Private Library backup of both original ZIPs under `/V13-Checkpoints/2026-10-27/Automation11-World-Action-Row/` was re-materialized byte-identical (SHA256 match).
- Frozen source SHA256 `21bb5a49906676050a1caf755ce441b36a483b3cb8db8d3f1a8a9048e2a7a0bf`, train IDs `e526ec41c33f4f639d662e053cbb8757de66737babc76df442a7d1eaed2c164b`, heldout IDs `dce3c8c36cf08617c193ea628112964796c23bbd78a5eb353c965396816b0760`. n64, train47, heldout17, seeds3/7, 400 steps, ensemble3, ridge lambda0.01. Script blob `63e3844aa0b04ed3635c046e068b7e96cc01ddc9`. Train/heldout row shift changed 100% of action identities in each split, exact split action counts preserved.

## Findings (pooled MAE; lower is better)

| Readout | MAE |
| --- | ---: |
| Scaled state-only ridge | 0.000241702 |
| Scaled state+action direct ridge | 0.000276405 |
| Correct predicted-latent, seed3 | 0.000292077 |
| Row-shuffled action predicted-latent, seed3 | 0.000221909 |
| Column-rotated action predicted-latent, seed3 | 0.000294590 |
| Correct predicted-latent, seed7 | 0.000253072 |
| Row-shuffled action predicted-latent, seed7 | 0.000235642 |
| Column-rotated action predicted-latent, seed7 | 0.000232078 |

**Result:** In both seeds the row-shuffled control **beats** the correctly paired action latent on this synthetic heldout. The legacy column rotation is a bijective action recoding, not a true action-association break. No action-specific incremental JEPA utility is attributable here. State-only direct ridge also outperforms the correctly paired latent for seed3 and is competitive for seed7. This is a tiny deterministic synthetic digital-outcome cohort, not proof that the architecture cannot work on real data. No significance or causal claim; no threshold tuned.

## Preserved negatives and continuation

LP1 `NO_ATTRIBUTABLE_GAIN`; LP2 `ALIGNS_NO_GAIN`; BJ1 `NO_SIGNAL`; STEP2 `UTILITY_FAIL`; B3 L1 `FAIL`; `jepa_weight=0`, `age_authority=0`, `redmi_measured=false`, `whole_system_complete=false`. No trained weights persisted, no runtime hook, no model/seed/cohort changes.

**Open:** action-specific information may be obscured by a near-deterministic synthetic outcome/state relation. Next authorized package: preregister a *new* independent synthetic cohort where the same state appears under distinct randomized actions and outcome has an explicit action effect; compare correct, row-shift, state-only, and direct baselines with disjoint heldout state-action combinations. Keep this frozen cohort and its negative result unchanged. Actual observed closed store and Redmi remain unmeasured.

**Exact focused reproduction (software):** `cd v13/code && PYTHONPATH=.:tests python -m unittest -v tests.test_world_jepa_action_permutation_control`. **Exact registered 400-step reproduction:** rerun `.github/workflows/world-action-row-synthetic400.yml` on this review branch and verify the three registered SHA256s and raw exits. Do not infer results from the unrelated `--synthetic-smoke` fixture. Independent review and reconciliation required before any integration.

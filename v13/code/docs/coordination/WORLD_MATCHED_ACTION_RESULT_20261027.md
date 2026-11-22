# World-JEPA matched-state heldout-action synthetic cohort — observed result 2026-10-27

Review-only child of PR #775 exact parent `3bf1b9a06b2eba573635880df67a5cddba650850`, not main. Prereg `d00c35b4daddac7f30cadb9a1489f61c535872dc` before source/tests; model `5ffd56097e66a37e2922e39d1dc0ba86cb28a760` unchanged. Owner GPT automation11 World-JEPA research. This is a **new, separately registered synthetic cohort**, not a replacement for the n64 SQLite negative result.

## Closed evidence

- Focused Actions **40585419665 SUCCESS**, 12/12 tests PASS, all FROZEN/PREREG/INSTALL/UNIT/COHORT_HASHES/COMPILE/PRIVACY/DIFF exits0, privacy CLEAN; ZIP artifact `12771066871`, SHA256 `fa933144d5af7ffb2e23af8ce3b8bcba68a8a6693488f830f76a625ad12d1c59`, CRC PASS, HEAD `8b4ae067fd124794b4daf5463ce69d51ce410052`.
- Registered 400-step Linux NumPy Actions **40585620040 SUCCESS**, all FROZEN/PREREG/INSTALL/SYNTHETIC/COMPILE/PRIVACY/DIFF exits0, privacy CLEAN; ZIP artifact `12772291356`, SHA256 `6e015a3741ff0bc07293192244b8773f0b8df5396e6fd9159b784b7828009a1e`, CRC PASS, HEAD `e24b58b2fc431a40a6d0aee274a2670003fe5df2`. Source script blob `f4c1136bb9a527a776522ccd776f03c390bdd3a3`; prereg blob `7ea24ad07c734f2bd658c25c124e0f01c4ce53d1`.
- Cohort source SHA256 `65f6881137771a87a5c7a8353b349ade633a96064a05a884c9771ccc06b4639e`, train IDs `d86d0d975e24d55cf4564905d9eeb6c49bf7022191d0905a33fd4a5ce043c537`, heldout IDs `c09921ffb68612ad7991bea716cef291c113ec87b4955a97f61be9325b52c9b7`. n192 (48 states ×4 actions), train144, heldout48, exactly 12 heldout per action, same states but disjoint state-action pairs. Seeds3/7, steps400, ensemble3, ridge lambda0.01, independent shuffle seeds11/23/37, no posthoc selection. Original ZIPs privately backed up and re-materialized byte-identical under `/V13-Checkpoints/2026-10-27/Automation11-World-Matched-Action/`.
- Source-wide full software regression `.github/workflows/world-matched-action-fullsuite.yml` requested separately; its result must be appended only after actual completion.

## Result (pooled heldout MAE, lower better)

| Readout | Pooled MAE |
| --- | ---: |
| Scaled state-only ridge | 0.160966744 |
| Scaled state+action direct ridge | **0.088868108** |
| Correct JEPA latent, seed3 | 0.109244161 |
| Correct JEPA latent, seed7 | 0.102825314 |
| Row-shuffled latent, seed3, seeds11/23/37 | 0.106431230 / 0.100375504 / 0.089625606 |
| Row-shuffled latent, seed7, seeds11/23/37 | 0.096803567 / 0.102426232 / 0.090705311 |

**Interpretation:** The direct state+action baseline beats both correctly paired JEPA latents in pooled MAE. All **six** row-shuffled controls beat their corresponding correct latent. Correct JEPA improves *duration* and *output-character* errors over direct for both seeds (duration 0.01247/0.01441 vs 0.01708; characters 0.00424/0.00303 vs 0.00505), but worsens binary-success MAE (0.3110/0.2910 vs 0.2445), so no overall incremental utility. Action identity is important in this designed cohort (direct MAE much better than state-only), but the trained JEPA predicted latent does not demonstrate action-specific advantage over the row-shuffled control. This is a controlled synthetic negative, not evidence that JEPA is impossible or a real-world causal result.

## Gates and next package

Keep LP1 `NO_ATTRIBUTABLE_GAIN`, LP2 `ALIGNS_NO_GAIN`, BJ1 `NO_SIGNAL`, STEP2 `UTILITY_FAIL`, B3 L1 `FAIL`, `jepa_weight=0`, `age_authority=0`, no Redmi/native LLM measurement, no runtime wiring, no weights persisted, `whole_system_complete=false`. No changes to frozen earlier cohorts.

**Next priority:** stop expanding synthetic action controls; return to the roadmap's STEP2/B1+B2 semantic complementarity, C3 actual answer-consumer and B3 native receiver/Redmi gates. A future real observed digital-outcome cohort needs permission/privacy-safe source-disjoint data and a fixed protocol. Exact focused command: `cd v13/code && PYTHONPATH=.:tests python -m unittest -v tests.test_world_jepa_matched_action_cohort`. The registered 400-step result is reproducible by rerunning `.github/workflows/world-matched-action-synthetic400.yml` on this review branch and checking all source/train/heldout hashes. Independent review required before integration; no auto-merge.

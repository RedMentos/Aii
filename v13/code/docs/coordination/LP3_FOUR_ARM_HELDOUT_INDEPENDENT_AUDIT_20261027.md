# LP3 four-arm heldout — independent raw-artifact audit (2026-10-27)

**Review-only child of PR #774**, exact parent `2b4905ba83f190ee4345b4af3fdf07f17b61f28a`, not main and not a change to its frozen native script, model, training facts, source, seeds, or gate. This is a **retrospective audit of an already registered run**, not a new preregistration or a rerun. Original prereg commit `8fa8f59833360c07370d43c2be5679ba81a3603b` predates the workflow and all four arms.

## Original raw evidence independently checked

Linux-native Actions `40580606132` **SUCCESS**, run head `2b4905ba83f190ee4345b4af3fdf07f17b61f28a`, original artifact `12769963825`, original ZIP SHA256 `2df70f533aa0d00836c096006f7e49fe4e78af78fce33822ab2ef9c2cb18c936`, CRC PASS. All ten recorded FROZEN/PREREG/INSTALL/UNIT/DOWNLOAD/VERIFY/NATIVE/COMPILE/PRIVACY/DIFF exit codes were 0; privacy CLEAN. **34/34 focused software tests PASS.** Exact pinned master `LiquidAI/LFM2.5-350M`, revision `120bf032c36dd1273de754669da040dba7ad4982`, SHA256 `1c9c77a4471a7f590f85240f74ed1fc26df7fbde88c3006724e2f93ca993ea4e` verified in the original native log.

Frozen script blob `87b5773d89e7dd1ee87f91e389919d4c43d29aa6`, frozen trajectory blob `488cd12de3d5103e2a456f42148697fd15d66bc6`, prereg blob `40d71f9bf036aaba59eb8281f03aeffb7e2b4300` each independently matched the remote branch. Raw ZIP privately backed up to `/V13-Checkpoints/2026-10-27/Automation11-LP3-FourArm-Audit-Review/NATIVE_40580606132_sha2df70f53.zip` and re-materialized byte-identical.

## Registered four-arm outcome (12 prompts per family; CE lower better)

| Frozen feature norm / LR | Original own CE / top1 | New-phrasing own CE / top1 | New-phrasing wrong-source CE | Retention CE change |
| --- | ---: | ---: | ---: | ---: |
| raw / 0.005 | 9.8417 / 0 | 18.2607 / 0 | 18.2606 | -1.9226 |
| raw / 0.0005 | **3.0430 / 4** | **10.6486 / 0** | 11.3137 | **+1.8192 (degrades)** |
| layernorm / 0.005 | 8.3463 / 1 | 17.0292 / 0 | 17.0289 | -0.7795 |
| layernorm / 0.0005 | 9.2083 / 1 | 18.2175 / 0 | 18.2460 | -2.3942 |

All four arms started from the same trainable SHA256 `f422575d1b01c6446852e9f9539082a2b097dd5bab00aec4f70184179505a033`, each trained 24 steps on the **same six facts** (seed109). The second family uses new phrasings, not new facts. The independent audit rechecked every arm's `both_families_meet_pilot_criteria=false`, all new-phrasing first-token top1 counts **0/12**, and `utility_proven=false`. Raw LR0.0005 improves original-family CE and 4/12 top1, but misses all new-phrasing top1 and violates retention bound; the result cannot establish generalizable answer utility. Original raw LR0.005 gradient saturation/vanishing signal remains, no failed run overwritten.

## Scope, gates and exact continuation

This is **Linux-native six-fact reused-cohort research only**, not a Redmi run, real B1/B2 Body-JEPA proof, production C3 consumer, independent-fact generalization or long-term retention. LP1 `NO_ATTRIBUTABLE_GAIN`, LP2 `ALIGNS_NO_GAIN`, BJ1 `NO_SIGNAL`, STEP2 `UTILITY_FAIL`, B3 L1 `FAIL`, `jepa_weight=0`, `age_authority=0`, whole-system incomplete. No model weights were published, no runtime source modified, no gate promoted.

**Next priority:** do not select the best arm posthoc or keep tuning this six-fact cohort; return to the existing roadmap's real B1/B2 semantic complementarity, C3 answer-consumer and B3 receiver prerequisites. A future LP3 proof requires a separately preregistered disjoint-facts/independent-host and retention protocol. Exact recheck: `cd v13/code && PYTHONPATH=.:tests python -m unittest -v tests.test_lp3_four_arm_heldout tests.test_lp3_lr_norm_ablation tests.test_lp3_optimizer_trajectory tests.test_lp3_state_prefix`; original native workflow `.github/workflows/lp3-four-arm-heldout-review.yml` remains unchanged. Independent review required, no auto-merge.

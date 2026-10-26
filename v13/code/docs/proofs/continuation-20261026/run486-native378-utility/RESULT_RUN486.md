# Run486 — actual Linux-native378 paired utility (descriptive, no gate promotion)

**Original native evidence:** Run479 Actions 40281793150 (GREEN), nine structurally verified native arms, 378 frozen rows. Source head `55d7f672aafec8b92ce0878253f88f9681d8bf22`. Safe no-model artifact `12633269066`, ZIP SHA256 `a87acfa38688e66e603fe9c07cbc0762b231a6eb74527a8010c595e487e46afe`; raw native artifact `12633398520`, ZIP SHA256 `24268aede979c0e122ed05afe01141f61546b8077312ae42ce52f5c8ea4f65bf`.

**Independent no-model utility:** Run486 Actions 40284808262 GREEN (also 40284773270 GREEN). Frozen Run468 nine-receipt verifier, Run469 paired utility and Run470 within-arm complementarity read the original SHA-pinned export; no model installation, training, or native inference. The earlier RED Actions 40284529482 is retained: GitHub upload-artifact omitted 64 empty directories, causing `EXPORT_INVENTORY_MISMATCH`. The follow-up recreated *only* empty directories explicitly listed by the authenticated Run409 manifest; all 211 copied file bytes were unchanged. First RED artifact `12633219653`, ZIP SHA256 `9ac39a02776de0f03a3a7e84844a6022daa6fa02f52d68ee8b12801a47ec252b`.

## Frozen 3-seed / 6-fixture / 7-variant exploratory results

Values below are mean tool-replay utility, not accuracy of an independent acceptance cohort.

| Arm | B1 only | B2 only | Both exact | Same-policy dual | Both none | Both control |
|---|---:|---:|---:|---:|---:|---:|
| O (off) | .681 | .097 | .509 | .722 | .292 | .250 |
| P (pointer) | .704 | .097 | .597 | .657 | .310 | .375 |
| S (shared-body) | .620 | .088 | .421 | .676 | .338 | .352 |

For the primary `both_exact` variant, P − O = **+.088** and P − S = **+.176** across 18 paired seed×fixture cells. P − O has 6 wins, 7 ties, 5 losses; P − S has 7 wins, 7 ties, 4 losses. These are descriptive paired differences, **not** a statistically established causal gain.

**Complementarity is not established.** The exploratory strict-dominance diagnostic is **false for O, P and S**. Within the pointer arm, `both_exact` is **−.106** versus `b1_only` and **−.060** versus `same_policy_dual`; B2-only utility is .097. Thus the pointer improves the dual-exact route relative to off/shared-body, but this cohort does not show that B1 and B2 complement each other better than relevant controls.

The Run394/397 six-fixture cohort is **not** the canonical ten-episode preregistered STEP2 acceptance cohort. Original negative gates remain: `STEP2 UTILITY_FAIL`, `B3 L1 FAIL`, `Body-JEPA UNAVAILABLE`, `jepa_weight=0`, `latent_authority=0`, `Redmi unmeasured`, whole V13 incomplete. No AGI or complete architecture claim.

**Next:** independent review of source-attested raw utility; then preregister the actual ten-episode STEP2 acceptance cohort with distinct B1/B2 information, C3 consumer controls, and an honest no-complementarity outcome if controls still dominate. Do not rerun Run479 models merely to regenerate evidence.

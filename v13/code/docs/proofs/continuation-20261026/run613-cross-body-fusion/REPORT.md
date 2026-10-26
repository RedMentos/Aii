# Run613 — original native B1/B2 fixed lexical fusion, negative result

Recorded 2026-10-26 UTC. Review-only PR608, child of Run612 PR607 exact verified head `7682123d4a206330331cf8b65d7457003913771e`. Owner GPT automation11. This is **posthoc to Run608**: original model outputs/cohort/results were previously observed. Protocol for the 50/50 fusion and controls frozen in `8f058d4d902ad0c55a0f5cc0cc93544f18a8f21f` before this new analysis; no claim of independent new heldout data.

## Result: NO_FUSION_PROXY_GAIN

Original Run608 Linux-native read-only B1/B2 states and 60/20 topic-disjoint cohort, **20 heldout prompts / 10 fact pairs**. Top1 retrieval of the opposite paraphrase among 19 nonself candidates:

| Fixed candidate method | Top1 | MRR |
|---|---:|---:|
| Lexical Jaccard | 0.30 | 0.427095 |
| Ridge B1→B2 mapped native | 0.25 | 0.420972 |
| B1-only native cosine | 0.55 | 0.690833 |
| B2-only native cosine | **0.65** | **0.800000** |
| Frozen 50/50 lexical + mapped-native fusion | 0.40 | 0.535538 |

The fusion improves lexical by +0.10 but **loses 0.25 against the best single-body B2**. Against 200 fixed train-label shuffles (lexical unchanged), fusion empirical p=**0.1144278607**, null mean top1=0.261; it fails the prospectively specified p<=.05 and >=+0.10 against each single-body baseline. **No cross-body complementarity, bridge utility or semantic transfer demonstrated.** B2-only native cosine is an exploratory within-space paraphrase proxy on this narrow synthetic cohort, not general model accuracy or proof of two-body benefit.

## Closed original evidence / independent checks

- Original Run608 native Actions `40402123481`, artifact `12688049715`, ZIP SHA256 `9cae2ac55a9ac773f3d3c2433d7ad485f479d8dc7b79f32e7555014f0eaad732`; original `RUN608_STATES.npz` SHA256 `c6e6a7a6521d14c90805a996e723e9cd7716cd6ba6d13577480eff30349625ca`. Original cohort blob `f452bdf80bb8d8a784c1909c98e310041d3157aa`. No new native inference/weights.
- Run613 Actions `40406884945` exact source/workflow head `c4449462317468c733be4495a8164295db7c3fc4` **SUCCESS**: 6 model-free adversarial tests PASS; original outer ZIP/hash/manifest and original negative gates checked; offline NumPy analysis exit 0, privacy CLEAN.
- New raw artifact `12691238052`, outer ZIP SHA256 `4a465b52a74bb3fab29f51572ee0937c8b86804b6a83e3a7fd81b027e9a14261`, GitHub digest matched, all **12/12** raw SHA256 manifest entries independently rehashed. Script SHA256 `f035c717105dbb82981fe8d512c8e3ec57266af88dcd0022d563025a373afdcb`; tests SHA256 `24419a402bd2ad40ff1d800c70460302a9c08cda10293b7fb607699c35a7bd9c`.
- Independent local read-only numeric recomputation from original NPZ (separate code path) reproduced B1-only top1 .55 / MRR .690833 and B2-only top1 .65 / MRR .80 exactly. No independent native model rerun.

## Gates and next

STEP2=UTILITY_FAIL; B3_L1=FAIL; Body_JEPA=UNAVAILABLE; jepa_weight=0; Redmi=UNMEASURED; V13=INCOMPLETE; canonical/user full scope false. No receiver injection, training, JEPA target, source/seed/model changes, age/approval rights or production integration. Historical Run596 RED preserved.

Exact reproduction (requires original pinned artifact ZIP):
`cd v13/code && PYTHONPATH="$PWD:$PWD/scripts" python -m unittest -v tests.test_run613_cross_body_fusion_offline && PYTHONPATH="$PWD:$PWD/scripts" python scripts/run613_cross_body_fusion_offline.py --original-zip <RUN608_original_artifact.zip> --output <RUN613_report.json>`

Next: avoid repeating the same mapping/lexical experiment on this cohort. Pursue actual receiver-conditioned/learned body utility with new preregistered independent data and source-bound native injection/training prerequisites; or another canonical functional package while native prerequisites are blocked. No automatic gate promotion.

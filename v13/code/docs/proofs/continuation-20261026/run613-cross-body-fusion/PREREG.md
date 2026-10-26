# Run613 — B1/B2/lexical fixed fusion on original Run608 native states

2026-10-26 UTC. Owner GPT automation11. Review-only child of verified Run612 PR607 exact `7682123d4a206330331cf8b65d7457003913771e`. **Posthoc follow-up to Run608**: the original 80-prompt cohort, raw native states and original Run608 metrics were already observed. The fusion protocol below is frozen before running *this* new analysis, but it is **not a new independent heldout cohort** and cannot promote B3/STEP2/Body-JEPA.

## Source and evidence locks

Use only original Run608 Linux-native read-only state artifact Actions `40402123481`, artifact `12688049715`, outer ZIP SHA256 `9cae2ac55a9ac773f3d3c2433d7ad485f479d8dc7b79f32e7555014f0eaad732`, inner `RUN608_STATES.npz` SHA256 `c6e6a7a6521d14c90805a996e723e9cd7716cd6ba6d13577480eff30349625ca`, frozen cohort blob `f452bdf80bb8d8a784c1909c98e310041d3157aa`, 60 train (transport/cooking/astronomy/gardening/finance/sports), 20 heldout (music/weather), 40 facts paired A/B. B1 80×2048, B2 80×1024; original model revisions, weights, native taps, labels and source hashes unchanged.

## Frozen computation / acceptance

1. Reproduce original Run608 mapped B1→B2 ridge alpha=1 on **train only**; verify original heldout mapped opposite top1=.25 and lexical Jaccard opposite top1=.30 exactly before further analysis. Source query itself excluded, 19 candidate opposite-paraphrase retrieval; ties use deterministic first-index `argmax` (original rule).
2. Additional single-body baselines: B1 within-space cosine and B2 within-space cosine, using the same heldout 19 candidates, no fitted test labels. Fixed fusion: for each query, min-max normalize lexical Jaccard and mapped-native cosine separately over the **19 nonself** candidates (constant row -> all zero), then `0.5*lexical_scaled + 0.5*native_scaled`. No weight, alpha, threshold, candidate set, tie-break or topic tuning.
3. Report top1 and MRR for lexical, mapped-native, B1-only, B2-only and fusion, and 200 fixed-seed train-label shuffles of B2 ridge targets with lexical unchanged. Empirical p=(1+#null_fusion_top1>=observed)/(201). Positive exploratory proxy only if fusion top1 exceeds **each** lexical, B1-only and B2-only by >=.10 absolute and p<=.05; otherwise `NO_FUSION_PROXY_GAIN`. A positive result remains exploratory posthoc and does not imply receiver injection, learned Body-JEPA, native training, user utility or B3 promotion.
4. Fail closed on wrong ZIP/inner SHA, missing/extra NPZ keys, changed cohort, train/test overlap, nonfinite arrays, malformed prompt IDs, altered source/proof authority. Preserve raw/failed attempts. Actual offline NumPy + adversarial tests and source-bound GitHub Actions; no new model inference, no native concurrency.
5. All original negative gates preserved: STEP2 UTILITY_FAIL, B3 L1 FAIL, Body-JEPA UNAVAILABLE, jepa_weight=0, Redmi UNMEASURED, V13 INCOMPLETE. No human/age/approval changes.

Owned new script `scripts/run613_cross_body_fusion_offline.py`, tests `tests/test_run613_cross_body_fusion_offline.py`, new proof/workflow. No mutation of original Run608 artifact, cohort or scripts. Next command: `cd v13/code && PYTHONPATH="$PWD:$PWD/scripts" python -m unittest -v tests.test_run613_cross_body_fusion_offline`.

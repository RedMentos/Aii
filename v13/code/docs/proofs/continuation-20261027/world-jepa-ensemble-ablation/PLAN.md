# World-JEPA ensemble primary-vs-mean ablation — preregistered research

Date 2026-10-27 UTC. Owner GPT-6 continuation. Review-only child of PR #741 exact `fe57536308819b6facc5947d24fcff66468ab34e`. Frozen World-JEPA source `v13/code/v13/world_jepa.py` blob `a691cae8aa19bf3a0700535c20dc8fc85c649d0d` remains byte-identical; no modification to registered World-JEPA cohorts, checkpoints, training seeds or source/model hashes. No native model or phone work.

## Question

`WorldJEPA.predict` documents a mean prediction but currently returns the jointly-trained primary predictor `ps[0]` and separately uses bootstrap ensemble spread. Changing production to ensemble mean without evidence could worsen the causal-action representation. Compare primary `ps[0]` against `mean(ps)` on a **new synthetic, held-out action-conditioned world** with frozen original WorldJEPA source, and preserve negative/neutral outcomes. Do not assert the mean is better a priori.

## Preregistered synthetic cohort and metrics

Seed `20261027`; training 512 independent source states with four binary controllable slots and four fresh nuisance dimensions. Each action flips its designated slot; nuisance dimensions redraw independently. Holdout 192 states from seed `20261028`, never used in fitting. Fit WorldJEPA with ensemble=3, steps=500, unchanged hyperparameters. For each held-out (state, action, future), compare target-latent MSE for primary, ensemble mean, no-action primary and shuffled-action primary. Also report ensemble disagreement (target-std units), noncollapse effective rank/min_std and exact source/script/seed. No optimizer updates outside the synthetic fit, no external data, no new model checkpoint activation. A PASS means the ablation ran with finite measurements and the intended independent controls; it does not mean improvement.

## Proof and next

CI must run with pinned NumPy, no downloads, no native model, raw stdout/stderr/exit and hash binding. Preserve all results even if mean loses. Any future change to the production `predict` aggregation requires a separate preregistered fresh-seed utility/retention study and explicit review; do not silently change registered source. LP1/LP2/BJ1/STEP2/B3 negative, `jepa_weight=0`, Age authority 0, Redmi unmeasured, V13 incomplete.

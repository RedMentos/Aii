# Run110 — WP-DS2 combined learning-progress + hunger goal + word novelty (preregistered)

Date: 2026-10-25 UTC. Base: verified Run109 PR #140 `7239df918faf03e80284ccde6394caed1d407bfa`. Independent owner: lab-only `v13/code/v13/sandbox.py`, `tests/test_sandbox_ds2_run110.py`, `scripts/sandbox_ds2_bench.py`, isolated workflow and this evidence folder. No changes to Runtime, Age, body weights, B3, WorldState or model/native cohort. No heavy native work.

## Claude DS1 provenance and selective source import

DS1 lives on unmerged Claude PR #25 `claude/project-thread-qt2cqv` `662d1f02a0a5dc9e56050a93ee1cbde8470c7ab2`, not in the Run109 source tree. Copy exactly the original `v13/code/v13/sandbox.py` blob `673b8c057bfa385aadcb94b2de45e5c17cc3560e`, `tests/test_sandbox.py` blob `d527bbc2ae3bff0eec652cef8b6b3bf603e071a7`, and `scripts/sandbox_ds1_bench.py` blob `816a48734dfca18c3d61e6f333fdd530458f3e6d` before modifying. Original prereg/report stay in Claude PR #25, cited by blob/hash; this is not a full merge of PR25. Confirm exact bytes after copy. Existing DS1 policy behavior must remain unchanged.

## Mechanism (BOOT, no post-result tuning in this cohort)

Two new lab-only arms, `lp_goal` and `lp_goal_novelty`. Both combine existing AG5 positive learning progress + visit novelty (`NOVELTY=.2`) with the existing DS1 EFE pragmatic hunger term (`PRAGMATIC=2`, same Dirichlet P(EATEN), same movement cost). `lp_goal_novelty` additionally uses a word-level novelty modulator: `WORD_NOVELTY_GAIN=.3/sqrt(1+word_interactions)` (new word highest, decays as learned), applied to *all* words, never hardcoded for pilz. No true-world table access in Agent policy. Lab only; STEP8 still locked.

## Preregistered comparison

Same 20 seeds 100..119, same 1500-step world and new word at 600 as DS1. Compare unchanged DS1 `lp`, `efe`, `novelty` against `lp_goal`, `lp_goal_novelty`. Record per-seed full KL curves, mean hunger, noisy-TV share, grounding, new-kind learned count and median delay. No model inference. Independent ablation: remove pragmatic goal (`lp`) and remove word novelty (`lp_goal`). Test exact determinism and no hidden TRUE-table use by the policy.

Success hypotheses (all must hold, otherwise DS2 FAIL, no promotion):
- H1: `lp_goal_novelty` mean hunger <= 0.10 and at least 0.05 below unchanged `lp`.
- H2: at least 15/20 seeds learn the new word, median delay <= 700 steps; >= 6 more successes than unchanged `efe`.
- H3: noisy-TV interaction share <= 0.25, final learnable KL <= 0.12; no catastrophic learning regression.
- H4: `lp_goal_novelty` new-kind success count >= `lp_goal` (word novelty not harmful). Report effect size and per-seed wins even if threshold fails.

## Gates/claim limits

Synthetic toy world only, no embodied phone proof, no real World-JEPA, no AGI, no production authority. STEP2 UTILITY_FAIL, B3 L1 FAIL, Body-JEPA UNAVAILABLE, jepa_weight=0, V13 INCOMPLETE. Preserve failed runs and do not tune same registered seeds after looking at results.

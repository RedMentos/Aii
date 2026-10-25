# Run346 prereg — DS2 combined curiosity/goal/word-novelty sandbox utility (2026-10-25)

Base: Run345 verified checkpoint `b9da91da6780b3dc43d3ed3814f205c1b4ada8c7`. Owner: only `v13/code/v13/sandbox.py`, new `tests/test_sandbox_ds2_run346.py`, `scripts/run346_ds2_bench.py`, Run346 workflow/proofs. No runtime/age/learning/approval/body source changes, no native/model/Redmi jobs, no existing model/source/cohort hash edits.

## Existing functional state and gap
Roadmap WP-DS2 calls for a combined learning-progress + hunger-goal + new-object novelty policy. `sandbox.Agent.value` already contains `lp_goal` and `lp_goal_novelty`, but `run()` does not report **per-new-kind visits or final new-kind KL**, so the claim that the novelty channel learns the new object cannot be tested directly. Existing DS1 7 software tests only check determinism and general learning. This package adds **measurement only** to the lab, then preregistered paired evaluation of existing policies; no tuning on the evaluation seeds.

## Frozen evaluation
- Deterministic paired seeds 401..420 (20 seeds), 1200 world steps, new kind introduced at step 500, same environment per seed. Policies: `lp`, `lp_goal`, `lp_goal_novelty`, `efe`. Source and cohort are pinned in the script and unchanged after results.
- New `run()` output keys: `new_kind_interactions` (sum actual interactions with `pilz`) and `new_kind_final_kl` (KL of its four actions at terminal step). No policy/physics/Dirichlet changes in this package.
- Before code: tests should RED on absent keys. After code: determinism, nonnegative visits, finite new-kind KL, no-new-kind returns None/0, original DS1 tests pass.
- A *supported* combined policy requires all predeclared mean paired criteria: `lp_goal_novelty` mean hunger at least 0.03 lower than `lp`; noise share no more than 0.03 above `lp`; final learnable KL no more than 0.05 above `lp`; new-kind final KL at least 0.05 below `lp_goal`; new-kind KL improvement in at least 14/20 paired seeds. Otherwise `NOT_SUPPORTED`, retain raw failure; do not retune on these seeds.
- Record every per-seed policy result, aggregate paired deltas, explicit pass/fail for each criterion, SHA256, exact GitHub head, privacy scan and private raw backup. No promotion to Age0/AG5/STEP8 or whole V13 from a lab result.

Next: add RED-first telemetry tests + exact-head workflow/benchmark; preserve RED; minimal telemetry patch; execute benchmark, inspect raw, checkpoint and continue.

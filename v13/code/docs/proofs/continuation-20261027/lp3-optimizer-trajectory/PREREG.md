# LP3 optimizer-trajectory diagnostic — preregistration (separate cohort)

2026-10-27 UTC. Review-only child of PR #736 exact `6331e5021e1e977183ece3d3b1ed7cfb8f05d4ba`. This preregistration is saved **before** source/tests/workflow and native execution. Original heldout pilot PR #734 Actions `40527420680` remains FAIL_MISSING_PREDICTOR_OR_PROJECTOR_GRADIENT; raw SHA256 `3fc467c37f92b2fe442b440c60904e626fc1ef513b92345b6c3a3d8768581004` preserved. PR #736 no-update diagnostic found positive initial single-row gradients on all six train prompts; optimizer/eval-state mechanism remains unknown.

## Frozen model, data and optimizer
Official `LiquidAI/LFM2.5-350M`, revision `120bf032c36dd1273de754669da040dba7ad4982`, FP32 master SHA256 `1c9c77a4471a7f590f85240f74ed1fc26df7fbde88c3006724e2f93ca993ea4e`, LFM Open License 1.0. Same pinned torch 2.14.1, transformers 5.20.2, huggingface_hub 2.3.0, seed 109, 2 soft-prefix tokens, original six `fixture()` rows, 24 cyclic steps, AdamW LR 0.005 weight_decay 0.0, frozen base. No altered prompts, hyperparameters or weights.

## Diagnostic arms (new, not a retry of original utility cohort)
- **PRE_EVAL**: run original `evaluate(candidate,base,tok,rows,torch)` and `retention_ce` before 24-step training, as in failed pilot; then collect every step's full-answer CE, predictor/projector gradient absolute sums, gradient finite flags, optimizer moment finiteness, parameter update magnitude and predictor tanh saturation. Do **not** abort on a finite zero gradient: record first such step, preserve remaining trace. On nonfinite loss/gradient, record exact failure step and stop that arm before unsafe optimizer update.
- **NO_EVAL**: restore exact initial trainable parameters, new optimizer, same frozen base and row sequence, but skip pre-evaluation. Collect identical 24-step trace. This isolates pre-evaluation-state effects from optimizer trajectory.
- Do not use heldout examples to train or score. No target-free generation, no source/control model change, no model/optimizer artifact publication. Verify initial trainable bytes same for both arms, frozen base sample SHA unchanged, no base gradients. Report first zero/nonfinite step or all 24 positive; retain both arms even if one fails. A diagnostic result is not a utility PASS.

## Evidence contract
New `scripts/lp3_optimizer_trajectory.py`, tests and isolated GitHub Actions workflow, source/fixture/prereg SHA, raw logs/exits, exact pinned master verification, timeout 18m and job 30m, no concurrent heavy native owner. Test the trace/first-failure classification in software, including zero/nonfinite cases. Private raw ZIP backup when permitted. No overwrite of prior failed attempt, no new Age or jepa authority. LP1 NO_ATTRIBUTABLE_GAIN, LP2 ALIGNS_NO_GAIN, BJ1 NO_SIGNAL, STEP2 UTILITY_FAIL, B3 L1 FAIL, `jepa_weight=0`, Age authority 0, Redmi unmeasured, whole V13 incomplete.

## Interpretation
PRE_EVAL zero but NO_EVAL positive suggests evaluation-state interaction. Both zero after same optimizer step suggests saturation/update path. Both positive means the original failure needs separate environment/evaluation reproduction. A zero is a recorded observation, not proof of model incapacity. Next: independent review of raw trajectory and a separately registered intervention only after diagnosis.

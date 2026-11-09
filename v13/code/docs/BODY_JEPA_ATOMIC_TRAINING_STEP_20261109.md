# Body-JEPA optimizer and EMA step — independent review, 2026-11-09

Status: **source-bound candidate, no live source overwrite**. The candidate is
a child of the other workstream's #1639 at
`f48b90320a976d9f9420e75e12427ede2a0ca42e`; the builder also recognizes the
exact #1641 numeric-preflight source at
`42a105360d7e86f91b2823b5c4843ff825cfe095`. Those owner branches remain
untouched. This is not a native B1/B2 or Redmi training result.

## Independent review of #1634–#1641

The newer chain adds device-correct latent/index tensors, fuller device
placement, a bounded detached CPU anchor cache, rollback on EMA swap entry,
finite-gradient checks and staged EMA updates; #1641 also rejects malformed
tokens and overflowing eligibility sums. #1639's six focused test files run
here: **45 passed, 3 CUDA tests skipped**, privacy CLEAN. #1641 plus those
files: **58 passed, 3 CUDA skipped**, privacy CLEAN; its reported focused CI is
green. These tests use small CPU Torch fixtures, not pinned mobile bodies.

Two further counterexamples were independently reproduced on exact #1639:

1. `EmaAdapter.update` validates all proposed tensors, but then calls `copy_`
   sequentially. An injected exception on the second copy leaves the first
   shadow changed while `updates` remains zero.
2. `checked_gradient_step` checks gradients but not AdamW's existing moments.
   With a NaN moment and finite gradients, `opt.step()` made the parameter NaN.

## Candidate and tests

`body_jepa_atomic_step_integration_candidate.py` verifies exact source hashes
and builds an isolated copy. Its EMA publishes a fully staged list instead of
mutating earlier shadows one by one. The actual `fit` loop in the copy calls
`body_jepa_atomic_step_candidate.checked_training_step`: before the step it
checks parameters, gradients and optimizer/EMA state, snapshots the selected
parameters, gradients and optimizer state, then checks the result and advances
EMA. A failed optimizer or EMA step restores the snapshot; failed recovery
marks the optimizer unusable and requires discarding model/optimizer. The
legacy `checked_gradient_step` function itself remains unchanged; this
candidate connects the stronger wrapper only in the disposable `fit` copy.

* Candidate/wrapper tests: **12 passed**, including the original copy-failure
  counterexample, finite-gradient/NaN-moment counterexample, nonfinite output,
  optimizer exception, EMA exception, restored clipped gradients, failed
  recovery and mismatched optimizer parameters.
* On the #1639 candidate copy, the broader Body-JEPA/checkpoint suite reports
  **75 passed, 3 CUDA skipped**. On a separately materialized #1641 copy, the
  same suite plus numeric-preflight tests reports **88 passed, 3 CUDA skipped**.
  A tiny synthetic GPT-2/PEFT `fit` and checkpoint-resume test really runs on
  CPU; a further injected EMA failure verifies rollback through that actual
  `fit` call. This is not evidence about the deployed Body master weights.
* Full regular `tests` directory at #1639 with tracked `v13/code` and the AG6
  historical fixture present: **8 failed, 5,446 passed, 53 skipped, 94 errors,
  3,022 subtests passed**, 447.84 s, exit 1. Local raw log SHA-256
  `e5354d817033380c8fb4f1632ec898b95e44f44f989a7c86001f5f75f29e3147`.
  Five failures are older AG6 trainer fixtures expecting behavior before the
  inherited stricter master preflight; two require missing original native
  ZIPs. One missing tracked neuro-ledger fixture passed individually after
  expanding `v13/bench-results`. The 94 errors require original native ZIPs.
  The full result stays RED; no raw-log backup is claimed.

The in-memory snapshots increase memory and copying; no actual mobile budget
or latency has been measured. The wrapper handles synchronous exceptions, not
process-crash atomicity across a future checkpoint or arbitrary concurrent
training. Publishing the EMA list changes alias semantics, so consumers that
retain individual old shadow tensor references require review; the existing
checkpoint restore already replaces the list, but that is not a universal
compatibility proof. An interrupted `swap()` restoration can also still fail.
No shared-weight unlearning, automatic promotion, STEP2/B3/JEPA or Age gate
change is claimed.

Parallel #1642 independently changes the #1619 online predictor's cursor and
has separate passing focused CI; #1631 also implements a source-hashed receipt
candidate. These alternatives require explicit reconciliation rather than
assuming either branch includes the other. #1640 covers the separate
event-bound local-error preview; background-context/data goals are tracked in
its child plan and do not alter the Body trainer here.

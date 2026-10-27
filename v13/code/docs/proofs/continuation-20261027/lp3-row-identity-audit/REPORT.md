# Independent LP3 wrong-source per-row identity audit — 2026-10-27

**Owner:** `codex/automation11b-lp3-row-identity-audit-20261027`, review-only child of PR #732 exact `41ec2d4a4e83e7a35314c2603208b7e139da3572`. No edits to PR #732 or to another owner's branch.

## Finding and counterexample

The source-control path in `v13/lp3_state_prefix.py::_prefix_from_source` rejected `torch.equal(source_prompt_ids, target_prompt_ids)` for the **whole batch**, but did not reject a row where the source equalled its target if any other row differed. For example, targets `[[3,4,5],[6,7,8]]` and sources `[[3,4,5],[3,4,5]]` passed. The first row was an *own-source* sample mislabeled as a wrong-source control. This contaminates future matched CE/own/wrong-source estimates and can create false causal utility claims.

The fix rejects **any** per-row identity for same-length source/target tensors, while preserving valid per-row permutations and different-length source controls. The API cannot determine semantic equivalence or answer leakage in source prompts: independently preregistered dataset provenance remains mandatory. It does not modify the registered LP1/LP2 cohorts, frozen base, training objectives, or live runtime.

## Verification

Added one regression `test_wrong_source_rejects_any_own_row_in_mixed_batch`, covering teacher-forced answer, next-token and bounded greedy, plus valid swapped-row control. Existing 14 synthetic tests retained; expected 15/15. Isolated Actions workflow `.github/workflows/lp3-row-identity-review.yml` uses a frozen tiny GPT2, pinned torch/transformers, `py_compile`, public privacy scan and `git diff --check`. No real model or Redmi execution.

**CI at checkpoint:** Actions run `40526437142` started for code/workflow commit `f18588c8018c28aa822d086672ce178471dfecf1`; result pending until exact-head verification. Do not claim PASS before it completes.

## Binding negative gates

LP1 `NO_ATTRIBUTABLE_GAIN`; LP2 `ALIGNS_NO_GAIN`; BJ1 `NO_SIGNAL`; STEP2 `UTILITY_FAIL`; B3 L1 `FAIL`; registered `jepa_weight=0`; Age authority 0; Redmi unmeasured; no real-model heldout utility; canonical architecture and user full scope incomplete. Software-only row integrity is **not** LP3 utility, Body-JEPA or STEP2 proof.

## Next

1. Verify exact-head CI, source SHA, 15 tests and privacy exit; update this report and BUILD_STATE with the actual result, including failures.
2. Independent reviewer: challenge row matching, semantic/answer leakage, frozen-base status and mixed-length controls. Do not merge to main without chain review.
3. Preregister matched heldout own/wrong-source/zero CE and target-free utility, hard negatives, source provenance, retention and drift gates **before** any new native run. Serialize against BP2b native owner.

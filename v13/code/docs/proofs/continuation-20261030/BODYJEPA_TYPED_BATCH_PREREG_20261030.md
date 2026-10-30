# IH-H25 Body-JEPA typed batch preflight — preregistration (2026-10-30)

## Parent and scope
Parent review chain: PR #1184, commit `e1e9228318b2152875bd6e5b402f5cf2c50213df`. Parent objective bridge blob `17eac02878f423d8d9e5147fd25b79c1f8377847`; original bridge tests blob `a769f284dd68ac0f819123a36622c561e6f80ae8`; immutable Canon blob `218464b12a2d27d92524c751922fa8e1c3fb0ea7`.

Problem: the research-only `research_loss` preflights the first token-ID tensors but does not validate the paired length tensors, target latent row shape/dtype, or boolean eligibility before invoking the student model. A malformed batch can be coerced or can cause a model forward before the failure is detected. The target latent is detached by `jepa_loss`; this package must retain that property.

## Falsifiable test plan, registered before code fix
- Add a separate test file using the existing tiny Torch model plus a counting forward wrapper.
- Negative cases: wrong context length shape; wrong target length shape; lengths out of range; wrong token dtype; wrong target latent row count; wrong target latent dtype; nonfinite target; boolean eligibility; malformed or mixed-typed eligibility. Each must raise `ValueError` before **any** student model forward.
- Positive: existing valid batch gives finite differentiable scalar, student/predictor receive gradients, EMA/base target does not.
- Torch tensor floating eligibility accepted but detached from gradient authority; no new learning or runtime registration.
- Preserve existing objective tests, `test_body_jepa` and original frozen source hashes. No source/model/seed/cohort change.
- Execute pinned isolated software CI on review branch, capture original raw even if RED, verify privacy/diff and all stage exit codes. Expected first RED is newly introduced regression tests against parent bridge. Then fix source and rerun same tests GREEN.

## Boundaries
Only `v13/code/v13/body_jepa_objective_bridge.py`, new tests, CI workflow and this prereg/result/checkpoint are owned here. Do not edit `body_jepa.py`, model weights, original datasets or registered native cohorts. B_local_JEPA remains UNAVAILABLE and `learn_gain=0`; `jepa_weight=0`, Age0 RECORD_ONLY, STEP2 UTILITY_FAIL, B3 L1 FAIL, Redmi unmeasured, whole system incomplete. This is software preflight integrity, not demonstrated Body-JEPA utility.

Next command after prereg: add RED regression tests and isolated workflow, inspect complete original RED logs, then implement typed preflight without runtime authority.

# IH-H25 ObjectiveAdapter input-boundary regression — preregistration (2026-10-30)

**Review-only child of PR #1184**, parent exact commit `e1e9228318b2152875bd6e5b402f5cf2c50213df`. Owner: this V13 automation; only `v13/code/v13/body_jepa_objective_bridge.py`, new dedicated tests, new workflow and this evidence/handoff are owned by this package. Canon Git blob must remain `218464b12a2d27d92524c751922fa8e1c3fb0ea7`; `body_jepa.py` must remain `be022258cd46cc11e460dd7438563c0d0cc4a0eb`. No registered source/model/seed/cohort changes.

## Hypothesis and expected original RED
The research-only Body-JEPA adapter currently validates only the **first** element of each `(ids, lengths)` pair. An invalid lengths tensor can escape the typed adapter boundary and cause a low-level exception or an ambiguous autograd failure. Boolean eligibility values are silently cast to 0/1 by `torch.as_tensor` although boolean controls are not measured eligibility weights. The pre-existing tests do not cover these cases.

## Scope and checks
1. Before source fix, add focused Torch tests that assert **ValueError** for boolean eligibility, malformed lengths (non-tensor, wrong row count, fractional dtype, zero length, beyond padded width), and malformed target latents (wrong source row count/nonfinite). Preserve the original failing test output.
2. Add explicit input validation before `jepa_loss`, preserving the existing valid differentiable loss, stop-gradient target, strict source alignment, true derangement, and zero live authority.
3. Focused tests: `PYTHONPATH=.:tests:scripts python -m unittest -v tests.test_body_jepa_objective_bridge_20261030 tests.test_body_jepa_objective_input_boundary_20261030 tests.test_body_jepa`. Run in isolated Linux software environment; no native model weights or Redmi evidence. Recheck source/Canon hashes, privacy, diff, raw logs and gate invariants. Fail-closed CI, artifact even on RED.
4. Status is **PARTIAL**, `B_local_JEPA` UNAVAILABLE with learn_gain=0, `jepa_weight` remains 0 in live path; STEP2/B3/Body-JEPA and whole-system acceptance remain unchanged.

A GREEN test only proves software input-boundary behavior; it does not establish learned utility, real-weight training, native device support, or any Age authority.

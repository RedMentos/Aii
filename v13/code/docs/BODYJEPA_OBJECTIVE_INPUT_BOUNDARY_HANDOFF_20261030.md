# Body-JEPA typed-input branch: independent RED witness, ownership handoff (2026-10-30)

Review-only branch `codex/v13-bodyjepa-objective-input-boundary-20261030-auto11s`, parent `e1e9228318b2152875bd6e5b402f5cf2c50213df`. Prereg `1d4adc0054f8ae0c1639842ac02532bfc4324866`, tests `e501f5e26550853749193fdb37810176412ffb20`, workflow `485809c3a8f64f8d741dea6d341570f75a23e36a`. Original RED Actions **40984160943**, 35 tests, 10 failing assertions + 4 errors, original raw uploaded as artifact **12946063122**. This is a **negative input-boundary witness**, not a fix or gate promotion. The error cases were unexpected low-level failures and remain part of the original evidence.

**Concurrent-owner discovery:** another owner independently started `v13/code/tests/test_bodyjepa_typed_batch_preflight_20261030.py` at commit `a1fc46786413eb0bb24904210a7a7a2e6404af15` with overlapping checks, original RED Actions **40983639114**. Do not simultaneously edit `body_jepa_objective_bridge.py` or overwrite their branch. This branch intentionally has **no source fix**, no PR and no merge request. Coordinate/compare the two tests after the other owner's candidate is finalized; keep both original RED artifacts.

Canon, registered cohorts, native models, Age gates and live `jepa_weight` unchanged. Exact next action on this branch: review the concurrent owner's eventual source candidate and decide whether any unique regression from this RED witness remains uncovered. Owner for the active source fix: **other concurrent Body-JEPA preflight thread**, not this branch.

## Independent differential review note

The concurrent owner's RED-first `test_bodyjepa_typed_batch_preflight_20261030.py` covers early `model.forward` refusal and detached float-tensor eligibility, which this branch does not. This branch adds **non-Tensor lengths** and **negative token IDs** as extra typed-boundary counterexamples (plus repeated wrong-shape target checks). These cases should be reviewed after the owner's GREEN; do not cherry-pick this branch blindly. Both original RED artifacts are independent and neither proves real-weight utility.

# Run134 prereg — composed source-verified option + project binding (2026-10-29)

This is a **post-observation integration diagnostic**. Preregistered before new Run134 source/test/workflow, but after the historical 42-row Run116 cohort and separate Run129/Run130/Run133 hypotheses were inspected. It cannot be used as a fresh held-out utility proof. The canonical STEP2 utility gate remains FAIL regardless of its result.

Review-only child of Run133 PR #1033 at `cebd9be65c189133e25eee3b060dff409fe0538b` (Run133 CI pending at branch creation), which itself is a review-only child of Run130 PR #1030. Import the **exact unmodified** Run129 source `step2_project_identity_binding_candidate.py` blob `2878ea7c67e017a35feff0fdd48ae3c76ae02b73` and its tests blob `fbc827f1b5483090b63b96caa36e97ca5e7b63f8`, from PR #1029; no original source/model/fixture/seed/registered cohort changes. Preserve donor prereg blob `4dbe04813d3dfa3d982d14ad695af5b7fb9250fe` and all original RED evidence.

Test the composition in the only valid order:
1. Verify original Run116 source and tool report SHA256, all 42 source/tool row hashes and source refs, no oracle visibility to any native/repair function.
2. Apply Run133 source-verified B1 option quote correction to the **raw C3 typed extraction**; reject forged/conflicting/ambiguous B1 sources, including same_policy_dual controls.
3. Re-run unchanged deterministic eligibility tool on the corrected extraction using original recorded consumer messages. Never call a model.
4. Apply Run129 exact literal `Project <trusted source fixture ID>` alias binding to the resulting **decision** (not to C3 raw extraction); reject foreign project IDs.
5. Score only afterward against the original oracle, compare to original recorded score and action, retain all 42 rows and original negative gates.

Acceptance is **software-only**: all 42 rows, 0 wrong committed, no changed original raw bytes, no altered action/options after project binding, no new native calls, exact SHA of all donors and originals, focused+full+privacy green. Report utility by variant and changed fields, but never promote STEP2/whole-system. Preserve every RED attempt and raw zip with hashes.

Current blockers: no native owner release, no Redmi, no new disjoint cohort. No main merge, no runtime integration, no authority promotion.

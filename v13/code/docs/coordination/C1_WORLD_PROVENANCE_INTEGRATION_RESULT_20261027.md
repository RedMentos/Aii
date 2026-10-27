# C1 + World-JEPA provenance integration — review checkpoint 2026-10-27

Review-only child of existing two-parent integration branch `assistant/v13-c1-world-integration-review-20261027`, exact parent `87dd02f82abdcc3762029dac3ea8170c9db30e7c` (not main). Prereg `541871a8a3d7fb4df6a710bbc2a34138f08b5e34` before source/tests/workflow.

**Exact reviewed C1 bytes:** final `v13/code/v13/executive.py` blob `057dda1e705053047489516fc9ab10581018f5a4` copied byte-for-byte from the independently tested unresolved-question branch; goal-sequence test blob `86cbbb3b20a7fe11aad77802d4be1ffaf2197925`; question-origin test blob `f1d081392cddc7b4bf69bf1d4bcf527b9699f974`. No World-JEPA script/model/test changes were intended; workflow explicitly checks the diff against parent for World paths and exact C1 blob identities.

**Verification pending:** `.github/workflows/c1-world-provenance-integration.yml` captures exact source/test/prereg, focused C1 + World-JEPA tests, complete software suite, compile, privacy and diff checks in original raw artifact. Do not claim success before actual raw exits/ZIP checks.

**Scope:** software-only integration candidate, no native model/Redmi, real-world causal gain, STEP2/B3/Body-JEPA/LP1/LP2/BJ1, jepa_weight or Age promotion. All original negative findings, user decisions and complete Canon retained. No production merge, no model weights or private data. Independent review and branch ordering required.

Exact next command: `cd v13/code && PYTHONPATH=.:tests python -m unittest -v tests.test_executive_goal_sequence_binding_review tests.test_executive_question_origin_binding_review tests.test_world_jepa_matched_action_cohort tests.test_world_jepa_digital_shadow`. If combined suite fails, preserve raw failure and fix only with new evidence; no auto-merge.

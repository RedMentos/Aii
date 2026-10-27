# C1 + World-JEPA provenance review integration — pre-integration contract (2026-10-27)

Review-only child of `assistant/v13-c1-world-integration-review-20261027` exact parent `87dd02f82abdcc3762029dac3ea8170c9db30e7c`; NOT main, no production merge. That parent is itself a two-parent C1 task-origin plus World-JEPA integration, with full software Actions `40586529906` SUCCESS. Preserve all World-JEPA model/source/seed/heldout/negative gates and original C1 RED/GREEN raw evidence.

## Exact reviewed inputs

- Parent `v13/code/v13/executive.py` blob `05500ee25d7cd83b3412f027e1503ca907e12d43`.
- Independently reviewed C1 goal-sequence source blob `e42e586b7e685cf3b0abc80a17c203bfc7dfc845`, tests blob `86cbbb3b20a7fe11aad77802d4be1ffaf2197925`, PR #778: focused RED 3/16, GREEN 16/16, full 1958 tests.
- Independently reviewed C1 unresolved-question source blob `057dda1e705053047489516fc9ab10581018f5a4`, tests blob `f1d081392cddc7b4bf69bf1d4bcf527b9699f974`: focused RED 3/30, GREEN 30/30, source-wide test pending at pre-integration time.
- Final source is intended to be **exact byte-identical** to the second reviewed blob; do not reimplement or silently change either guard. Add the two test files unchanged. Leave all World-JEPA, LP3, B1/B2, C3, B3, learning, age and runtime code untouched.

## Falsifiable integration checks

Run both C1 provenance focused tests and the existing World-JEPA matched-action/closed-store software tests on the combined tree; then run the full source-wide software suite, compile, privacy and diff checks with raw exits. Confirm exact source/test Git blob identities, compare World source blobs against parent, and preserve all negative gates. This integration is software-only and cannot establish native model, Redmi, semantic utility or production integration. No auto-merge; independent review required.

Next command: `cd v13/code && PYTHONPATH=.:tests python -m unittest -v tests.test_executive_goal_sequence_binding_review tests.test_executive_question_origin_binding_review tests.test_world_jepa_matched_action_cohort tests.test_world_jepa_digital_shadow`. If any dependency is missing, resolve in isolated CI rather than fabricating a PASS.

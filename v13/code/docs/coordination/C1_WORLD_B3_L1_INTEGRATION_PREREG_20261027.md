# C1 + World-JEPA + B3 L1 provenance/acceptance integration — prereg (2026-10-27)

Review-only child of verified C1+World integration PR #780 at exact parent `3a3892a8525f51e0dab914b4a58e44a7ac4c3017` (not main). No auto-merge, no production weights. Existing C1+World source-wide Actions `40589265710` PASS 1990 tests. This integration will copy byte-identical, independently preregistered B3 L1 gate fixes from their review chain after focused verification; preserve all World-JEPA model/source/seed/heldout artifacts and all negative gates.

## Exact immutable source and test expectations

- C1 `executive.py` `057dda1e705053047489516fc9ab10581018f5a4`, goal test `86cbbb3b20a7fe11aad77802d4be1ffaf2197925`, question test `f1d081392cddc7b4bf69bf1d4bcf527b9699f974` remain unchanged.
- B3 `b3bridge.py` final `3f0efe54e2087babf267ef3d4ccbd424b897faf8` (strict complete paired L1 gate + persisted doctor/completion revalidation).
- B3 `b3degrade.py` final `5cc822ecad749887acfad69f5fcba39a5a2dae8f` (explicit promotion requires full L1).
- B3 new tests `test_b3_l1_baseline_completeness_review.py` `869c98dc79000673ec1ae7e739c8d2aa548204b8`, `test_b3_l1_report_revalidation_review.py` `ba2662593bdf260b5cbed7cb3158793a26638c92`, `test_b3_l1_promotion_evidence_review.py` `d5f819f6fab02c8a65e308fd62920f8534182b99`.
- B3 corrected existing synthetic fixtures `test_b3bridge.py` `50b9fcf38bee7e04aa792be51df164adeb88d2a7`, `test_b3_completion.py` `188ce376f1012ade7560d058752901afc22da930`, `test_b3degrade.py` `f40b40f6ef114524d318507a5106f5d03d6c5bcf`.
- All World-JEPA scripts, model files, original cohorts, B1/B2/C3, runtime and learning/age gates untouched.

## Falsifiable integration

Run focused C1 + B3 + World software tests on combined tree, then full source-wide suite with exact source/test Git blobs, changed-path allowlist, compile, privacy and diff exits in original raw artifact. Preserve all previous RED/intermediate failures. A synthetic L1 gate PASS is **not** native B3 receiver proof. No STEP2/B3/Body-JEPA/LP1/LP2/BJ1/jepa_weight/Age promotion; whole V13 incomplete.

Exact next command: `cd v13/code && PYTHONPATH=.:tests python -m unittest -v tests.test_executive_goal_sequence_binding_review tests.test_executive_question_origin_binding_review tests.test_b3_l1_baseline_completeness_review tests.test_b3_l1_report_revalidation_review tests.test_b3_l1_promotion_evidence_review tests.test_world_jepa_matched_action_cohort`. Independent review, no auto-merge.

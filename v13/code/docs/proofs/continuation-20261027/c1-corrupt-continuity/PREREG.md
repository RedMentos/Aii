# C1/JEF executive persisted-continuity malformed-item review prereg (2026-10-27)

Exact parent `3a14e9bc62e19a58d6fa4bad1fcddbb3e9c179b2` (#754), branch `assistant/v13-c1-corrupt-continuity-review-20261027` review-only, not main. Prereg committed before RED test or GREEN source. File ownership: `v13/code/v13/executive.py` **candidate only** (frozen runtime remains unintegrated), `v13/code/tests/test_executive_corrupt_continuity_review.py`, isolated CI and proof folder.

Static defect: `Executive._clean` assumes persisted `goal_sequence`, `memory_refs`, `open_questions` and `salient_B_offer` are lists of dicts. A malformed/legacy state can contain a scalar, null or a non-dict list member; `x.get` and direct iteration then raise `AttributeError`/`TypeError` while reading C1 continuity. This should fail closed to an empty list or drop invalid members, not crash a turn or resurrect untrusted memory.

RED protocol: create a real SQLite Store and event, persist one malformed C1 state with scalar/null list fields and another with mixed valid source-bound dicts and invalid entries. Expect `Executive.view` and `report_context` to preserve valid source-bound goal/task while dropping invalid items; original source should throw. Retain original raw failures.

GREEN protocol: minimal helper to normalize only these four list fields to dict-only entries before existing source/ref/session/generation validation. Do not weaken `_valid_ref`, memory revocation, session isolation, packet provenance, permissions, Age or source binding. Existing `test_executive` must remain green. Focused CI with SQLite tests, compile, privacy and diff raw exits; full software suite separately.

No native, no Redmi, no utility/learning/age promotion. LP1 NO_ATTRIBUTABLE_GAIN, LP2 ALIGNS_NO_GAIN, BJ1 NO_SIGNAL, STEP2 UTILITY_FAIL, B3 L1 FAIL, jepa_weight0, Age authority0, V13 incomplete. Independent frozen-runtime owner review before merge.

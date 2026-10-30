# Run21 AG12 solver identity — preregistration (2026-10-30)

Owner: GPT-6 scheduled continuation. Review-only child of Run20 PR #1347 at exact parent `8cb422295156ef50199d0c24df2e80d379fac692`.
Frozen original `v13/code/v13/agi/generality.py` blob: `84ca3580c37a00701286d0d9b00d535ee8c3153f`. Canon blob `218464b12a2d27d92524c751922fa8e1c3fb0ea7` unchanged.

## Concrete bug hypothesis
`GeneralityEval.run(..., solver_name=...)` currently uses `str(solver_name or 'default')[:32]`. Two different legitimate solver identifiers sharing the first 32 characters collide in the persisted `last_by` key and `curve(solver=...)` history. An oracle result from solver A followed by an incorrect solver B can be reported as B forgetting A's prior correct answers, obscuring English-first/German-later learning comparisons.

## Predeclared counterexample
Two distinct >32-character names with identical first 32 characters; run A with oracle, run B with null, then run A with null on the same fixed English suite. Expected independent B forgetting baseline `None`, A forgetting `1.0`, distinct stable solver keys <=32 chars, restart persistence and curve separation. Original source should fail. The fixed implementation must preserve all <=32-character existing solver names exactly, preserve default behavior, and fail closed on malformed names rather than silently converting arbitrary types. Run an independent negative test with the German suite, without modifying AG12 holdout registration or score math.

## Verification and scope
Test-first regression on actual Runtime/SQLite Store, then focused AG12 tests; record original RED and candidate GREEN independently if CI can run. No source/seed/model cohort changes; only AG12 solver label identity and its tests. No training, external tool permission, Age promotion, native/Redmi claim, STEP2/B3/Body-JEPA/JEPA promotion. Whole-system incomplete.

Next after checkpoint: independent read-side review and additional canonical package, not an automatic end of session.

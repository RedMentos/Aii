# Run313b preregistration — JEF source row and label receipt atomicity

2026-10-25, parent verified Run313 GREEN `aceb6e0b1a718aa1fd72cc97fbb06345ffeec6c7`.
Owned files unchanged: jefoutcome.py, Run313 tests/proofs/CI only. No Store/Runtime/Canon/model/seed/cohort edits.

New RED test: inject failure at receipt serialization *after* source allocation for one new FINAL self-label. Current Run313 source allocation calls Store.source in an earlier SQLite transaction, so a source row survives although no trainable label/receipt committed. Acceptance requires the count of `sources WHERE kind='OUTCOME_SELF_LABEL'` and JEF state/version to remain unchanged on this injected failure; retry must create exactly one valid source/label/receipt. Preserve immutable content-addressed blob semantics (orphan unreferenced blob file is acceptable; source DB row is not). Re-run Run313 45 original tests and all JEF human veto tests.

Minimal candidate: prepare immutable source bytes/hash/path outside the DB transaction, then insert the source row using the existing Store schema in the *same* Store.tx as JEF label/receipt. Do not alter Store.source or schema. Explicitly compare tuple fields to Store.source and keep source integrity checks. Actual SQLite software proof only; no native/Redmi/gate promotion.

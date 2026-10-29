# Run135 prereg — Age0 + STEP2 candidate cross-chain software integration (2026-10-29)

Review-only child of Run134 PR #1034 exact source checkpoint `58dad4b349719104a1db227c6f01360891466e8b`; parent Run134 CI pending at branch creation. This prereg is committed **before** Run135 donor imports/test/workflow. It is a source-only integration check, not a production Age or STEP2 feature release.

Import exact unchanged source/test/prereg blobs from independent Age branch Run131 PR #1031:
- `scripts/age_evidence_finite_candidate.py` `6f10566fb141e618111efa3102929d8f078f0f9b`
- `tests/test_age_evidence_finite_candidate.py` `d11d0ac1aac63a13c5c394c40bb82caa369cb8e8`
- `docs/proofs/continuation-20261029/AGE_EVIDENCE_FINITE_PREREG.md` `c1a3039b6bb4df4b7c8c2c5f577d7a3cd232735f`

And exact unchanged blobs from Run132 PR #1032:
- `scripts/age_state_quarantine_candidate.py` `8143c5995ab04e4c08e87dfa76d3345570dede22`
- `tests/test_age_state_quarantine_candidate.py` `eab41fbe046d167530f2ed5187c78ce52e142b4b`
- `docs/proofs/continuation-20261029/AGE_STATE_QUARANTINE_RUN132_PREREG.md` `e8da3fa027a959b7e0f7556a3a126da85fba915e`

No production `v13/age.py`, `operator.py`, `runtime.py`, models, registered fixtures, source hashes or seeds may change. Run135 tests should exercise both Age read-only candidates in the same actual Store lifecycle, with valid evidence, corrupt persisted state, freeze, and build ceiling 0; confirm no unauthorized stage or right and no stored-state repair. In the same branch, replay the original 42 STEP2 source/tool rows through Run134's post-observation composition and verify no wrong committed, no new native calls, source/model hashes unchanged, no canonical gate promotion. Both paths must remain **independent**, default-off and diagnostic-only.

Acceptance: exact donor blob identity, focused Age/STEP2 tests, original 42-row offline replay, full Linux suite, privacy, diff, SHA256-closed raw, independent exact-head audit. Preserve all earlier RED and skipped evidence; a failure is RED, not a reason to alter a frozen cohort. Do not claim whole-system integration or AGI.

Gates remain Age0 RECORD_ONLY; STEP2 UTILITY_FAIL; B3 FAIL; Body-JEPA UNAVAILABLE; LP3 FAIL; jepa_weight=0; Redmi UNMEASURED; whole system INCOMPLETE. No main merge or native owner release.

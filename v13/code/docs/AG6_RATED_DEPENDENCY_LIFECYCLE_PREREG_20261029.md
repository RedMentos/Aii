# AG6 rated-answer dependency lifecycle — preregistration (2026-10-29)

Review-only child of PR #1126, exact parent `89a7422916d60b6a0966713eb584c725069c9f2c`. New branch `codex/v13-ag6-rated-dependency-lifecycle-20261029-auto10m`. The parent branch and its original RED/GREEN artifacts are immutable to this package. Own paths: `v13/code/v13/agi/weights.py` **on this child only**, `v13/code/tests/test_ag6_rated_dependency_lifecycle_20261029.py`, own CI and this document. No merge, activation, cohort or gate promotion.

## Hypothesis / original RED

The parent checks declared `context_source_refs` only while constructing `rated_candidates`. The returned rated item retains the user prompt `source_ref` but discards the answer's declared supporting SourceRefs. If an independent supporting source is revoked **after stage** but **before fit or manual approval**, both existing lifecycle guards inspect only the user source. A candidate trained from revoked supporting evidence may therefore reach `trainer.fit` or be explicitly approved. This is distinct from PR #1126's direct-source fix.

## Predeclared tests

1. Real Store: user prompt + assistant FINAL with explicit `context_source_refs` including a separate HUMAN_FACT source + explicit 9/10 rating. Stage with SHADOW_UPDATE and `include_rated=True`, then revoke only the supporting source. Training must veto before `trainer.fit`, retain original batch, mark SOURCE_INVALID.
2. Same setup with authored FakeLora and valid gate; revoke the supporting source only after PENDING_USER. Manual approval must refuse, leaving request PENDING, batch PENDING_USER, no active adapter or consolidated memory.
3. Untampered valid declared supporting sources retain the existing training/approval path.
4. Malformed or removed staged dependency metadata cannot silently skip the new guard; legacy batches without declared dependency metadata must not gain authority.
5. Inherited AG6 focused tests and full software suite, compile/privacy/diff. Original RED raw evidence and corrected GREEN kept separately.

## Narrow candidate / limits

Retain typed declared supporting SourceRefs in a staged rated item (distinct from its direct user `source_ref`), and recheck each at the same pre-fit and in-transaction pre-approval admission points. Do not change existing source/model/seed/holdout hashes or rated quality semantics. No native model, no activation, no AG6 approval by automation. This does not prove completeness of historical assistant source metadata, immutability against an adversary who can arbitrarily rewrite SQLite, or post-approval source revocation response. Preserve Age0 RECORD_ONLY, STEP2 UTILITY_FAIL, B3 L1 FAIL, Body-JEPA UNAVAILABLE, LP3 FAIL, jepa_weight0, Redmi unmeasured and V13 incomplete.

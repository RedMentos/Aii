# V13 AG6 manual approval source revocation — branch-scoped BUILD_STATE delta

**Date:** 2026-10-29. **Owner:** independent child PR #1126, `codex/v13-ag6-approval-source-recheck-20261029-auto10l`, parent PR #1125 `c2347b437c07faae7273577742219eaefdbea107`. This is NOT a production merge and does not replace the canonical BUILD_STATE, ROADMAP, Canon or newer user decisions.

## Closed source and raw evidence

- Prereg commit `54bc6e86480e5053a526cf99053f1a6f85e0bb7c`, before test.
- Original real-Store RED Actions `40920614233`, source head `f3cbfa82595f50ff1cdb2db3081204bad6105462`: **2 genuine assertion FAIL, 1 PASS**, no fixture error. Revoked source and mutated staged source hash still approved in original. Privacy/diff exit0. Artifact `12918236256`, ZIP SHA256 `8fa0d104b54a5647547a034ff35fa1bd071dafbcc213c9fe5769ee6adb8742f6`, CRC and 8/8 internal hashes checked.
- Candidate source commit `a21e2da1992fd3ee270af765d34f8dbdf9a9457e`, `v13/code/v13/agi/weights.py` blob `974069a4aca362ff8fc161b23adbc3ef1d1fc7cf`. Direct SourceRefs rechecked inside Store.mutex and initial SQLite approval transaction before ACTIVATING journal; refusal leaves PENDING_USER request and adapter unchanged.
- Focused Actions `40920799310`, exact head `24368f7620dfb86ead92ec1fa45552e10d78a9de`: **41/41 PASS**, compile/privacy/diff exit0, artifact `12916684579` ZIP SHA256 `e027f43f7e07525635bc856294013e4311ecbfb92219d366884fb09cd7fbb83e`, CRC and 10/10 hashes checked.
- Full pinned software Actions `40920821646`, workflow-only head `9f4516b30b86c87a8bebcafef756c848a6472245`: **PENDING** at this checkpoint. Do not claim full-suite GREEN.
- Private Library `/V13-Checkpoints/2026-10-29/GPT6-Auto10-AG6-Approval-Revocation/`: both RED and focused GREEN raw ZIPs uploaded. Focused GREEN ZIP re-materialized and byte-compared; original RED also re-materialized and byte-compared. No private raw in public git.

## BUILD_STATE and negative gates

Narrow software claim `AG6_MANUAL_APPROVAL_DIRECT_SOURCE_REVOKED_VETO_SOFTWARE_PASS`, not an AG6 training utility or deployment proof. Local Store mutex/SQLite transaction serializes revocation versus approval intent; filesystem-only runner readers and external changes are outside this test. Remaining open: rated-answer context dependency revocation **after** staging; sources revoked **after** an adapter has been approved; metadata tampering and model-derived answer lineage; source kind changes; full native/Redmi proof.

Age0 RECORD_ONLY; STEP2 UTILITY_FAIL; B3 L1 FAIL; Body-JEPA UNAVAILABLE; LP3 FAIL; jepa_weight=0; AG6 unapproved; Redmi unmeasured; V13 incomplete. Original historical failures and all frozen source/model/seed hashes unchanged.

## Exact next commands

1. Fetch Actions `40920821646`, download original raw artifact, verify ZIP SHA256, CRC, internal SHA256SUMS, exact HEAD/source blobs, FOCUSED/FULL/COMPILE/PRIVACY/DIFF exits. Record **every** full-suite failure; never rewrite run34/run37 pinned-source RED.
2. Update PR #1126 and this handoff with exact outcome; repair only new regressions on this child branch.
3. Fresh-context independent reviewer: check `_approve_locked` initial Store.tx read_source under RLock, absence of side effects on refusal, existing rollback and manual approval tests, and no age/gate promotion.
4. Next separate package: post-approval revocation and dependency revalidation, with preregistered rollback/runner-reader safety; do not change active adapter behavior without a real test.
5. Focused command: `cd v13/code && PYTHONPATH=.:tests:scripts python3 -m unittest -v tests.test_ag6_approval_source_revocation_20261029 tests.test_ag6_staged_source_revocation_20261029 tests.test_ag6_rated_answer_dependencies_20261029 tests.test_ag6_rated_source_admission_20261029 tests.test_weight_approval_atomic tests.test_agi_trainers`.

Remaining platform budget: UNKNOWN. No native model execution or Redmi access in this package.

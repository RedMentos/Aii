# Run11 HX1/LP3 + AG8 human-request binding integration preregistration — 2026-10-28

## Authority and exact inputs (before integration)
This is a **review-only**, non-production candidate. Never overwrite parent/owner branches, merge into main, promote authority, or retune frozen cohorts.

Parent PR #813 `assistant/v13-hx1-lp3-merged-review-20261028` exact docs-only head `03c3aacd565d2da999fd83697b62cd0acf98ac5b`. Its exact tested source/workflow ancestor `616ca803ed31b8036726b39fad99958fbf8e5518` had Actions 40613590051 SUCCESS: 48 focused, 2111 full Linux software OK (1 skipped), all seven exits zero, privacy CLEAN. Raw artifact 12784691243 ZIP SHA256 `9ed1f129b0c3201a3dfe483a19c7ef70e9098a1da388bc8a7b69d1a40ad54ca7`; private Library byte-exact readback already reported. Parent handoff: `v13/code/docs/coordination/RUN11_HX1_LP3_INTEGRATION_HANDOFF_20261028.md`.

Independent PR #814 `assistant/v13-ag8-request-payload-binding-review-20261028` exact head `57eeccbd84ef60da8f313aac406b2328a9bc308d`, parent base `e2773e06075486ce8ed54c1fffec92f4200ec44c`. RED Actions 40613998046: 23 focused, 7 expected failures; RED artifact 12784127307 SHA256 `49a2b09d62bf3c13f651190b7e9d52569a1dcd6ae33335873b59e50625b0fc87`. GREEN Actions 40614151790 SUCCESS at exact head: 23 focused, 2110 full Linux software OK (1 skipped), all seven exits zero; artifact 12784327930 SHA256 `a6a79c3196707a374ae4e9f3f3cddd62f3ad6c9cf8f2f0a89398d7d0c2240226`. Original RED/GREEN private Library backups are recorded by PR #814 and must not be overwritten.

## Registered integration operation
Compare `e2773e0...HEAD` for both PRs. PR #813 changes LP3 source/test/workflow/docs only; PR #814 changes `v13/code/v13/agi/self_improve.py`, AG8 request-payload test, prereg and workflow. Verify file ownership disjoint and Git blobs identical to PR #814. Import exactly four PR #814 blobs into the PR #813 head tree; retain both parents via a two-parent merge commit. Do not touch Canon, source/model/seed/cohort hashes or other organs. Create a **new** branch-scoped combined focused/full Linux Actions workflow and save all raw exits and SHA256 sums; test both sets of focused cases and full `unittest discover`, compile, privacy scan, `git diff --check`. Preserve any RED, missing dependency, workflow failure or nonzero exit; no automatic retry with changed cohort.

## Acceptance, negatives and next command
Accept this integration as software-review GREEN only if exact integrated source/workflow SHA is reported by Actions SUCCESS, focused+full raw exits are zero, privacy CLEAN, canonical blob unchanged, Git parents/blobs verified, raw ZIP CRC and internal hashes verified, and a permitted private persistent backup read back byte-identically. Until then status is **PENDING**, not GREEN. The parent/sibling standalone GREEN results are not a combined result.

STEP2 UTILITY_FAIL; B3 L1 FAIL; Body-JEPA UNAVAILABLE; LP1 NO_ATTRIBUTABLE_GAIN; LP2 ALIGNS_NO_GAIN; LP3 new phrasing heldout 0/12 top1; jepa_weight=0; Age0/RECORD_ONLY; no live HX1/AG8 authority, no native/Redmi evidence; `canonical_architecture_complete=false`, `user_full_scope_complete=false`.

Owner: GPT-6 review-only integration branch `assistant/v13-run11-hx1-lp3-ag8-request-integration-20261028`. Next: create exact Git tree/merge, add workflow, wait for exact combined Actions evidence; then choose next independent substantive blueprint package. Platform budget remaining UNKNOWN.

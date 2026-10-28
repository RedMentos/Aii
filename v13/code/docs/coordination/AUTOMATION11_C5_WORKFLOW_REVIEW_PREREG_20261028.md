# Automation11 C5 attached-manifest workflow review — preregistration

Date: 2026-10-28. Owner: independent GPT-6 review, **workflow file and review evidence only**. Parent: PR #880 branch `assistant/v13-run11-c5-attached-manifest-20261028-0950` at `3dd870a73f367ed86a48292c5164cbe2d80727e0`. Earlier #874/#875 failed full historical lineage; neither is accepted. The original #871 20-stage native run remains 15 PASS / 5 FAIL. #879 reports a separate scoped native C3 source-consumer workflow success, **not** Stage11 promotion.

## Observed prerequisite failure before edit
GitHub Actions run `40657327320` (PR #880) failed in the FOCUSED step with `ModuleNotFoundError: No module named 'tests.test_c5_manifest_proactive'`. The source branch contains `v13/code/tests/test_c5_attached_manifest.py` instead. Full suite was `SKIPPED_FOCUSED_RED`. No source defect or full-suite verdict can be inferred from this run.

## Fixed prospective review
- Make a **separate review branch**, never change another owner's head or force-push.
- Correct only the focused test module in a branch-specific workflow, leave all frozen runtime/source/model/cohort/seed bytes and existing PR #880 unchanged.
- Check pinned blobs, isolated dependency installation, focused tests (new C5 plus original actionlearn/focal), entire original software suite, compileall, public privacy scan and `git diff --check`. Preserve raw logs, nonzero exits and failed tests. Require every check to pass before describing a software GREEN.
- Record run id, commit, raw artifact id/hashes and exact negative results. **Do not** infer native JEF/STEP12 or any gate from software. If software passes, preregister a separate no-B native run; do not run concurrent heavy jobs.
- Review an independent negative case: an attached ModelManager with an **empty** `installed` mapping currently returns `None` (test seam), allowing B1 selection. This is a known candidate hazard, not part of this workflow-only fix. Do not silently treat empty installed as native readiness; resolve in a separate source/test package with full regression evidence.
- No promotion of STEP2, B3, Body-JEPA, LP3, jepa_weight, Age, or Redmi. Preserve Age0 RECORD_ONLY and all original REDs.

## Recovery
Parent SHA `3dd870a73f367ed86a48292c5164cbe2d80727e0`. Next action after this prereg: branch-specific workflow correction; inspect its GitHub Actions run; save a scoped BUILD_STATE/evidence note and independently review any failures. The exact final status is pending measurement.

# V13 C1 + World + B3 + Sleep A exact-ID integration preregistration (2026-10-27)

Status: **REVIEW-ONLY, SOFTWARE EVIDENCE ONLY, NOT PRODUCTION MERGED**. This preregistration is committed before the candidate integration and its first combined CI run.

## Frozen inputs and scope

- Primary base: `assistant/v13-c1-world-b3-allgates-integration-20261027` at `117f503aea0503c39351cbf064e7e64898cf4eb0`, PR #785. Base tree `840a43c67013d0670f1df0dd6e2f582905ae2c63`.
- Independent Sleep A review: `assistant/v13-sleep-a-exact-recall-identity-review-20261027` at `c6e78f72dfa8da0cb23d8be75ad032bbb1ffebac`, PR #786. Source `v13/code/v13/sleep.py` blob `469101c9979b9cabe0dbd154cffde40912fa8a2c`.
- Integration method: preserve all base files and copy **exact seven** changed Sleep A paths (two workflows, two docs, BUILD_STATE delta, one test, one source) from the reviewed Sleep A head. No source re-implementation, no parameter/cohort/seed/model changes. Record both parents in the merge commit.
- Preserve base exact blobs: C1 `057dda1e705053047489516fc9ab10581018f5a4`, B3 bridge `8837693b4ee1b37ed2fec538c40a2b398ad8261a`, B3 degradation `5cc822ecad749887acfad69f5fcba39a5a2dae8f`, Sleep A source `469101c9979b9cabe0dbd154cffde40912fa8a2c`.

## Verification to perform on exact candidate HEAD

1. Verify both parent commits are ancestors and exact source/test blobs match.
2. Install pinned isolated Linux software dependencies; no native model downloads.
3. Run focused C1/World/B3/Sleep A regression families and full `cd v13/code && PYTHONPATH=.:tests python -m unittest discover -s tests -p 'test_*.py' -q`.
4. Run `python -m compileall -q v13/code/v13`, `git diff --check`, and `python v13/code/scripts/public_repo_privacy_scan.py`; retain original raw stdout/stderr and individual exit statuses as Actions artifact.
5. Fail the CI check on any failed exit. Explicitly distinguish dependency setup errors, test failures, and missing evidence.

## Acceptance / claim limits

This can establish only cross-branch Linux **software** compatibility. Existing B3 L1 FAIL, STEP2 UTILITY_FAIL, LP1 NO_ATTRIBUTABLE_GAIN, LP2 ALIGNS_NO_GAIN, BJ1 NO_SIGNAL, `jepa_weight=0`, Age-0 and authority-zero gates remain unchanged. No native receiver or Redmi proof, no semantic utility, no AGI/whole-system completion, no autonomous training, no production merge/auto-merge. Independent review remains required.

## Recovery / ownership

Owner: GPT automation, integration-only files `v13/code/docs/coordination/C1_WORLD_B3_SLEEP_A_*` and `.github/workflows/c1-world-b3-sleep-a-integration.yml`; imported Sleep A files are immutable exact blobs. Parent branches remain owned by their existing authors. Next command: inspect Actions run for this branch, verify original artifact bytes and report raw exits; if successful, independently review another non-overlapping canonical package.

# Run11 HX1 + LP3 integration preregistration — 2026-10-28

Review-only integration, no production merge. Source baseline: PR #809 verified `4bd69282647d260efe815b6f57b72ed675fef588`, Linux Actions `40610977438` SUCCESS (31 focused, 2105 full software, 1 skipped, privacy CLEAN), raw ZIP SHA256 `958d5d8d3c31d828af1592eae955793af9f20d0c524215a2b62cc3698b32969e` with private Library read-back.

Candidate parent #811 HX1 exact `e2773e06075486ce8ed54c1fffec92f4200ec44c`; candidate sibling #812 LP3 exact `8aaa753558a4171f2e0e1da2712e58939d91b632`. Both have preregistered RED witnesses and original raw failures retained. **Do not merge or claim GREEN until both exact final source SHAs pass their own complete Linux workflows.** At prereg creation, HX1 final Actions `40612498319` and LP3 final Actions `40612912886` were still in progress. This document precedes any combined source tree.

## Intended integration

Import only the four exact #812 LP3 source/test/workflow/prereg blobs into a tree based on this #811-descendant branch. HX1 and LP3 file ownership is disjoint. Make a two-parent Git commit retaining both lineages; verify exact tree and blob SHAs remotely. Run a new integration workflow on the combined source: focused HX1, LP3, AG8/F5/HX3/B3 controls, complete Linux software suite, compile, privacy/diff; close raw ZIP, verify CRC/internal SHA256, private Library backup and byte-identical read-back. No native/model download or Redmi evidence in this integration.

If either parent fails or combined tests fail, preserve the original failure and do not promote. No change to canon, original cohorts/seeds, jepa_weight, Age, live authority, STEP2 UTILITY_FAIL, B3 L1 FAIL, Body-JEPA UNAVAILABLE, LP1/LP2 negative, LP3 heldout 0/12 or whole-system incomplete status.

Owner: GPT-6 review-only branch `assistant/v13-hx1-lp3-merged-review-20261028`. Next command after both parent GREEN: import exact four LP3 Git blobs into this branch, make two-parent merge commit, then run branch-scoped full software Actions. Budget remaining UNKNOWN.

# C1+World+B3 complete L1 diagnostic/report/promotion integration — prereg (2026-10-27)

Review-only child of the disjoint C1+World+B3-seed candidate at `97f7a775540342c1e30c20d323c8d9cf4ba31254`, not main. Independent B3 report revalidation and explicit human promotion guard live on the separate report/promotion review chain; its legacy-positive-fixture compatibility child is `assistant/v13-b3-promotion-legacy-fixture-review-20261027`. Owner GPT coordinator; do not modify other owners' branches.

## Integration scope

Keep exact C1 provenance source blob `057dda1e705053047489516fc9ab10581018f5a4` and exact seed guard source changes `556c0a9f018f183483812e41db96ee4ebcc93258`. Merge B3 report validity/doctor/completion and promotion source/test/workflow/coordination changes from the verified child when ready. The one overlapping source file `b3bridge.py` must combine *both* disjoint modifications: seed identity validation inside `l1_gate` and persisted `l1_report_valid` plus its doctor/completion consumers. Do not overwrite either. Legacy positive promotion fixtures must contain complete synthetic L1 evidence, while malformed labels remain rejected.

## Falsifiable acceptance

- Two-parent merge lineage includes both verified parents, with exact source/test blob checks and independent review.
- B3 seed negative tests, persisted report negative tests, explicit promotion negative tests, legacy calibration/order tests, C1 goal/question tests and full source-wide suite pass together.
- All CI raw exits (install, focused, full, compile, privacy, diff, ancestry) zero; archive raw ZIP, CRC and SHA256, private backup.
- This is Linux software-only integration. B3 L1 native FAIL, STEP2 UTILITY_FAIL, LP1/LP2/BJ1 negatives, no native receiver/Redmi, `jepa_weight=0`, Age0, no production merge or automatic LATENT authority. Preserve original failed attempts and source/model/seed cohorts.

Proceed only after individual full suites are verified, then construct merge tree, run CI and publish a review PR. If blocked, keep branch prereg and continue independent work; do not invent success.

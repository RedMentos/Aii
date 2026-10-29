# Correction to family-cluster addendum — source audit RED (2026-10-29, before 600 result)

The preceding `P0X_PAIRED_FAMILY_CLUSTER_ADDENDUM.md` incorrectly described the frozen cohort as 30 families × 5 heldout rows. That was an independent review mistake. The immutable source generator `p0x_independent_source_holdout.py` actually creates **30 total families × 6 rows each**, of which **5 families (family % 6 == 0) are calibration** and **25 families × 6 rows = 150 heldout**. The failed CI [40842155616] preserves the original `P0X_PAIRED_FAMILY_COVERAGE_RED` test failure. Do not rewrite or erase that attempt.

The corrected robustness analysis is **25 heldout families, each with 6 matched tasks**. Keep fixed seed `2026102920`, 5,000 replicates, and four original contrasts. Sample 25 whole families with replacement per replicate, preserving all 6 rows, divide summed paired correctness deltas by 150, and report percentile CI. Validate exactly 25 clusters of size 6 against the frozen externally pinned fixture SHA. Original row-level McNemar/Holm remains exploratory and is not independent-family inference. No change to P0X cohort, source/model/seed, original native run, preregistered success criteria, or Canon gates.

This correction was made from source inspection and failing software tests, not from observing the 600-arm native outcome. Negative gates remain unchanged.

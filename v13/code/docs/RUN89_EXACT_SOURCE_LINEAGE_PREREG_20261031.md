# Run89 exact source-lineage mismatch diagnostic prereg — 2026-10-31

**Owner:** GPT-6 Auto11, read-only child of Run88 PR #1453 exact parent `273365e3be791df2a93b1a3f8f326ba0c79df6d0`. No native jobs, no production or frozen changes.

Run88 original full-suite parent `41176551097` RED **4612 / 4 FAIL / 66 ERROR / 28 SKIP**. Run88 software CI `41197664211` GREEN 10/10, original artifact SHA256 `4adbb12881a0d91660f8085da37c12b726d0a856b135463d74dea4d0e722e396`. Both existing candidate source checks strictly refuse current runtime. No relaxation permitted.

**Hypothesis:** exact source diff of current live vs (a) existing frozen native integrated chain and (b) SourceHandoff frozen baseline/candidate rebased through that chain will isolate which files/lines diverged. All source baselines remain digest-verified; comparison is read-only and reports SHA256/first changed line/count of changed hunks, not source text or a new allowed hash list. If the integrated chain cannot construct, report a failure rather than silently accepting current live. No automatic rebase/whitelist. Unit controls must cover byte equality, newline-only drift, added lines, changed content, mismatched file sets, non-text, immutability. A CI workflow on exact branch should run stdlib tests, actual current-source diagnostic, privacy/diff, and close raw hashes.

**Gates:** Age0 RECORD_ONLY, STEP2 UTILITY_FAIL, B3 NO_PROMOTION, Body-JEPA UNAVAILABLE, World-JEPA SHADOW, jepa_weight0, whole V13 incomplete; historical full-suite RED unchanged. Exact next step: compare source hashes, then separately preregister a reviewed compatibility candidate with counterexamples; never modify frozen cohort.

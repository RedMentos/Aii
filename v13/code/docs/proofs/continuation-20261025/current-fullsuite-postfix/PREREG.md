# Exact current-chain full suite after three reviewed packages — prereg (2026-10-25)

Base: verified PR254 head `fca5cf1b59f81ea955e1c2237dd0369c3eec07d6`. Own only unique workflow and this proof directory; **no production or historical test edits**. Serialized CI concurrency group `v13-native-c3-run131-serialized` (no overlapping heavy native/model jobs). Check latest owners before launch.

Changes since Run221:
- PR252 WP-T8 production WorldModel EventEnvelope source revalidation, 28 focused PASS, independent actual Runtime Run218 PASS.
- PR253 historical Age test now respects Run200 non-competence regression safety, 14 focused PASS.
- PR254 historical LP3 orphan test now respects Run21 no unsafe post-reap PGID signal, 41 synthetic PASS.

Predeclared expected classification (not a claim): Run221 had 2646 tests, 2 FAIL and 36 ERROR from historical native-firing candidate source mismatch. The two FAIL should be resolved, while 36 ERROR may remain; additional regressions are possible. **Never mask failures or treat partial PASS as full-suite PASS.** Preserve complete raw log, true exit code, exact head, prerequisite hashes, and test counts. No changes to registered model/seed cohorts, STEP2/B3/Body-JEPA/jepa_weight or safety gates.

CI uses Run221's exact pinned source/fixture staging, read-only Run147 artifact, isolated CPU dependencies and official privacy scanner; any unavailable prerequisite is a separate explicit failure. Do not infer current native readiness from earlier scratch.

Next if 36 errors persist: independently inspect baseline manifests and `integrated_candidates.overlay`, design source-bound candidate rebase without mutating frozen cohorts or live runtime; preserve historical failed attempts.

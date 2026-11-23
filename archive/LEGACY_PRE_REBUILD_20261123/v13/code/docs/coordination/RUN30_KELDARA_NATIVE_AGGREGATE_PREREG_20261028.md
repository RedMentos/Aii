# Run30 independent native Keldara CQ evidence aggregate audit — prereg (2026-10-28)

**Parent:** Run26 native-only review branch exact `03c664c6a70eebe943ec6a0384a24814ca59c0c5`, Actions `40715223545` SUCCESS. This is a separate read-only reviewer branch; no change to the Run26 owner, pinned Run15/Run16 sources, native cohort, model/runner artifacts, Runtime, Store, or main. Original Run26 workflow raw ZIP remains in the GitHub Actions artifact, not copied to this public repository.

**Question:** In the first real Linux-native Keldara/CQ/seed-20261114 one-fixture diagnostic, does `both_exact` improve on `b1_only` and which of the 12 fixed output fields fail consistently across seven variants? A structural native PASS must not be mistaken for the canonical STEP2 utility PASS.

**Verification:** Read original raw Actions ZIP privately; verify ZIP CRC and its SHA256SUMS, HEAD SHA, receipt/report raw SHA, seven per-row canonical SHA hashes, exact variants and source/model/runner identity, negative gate flags. Produce *only* aggregate field masks, utilities, and the both-minus-B1 difference. No raw source/user text or model completions in public GitHub. A tiny stdlib read-only script plus synthetic unit tests must reject a modified hash, missing/duplicate variants, promoted gates and inconsistent field score. Preserve any RED attempt and report the original raw ZIP SHA256. This analysis is observational, not a new native inference run.

**Next after verified aggregate:** Design a fresh preregistered consumer ablation for the four shared failures (project normalization, remaining budget calculation, final action), with source-bound deterministic control, native C3 output unchanged, disjoint heldout fixture(s), and exact F5 permission separation. Do not retroactively repair or rescore the frozen Run26 original evidence.

**Gates:** Age0 RECORD_ONLY; STEP2 UTILITY_FAIL; B3 L1 FAIL; Body-JEPA UNAVAILABLE; LP3 FAIL; jepa_weight=0; Redmi unmeasured; whole V13 incomplete. Remaining platform budget UNKNOWN.

# Run11W prereg — independent C2 route/Body regret audit (2026-10-30)

Review-only child of Run11V PR #1251 at source head `b8c225d122b970ae199ea36c6d712e9fa8d039f5`. This is **read-only analysis** of frozen model-generated raw, not training or routing authority. Do not change Run11R seed163 or Run11V seed181 models, source, scoring, results, or acceptance gates.

Inputs must be explicit SHA256/HEAD-pinned original ZIPs, with CRC, complete SHA256SUMS, safe archive paths, 24 raw rows and preclose witnesses, exact report/raw identity, and negative gates verified before any comparison. Run11R original native Actions 41035932580 artifact 12967698710 SHA256 `47493d719ac1d6dedcb0142106b29b96817c0d4a211a6a2219879dec93cc8c5e`, HEAD `3d76c8e28735cfef4d40c290baad4556b61e04a7`. Its original primary strict score is 0/48; for route comparison use the already-frozen **secondary** contradiction-veto `score_pair` (12/48), not a rescore. Run11V fresh seed181 native Actions 41039528340, HEAD `6ba8986202febfe0faa813e8c1589ca85acac939`, original ZIP SHA **UNKNOWN until terminal**. Its preregistered **primary** is the same frozen `score_pair`. If Run11V native fails, retain RED and do not infer comparative completion.

For each of four fixtures in each cohort, compute only descriptive paired-arm deltas from stored scores:
- best observed single-organ score = max(A_C3_ONLY, B_B1_ONLY, C_B2_ONLY);
- D distinct-both minus best single; D minus E shared-dual;
- F native-auto minus best single and minus A C3-only;
- F native C2 invocation/selected flags, actual route and final runner role.
Record exact arm order and per-fixture scores; never infer causal improvement from a 4-fixture nonrandomized/stochastic comparison. If any row invalid, report structural RED and withhold full-cohort deltas, preserving every raw error. Do not silently count absent evidence as a native success.

Implement stdlib-only audit, adversarial ZIP/row/hash/score/route tests and separate software CI. A successful source-only audit is not a new native run. Preserve original failed attempts, no private raw publication, private Library backup, source/model/provenance pins. Negative gates Age0 RECORD_ONLY, STEP2 UTILITY_FAIL, B3 NO_PROMOTION, Body-JEPA UNAVAILABLE, jepa_weight0, Redmi UNMEASURED, whole V13 incomplete. Owner GPT-6 Run11W; new source/tests/workflow/scoped evidence only. Next: implement, test against synthetic and exact original seed163 ZIP, then add seed181 original only after terminal SHA and independent raw verification.

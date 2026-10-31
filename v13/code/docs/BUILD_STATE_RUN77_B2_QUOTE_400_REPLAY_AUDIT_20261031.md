# Run77 B2 400-char quote pointer diagnostic — verified replay evidence (2026-10-31)

**Owner:** GPT-6 independent PR #1439, parent PR #1438 exact `8da75d9396760c7907726d71d783c236527cefa7`. Initial prereg `9fb86e8bca5fded6db63db03d8e11733121cfbd4`, initial 200-char software preflight Actions `41188265973` **19/19 GREEN**, original ZIP SHA256 `eb18bca18c274a1a1190d0af6392c49b6b5321d0f0501248ba46fd5209c9b711` retained and privately byte-backed. After inspecting frozen replay, explicit 400-char compatibility addendum `0110d64119c4b5e1584ce3fdde93e92e646bf53c` was remotely verified **before** modifying code.

## Corrected diagnostic software
The frozen Run52 `OVERRIDES['offer_quote_context_chars']=400` is inherited unchanged by Run77; the first diagnostic's cap 200 would falsely reject all six actual B2 current offers. Corrected *diagnostic only* to cap 400, added positive width400 and negative width401/bool/negative/string tests. Original frozen Run77 driver/verifier, fixture, model/runner/seed, scientific scorer and report unchanged.

GitHub Actions `41188485907` exact tested HEAD `5568fae518b584b43bb5546e0474fb229ea018e5`: terminal **SUCCESS**, **20/20** tests, all VENV/DEPS/TEST/COMPILE/PRIVACY/DIFF exits 0, privacy CLEAN. Original ZIP artifact ID `13037184227`, size 2,752 bytes, independently downloaded SHA256 **`4e4126defa8e009bf83428c1fc965bb078b11e321a1b3656d2de0186e4ee1d59`**, CRC PASS, 13/13 SHA256SUMS PASS, zero unhashed members. Private Library `/V13-Checkpoints/2026-10-31/Run77-B2-Quote-Review/CORRECTED_400_SOFTWARE_41188485907_SHA4E4126DE.zip` rematerialized and `cmp BYTE_IDENTICAL`.

## Separate independent offline reparse of **engineering replay** (not original Run77 native)
Independently re-downloaded existing frozen Run77 forensic compact artifact ID `13037561711` (Actions `41187084497`), ZIP SHA256 **`62ebd85d4c3defb40c15c03148d24aea3017687217f2299db561ac17ceba0e5c`**, CRC PASS, 55/55 inner SHA256SUMS PASS. **Two SIZE receipts are unsealed**; retain evidence-packaging RED. The original 17.5GB Run77 native artifact ID `13036187463` is **not** independently downloaded/verified.

Independent stdlib-only local auditor (separate from repository diagnostic) reconstructed frozen six prior/current texts and verified SHA256, source_id, char spans, offered quotes and exact `Cognition.quote_span` bounded pointer semantics. Result on replay:
- **5/6** B2 WITH_PRIOR projects have at least one source-bound prior quote pointer (Alder/Birch/Cedar/Dune/Fir; Elm has no prior evidence ref).
- **5 prior** refs and **3 current** refs pass source/quote pointer checks; **0 invalid**. All eight were **POINTER**, not exact full-source-quote equality.
- Frozen Run77 independent verifier remains **RED** (it requires entire full-source span to equal a short quote). This explains the replay's predicate mismatch without modifying or waiving that verifier.
- **B1 and B2 strict semantic utility remain 0/6 WITH_PRIOR and 0/6 CURRENT_ONLY** on the replay; `B1B2_CONTEXT_UTILITY_SCIENTIFIC_RED` unchanged. Quote transport is not reasoning or a utility gate.

Offline auditor SHA256 `fa9dd9af4e8c519055c3eafa854c7704001015a02557156ef449f0583422f55b`, derived JSON SHA256 `8e89b6c6ad62df0b50de9ece2b836c41f76cf531ddf479729a4dfc4c0290ceb3`. Both privately uploaded under `/V13-Checkpoints/2026-10-31/Run77-B2-Quote-Review/` and re-materialized `cmp BYTE_IDENTICAL`. No original raw overwritten or public raw uploaded.

**Scope/negative gates:** software diagnostic + separately observed Linux-native engineering replay; not a new scientific cohort, not original 17.5GB native verification, not Redmi. Age0 RECORD_ONLY, STEP2 UTILITY_FAIL, B3 NO_PROMOTION, Body-JEPA UNAVAILABLE, World-JEPA SHADOW, jepa_weight 0, Run70 C3 source-only 3/6 RED, full suite 4 FAIL/66 ERROR/28 SKIP, whole V13 incomplete.

**Next command:** independent review of quote provenance logic and original packet contract; preregister **new disjoint** B1/B2 semantic utility experiment if scientifically justified, rather than retuning frozen seed797; separately review Run80 C3 QueryPacket/retained-state post-render guard. **Current owner:** GPT-6 on isolated PR #1439; no other branch overwritten. **Remaining platform budget:** UNKNOWN. **Stop reason:** none at checkpoint; continue other package.

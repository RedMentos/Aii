# C3 scoped active correction integrity veto — verified software checkpoint (2026-10-28)

Review-only child of #892 `6b4d99822e69ded08ddca3d9c9f4057fa09a351e`. Preregistration `7515aa6b73e417601d318e296bb069e1ad25403d` predates source changes. Exact CI head `f5f7b0b03814fe7f1364ae8962b8c510694a506f`.

**Exact-source Linux software GREEN**, Actions `40669399028`, artifact `12808131809`. Independently downloaded original ZIP SHA256 `0e1d66068e4d08b0d9cb10109e19d52e3bf2670002de185e6e42420973a0ba5f`, 7,179 bytes, CRC clean, **16/16** internal SHA256 manifest entries, **7/7** stage exit files zero. Pinned frozen runtime `68e7ed1352800174972558f1e0b0683a42c8689a`, runners `efda7aa1aa5729e974d0d641870d4da05d21c961`, catalog `7af05962af41d0bc3f7dd18ef01d4eba55eabf99`, source consumer `0edb409e5ee6674e22539713874e9a038f9cba24`, new recall test `bef8f256ca81b3a88c496ae0b106d0a270c1fab7` matched. **35 focused tests OK; 2304 full tests OK (1 skipped)**, compile0, privacy CLEAN, diff0.

Changed behavior: if any active exact-key same-project correction is unreadable or its F1/F5 lineage fails, `recall_and_admit` now deterministically returns `CLARIFY / UNVERIFIABLE_SCOPED_CORRECTION` instead of ignoring the competing row. Tests cover corrupted competing blob and mocked F1/F5 failure while a valid first source remains. This is software evidence, not native inference.

Private persistent backup: ChatGPT Library `/V13/RawEvidence/V13_C3_SCOPED_UNVERIFIABLE_SOFTWARE_40669399028_RAW.zip`. Library readback byte-exact, SHA256 identical. No public Drive backup.

**Negative gates unchanged:** No changed-source native run, no normal Runtime._turn integration, no Redmi measurement, no original Stage11/STEP2/B3/Body-JEPA/LP3/Age promotion. Exact-key scan remains bounded to supported key grammar; semantic alias conflict proof remains open.

Next: independent source review and compatibility integration with #893/#895 operator CLI without rewriting frozen runtime or claiming merged production.
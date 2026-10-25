# Run365 RED — confirmed before production change

- Parent source: `assistant/run364-plain-ui-cursor-20261025` @ `4616bb0618b7ff64969df6f1af369da723f5da3e`.
- Preregistration commit: `c10c382860c319ddfa8a55011403f7c93aab8205`; test commit: `f9f1265d4a355d3e854385c9ff236ca9d47781f3`; CI commit/actual checkout: `b3dc77da2a3d87de7d20d2ddaf19e0f7c0ce6a41`.
- Actions run: `40231388826`, job `121283681966`, completed FAILURE as expected.
- Exact source SHA256: `v13/code/v13/organ.py` = `5b4cfef7716b5ab3182b769278fdfc80320d5213d0cfca6cfc6a18d88b8d56b2`.
- Test result: **13 run, 4 expected failures**, 9 inherited `test_organ` PASS. Failures: role traversal, wildcard snapshot ID, hash-consistent role mismatch, symlinked root. The four failures were assertion failures (guard absent), not fixture errors.
- Privacy scan: `CLEAN`.
- Raw Actions artifact ID: `12613721197`, name `V13-Run365-OrganPath-Raw-caa18edec907b4f5cb20971bfec8472d484a5927`, GitHub reported digest `sha256:b090f3a75a81dd5bdf6f95088740ec0e47fe4d48be645f5c7d3893bcbf442bd4`. ZIP has not been independently downloaded/hash-verified in this environment; do not imply otherwise.
- Evidence level: source/SQLite GitHub Actions; no native model, Redmi, STEP2, B3 or learning claim.
- Next: implement minimal validation of existing model roles and generated snapshot IDs, bind manifest identity to its location, reject escaping symlinks, rerun exact-head Actions; then independent review and next blueprint package.

# Run98 preregistration — packaged phone source with bounded installer smoke (2026-10-31)

Owner GPT-6 Auto11, review-only child of Run97 PR #1463 exact parent `6af289cde1e97c9e6bfafd8df486c58670db1d03`. Run97 source smoke Linux Actions 41204425539 GREEN, 18/18 real model-free smoke + 5/5 contract; original ZIP SHA256 `6706b267ecf67bae52f2a9f2c70ea0fb6c97bfd3843b1e7a403ce8d8a84ae903` privately byte-backed. No Redmi evidence.

## Fixed plan before execution
- Use unchanged `scripts/package_source.py` blob `06167e0bcb82b36cb08841cd31b9618c4ba0926e` with `--phone-install` to pack a new **Run98** ZIP; never replace Run95.
- Verify exact source blob pins for package tool, source archive verifier, `STARTEN.sh`, Canon and new bounded `setup.sh` / `install_selftest.py`. Two independent packages must be byte-identical.
- Check ZIP CRC, full WORKSPACE_FILES.json SHA256 manifest, file inventory, no models/SQLite/secrets, required scripts/test/Canon, and extracted file SHA256. Run **actual extracted** `scripts/install_selftest.py` (18 cases) and `tests/test_install_selftest.py` (5 contracts) in fresh Linux minimal-deps venv. Verify extracted bytes again after tests, shell syntax, compile, privacy/diff; preserve all raw receipts and SHA256SUMS.
- Do **not** execute `setup.sh` itself in CI (it downloads/builds native dependencies); do not assert Android install, model/Needle execution, learning or scientific utility.
- Publish exact original ZIP artifact, SHA256 and private backup only after independent audit. If RED, preserve it and fix in a separate child.

Gates remain Age0 RECORD_ONLY; STEP2 UTILITY_FAIL; B3 NO_PROMOTION; Body-JEPA UNAVAILABLE; World-JEPA SHADOW; jepa_weight=0; Redmi UNMEASURED; whole system INCOMPLETE. Draft/no merge, no frozen source/registered cohort changes.

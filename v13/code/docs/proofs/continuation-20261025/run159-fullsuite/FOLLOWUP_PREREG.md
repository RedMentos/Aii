# Run159 full-suite prerequisite correction registration

Before rerunning, replace the historical Run16 LP3 helper with reconstructed exact Run21 source, using repository's Run20 code-only tar.xz.base64 plus Run21 post-reap patch. Verify SHA-256 of reconstructed `v13/code/scripts/lp3_serial_cohort.py` equals `05e5bf300f582a03efeaae0133c8e20bf60948a2fa4e05a4867924ac4dc4b831`. This is test fixture staging in temp only; no Runtime or source changes. Preserve original Run16 suite failure.

Stage immutable Run147 native artifact 12585363362 (ZIP SHA-256 `ddd60c897e1bdc634a40179b67e434097bb1e1999a6a2141372f6272682b9676`) into temp and set `RUN147_ARTIFACT` env. Do not rerun native model. Leave optional `/root/native/restore` PermissionError visible until independently fixed in test code; do not chmod /root or blanket skip tests.

Next suite still must run all discovered tests, preserve raw log, enforce true exit. If LP3 orphan failure persists with Run21, retain it as a real candidate safety failure.

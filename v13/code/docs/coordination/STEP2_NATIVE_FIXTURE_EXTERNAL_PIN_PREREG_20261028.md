# Native fixture external pin enforcement — preregistration, 2026-10-28

The integrated read-only scorer currently accepts `load(root, manifest, externally_pinned_manifest_sha, fixture_ids)` with no external fixture SHA. For native-labelled bundles this lets a self-consistent *different* fixture corpus be sealed and analyzed without checking against the registered canonical corpus. The CLI passes the expected fixture hash, but API callers can omit it.

Narrow next package: require a valid external expected fixture SHA256 for `LINUX_NATIVE` and `REDMI_NATIVE` summaries. Preserve the optional argument for `SOFTWARE_SYNTHETIC` tests, and reject any mismatch before diagnostic analysis. No new cohort, no new model, no inference, no Runtime/Canon edit.

Test before code: complete native-shaped mocked 12-run sealed bundle with manifest pin but **without** expected fixture pin must be rejected; the same bundle with correct fixture pin remains diagnostic-only. Preserve RED evidence and GREEN CI. The source of the expected fixture hash must be the frozen registered corpus, not read from the untrusted manifest itself.

Gate status unchanged: STEP2 UTILITY_FAIL; B3 L1 FAIL; Body-JEPA UNAVAILABLE; jepa_weight=0; Age0 RECORD_ONLY.

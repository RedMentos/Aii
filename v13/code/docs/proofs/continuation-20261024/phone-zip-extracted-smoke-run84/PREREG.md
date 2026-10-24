# Run84 prereg — extract and smoke-test the actual phone source ZIP

2026-10-24. Base Run83 PR116 `739660bc2c84d1c9f32cbb63f2f0c82558ce44ec`.
Owner only `.github/workflows/v13-focused-proof.yml` extracted-source test step and new Run84 evidence. No production/model/canon modifications or other active-owner files.

Run83 generated a verified 12.5 MB model-free phone source ZIP, but ZIP contents were not independently executed after extraction. Add a fail-closed Linux CI step **before upload**: unzip into a fresh temporary directory; compile extracted v13/scripts/tests; run `tests.test_context_os`, `tests.test_jefoutcome`, `tests.test_history_lineage`, `tests.test_age`, `tests.test_standstill`, and `tests.test_package_source` from the extracted tree; instantiate an isolated Runtime, create/read a user source, close/reopen Runtime and re-read the exact SourceRef; do not submit a model turn or download weights.

All tests are model-free Python/SQLite with the existing isolated pinned CI dependencies. A missing phone fixture or package-path defect is a real release failure to preserve, not a reason to skip tests. The ZIP must only be uploaded after the extracted smoke passes, preserving the original 377+ CI and privacy gates. Evidence type: actual Linux source ZIP extraction and SQLite/software tests, NOT Redmi or native model. All original STEP2/B3/Body-JEPA/age/approval gates unchanged.

# Five-way exact review source ZIP + extracted software smoke prereg (2026-10-27)

**Parent:** exact integrated review commit `9eae3cc175512382038cc5f55887e7a8dbc9797f` (draft PR #672), verified tree `9ff3f1e7cbe6fe3508ccb38e2265c614e0a8463a`. No source or registered model/cohort/seed changes. This branch adds only review CI and evidence.

**Problem:** A focused Linux merge test does not prove that the current AG5+World+Claude+PR667+PR669 source can be packaged into a self-contained, integrity-checked phone source ZIP and run its software operator tests after extraction. The existing pinned 2026-10-26 ZIP review references older exact runtime blobs and cannot be reinterpreted as a current integrated test.

**Protocol:** Isolated Linux Python venv, no model downloads/autostart, run `package_source.py --phone-install`, independent `verify_phone_zip_current_run268.py` (member/source hashes, path safety, no private/model payload), `tests.test_package_source`, extract verified archive, `bash -n` launchers, run `tests.test_phone_halt tests.test_modules_gate tests.test_guard2` on extracted source. Preserve raw logs/exits even on failure, ZIP SHA, privacy scan. Any missing required fixture, failed extracted test, or unexpected source change is RED; no synthetic success substitution.

**Evidence scope:** Linux software source packaging and extracted operator smoke only, **not Redmi install**, actual models, native inference, B3/STEP2/Body-JEPA proof or age promotion. Existing full suite 5 FAIL/73 ERROR historical RED. Next owner independent phone-package reviewer. Workflow `.github/workflows/fiveway-phone-package-review.yml`.

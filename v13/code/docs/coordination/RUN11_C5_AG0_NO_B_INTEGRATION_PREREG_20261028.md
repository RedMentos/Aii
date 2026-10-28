# Run11 C5 + AG0 no-B manifest guard integration prereg — 2026-10-28

Owner: GPT-6 independent review integration, based on Codex #845 source `82b58f270c7770d88c64a55c648561e2b5d93c62` (C5 owner branch untouched) and GPT-6 #846 `7ceaecf55edaee0e0544da3351d6ae112b9acb12` (AG0 owner branch untouched). Parent #844 native RED 40632157217 is retained. This is not main.

Import **exact** Git blobs only for disjoint files from #846:
- `v13/code/v13/bodies.py` `82fb81c8a98c51ca1c339737184e2fda8ab6a692`
- `v13/code/tests/test_bodies.py` `e71f6f7a0e0f5a5016d81f0ba17c4bb793e1f6e4`
- `v13/code/docs/coordination/RUN11_JEF_STALE_SLOT_PREREG_20261028.md` `c2547acefaac14ac2146a0b53a5ec1617fabda20`

Keep #845 C5 `v13/code/v13/focal.py` blob `ed0e88842b723b4aaffda46878b2d66d8ed9d9b7`, `v13/code/v13/runtime.py` blob `5c086af98e1b5fe033a0510b2463909e3b0cca38`, and `tests/test_c5_manifest_availability_20261028.py` blob `356ac40b28e111218e71ec8558488949806726b2` unchanged. Check exact SHA of every import, run combined focused C5+AG0+JEF/STEP12 tests, full software suite, privacy and diff, then only serial native Age0 JEF+STEP12 on a new review branch after both full suites GREEN and no competing native owner.

Original negative gates remain: STEP2 UTILITY_FAIL, B3 L1 FAIL, Body-JEPA UNAVAILABLE, LP3 heldout FAIL, jepa_weight=0, Age0 RECORD_ONLY. No new model artifacts, changed seeds or learning authority. Evidence levels Linux software / Linux native / Redmi distinct. Failed 40632157217 and 40632820503 remain RED; no whole-system claim.

Next command: inspect full software workflows 40632930791 (#845) and 40632990148 (#846); then import exact three blobs, run focused + full regression. Remaining platform budget UNKNOWN.

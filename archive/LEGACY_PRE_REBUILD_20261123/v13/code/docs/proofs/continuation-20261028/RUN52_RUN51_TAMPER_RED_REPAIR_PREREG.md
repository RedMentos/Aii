# Run52 — Run51 exact-head RED diagnosis and regression repair (2026-10-28)

Owner: GPT-6 scheduled continuation. Review-only child of Run51 PR #959 exact head `686480a88f3fe42a9c7ded5761bcc3163a854a63`; do not edit owner branch or production main. This is a software-only source/test correction, not a new cohort or model experiment.

## Original preserved RED
GitHub Actions run `40753922127` (PR merge SHA `25cfe35c63e4d2e3bd280827f0fef4a40ccd59f5`), artifact `12845900201`, SHA256 `1e18576fccdc35f87ae19f064372a014feaf2e550bd09cf50104541779d15837`. Focused: 22 tests, 1 ERROR. `test_declared_synthetic_but_changed_array_bytes_refused_before_fit` mutates only train X[0,0]; this violates the structural X2[:,:4] == X[:,:4] contract, so the source correctly rejects with `RUN51_INVALID_ACTION_OUTCOME_EMBEDDING` before reaching the expected digest check. Original failure remains evidence and must not be overwritten.

## Preregistered fix
Change only the tamper test so X and X2 state columns are changed together, retaining structural validity but changing the preregistered array bytes. It must then fail closed with `RUN51_UNREGISTERED_SYNTHETIC_ARRAYS` before any fit. Add a separate explicit malformed-embedding test proving the earlier structural refusal still happens. Preserve Run50 fixture and source/seed/model hashes. Do not weaken `_arrays` checks to satisfy the test.

Use a new isolated review branch, dedicated GitHub Actions software-only workflow on push (pinned NumPy, focused/full tests, compile, frozen-source check, privacy/diff and raw hashed logs). The original RED artifact remains intact. No native/Redmi claims. Negative gates unchanged: Age0 RECORD_ONLY; STEP2 UTILITY_FAIL; B3 L1 FAIL; Body-JEPA UNAVAILABLE; LP3 FAIL; jepa_weight=0; Redmi UNMEASURED; full V13 incomplete.

## Acceptance
Exact-head focused tests green, full Linux software suite green, frozen Run51 source unchanged, raw artifacts verified before GREEN claim. If blocked, record exact failure and continue independent work. Next package after this fix: assess action permutation provenance and explicit baseline comparisons without promoting SHADOW utility.

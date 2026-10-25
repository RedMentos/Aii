# Run367 — exact current-chain complete Python suite after Run365/366 (preregistered)

Parent: `codex/ag12-finite-confidence-20261025` @ `91416e63c1b9813e9aa3e140e85bd256092adcdc` (review branch, not main). Run365 and Run366 isolated/focused suites are GREEN, but the **complete** current-source Python suite has historical REDs. Do not infer overall PASS from focused tests.

Owned files: `.github/workflows/run367-current-fullsuite.yml`, `v13/code/docs/proofs/continuation-20261025/run367-current-fullsuite/**`. No runtime/test/model/seed/hash modifications in this measurement package.

Precommitted protocol: GitHub ubuntu-24.04 exact PR head checkout, immutable Canon SHA256 `3423906b01b24443fcef733fb5c7ef47296963df63e603d8f843c99d544877ee`; isolated numpy 2.3.5, prompt-toolkit 3.0.52, CPU-only torch 2.9.1; no model downloads; restore the **original** Run147 historical native ZIP artifact ID `12585363362` with SHA256 `ddd60c897e1bdc634a40179b67e434097bb1e1999a6a2141372f6272682b9676` read-only; compileall, full unittest discovery with timeout, official privacy scan. Preserve all failures and errors in raw ZIP with SHA256 manifest. Run under existing `v13-native-c3-run131-serialized` concurrency group to respect heavy-job owners.

Expected: complete suite may remain RED due historical frozen-source/fixture conflicts (Run355 3094 tests: 3 failures, 63 errors, 14 skips); **do not retune or hide**. Classify exact failure names and choose a distinct authorized repair package, preserving original negative gates. No native training, Redmi, STEP2/B3/JEPA/whole-system promotion.

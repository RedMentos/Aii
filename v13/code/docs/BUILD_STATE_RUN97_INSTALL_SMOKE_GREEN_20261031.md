# Run97 bounded first-install smoke GREEN — 2026-10-31

Owner GPT-6 Auto11; review-only branch `assistant/v13-run97-installer-smoke-20261031-auto11` child of Run96 PR #1462 exact parent `2f9ad42c1c448c4f08f2319e03770de996816626`. Preregistration `6c2d07edbe0c0d4a4dbe0268dcf218e3f5285ca9` preceded code and CI. **No production merge.**

## Concrete change
- Added `scripts/install_selftest.py`: 18 exact real model-free age, Runtime/Store durable queue, standstill, SourceHandoff and admission tests. Fixed allowlist; refuses empty/renamed/import-error/substituted tests; separate process, maximum 120s, kills worker process group on timeout; no model downloads or native inference.
- Changed one line in `setup.sh`: installer invokes this bounded smoke instead of the unfiltered 4907-test `v13 selftest`. Full developer `v13 selftest` implementation in `v13/__main__.py` remains byte-identical at blob `9248e46e199a4227c296d538e6a2ef969e8e10cb`. Original `v13 probe` after smoke remains.
- Added 5 contract/negative tests and minimal-deps Linux Actions workflow. No frozen Runtime/Store, model, seed, cohort, Canon, learning authority or scientific-gate changes.

## Original evidence audit
Actions **41204425539**, exact tested HEAD `75b1179bf19573749f5fe46dbc312b713f98614e`, terminal SUCCESS. Fresh Linux venv with `numpy==2.2.6` and `prompt-toolkit==3.0.52`; **18/18 smoke PASS in 1.361s**, **5/5 contract PASS in 0.267s**. All VENV/DEPS/SHELL/COMPILE/CONTRACT/SMOKE/RESULT/PRIVACY/DIFF exit0; privacy CLEAN. Timeout and missing/duplicate test controls explicitly refuse; negative-control messages in passing contract log are expected.

Original GitHub artifact **13044475312**, ZIP SHA256 `6706b267ecf67bae52f2a9f2c70ea0fb6c97bfd3843b1e7a403ce8d8a84ae903`, 4883 bytes, CRC PASS, **21/21** SHA256SUMS entries PASS. Private Library original ZIP `/V13-Checkpoints/2026-10-31/Run97-Installer-Smoke/RUN97_ORIGINAL_SMOKE_41204425539_SHA6706B267.zip` re-materialized and byte-identical. Original Run96 unfiltered selftest timeout exit124 and fully provisioned Run94 4907 tests/28 skipped are retained without reinterpretation.

## Evidence limits and next exact command
This is **Linux model-free test execution only**. It does not execute `setup.sh` bootstrap (which downloads/builds native models), does not install on Redmi, and does not prove Termux or full suite portability. Next package: create a new review child from this verified HEAD, then package a **new** source ZIP using `python v13/code/scripts/package_source.py --root v13/code --out "$RUNNER_TEMP/V13-Redmi-Install-Run98.zip" --phone-install`; verify CRC, WORKSPACE_FILES.json, exact SHA256 manifest, extracted 18-test bounded smoke and `setup.sh` invocation under minimal deps. Do not overwrite original Run95 ZIP. After independent raw audit, user/device operator can run actual Termux setup; do not claim phone success before evidence.

Age0 RECORD_ONLY; STEP2 UTILITY_FAIL; B3 NO_PROMOTION; Body-JEPA UNAVAILABLE; World-JEPA SHADOW; jepa_weight=0; Redmi UNMEASURED; whole V13 INCOMPLETE. Stop at this checkpoint is **not** project completion; proceed to next authorized package.

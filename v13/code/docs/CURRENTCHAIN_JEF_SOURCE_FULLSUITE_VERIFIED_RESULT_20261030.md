# Current-chain full unfiltered JEF source software regression — verified 2026-10-30

Exact tested HEAD `81ca76bc6637a5f543f364cf7464f3a241ce0bf3`, parent `cee5af7064ec81f6eff27eb00b20a3f3aa7596f7` (PRs #1192/#1193 merged in review only). Preregistered `3a24ce7126d733af22b16a2f802b1c067ca5b393`, Canon blob `218464b12a2d27d92524c751922fa8e1c3fb0ea7`.

Actions run **40987907341**, Ubuntu 24.04, fresh isolated venv. Verified `torch==2.5.1+cpu`, `transformers==4.44.2`, `peft==0.13.2`, `numpy==2.2.6`; all dependency installs/imports, pip check, compile, privacy, diff **exit0**.

**Entire unfiltered software suite:** `Ran 3404 tests in 352.172s`, **2 errors**, **11 skipped**, no other failures. Both errors are the preexisting frozen historical source-pin mismatch: `test_run34_c3_native_quote_intervention_pilot.Run34NativePilotPreflight.test_pinned_source_model_runner_and_negative_gates` and `test_run37_c3_rule_use_native_pilot.Run37NativePreflight.test_pinned_source_model_runner_and_negative_gates` each raised `ValueError: native_source_or_catalog_changed`. Do **not** edit/waive those historical preregistrations or call the suite green. Current-chain JEF report-source fix introduced no additional failures in this unfiltered run. The later JEF self-label source fix on PR #1194 was not part of this exact tested HEAD and requires its own combined full-suite run.

Original raw ZIP artifact **12947204544**, SHA256 `9c8a75ca343324e6df20a8a48a4a1c6d88b37570f052d2838ecbf8407e997f49`, size 9449 bytes, CRC clean, **30/30** inner hashes verified, private byte-identical backup `/V13-Checkpoints/2026-10-30/Run11-CurrentChain-JEF-FullSuite/RAW_RED_40987907341_SHA256_9c8a75ca343324e6.zip`. All original failures retained. Software/synthetic evidence only, no native model inference, no Redmi, no STEP2/B3/Body-JEPA/JEPA/Age promotion.

Owner: V13 hourly automation, review branch. Exact next: full unfiltered suite on the later integrated JEF self-label source fix (PR #1194) with the same pinned environment; retain historical two RED. Separately run paired STEP2 semantic utility with a fixed no-body control; the current Linux-native vertical structural PASS is not a semantic result.
